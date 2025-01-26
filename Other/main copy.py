import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import logging
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

logging.basicConfig(level=logging.ERROR)

def set_dark_theme(app):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

def load_market_data(data_dir, stock):
    all_data = []
    try:
        market_files = [f for f in os.listdir(data_dir) if
                       f.startswith(f"market_data_{stock}") and f.endswith('.csv')]

        for file in market_files:
            file_path = os.path.join(data_dir, file)
            try:
                df = pd.read_csv(file_path)
                all_data.append(df)
            except Exception as e:
                logging.error(f"Error reading file {file_path}: {e}")

        return pd.concat(all_data) if all_data else None
    except FileNotFoundError:
        logging.error(f"Directory not found: {data_dir}")
        return None

def load_trade_data(data_dir, stock):
    file_path = os.path.join(data_dir, f"trade_data_{stock}.csv")
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        logging.error(f"Trade data file not found: {file_path}")
        return None

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
        if market_data.iloc[i]['trend_change']:
            if i + prediction_window < len(market_data):
                future_timestamps = market_data.iloc[i + 1:i + prediction_window + 1]['timestamp']
                momentum = market_data.iloc[i]['momentum']
                start_price = market_data.iloc[i]['bidPrice']

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
        
        # Set dark theme for matplotlib
        plt.style.use('dark_background')
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 1000, 700)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        controls_layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.period_combo.setStyleSheet("QComboBox { background-color: #353535; color: white; }")
        self.load_button = QPushButton("Load Data")
        self.load_button.setStyleSheet("QPushButton { background-color: #454545; color: white; }")
        controls_layout.addWidget(self.period_combo)
        controls_layout.addWidget(self.load_button)

        self.stock_checkboxes = self._setup_stock_checkboxes()
        stock_layout = QHBoxLayout()
        for stock, checkbox in self.stock_checkboxes.items():
            checkbox.setStyleSheet("QCheckBox { color: white; }")
            stock_layout.addWidget(checkbox)

        toggle_layout = QHBoxLayout()
        self._setup_visualization_toggles(toggle_layout)

        self.figure, self.ax = plt.subplots(figsize=(10, 7))
        self.figure.patch.set_facecolor('#353535')
        self.ax.set_facecolor('#353535')
        self.canvas = FigureCanvas(self.figure)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setStyleSheet("QToolBar { background-color: #353535; color: white; }")

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
        label = QLabel("Show/Hide:")
        label.setStyleSheet("QLabel { color: white; }")
        toggle_layout.addWidget(label)
        
        for toggle_attr, label_text, default_state in self.VISUALIZATION_TOGGLES:
            checkbox = QCheckBox(label_text)
            checkbox.setStyleSheet("QCheckBox { color: white; }")
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

        # Set dark theme colors for plot
        self.ax.set_facecolor('#353535')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        for spine in self.ax.spines.values():
            spine.set_color('white')

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
                                                      color='#FFA500',
                                                      linestyle='--',
                                                      label=f'{stock} Predicted Price',
                                                      alpha=0.7)
                        self.prediction_lines[f'{stock}_prediction'] = prediction_line

            if trade_data is not None:
                self.plot_trade_data(trade_data, stock)

        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')
        self.ax.set_title(f"{period} - Selected Stocks")

        if len(self.ax.get_lines()) > 0 or len(self.ax.collections) > 0:
            legend = self.ax.legend()
            plt.setp(legend.get_texts(), color='white')

        plt.tight_layout()
        self.canvas.draw()

    def plot_market_data(self, market_data, stock):
        try:
            market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')

            plot_conditions = [
                (self.bid_price_check, 'bidPrice', f'{stock} Bid Price', '#00FF00'),
                (self.ask_price_check, 'askPrice', f'{stock} Ask Price', '#FF69B4')
            ]

            for checkbox, price_column, label, color in plot_conditions:
                if checkbox.isChecked():
                    line, = self.ax.plot(market_data['timestamp'], market_data[price_column],
                                       label=label, color=color)
                    self.plot_lines[f'{stock}_{label.split()[-1].lower()}'] = line

            self._plot_standard_deviation(market_data, stock)

        except Exception as e:
            logging.error(f"Error plotting market data for stock {stock}: {e}")

    def _plot_standard_deviation(self, market_data, stock):
        std_dev_configs = [
            (self.std_dev_30s_check, 30, '#4169E1', f'{stock} 30s Std Dev'),
            (self.std_dev_60s_check, 60, '#DC143C', f'{stock} 60s Std Dev')
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
        try:
            trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')

            if self.trades_check.isChecked():
                trade_line, = self.ax.plot(trade_data['timestamp'], trade_data['price'],
                                         color='#FFD700',
                                         linestyle='-', marker='',
                                         label=f'{stock} Trade Price', alpha=0.7)
                self.plot_lines[f'{stock}_trade'] = trade_line

        except Exception as e:
            logging.error(f"Error plotting trade data for stock {stock}: {e}")

    def update_plot_visibility(self):
        visibility_map = {
            'bid': self.bid_price_check.isChecked(),
            'ask': self.ask_price_check.isChecked(),
            'trade': self.trades_check.isChecked(),
            'model_prediction': self.model_prediction_check.isChecked()
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    set_dark_theme(app)
    viewer = MarketDataViewer()
    viewer.show()
    sys.exit(app.exec_())