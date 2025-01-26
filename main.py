import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QCheckBox, QPushButton, QWidget, QLabel, QComboBox)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

# Set up logging to only log errors
logging.basicConfig(level=logging.ERROR)


class MarketDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        # Get the absolute path of the script's directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 1000, 700)

        # Create main widget and layout
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
            self.stock_checkboxes[stock] = checkbox
            stock_layout.addWidget(checkbox)

        toggle_layout = QHBoxLayout()
        self.bid_price_check = QCheckBox("Bid Price")
        self.ask_price_check = QCheckBox("Ask Price")
        self.trades_check = QCheckBox("Trades")


        self.bid_price_check.setChecked(True)
        self.ask_price_check.setChecked(True)
        self.trades_check.setChecked(True)

        toggle_layout.addWidget(QLabel("Show/Hide:"))
        toggle_layout.addWidget(self.bid_price_check)
        toggle_layout.addWidget(self.ask_price_check)
        toggle_layout.addWidget(self.trades_check)

        self.figure, self.ax = plt.subplots(figsize=(10, 7))
        self.canvas = FigureCanvas(self.figure)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        main_layout.addLayout(controls_layout)
        main_layout.addLayout(stock_layout)
        main_layout.addLayout(toggle_layout)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        self.plot_lines = {}

        self.load_button.clicked.connect(self.load_and_plot_data)
        self.bid_price_check.stateChanged.connect(self.update_plot_visibility)
        self.ask_price_check.stateChanged.connect(self.update_plot_visibility)
        self.trades_check.stateChanged.connect(self.update_plot_visibility)

        self.initialize_period_combo()

    def initialize_period_combo(self):
        for i in range(1, 16):
            self.period_combo.addItem(f"Period{i}")

    def load_and_plot_data(self):
        # Get selected period
        period = self.period_combo.currentText()

        # Get selected stocks
        selected_stocks = [stock for stock, checkbox in self.stock_checkboxes.items() if checkbox.isChecked()]

        # Clear previous plots
        self.ax.clear()
        self.plot_lines.clear()

        # Plot data for each selected stock
        for stock in selected_stocks:
            data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)
            market_data = self.load_market_data(data_dir, stock)
            trade_data = self.load_trade_data(data_dir, stock)

            if market_data is not None:
                self.plot_market_data(market_data, stock)

            if trade_data is not None:
                self.plot_trade_data(trade_data, stock)

        # Set labels and title
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')
        self.ax.set_title(f"{period} - Selected Stocks")
        self.ax.legend()

        # Enable tight layout and draw canvas
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

            # Plot bid price
            if self.bid_price_check.isChecked():
                bid_line, = self.ax.plot(market_data['timestamp'], market_data['bidPrice'], label=f'{stock} Bid Price')
                self.plot_lines[f'{stock}_bid'] = bid_line

            # Plot ask price
            if self.ask_price_check.isChecked():
                ask_line, = self.ax.plot(market_data['timestamp'], market_data['askPrice'], label=f'{stock} Ask Price')
                self.plot_lines[f'{stock}_ask'] = ask_line

        except Exception as e:
            logging.error(f"Error plotting market data for stock {stock}: {e}")

    def plot_trade_data(self, trade_data, stock):
        try:
            trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')

            # Plot trades
            if self.trades_check.isChecked():
                trade_line, = self.ax.plot(trade_data['timestamp'], trade_data['price'], linestyle='-', marker='',
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
        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = MarketDataViewer()
    viewer.show()
    sys.exit(app.exec_())
