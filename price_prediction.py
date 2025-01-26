import pandas as pd
import numpy as np
from typing import Optional


def predict_price_changes(market_data: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Predict price changes based on market data analysis.

    Args:
        market_data: DataFrame containing market data

    Returns:
        DataFrame with predictions or None if insufficient data
    """
    if market_data is None or len(market_data) < 30:  # Minimum required for long EMA
        return None

    try:
        # Work with a copy to prevent modifications to original data
        data = market_data.copy()

        # Ensure timestamp is datetime
        data['timestamp'] = pd.to_datetime(data['timestamp'], format='%H:%M:%S.%f')
        data = data.sort_values('timestamp')

        # Calculate technical indicators
        data['ema_short'] = data['bidPrice'].ewm(span=10, adjust=False).mean()
        data['ema_long'] = data['bidPrice'].ewm(span=30, adjust=False).mean()
        data['momentum'] = data['bidPrice'].diff(periods=10)
        data['volatility'] = data['bidPrice'].rolling(window=20, min_periods=1).std()

        # Identify trend changes
        data['trend_change'] = (
                (data['ema_short'] > data['ema_long']) &
                (data['momentum'].abs() > data['volatility'])
        )

        prediction_window = 5
        predictions = []

        # Find trend change points and generate predictions
        trend_change_indices = data.index[data['trend_change']].tolist()

        for idx in trend_change_indices:
            if idx + prediction_window >= len(data):
                continue

            momentum = data.loc[idx, 'momentum']
            start_price = data.loc[idx, 'bidPrice']

            # Generate future timestamps and prices
            future_slice = data.iloc[idx + 1:idx + prediction_window + 1]

            # Calculate predicted prices using momentum
            price_changes = np.arange(1, prediction_window + 1) * momentum
            predicted_prices = start_price + price_changes

            # Create prediction entries
            predictions.extend([
                {
                    'timestamp': ts,
                    'predicted_price': price
                }
                for ts, price in zip(future_slice['timestamp'], predicted_prices)
            ])

        # Convert predictions to DataFrame if any exist
        if predictions:
            prediction_df = pd.DataFrame(predictions)

            # Remove duplicate predictions for the same timestamp
            prediction_df = prediction_df.groupby('timestamp')['predicted_price'].mean().reset_index()

            # Sort by timestamp
            prediction_df = prediction_df.sort_values('timestamp')

            return prediction_df

        return None

    except Exception as e:
        print(f"Error in price prediction: {str(e)}")
        return None