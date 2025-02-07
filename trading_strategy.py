import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class Position:
    entry_price: float
    size: int
    entry_time: pd.Timestamp
    stop_loss: float
    take_profit: float


class TradingStrategy:
    def __init__(self):
        self.RISK_PER_TRADE = 0.02  # 2% risk per trade
        self.MAX_POSITIONS = 3  # Maximum concurrent positions
        self.MIN_RR_RATIO = 2.0  # Minimum risk-reward ratio
        self.positions: Dict[str, Position] = {}

    def calculate_signals(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate trading signals using multiple technical indicators."""
        df = market_data.copy()

        # Price action indicators
        df['mid_price'] = (df['bidPrice'] + df['askPrice']) / 2
        df['price_sma_20'] = df['mid_price'].rolling(window=20).mean()
        df['price_sma_50'] = df['mid_price'].rolling(window=50).mean()

        # Volume analysis
        df['volume_ratio'] = df['bidVolume'] / df['askVolume']
        df['volume_sma'] = df['volume_ratio'].rolling(window=20).mean()

        # Volatility indicators
        df['atr'] = self._calculate_atr(df, period=14)
        df['bollinger_upper'], df['bollinger_lower'] = self._calculate_bollinger_bands(df, period=20)

        # Momentum indicators
        df['rsi'] = self._calculate_rsi(df, period=14)
        df['macd'], df['macd_signal'] = self._calculate_macd(df)

        # Order book imbalance
        df['book_imbalance'] = (df['bidVolume'] - df['askVolume']) / (df['bidVolume'] + df['askVolume'])
        df['imbalance_sma'] = df['book_imbalance'].rolling(window=10).mean()

        # Generate trading signals
        df['long_signal'] = self._generate_long_signals(df)
        df['short_signal'] = self._generate_short_signals(df)

        return df

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

    def _generate_long_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate long entry signals based on multiple conditions."""
        return (
            # Trend conditions
                (df['price_sma_20'] > df['price_sma_50']) &
                (df['mid_price'] > df['price_sma_20']) &

                # Momentum conditions
                (df['rsi'] > 40) & (df['rsi'] < 70) &
                (df['macd'] > df['macd_signal']) &

                # Volume conditions
                (df['volume_ratio'] > df['volume_sma']) &

                # Order book conditions
                (df['book_imbalance'] > 0.2) &

                # Volatility conditions
                (df['mid_price'] > df['bollinger_lower']) &
                (df['atr'] > df['atr'].rolling(100).mean())
        )

    def _generate_short_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate short entry signals based on multiple conditions."""
        return (
            # Trend conditions
                (df['price_sma_20'] < df['price_sma_50']) &
                (df['mid_price'] < df['price_sma_20']) &

                # Momentum conditions
                (df['rsi'] < 60) & (df['rsi'] > 30) &
                (df['macd'] < df['macd_signal']) &

                # Volume conditions
                (df['volume_ratio'] < df['volume_sma']) &

                # Order book conditions
                (df['book_imbalance'] < -0.2) &

                # Volatility conditions
                (df['mid_price'] < df['bollinger_upper']) &
                (df['atr'] > df['atr'].rolling(100).mean())
        )

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

    def calculate_pnl(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate PnL based on trading signals and positions."""
        signals_df = self.calculate_signals(market_data)
        portfolio_value = 1_000_000  # Initial portfolio value (why do we have this also set in the market data viewer?)
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

                    self.positions[f'long_{timestamp}'] = Position(
                        entry_price=current_price,
                        size=size,
                        entry_time=timestamp,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )

                elif signals_df['short_signal'].iloc[i]:
                    stop_loss = self.calculate_stop_loss(signals_df, i, False)
                    size = self.calculate_position_size(current_price, stop_loss, portfolio_value)
                    take_profit = self.calculate_take_profit(current_price, stop_loss, False)

                    self.positions[f'short_{timestamp}'] = Position(
                        entry_price=current_price,
                        size=-size,  # Negative size for short positions
                        entry_time=timestamp,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )

            # Calculate current PnL
            total_pnl = sum(
                position.size * (current_price - position.entry_price)
                for position in self.positions.values()
            )

            pnl_records.append({
                'timestamp': timestamp,
                'pnl': total_pnl,
                'pnl_percentage': (total_pnl / portfolio_value) * 100
            })

        return pd.DataFrame(pnl_records)


def calculate_trading_metrics(pnl_df: pd.DataFrame) -> Dict[str, float]:
    """Calculate trading performance metrics."""
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
    cumulative = pnl.cumsum()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    return abs(drawdown.min())


def calculate_sharpe_ratio(returns: pd.Series) -> float:
    """Calculate Sharpe ratio."""
    returns_std = returns.std()
    if returns_std == 0:
        return 0
    return (returns.mean() / returns_std) * np.sqrt(252)  # Annualized


def calculate_win_rate(pnl: pd.Series) -> float:
    """Calculate win rate."""
    trades = pnl.diff().dropna()
    winning_trades = (trades > 0).sum()
    total_trades = len(trades)
    return (winning_trades / total_trades * 100) if total_trades > 0 else 0