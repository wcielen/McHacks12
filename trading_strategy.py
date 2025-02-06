import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Position:
    entry_price: float
    size: int
    entry_time: pd.Timestamp
    stop_loss: float
    take_profit: float
    stock: str  # Added stock identifier

@dataclass
class StockRelationship:
    stock_a: str
    stock_b: str
    correlation: float
    lead_lag_effect: float  # Positive means stock_a leads, negative means stock_b leads
    strength: float  # Relationship strength score (0-1)

class TradingStrategy:
    def __init__(self):
        self.RISK_PER_TRADE = 0.02  # 2% risk per trade
        self.MAX_POSITIONS = 3  # Maximum concurrent positions
        self.MIN_RR_RATIO = 2.0  # Minimum risk-reward ratio
        self.CORRELATION_THRESHOLD = 0.7  # Minimum correlation to consider relationship
        self.RELATIONSHIP_MEMORY = 100  # Number of periods to consider for relationship analysis
        self.positions: Dict[str, Position] = {}
        self.stock_relationships: Dict[str, List[StockRelationship]] = defaultdict(list)
        self.stock_data_cache: Dict[str, pd.DataFrame] = {}

    def update_stock_cache(self, stock: str, market_data: pd.DataFrame) -> None:
        """Update the cache with latest market data for a stock."""
        self.stock_data_cache[stock] = market_data.copy()

    def analyze_stock_relationships(self, all_market_data: Dict[str, pd.DataFrame]) -> None:
        """Analyze relationships between all pairs of stocks."""
        stocks = list(all_market_data.keys())
        
        for i, stock_a in enumerate(stocks):
            for stock_b in stocks[i+1:]:
                df_a = all_market_data[stock_a]
                df_b = all_market_data[stock_b]

                # Ensure timestamps align
                common_times = pd.Index(
                    sorted(set(df_a.index).intersection(set(df_b.index)))
                )
                if len(common_times) < self.RELATIONSHIP_MEMORY:
                    continue

                aligned_a = df_a.loc[common_times]['mid_price']
                aligned_b = df_b.loc[common_times]['mid_price']

                # Calculate correlation
                correlation = aligned_a.corr(aligned_b)

                # Calculate lead-lag relationship using cross-correlation
                lead_lag = self._calculate_lead_lag(aligned_a, aligned_b)

                # Calculate relationship strength
                strength = self._calculate_relationship_strength(
                    aligned_a, aligned_b, correlation, lead_lag
                )

                if abs(correlation) >= self.CORRELATION_THRESHOLD:
                    relationship = StockRelationship(
                        stock_a=stock_a,
                        stock_b=stock_b,
                        correlation=correlation,
                        lead_lag_effect=lead_lag,
                        strength=strength
                    )
                    self.stock_relationships[stock_a].append(relationship)
                    self.stock_relationships[stock_b].append(relationship)

    def _calculate_lead_lag(self, series_a: pd.Series, series_b: pd.Series, 
                           max_lag: int = 10) -> float:
        """Calculate the lead-lag relationship between two price series."""
        correlations = [series_a.corr(series_b.shift(lag)) for lag in range(-max_lag, max_lag + 1)]
        max_corr_idx = np.argmax(np.abs(correlations))
        return max_corr_idx - max_lag  # Positive means series_a leads, negative means series_b leads

    def _calculate_relationship_strength(self, series_a: pd.Series, series_b: pd.Series,
                                      correlation: float, lead_lag: float) -> float:
        """Calculate the strength of the relationship between two stocks."""
        # Combine multiple factors for relationship strength
        volatility_ratio = min(series_a.std(), series_b.std()) / max(series_a.std(), series_b.std())
        trend_alignment = np.mean(np.sign(series_a.diff()) == np.sign(series_b.diff()))
        
        strength = (abs(correlation) * 0.4 +  # Correlation contribution
                   volatility_ratio * 0.3 +   # Volatility similarity contribution
                   trend_alignment * 0.3)     # Trend alignment contribution
        
        return min(1.0, max(0.0, strength))

    def calculate_signals(self, market_data: pd.DataFrame, stock: str) -> pd.DataFrame:
        """Calculate trading signals using multiple technical indicators and inter-stock relationships."""
        df = market_data.copy()

        # Basic indicators (from original implementation)
        df['mid_price'] = (df['bidPrice'] + df['askPrice']) / 2
        df['price_sma_20'] = df['mid_price'].rolling(window=20).mean()
        df['price_sma_50'] = df['mid_price'].rolling(window=50).mean()
        df['volume_ratio'] = df['bidVolume'] / df['askVolume']
        df['volume_sma'] = df['volume_ratio'].rolling(window=20).mean()
        df['atr'] = self._calculate_atr(df, period=14)
        df['bollinger_upper'], df['bollinger_lower'] = self._calculate_bollinger_bands(df, period=20)
        df['rsi'] = self._calculate_rsi(df, period=14)
        df['macd'], df['macd_signal'] = self._calculate_macd(df)
        df['book_imbalance'] = (df['bidVolume'] - df['askVolume']) / (df['bidVolume'] + df['askVolume'])
        df['imbalance_sma'] = df['book_imbalance'].rolling(window=10).mean()

        # Add inter-stock relationship signals
        df['related_stocks_signal'] = self._calculate_related_stocks_signal(df, stock)
        
        # Generate enhanced trading signals
        df['long_signal'] = self._generate_long_signals(df)
        df['short_signal'] = self._generate_short_signals(df)

        return df

    def _calculate_related_stocks_signal(self, df: pd.DataFrame, stock: str) -> pd.Series:
        """Calculate trading signal based on related stocks' movements."""
        if stock not in self.stock_relationships:
            return pd.Series(0, index=df.index)

        combined_signal = pd.Series(0, index=df.index)

        for relationship in self.stock_relationships[stock]:
            other_stock = relationship.stock_b if relationship.stock_a == stock else relationship.stock_a
            
            if other_stock not in self.stock_data_cache:
                continue

            other_df = self.stock_data_cache[other_stock]
            
            # Align timestamps
            common_times = df.index.intersection(other_df.index)
            if len(common_times) < 20:  # Minimum required for meaningful signal
                continue

            # Calculate other stock's recent movement
            other_returns = other_df['mid_price'].pct_change()
            
            # Apply lead-lag adjustment
            if relationship.lead_lag_effect > 0:
                other_returns = other_returns.shift(-int(relationship.lead_lag_effect))
            elif relationship.lead_lag_effect < 0:
                other_returns = other_returns.shift(int(abs(relationship.lead_lag_effect)))

            # Calculate signal contribution
            signal = other_returns * relationship.correlation * relationship.strength
            
            # Combine signals using relationship strength as weight
            combined_signal += signal * relationship.strength

        return combined_signal

    def _generate_long_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate long entry signals based on multiple conditions including inter-stock relationships."""
        traditional_signals = (
            # Original conditions
            (df['price_sma_20'] > df['price_sma_50']) &
            (df['mid_price'] > df['price_sma_20']) &
            (df['rsi'] > 40) & (df['rsi'] < 70) &
            (df['macd'] > df['macd_signal']) &
            (df['volume_ratio'] > df['volume_sma']) &
            (df['book_imbalance'] > 0.2) &
            (df['mid_price'] > df['bollinger_lower']) &
            (df['atr'] > df['atr'].rolling(100).mean())
        )

        # Incorporate related stocks signal
        relationship_signals = df['related_stocks_signal'] > 0.001  # Threshold for positive signal

        return traditional_signals & relationship_signals

    def _generate_short_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate short entry signals based on multiple conditions including inter-stock relationships."""
        traditional_signals = (
            # Original conditions
            (df['price_sma_20'] < df['price_sma_50']) &
            (df['mid_price'] < df['price_sma_20']) &
            (df['rsi'] < 60) & (df['rsi'] > 30) &
            (df['macd'] < df['macd_signal']) &
            (df['volume_ratio'] < df['volume_sma']) &
            (df['book_imbalance'] < -0.2) &
            (df['mid_price'] < df['bollinger_upper']) &
            (df['atr'] > df['atr'].rolling(100).mean())
        )

        # Incorporate related stocks signal
        relationship_signals = df['related_stocks_signal'] < -0.001  # Threshold for negative signal

        return traditional_signals & relationship_signals

    # Keep existing helper methods
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['askPrice']
        low = df['bidPrice']
        close = df['mid_price']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = df['mid_price'].rolling(window=period).mean()
        std = df['mid_price'].rolling(window=period).std()

        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)

        return upper_band, lower_band

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = df['mid_price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Calculate MACD and Signal line."""
        exp1 = df['mid_price'].ewm(span=12, adjust=False).mean()
        exp2 = df['mid_price'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()

        return macd, signal

    def calculate_position_size(self, price: float, stop_loss: float, portfolio_value: float) -> int:
        """Calculate position size based on risk management rules."""
        risk_amount = portfolio_value * self.RISK_PER_TRADE
        price_risk = abs(price - stop_loss)

        if price_risk == 0:
            return 0

        position_size = risk_amount / price_risk
        return int(position_size)

    def calculate_stop_loss(self, df: pd.DataFrame, index: int, is_long: bool) -> float:
        """Calculate stop loss level based on ATR and recent price action."""
        atr = df['atr'].iloc[index]
        price = df['mid_price'].iloc[index]

        if is_long:
            recent_low = df['bidPrice'].iloc[max(0, index - 20):index + 1].min()
            return min(price - 2 * atr, recent_low)
        else:
            recent_high = df['askPrice'].iloc[max(0, index - 20):index + 1].max()
            return max(price + 2 * atr, recent_high)

    def calculate_take_profit(self, entry_price: float, stop_loss: float, is_long: bool) -> float:
        """Calculate take profit level based on risk-reward ratio."""
        risk = abs(entry_price - stop_loss)
        if is_long:
            return entry_price + (risk * self.MIN_RR_RATIO)
        else:
            return entry_price - (risk * self.MIN_RR_RATIO)

    def update_positions(self, current_price: float, timestamp: pd.Timestamp) -> None:
        """Update positions and check for exits."""
        closed_positions = []

        for symbol, position in self.positions.items():
            # Check stop loss
            if position.size > 0:  # Long position
                if current_price <= position.stop_loss:
                    closed_positions.append(symbol)
                elif current_price >= position.take_profit:
                    closed_positions.append(symbol)
            else:  # Short position
                if current_price >= position.stop_loss:
                    closed_positions.append(symbol)
                elif current_price <= position.take_profit:
                    closed_positions.append(symbol)

        # Remove closed positions
        for symbol in closed_positions:
            del self.positions[symbol]

    def calculate_pnl(self, market_data: pd.DataFrame, stock: str) -> pd.DataFrame:
        """Calculate PnL based on trading signals and positions."""
        signals_df = self.calculate_signals(market_data, stock)
        portfolio_value = 1_000_000
        pnl_records = []

        for i in range(len(signals_df)):
            current_price = signals_df['mid_price'].iloc[i]
            timestamp = signals_df.index[i]

            # Update existing positions
            self.update_positions(current_price, timestamp)

            # Check for new entries
            if len(self.positions) < self.MAX_POSITIONS:
                if signals_df['long_signal'].iloc[i]:
                    stop_loss = self.calculate_stop_loss(signals_df, i, True)
                    size = self.calculate_position_size(current_price, stop_loss, portfolio_value)
                    take_profit = self.calculate_take_profit(current_price, stop_loss, True)

                    self.positions[f'long_{stock}_{timestamp}'] = Position(
                        entry_price=current_price,
                        size=size,
                        entry_time=timestamp,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        stock=stock
                    )

                elif signals_df['short_signal'].iloc[i]:
                    stop_loss = self.calculate_stop_loss(signals_df, i, False)
                    size = self.calculate_position_size(current_price, stop_loss, portfolio_value)
                    take_profit = self.calculate_take_profit(current_price, stop_loss, False)

                    self.positions[f'short_{stock}_{timestamp}'] = Position(
                        entry_price=current_price,
                        size=-size,  # Negative size for short positions
                        entry_time=timestamp,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        stock=stock
                    )

            # Calculate current PnL
            total_pnl = sum(
                position.size * (current_price - position.entry_price)
                for position in self.positions.values()
                if position.stock == stock  # Only consider positions for current stock
            )

            pnl_records.append({
                'timestamp': timestamp,
                'pnl': total_pnl,
                'pnl_percentage': (total_pnl / portfolio_value) * 100
            })

        return pd.DataFrame(pnl_records)


def calculate_trading_metrics(pnl_df: pd.DataFrame) -> Dict[str, float]:
    """Calculate trading performance metrics."""
    if pnl_df.empty:
        return {
            'total_return': 0.0,
            'return_percentage': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0
        }

    metrics = {
        'total_return': pnl_df['pnl'].iloc[-1],
        'return_percentage': pnl_df['pnl_percentage'].iloc[-1],
        'max_drawdown': calculate_max_drawdown(pnl_df['pnl']),
        'sharpe_ratio': calculate_sharpe_ratio(pnl_df['pnl_percentage']),
        'win_rate': calculate_win_rate(pnl_df['pnl'])
    }
    return metrics


def calculate_max_drawdown(pnl: pd.Series) -> float:
    """Calculate maximum drawdown."""
    if pnl.empty:
        return 0.0
    cumulative = pnl.cumsum()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    return abs(drawdown.min()) if not drawdown.empty else 0.0


def calculate_sharpe_ratio(returns: pd.Series) -> float:
    """Calculate Sharpe ratio."""
    if returns.empty:
        return 0.0
    returns_std = returns.std()
    if returns_std == 0:
        return 0
    return (returns.mean() / returns_std) * np.sqrt(252)  # Annualized


def calculate_win_rate(pnl: pd.Series) -> float:
    """Calculate win rate."""
    if pnl.empty:
        return 0.0
    trades = pnl.diff().dropna()
    winning_trades = (trades > 0).sum()
    total_trades = len(trades)
    return (winning_trades / total_trades * 100) if total_trades > 0 else 0.0