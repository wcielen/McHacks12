import pandas as pd

def predict_price_changes(market_data):
    if market_data is None or market_data.empty:
        return None

    market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')
    market_data = market_data.sort_values('timestamp')

    market_data['ema_short'] = market_data['bidPrice'].ewm(span=10, adjust=False).mean()
    market_data['ema_long'] = market_data['bidPrice'].ewm(span=30, adjust=False).mean()

    market_data['momentum'] = market_data['bidPrice'].diff(periods=10)
    market_data['volatility'] = market_data['bidPrice'].rolling(window=20).std()

    market_data['trend_change'] = (
            (market_data['ema_short'] > market_data['ema_long']) &
            (market_data['momentum'].abs() > market_data['volatility'])
    )

    prediction_window = 5
    predictions = []

    for i in range(len(market_data)):
        if market_data.loc[i, 'trend_change']:
            if i + prediction_window < len(market_data):
                future_timestamps = market_data.loc[i + 1:i + prediction_window, 'timestamp']

                momentum = market_data.loc[i, 'momentum']
                start_price = market_data.loc[i, 'bidPrice']

                future_prices = [start_price + momentum * (j + 1) for j in range(prediction_window)]

                for timestamp, price in zip(future_timestamps, future_prices):
                    predictions.append({
                        'timestamp': timestamp,
                        'predicted_price': price
                    })

    if predictions:
        prediction_df = pd.DataFrame(predictions)
        return prediction_df

    return None