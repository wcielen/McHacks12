import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import logging
<<<<<<< HEAD
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QComboBox, QWidget, QPushButton)
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import Qt
=======
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QWidget, QCheckBox, QLabel)
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

logging.basicConfig(level=logging.ERROR)


class MarketDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()
<<<<<<< HEAD
        
=======

        # Get the absolute path of the script's directory
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.setWindowTitle("Market Data Viewer")
<<<<<<< HEAD
        self.setGeometry(100, 100, 800, 600)
        
=======
        self.setGeometry(100, 100, 1000, 700)

        # Create main widget and layout
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
<<<<<<< HEAD
        
=======

        # Create controls
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        controls_layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.stock_combo = QComboBox()
        
        # Dark mode toggle button
      
        self.dark_mode_button.setIcon(QIcon("dark_mode_icon.png"))  # Replace with an actual icon file
        self.dark_mode_button.setToolTip("Toggle Dark Mode")
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        
        # Add components to controls layout
        controls_layout.addWidget(self.period_combo)
        controls_layout.addWidget(self.stock_combo)
<<<<<<< HEAD
        controls_layout.addWidget(self.dark_mode_button)  # Add the button here
        
        plt.rcParams.update({
            'figure.facecolor': '#1E1E1E',
            'axes.facecolor': '#1E1E1E',
            'axes.edgecolor': 'white',
            'axes.labelcolor': 'white',
            'text.color': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white',
        })
        
        self.figure, self.ax = plt.subplots(figsize=(8, 6), facecolor='#1E1E1E', edgecolor='white')
        self.figure.set_facecolor('#1E1E1E')
        
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)
        
=======
        controls_layout.addWidget(self.load_button)

        # Create toggle checkboxes
        toggle_layout = QHBoxLayout()
        self.bid_price_check = QCheckBox("Bid Price")
        self.ask_price_check = QCheckBox("Ask Price")
        self.trades_check = QCheckBox("Trades")
        self.prediction_check = QCheckBox("Price Prediction")  # New checkbox

        # Set checkboxes to checked by default
        self.bid_price_check.setChecked(True)
        self.ask_price_check.setChecked(True)
        self.trades_check.setChecked(True)
        self.prediction_check.setChecked(True)  # Set prediction to visible by default

        toggle_layout.addWidget(QLabel("Show/Hide:"))
        toggle_layout.addWidget(self.bid_price_check)
        toggle_layout.addWidget(self.ask_price_check)
        toggle_layout.addWidget(self.trades_check)
        toggle_layout.addWidget(self.prediction_check)  # Add prediction checkbox

        # Create matplotlib figure and canvas
        self.figure, self.ax = plt.subplots(figsize=(10, 7))
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
        self.trade_scatter = None
        self.trade_line = None
        self.prediction_line = None  # Store the prediction line

        # Connect signals
        self.load_button.clicked.connect(self.load_and_plot_data)
        self.bid_price_check.stateChanged.connect(self.toggle_bid_price)
        self.ask_price_check.stateChanged.connect(self.toggle_ask_price)
        self.trades_check.stateChanged.connect(self.toggle_trades)
        self.prediction_check.stateChanged.connect(self.toggle_prediction)  # Connect the prediction toggle

        # Initialize combo boxes
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        self.initialize_combos()
        
        # Connect combo changes to auto load
        self.period_combo.currentTextChanged.connect(self.auto_load_data)
        self.stock_combo.currentTextChanged.connect(self.auto_load_data)
        
        self.is_dark_mode = True
        self.set_dark_mode(True)
        
        # Auto load initial data
        self.auto_load_data()

    def initialize_combos(self):
        for i in range(1, 16):
            self.period_combo.addItem(f"Period{i}")
<<<<<<< HEAD
        
=======

        # Populate stock combo box
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        for stock in ['A', 'B', 'C', 'D', 'E']:
            self.stock_combo.addItem(stock)

    def auto_load_data(self):
        period = self.period_combo.currentText()
        stock = self.stock_combo.currentText()
<<<<<<< HEAD
        
        data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)
        
        market_data = self.load_market_data(data_dir, stock)
        trade_data = self.load_trade_data(data_dir, stock)
        
=======

        # Construct full path to data directory
        data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)

        # Load market data
        market_data = self.load_market_data(data_dir, stock)

        # Load trade data
        trade_data = self.load_trade_data(data_dir, stock)

        # Plot data
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        self.plot_data(market_data, trade_data)

    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        self.set_dark_mode(self.is_dark_mode)

    def set_dark_mode(self, is_dark):
        if is_dark:
            self.setStyleSheet("""
                QWidget { 
                    background-color: #353535; 
                    color: white; 
                }
                QComboBox {
                    background-color: #2E2E2E;
                    color: white;
                    border: 1px solid #4E4E4E;
                    border-radius: 4px;
                }
            """)
            
            plt.style.use('dark_background')
            self.figure.set_facecolor('#1E1E1E')
            self.ax.set_facecolor('#1E1E1E')
        else:
            self.setStyleSheet("")
            plt.style.use('default')
            self.figure.set_facecolor('white')
            self.ax.set_facecolor('white')
        
        self.canvas.draw()

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
<<<<<<< HEAD
        
=======

        # Plot market data
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
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
<<<<<<< HEAD
        
=======

        # Plot trade data (with only the trade line in green)
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        if trade_data is not None and not trade_data.empty:
            try:
                trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')

                # Create a solid green line for trades (removing red dots/scatter)
                self.trade_line, = self.ax.plot(trade_data['timestamp'], trade_data['price'],
                                                color='green', linestyle='-',  # Solid line and green color
                                                alpha=0.7, label='Trade Line',  # Adjusted transparency (optional)
                                                visible=self.trades_check.isChecked())
            except Exception as e:
                logging.error(f"Error plotting trade data: {e}")
<<<<<<< HEAD
        
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')
        
=======

        # Plot price prediction if checkbox is checked
        if self.prediction_check.isChecked():
            prediction_data = self.predict_price_changes(market_data)
            if prediction_data is not None and not prediction_data.empty:
                self.prediction_line, = self.ax.plot(prediction_data['timestamp'], prediction_data['predicted_price'],
                                                     color='orange', linestyle='--', label='Predicted Price',
                                                     visible=self.prediction_check.isChecked())

        # Set labels and title
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')

        # Only add legend if there are artists
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
        if len(self.ax.get_lines()) > 0 or len(self.ax.collections) > 0:
            self.ax.legend()

        self.ax.set_title(f"{self.period_combo.currentText()} - Stock {self.stock_combo.currentText()}")
<<<<<<< HEAD
        
=======

        # Enable tight layout and auto-adjust
>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
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
<<<<<<< HEAD
=======

'''
sample data in TrainingData/Period3/C/market_data_C.csv:
bidVolume,bidPrice,askVolume,askPrice,timestamp
11,5043.75,27,5044.0,08:00:00.005926909
11,5043.75,27,5044.0,08:00:00.005933024
11,5043.75,27,5044.0,08:00:00.005946458
11,5043.75,27,5044.0,08:00:00.005954208
11,5043.75,27,5044.0,08:00:00.005962634

sample data in TrainingData/Period3/C/trade_data_C.csv:
price,volume,timestamp
5044.0,1,08:00:00.015534389
5043.75,2,08:00:00.037621161
5043.75,2,08:00:00.037831342
5043.75,1,08:00:00.038177428

'''

>>>>>>> 8ec077799523ca89e5a99001bb066d593100e6ff
