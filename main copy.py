import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QWidget, QCheckBox, QLabel)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib

# Set up logging to only log errors
logging.basicConfig(level=logging.ERROR)

class MarketDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set dark theme for entire application
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QComboBox, QComboBox QAbstractItemView {
                background-color: #3c3f41;
                color: white;
                selection-background-color: #4f5b66;
            }
            QPushButton {
                background-color: #3c3f41;
                color: white;
                border: 1px solid #555;
            }
            QCheckBox {
                color: white;
            }
        """)

        # Get the absolute path of the script's directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 1000, 700)

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Create controls
        controls_layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.stock_combo = QComboBox()
        
        # Remove load button since we'll autoload
        controls_layout.addWidget(self.period_combo)
        controls_layout.addWidget(self.stock_combo)

        # Create toggle checkboxes
        toggle_layout = QHBoxLayout()
        self.bid_price_check = QCheckBox("Bid Price")
        self.ask_price_check = QCheckBox("Ask Price")
        self.trades_check = QCheckBox("Trades")
        self.prediction_check = QCheckBox("Price Prediction")

        # Set checkboxes to checked by default
        self.bid_price_check.setChecked(True)
        self.ask_price_check.setChecked(True)
        self.trades_check.setChecked(True)
        self.prediction_check.setChecked(True)

        toggle_layout.addWidget(QLabel("Show/Hide:"))
        toggle_layout.addWidget(self.bid_price_check)
        toggle_layout.addWidget(self.ask_price_check)
        toggle_layout.addWidget(self.trades_check)
        toggle_layout.addWidget(self.prediction_check)

        # Set dark mode for matplotlib
        plt.style.use('dark_background')
        matplotlib.rcParams['axes.facecolor'] = '#2b2b2b'
        matplotlib.rcParams['figure.facecolor'] = '#2b2b2b'
        matplotlib.rcParams['text.color'] = 'white'
        matplotlib.rcParams['axes.labelcolor'] = 'white'
        matplotlib.rcParams['xtick.color'] = 'white'
        matplotlib.rcParams['ytick.color'] = 'white'

        # Create matplotlib figure and canvas
        self.figure, self.ax = plt.subplots(figsize=(10, 7), facecolor='#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.canvas = FigureCanvas(self.figure)

        # Add navigation toolbar with all tools enabled
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        # Add widgets to main layout
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(toggle_layout)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        # Store plot lines and scatter for toggling
        self.bid_line = None
        self.ask_line = None
        self.trade_line = None
        self.prediction_line = None

        # Connect signals
        self.period_combo.currentIndexChanged.connect(self.load_and_plot_data)
        self.stock_combo.currentIndexChanged.connect(self.load_and_plot_data)
        self.bid_price_check.stateChanged.connect(self.toggle_bid_price)
        self.ask_price_check.stateChanged.connect(self.toggle_ask_price)
        self.trades_check.stateChanged.connect(self.toggle_trades)
        self.prediction_check.stateChanged.connect(self.toggle_prediction)

        # Initialize combo boxes
        self.initialize_combos()

        # Automatically load data when app starts
        self.load_and_plot_data()

    def initialize_combos(self):
        # Populate period combo box
        for i in range(1, 16):
            self.period_combo.addItem(f"Period{i}")

        # Populate stock combo box
        for stock in ['A', 'B', 'C', 'D', 'E']:
            self.stock_combo.addItem(stock)

    def load_and_plot_data(self):
        # Get selected period and stock
        period = self.period_combo.currentText()
        stock = self.stock_combo.currentText()

        # Construct full path to data directory
        data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)

        # Load market data
        market_data = self.load_market_data(data_dir, stock)

        # Load trade data
        trade_data = self.load_trade_data(data_dir, stock)

        # Plot data
        self.plot_data(market_data, trade_data)

    def load_market_data(self, data_dir, stock):
        all_data = []
        try:
            for file in os.listdir(data_dir):
                if file.startswith(f"market_data_{stock}") and file.endswith('.csv'):
                    file_path = os.path.join(data_dir, file)
                    try:
                        df = pd.read_csv(file_path)
                        all_data.append(df)
                    except Exception as e:
                        logging.error(f"Error reading file {file_path}: {e}")

            if not all_data:
                logging.error(f"No market data files found in {data_dir}")
                return None

            return pd.concat(all_data)
        except FileNotFoundError:
            logging.error(f"Directory not found: {data_dir}")
            return None

    def load_trade_data(self, data_dir, stock):
        file_path = os.path.join(data_dir, f"trade_data_{stock}.csv")
        try:
            return pd.read_csv(file_path)
        except FileNotFoundError:
            logging.error(f"Trade data file not found: {file_path}")
            return None

    def plot_data(self, market_data, trade_data):
        # Clear previous plot
        self.ax.clear()

        # Plot market data
        if market_data is not None and not market_data.empty:
            try:
                market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')

                # Plot bid price line
                self.bid_line, = self.ax.plot(market_data['timestamp'], market_data['bidPrice'],
                                              label='Bid Price', visible=self.bid_price_check.isChecked())

                # Plot ask price line
                self.ask_line, = self.ax.plot(market_data['timestamp'], market_data['askPrice'],
                                              label='Ask Price', visible=self.ask_price_check.isChecked())
            except Exception as e:
                logging.error(f"Error plotting market data: {e}")

        # Plot trade data (with only the trade line in green)
        if trade_data is not None and not trade_data.empty:
            try:
                trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')

                # Create a solid green line for trades
                self.trade_line, = self.ax.plot(trade_data['timestamp'], trade_data['price'],
                                                color='green', linestyle='-',
                                                alpha=0.7, label='Trade Line',
                                                visible=self.trades_check.isChecked())
            except Exception as e:
                logging.error(f"Error plotting trade data: {e}")

        # Plot price prediction if checkbox is checked
        if self.prediction_check.isChecked():
            prediction_data = self.predict_price_changes(market_data)
            if prediction_data is not None and not prediction_data.empty:
                self.prediction_line, = self.ax.plot(prediction_data['timestamp'], prediction_data['predicted_price'],
                                                     color='orange', linestyle='--', label='Predicted Price',
                                                     visible=self.prediction_check.isChecked())

        # Set labels and title
        self.ax.set_xlabel('Time', color='white')
        self.ax.set_ylabel('Price', color='white')

        # Only add legend if there are artists
        if len(self.ax.get_lines()) > 0 or len(self.ax.collections) > 0:
            legend = self.ax.legend()
            for text in legend.get_texts():
                text.set_color('white')

        self.ax.set_title(f"{self.period_combo.currentText()} - Stock {self.stock_combo.currentText()}", color='white')

        # Enable tight layout and auto-adjust
        plt.tight_layout()
        self.canvas.draw()

    def toggle_bid_price(self):
        if self.bid_line:
            self.bid_line.set_visible(self.bid_price_check.isChecked())
            self.canvas.draw()

    def toggle_ask_price(self):
        if self.ask_line:
            self.ask_line.set_visible(self.ask_price_check.isChecked())
            self.canvas.draw()

    def toggle_trades(self):
        if self.trade_line:
            self.trade_line.set_visible(self.trades_check.isChecked())
        self.canvas.draw()

    def toggle_prediction(self):
        if self.prediction_line:
            self.prediction_line.set_visible(self.prediction_check.isChecked())
        self.canvas.draw()

    def predict_price_changes(self, market_data):
        """
        Predict potential price changes using advanced statistical methods

        Strategy:
        1. Use exponential moving average for trend detection
        2. Calculate volatility using standard deviation
        3. Use momentum and trend to predict potential price changes
        4. Look ahead to identify potential significant movements
        """
        if market_data is None or market_data.empty:
            return None

        # Convert timestamp to datetime
        market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')

        # Sort by timestamp to ensure correct calculations
        market_data = market_data.sort_values('timestamp')

        # Calculate exponential moving averages with different windows
        market_data['ema_short'] = market_data['bidPrice'].ewm(span=10, adjust=False).mean()
        market_data['ema_long'] = market_data['bidPrice'].ewm(span=30, adjust=False).mean()

        # Calculate price momentum
        market_data['momentum'] = market_data['bidPrice'].diff(periods=10)

        # Calculate volatility
        market_data['volatility'] = market_data['bidPrice'].rolling(window=20).std()

        # Predict potential significant changes
        market_data['trend_change'] = (
                (market_data['ema_short'] > market_data['ema_long']) &
                (market_data['momentum'].abs() > market_data['volatility'])
        )

        # Look ahead prediction
        prediction_window = 5  # Number of future points to project

        # Create a DataFrame to store predictions
        predictions = []

        for i in range(len(market_data)):
            if market_data.loc[i, 'trend_change']:
                # Predict potential future points
                if i + prediction_window < len(market_data):
                    future_timestamps = market_data.loc[i + 1:i + prediction_window, 'timestamp']

                    # Linear extrapolation based on current momentum
                    momentum = market_data.loc[i, 'momentum']
                    start_price = market_data.loc[i, 'bidPrice']

                    future_prices = [start_price + momentum * (j + 1) for j in range(prediction_window)]

                    # Create prediction points
                    for timestamp, price in zip(future_timestamps, future_prices):
                        predictions.append({
                            'timestamp': timestamp,
                            'predicted_price': price
                        })

        # Convert predictions to DataFrame
        if predictions:
            prediction_df = pd.DataFrame(predictions)
            return prediction_df

        return None


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = MarketDataViewer()
    viewer.show()
    sys.exit(app.exec_())