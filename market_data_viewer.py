import os
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QWidget, QCheckBox, QLabel)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib.pyplot as plt
from data_loader import load_market_data, load_trade_data
from price_prediction import predict_price_changes
import pandas as pd

class MarketDataViewer(QMainWindow):
    STOCKS = ['A', 'B', 'C', 'D', 'E']
    VISUALIZATION_TOGGLES = [
        ('bid_price_check', "Bid Price", True),
        ('ask_price_check', "Ask Price", True),
        ('trades_check', "Trades", True),
        ('prediction_check', "Price Prediction", True),
        ('std_dev_30s_check', "30s Std Dev", False),
        ('std_dev_60s_check', "60s Std Dev", False)
    ]

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

        self.stock_checkboxes = self._setup_stock_checkboxes()
        stock_layout = QHBoxLayout()
        for stock, checkbox in self.stock_checkboxes.items():
            stock_layout.addWidget(checkbox)

        toggle_layout = QHBoxLayout()
        self._setup_visualization_toggles(toggle_layout)

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

        for toggle_attr, _, _ in self.VISUALIZATION_TOGGLES:
            getattr(self, toggle_attr).stateChanged.connect(self.update_plot_visibility)

        for i in range(1, 16):
            self.period_combo.addItem(f"Period{i}")
        self.period_combo.setCurrentText("Period1")

    def _setup_stock_checkboxes(self):
        stock_checkboxes = {}
        for stock in self.STOCKS:
            checkbox = QCheckBox(stock)
            checkbox.setChecked(stock == 'A')
            stock_checkboxes[stock] = checkbox
        return stock_checkboxes

    def _setup_visualization_toggles(self, toggle_layout):
        toggle_layout.addWidget(QLabel("Show/Hide:"))
        for toggle_attr, label, default_state in self.VISUALIZATION_TOGGLES:
            checkbox = QCheckBox(label)
            checkbox.setChecked(default_state)
            setattr(self, toggle_attr, checkbox)
            toggle_layout.addWidget(checkbox)

    def load_and_plot_data(self):
        period = self.period_combo.currentText()

        selected_stocks = [stock for stock, checkbox in self.stock_checkboxes.items() if checkbox.isChecked()]

        self.ax.clear()
        self.plot_lines.clear()
        self.std_dev_fills.clear()
        self.prediction_lines.clear()

        for stock in selected_stocks:
            data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)
            market_data = load_market_data(data_dir, stock)
            trade_data = load_trade_data(data_dir, stock)

            if market_data is not None:
                self.plot_market_data(market_data, stock)

                if self.prediction_check.isChecked():
                    prediction_data = predict_price_changes(market_data)
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

    def plot_market_data(self, market_data, stock):
        market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')

        plot_conditions = [
            (self.bid_price_check, 'bidPrice', f'{stock} Bid Price'),
            (self.ask_price_check, 'askPrice', f'{stock} Ask Price')
        ]

        for checkbox, price_column, label in plot_conditions:
            if checkbox.isChecked():
                bid_line, = self.ax.plot(market_data['timestamp'], market_data[price_column],
                                            label=label)
                self.plot_lines[f'{stock}_{label.split()[-1].lower()}'] = bid_line

        self._plot_standard_deviation(market_data, stock)

    def _plot_standard_deviation(self, market_data, stock):
        std_dev_configs = [
            (self.std_dev_30s_check, 30, 'blue', f'{stock} 30s Std Dev'),
            (self.std_dev_60s_check, 60, 'red', f'{stock} 60s Std Dev')
        ]

        for checkbox, window_seconds, color, label in std_dev_configs:
            if checkbox.isChecked():
                window_size = int(window_seconds * 1000)
                std_dev = market_data['bidPrice'].rolling(window=window_size, min_periods=1).std()

                lower_bound = market_data['bidPrice'] - std_dev
                upper_bound = market_data['bidPrice'] + std_dev

                std_dev_fill = self.ax.fill_between(market_data['timestamp'],
                                                    lower_bound.clip(lower=None, upper=upper_bound),
                                                    upper_bound.clip(lower=lower_bound, upper=None),
                                                    alpha=0.2, color=color, label=label)
                self.std_dev_fills[f'{stock}_{window_seconds}s'] = std_dev_fill

    def plot_trade_data(self, trade_data, stock):
        trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')

        if self.trades_check.isChecked():
            trade_line, = self.ax.plot(trade_data['timestamp'], trade_data['price'],
                                        linestyle='-', marker='',
                                        label=f'{stock} Trade Price', alpha=0.7)
            self.plot_lines[f'{stock}_trade'] = trade_line

    def update_plot_visibility(self):
        visibility_map = {
            'bid': self.bid_price_check.isChecked(),
            'ask': self.ask_price_check.isChecked(),
            'trade': self.trades_check.isChecked()
        }

        for key, line in self.plot_lines.items():
            line.set_visible(any(vis_type in key for vis_type in visibility_map
                                    if visibility_map[vis_type]))

        std_dev_visibility = {
            '30s': self.std_dev_30s_check.isChecked(),
            '60s': self.std_dev_60s_check.isChecked()
        }

        for key, fill in self.std_dev_fills.items():
            fill.set_visible(any(dev_type in key for dev_type in std_dev_visibility
                                    if std_dev_visibility[dev_type]))

        for key, line in self.prediction_lines.items():
            line.set_visible(self.prediction_check.isChecked())

        self.canvas.draw()
