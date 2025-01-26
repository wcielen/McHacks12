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
    # Dark theme setup remains the same
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)


class MarketDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_plot()
        self.connect_signals()

    def init_ui(self):
        # UI setup remains largely the same
        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 1000, 700)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Controls
        controls = QHBoxLayout()
        self.period_combo = QComboBox()
        self.period_combo.setStyleSheet("background-color: #353535; color: white;")
        self.period_combo.addItems([f"Period{i}" for i in range(1, 16)])

        self.load_button = QPushButton("Load Data")
        self.load_button.setStyleSheet("background-color: #454545; color: white;")

        controls.addWidget(self.period_combo)
        controls.addWidget(self.load_button)

        # Stock selection
        stocks = QHBoxLayout()
        self.stock_checks = {}
        for stock in ['A', 'B', 'C', 'D', 'E']:
            cb = QCheckBox(stock)
            cb.setStyleSheet("color: white;")
            cb.setChecked(stock == 'A')
            self.stock_checks[stock] = cb
            stocks.addWidget(cb)

        # Plot controls
        plot_controls = QHBoxLayout()
        plot_controls.addWidget(QLabel("Show/Hide:"))

        self.vis_checks = {
            'bid': QCheckBox("Bid Price"),
            'ask': QCheckBox("Ask Price"),
            'trades': QCheckBox("Trades"),
            'pred': QCheckBox("Predictions"),
            'std30': QCheckBox("30s Std Dev"),
            'std60': QCheckBox("60s Std Dev")
        }

        for name, cb in self.vis_checks.items():
            cb.setStyleSheet("color: white;")
            cb.setChecked(name not in ['std30', 'std60'])
            plot_controls.addWidget(cb)

        layout.addLayout(controls)
        layout.addLayout(stocks)
        layout.addLayout(plot_controls)

    def setup_plot(self):
        plt.style.use('dark_background')
        self.figure, self.ax = plt.subplots(figsize=(10, 7))
        self.figure.patch.set_facecolor('#353535')
        self.ax.set_facecolor('#353535')

        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #353535; color: white;")

        self.centralWidget().layout().addWidget(self.toolbar)
        self.centralWidget().layout().addWidget(self.canvas)

        self.plot_elements = {
            'lines': {},
            'fills': {},
            'predictions': {},
            'daily_lines': {}
        }

    def connect_signals(self):
        self.load_button.clicked.connect(self.update_plot)
        for cb in self.vis_checks.values():
            cb.stateChanged.connect(self.update_visibility)

    def load_market_data(self, file_path):
        try:
            # Read data in chunks to handle large files
            chunks = []
            for chunk in pd.read_csv(file_path, chunksize=10000):
                chunks.append(chunk)
            data = pd.concat(chunks, ignore_index=True)

            # Convert timestamp using a specific format
            data['timestamp'] = pd.to_datetime(data['timestamp'], format='%H:%M:%S.%f')
            return data
        except Exception as e:
            logging.error(f"Error loading market data: {str(e)}")
            return None

    def update_plot(self):
        self.ax.clear()
        for elements in self.plot_elements.values():
            elements.clear()

        # Setup dark theme for plot
        self.ax.set_facecolor('#353535')
        self.ax.tick_params(colors='white')
        for item in [self.ax.xaxis.label, self.ax.yaxis.label, self.ax.title]:
            item.set_color('white')
        for spine in self.ax.spines.values():
            spine.set_color('white')

        period = self.period_combo.currentText()
        selected_stocks = [s for s, cb in self.stock_checks.items() if cb.isChecked()]

        for stock in selected_stocks:
            self.plot_stock_data(stock, period)

        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')
        self.ax.set_title(f"{period} - Selected Stocks")

        if self.ax.get_lines() or self.ax.collections:
            legend = self.ax.legend()
            plt.setp(legend.get_texts(), color='white')

        plt.tight_layout()
        self.canvas.draw()

    def plot_stock_data(self, stock, period):
        data_dir = os.path.join(os.path.dirname(__file__), 'TrainingData', period, stock)

        # Load market data
        market_data_path = os.path.join(data_dir, f'market_data_{stock}.csv')
        market_data = self.load_market_data(market_data_path)

        if market_data is not None:
            # Plot market data
            if self.vis_checks['bid'].isChecked():
                self.plot_elements['lines'][f'{stock}_bid'] = self.ax.plot(
                    market_data['timestamp'], market_data['bidPrice'],
                    color='#00FF00', label=f'{stock} Bid'
                )[0]

            if self.vis_checks['ask'].isChecked():
                self.plot_elements['lines'][f'{stock}_ask'] = self.ax.plot(
                    market_data['timestamp'], market_data['askPrice'],
                    color='#FF69B4', label=f'{stock} Ask'
                )[0]

            # Daily high/low lines
            high = market_data['bidPrice'].max()
            low = market_data['bidPrice'].min()
            self.plot_elements['daily_lines'][f'{stock}_high'] = self.ax.axhline(
                y=high, color='#00FF00', linestyle=':', alpha=0.8,
                label=f'{stock} Daily High'
            )
            self.plot_elements['daily_lines'][f'{stock}_low'] = self.ax.axhline(
                y=low, color='#FF0000', linestyle=':', alpha=0.8,
                label=f'{stock} Daily Low'
            )

            # Standard deviations
            if self.vis_checks['std30'].isChecked():
                self.plot_std_dev(market_data, stock, 30, '#4169E1')
            if self.vis_checks['std60'].isChecked():
                self.plot_std_dev(market_data, stock, 60, '#DC143C')

            # Predictions
            if self.vis_checks['pred'].isChecked():
                self.plot_predictions(market_data, stock)

        # Load and plot trades
        try:
            trade_data_path = os.path.join(data_dir, f'trade_data_{stock}.csv')
            trade_data = self.load_market_data(trade_data_path)

            if trade_data is not None and self.vis_checks['trades'].isChecked():
                self.plot_elements['lines'][f'{stock}_trades'] = self.ax.plot(
                    trade_data['timestamp'], trade_data['price'],
                    color='#FFD700', alpha=0.7, label=f'{stock} Trades'
                )[0]
        except Exception as e:
            logging.error(f"Error loading trade data: {str(e)}")

    def plot_std_dev(self, data, stock, window, color):
        window_ms = window * 1000
        std = data['bidPrice'].rolling(window=window_ms, min_periods=1).std()
        center = data['bidPrice']
        self.plot_elements['fills'][f'{stock}_std{window}'] = self.ax.fill_between(
            data['timestamp'],
            center - std, center + std,
            color=color, alpha=0.2, label=f'{stock} {window}s Std Dev'
        )

    def plot_predictions(self, data, stock):
        # Simple moving average crossover prediction
        data['sma_fast'] = data['bidPrice'].rolling(window=10).mean()
        data['sma_slow'] = data['bidPrice'].rolling(window=30).mean()

        crossover_points = data[
            (data['sma_fast'] > data['sma_slow']) &
            (data['sma_fast'].shift(1) <= data['sma_slow'].shift(1))
            ]

        if not crossover_points.empty:
            self.plot_elements['predictions'][stock] = self.ax.plot(
                crossover_points['timestamp'],
                crossover_points['bidPrice'],
                'o', color='#FFA500', label=f'{stock} Signals'
            )[0]

    def update_visibility(self):
        # Update visibility of plot elements based on checkboxes
        visibility = {
            'bid': self.vis_checks['bid'].isChecked(),
            'ask': self.vis_checks['ask'].isChecked(),
            'trades': self.vis_checks['trades'].isChecked()
        }

        for key, line in self.plot_elements['lines'].items():
            line.set_visible(any(k in key and visibility[k] for k in visibility))

        for key, fill in self.plot_elements['fills'].items():
            if '30' in key:
                fill.set_visible(self.vis_checks['std30'].isChecked())
            elif '60' in key:
                fill.set_visible(self.vis_checks['std60'].isChecked())

        for line in self.plot_elements['predictions'].values():
            line.set_visible(self.vis_checks['pred'].isChecked())

        # Daily lines always visible
        for line in self.plot_elements['daily_lines'].values():
            line.set_visible(True)

        self.canvas.draw()