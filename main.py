import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QWidget, QCheckBox, QLabel)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

logging.basicConfig(level=logging.ERROR)

class MarketDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 1000, 700)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        controls_layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.load_button = QPushButton("Load Data")
        controls_layout.addWidget(self.period_combo)
        controls_layout.addWidget(self.load_button)

        self.stock_checkboxes = {}
        stock_layout = QHBoxLayout()
        for stock in ['A', 'B', 'C', 'D', 'E']:
            checkbox = QCheckBox(stock)
            checkbox.setChecked(stock == 'A')
            self.stock_checkboxes[stock] = checkbox
            stock_layout.addWidget(checkbox)

        toggle_layout = QHBoxLayout()
        self.bid_price_check = QCheckBox("Bid Price")
        self.ask_price_check = QCheckBox("Ask Price")
        self.trades_check = QCheckBox("Trades")
        self.prediction_check = QCheckBox("Price Prediction")
        self.std_dev_30s_check = QCheckBox("30s Std Dev")
        self.std_dev_60s_check = QCheckBox("60s Std Dev")

        self.bid_price_check.setChecked(True)
        self.ask_price_check.setChecked(True)
        self.trades_check.setChecked(True)
        self.prediction_check.setChecked(True)
        self.std_dev_30s_check.setChecked(False)
        self.std_dev_60s_check.setChecked(False)

        toggle_layout.addWidget(QLabel("Show/Hide:"))
        toggle_layout.addWidget(self.bid_price_check)
        toggle_layout.addWidget(self.ask_price_check)
        toggle_layout.addWidget(self.trades_check)
        toggle_layout.addWidget(self.prediction_check)
        toggle_layout.addWidget(self.std_dev_30s_check)
        toggle_layout.addWidget(self.std_dev_60s_check)

        self.figure, self.ax = plt.subplots(figsize=(10, 7))
        self.canvas = FigureCanvas(self.figure)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        main_layout.addLayout(controls_layout)
        main_layout.addLayout(stock_layout)
        main_layout.addLayout(toggle_layout)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        self.plot_lines = {}
        self.std_dev_fills = {}
        self.prediction_lines = {}

        self.load_button.clicked.connect(self.load_and_plot_data)

        self.bid_price_check.stateChanged.connect(self.update_plot_visibility)
        self.ask_price_check.stateChanged.connect(self.update_plot_visibility)
        self.trades_check.stateChanged.connect(self.update_plot_visibility)
        self.prediction_check.stateChanged.connect(self.update_plot_visibility)
        self.std_dev_30s_check.stateChanged.connect(self.update_plot_visibility)
        self.std_dev_60s_check.stateChanged.connect(self.update_plot_visibility)

        for i in range(1, 16):
            self.period_combo.addItem(f"Period{i}")
        self.period_combo.setCurrentText("Period1")

    def load_and_plot_data(self):

        period = self.period_combo.currentText()

        selected_stocks = [stock for stock, checkbox in self.stock_checkboxes.items() if checkbox.isChecked()]

        self.ax.clear()
        self.plot_lines.clear()
        self.std_dev_fills.clear()
        self.prediction_lines.clear()

        for stock in selected_stocks:
            data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)
            market_data = self.load_market_data(data_dir, stock)
            trade_data = self.load_trade_data(data_dir, stock)

            if market_data is not None:
                self.plot_market_data(market_data, stock)

                if self.prediction_check.isChecked():
                    prediction_data = self.predict_price_changes(market_data)
                    if prediction_data is not None and not prediction_data.empty:
                        prediction_line, = self.ax.plot(prediction_data['timestamp'],
                                                        prediction_data['predicted_price'],
                                                        color='orange', linestyle='--',
                                                        label=f'{stock} Predicted Price', alpha=0.7)
                        self.prediction_lines[f'{stock}_prediction'] = prediction_line

            if trade_data is not None:
                self.plot_trade_data(trade_data, stock)

        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')
        self.ax.set_title(f"{period} - Selected Stocks")

        if len(self.ax.get_lines()) > 0 or len(self.ax.collections) > 0:
            self.ax.legend()

        plt.tight_layout()
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

    def plot_market_data(self, market_data, stock):
        try:
            market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')

            if self.bid_price_check.isChecked():
                bid_line, = self.ax.plot(market_data['timestamp'], market_data['bidPrice'],
                                         label=f'{stock} Bid Price')
                self.plot_lines[f'{stock}_bid'] = bid_line

            if self.ask_price_check.isChecked():
                ask_line, = self.ax.plot(market_data['timestamp'], market_data['askPrice'],
                                         label=f'{stock} Ask Price')
                self.plot_lines[f'{stock}_ask'] = ask_line

            if self.std_dev_30s_check.isChecked():
                window_size = int(30 * 1000)
                std_dev_30s = market_data['bidPrice'].rolling(window=window_size, min_periods=1).std()

                lower_bound = market_data['bidPrice'] - std_dev_30s
                upper_bound = market_data['bidPrice'] + std_dev_30s

                std_dev_30s_fill = self.ax.fill_between(market_data['timestamp'],
                                                        lower_bound.clip(lower=None, upper=upper_bound),
                                                        upper_bound.clip(lower=lower_bound, upper=None),
                                                        alpha=0.2, color='blue', label=f'{stock} 30s Std Dev')
                self.std_dev_fills[f'{stock}_30s'] = std_dev_30s_fill

            if self.std_dev_60s_check.isChecked():
                window_size = int(60 * 1000)
                std_dev_60s = market_data['bidPrice'].rolling(window=window_size, min_periods=1).std()

                lower_bound = market_data['bidPrice'] - std_dev_60s
                upper_bound = market_data['bidPrice'] + std_dev_60s

                std_dev_60s_fill = self.ax.fill_between(market_data['timestamp'],
                                                        lower_bound.clip(lower=None, upper=upper_bound),
                                                        upper_bound.clip(lower=lower_bound, upper=None),
                                                        alpha=0.2, color='red', label=f'{stock} 60s Std Dev')
                self.std_dev_fills[f'{stock}_60s'] = std_dev_60s_fill

        except Exception as e:
            logging.error(f"Error plotting market data for stock {stock}: {e}")

    def plot_trade_data(self, trade_data, stock):
        try:
            trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')

            if self.trades_check.isChecked():
                trade_line, = self.ax.plot(trade_data['timestamp'], trade_data['price'],
                                           linestyle='-', marker='',
                                           label=f'{stock} Trade Price', alpha=0.7)
                self.plot_lines[f'{stock}_trade'] = trade_line

        except Exception as e:
            logging.error(f"Error plotting trade data for stock {stock}: {e}")

    def update_plot_visibility(self):

        for key, line in self.plot_lines.items():
            if 'bid' in key:
                line.set_visible(self.bid_price_check.isChecked())
            elif 'ask' in key:
                line.set_visible(self.ask_price_check.isChecked())
            elif 'trade' in key:
                line.set_visible(self.trades_check.isChecked())

        for key, fill in self.std_dev_fills.items():
            if '30s' in key:
                fill.set_visible(self.std_dev_30s_check.isChecked())
            elif '60s' in key:
                fill.set_visible(self.std_dev_60s_check.isChecked())

        for key, line in self.prediction_lines.items():
            line.set_visible(self.prediction_check.isChecked())

        self.canvas.draw()

    def predict_price_changes(self, market_data):
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = MarketDataViewer()
    viewer.show()
    sys.exit(app.exec_())

'''
sample data in TrainingData/Period3/C/market_data_C.csv:
bidVolume,bidPrice,askVolume,askPrice,timestamp
11,5043.75,27,5044.0,08:00:00.005926909
11,5043.75,27,5044.0,08:00:00.005933024

sample data in TrainingData/Period3/C/trade_data_C.csv:
price,volume,timestamp
5044.0,1,08:00:00.015534389
5043.75,2,08:00:00.037621161
'''