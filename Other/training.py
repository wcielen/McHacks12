import pandas as pd
import numpy as np
from scipy.stats import linregress


def calculate_technical_indicators(df):
    """Calculate technical indicators for prediction"""
    df = df.copy()
    
    # Basic price features
    df['mid_price'] = (df['bidPrice'] + df['askPrice']) / 2
    df['spread'] = df['askPrice'] - df['bidPrice']
    df['price_change'] = df['mid_price'].diff()
    
    # Rolling statistics
    windows = [5, 10, 20, 50]
    for window in windows:
        # Price-based indicators
        df[f'ma_{window}'] = df['mid_price'].rolling(window=window).mean()
        df[f'std_{window}'] = df['mid_price'].rolling(window=window).std()
        df[f'upper_band_{window}'] = df[f'ma_{window}'] + (df[f'std_{window}'] * 2)
        df[f'lower_band_{window}'] = df[f'ma_{window}'] - (df[f'std_{window}'] * 2)
        
        # Momentum indicators
        df[f'momentum_{window}'] = df['mid_price'].diff(window)
        df[f'roc_{window}'] = df['mid_price'].pct_change(window) * 100
        
        # Volatility indicators
        df[f'volatility_{window}'] = df['price_change'].rolling(window=window).std()
        
    return df

def predict_price_changes(market_data):
    """
    Predict price changes based on market data
    Args:
        market_data (pd.DataFrame): Market data with timestamp, bidPrice, askPrice columns
    Returns:
        pd.DataFrame: Predictions with timestamp and predicted_price columns
    """
    try:
        # Prepare data
        df = calculate_technical_indicators(market_data)
        
        # Linear regression on recent price trend
        window_size = 20
        df['predicted_price'] = np.nan
        
        for i in range(window_size, len(df)):
            y = df['mid_price'].iloc[i-window_size:i].values
            X = np.arange(window_size).reshape(-1, 1)
            
            slope, intercept, _, _, _ = linregress(X.flatten(), y)
            next_point = window_size
            prediction = slope * next_point + intercept
            
            df.iloc[i, df.columns.get_loc('predicted_price')] = prediction
        
        # Add confidence bands
        df['prediction_std'] = df['std_20']
        df['upper_prediction'] = df['predicted_price'] + df['prediction_std']
        df['lower_prediction'] = df['predicted_price'] - df['prediction_std']
        
        return df[['timestamp', 'predicted_price', 'upper_prediction', 'lower_prediction']].dropna()
    
    except Exception as e:
        print(f"Error in prediction: {str(e)}")
        return None

class PredictionPlotter:
    def __init__(self, ax, prediction_lines=None):
        self.ax = ax
        self.prediction_lines = prediction_lines if prediction_lines is not None else {}
        self.confidence_bands = {}
    
    def plot_predictions(self, market_data, stock, show_predictions=True):
        """Plot price predictions with confidence bands"""
        try:
            # Clear previous predictions for this stock
            if f'{stock}_prediction' in self.prediction_lines:
                self.prediction_lines[f'{stock}_prediction'].remove()
                del self.prediction_lines[f'{stock}_prediction']
            
            if f'{stock}_confidence' in self.confidence_bands:
                self.confidence_bands[f'{stock}_confidence'].remove()
                del self.confidence_bands[f'{stock}_confidence']
            
            if not show_predictions:
                return
            
            prediction_data = predict_price_changes(market_data)
            if prediction_data is None or prediction_data.empty:
                return
            
            # Plot prediction line
            prediction_line, = self.ax.plot(
                prediction_data['timestamp'],
                prediction_data['predicted_price'],
                color='orange',
                linestyle='--',
                label=f'{stock} Predicted',
                alpha=0.7
            )
            self.prediction_lines[f'{stock}_prediction'] = prediction_line
            
            # Plot confidence bands
            confidence_band = self.ax.fill_between(
                prediction_data['timestamp'],
                prediction_data['lower_prediction'],
                prediction_data['upper_prediction'],
                color='orange',
                alpha=0.1,
                label=f'{stock} Prediction '
            )
            self.confidence_bands[f'{stock}_confidence'] = confidence_band
            
        except Exception as e:
            print(f"Error plotting predictions: {str(e)}")

