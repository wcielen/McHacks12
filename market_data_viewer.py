import os
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QWidget, QCheckBox, QLabel)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib.pyplot as plt
import pandas as pd
from Other.training import PredictionPlotter
from data_loader import load_market_data, load_trade_data
from price_prediction import predict_price_changes
#from .Other.model import load_model_and_predict
from weakref import WeakKeyDictionary
import gc


class MarketDataViewer(QMainWindow):
    STOCKS = ['A', 'B', 'C', 'D', 'E']
    VISUALIZATION_TOGGLES = [
        ('bid_price_check', "Bid Price", True),
        ('ask_price_check', "Ask Price", True),
        ('trades_check', "Trades", True),
        ('minmax_lines_check', "Show Min/Max Lines", False),
        ('prediction_check', "Price Prediction", True),
         ('model_prediction_check', "Model Prediction", True),
        ('std_dev_30s_check', "30s Std Dev", False),
        ('std_dev_60s_check', "60s Std Dev", False),
        ('pnl_check', "Show PNL", True),
        ('pnl_percent_check', "PNL as Percentage", True)
    ]
    INITIAL_INVESTMENT = 1_000_000  # $1,000,000 initial investment

    def __init__(self):
        super().__init__()
        self._data_cache = WeakKeyDictionary()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 1200, 900)  # Increased height for PNL graph

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Create layouts
        controls_layout = self._create_controls_layout()
        stock_layout = self._create_stock_layout()
        toggle_layout = QHBoxLayout()
        self._setup_visualization_toggles(toggle_layout)

        # Setup matplotlib with two subplots
        self.figure, (self.ax_price, self.ax_pnl) = plt.subplots(2, 1, figsize=(12, 9), height_ratios=[2, 1])
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        # Add layouts to main layout
        main_layout.addLayout(controls_layout)
        main_layout.addLayout(stock_layout)
        main_layout.addLayout(toggle_layout)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        # Initialize plot storage with weak references
        self.plot_lines = WeakKeyDictionary()
        self.std_dev_fills = WeakKeyDictionary()
        self.prediction_lines = WeakKeyDictionary()
        self.pnl_lines = WeakKeyDictionary()
        self.minmax_lines = WeakKeyDictionary()
        self.prediction_plotter = PredictionPlotter(self.ax_price, self.prediction_lines)

    def _create_controls_layout(self):
        controls_layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.load_button = QPushButton("Load Data")

        # Add periods to combo box
        self.period_combo.addItems([f"Period{i}" for i in range(1, 16)])
        self.period_combo.setCurrentText("Period1")

        controls_layout.addWidget(self.period_combo)
        controls_layout.addWidget(self.load_button)
        return controls_layout

    def _create_stock_layout(self):
        stock_layout = QHBoxLayout()
        self.stock_checkboxes = {
            stock: QCheckBox(stock) for stock in self.STOCKS
        }
        # Set only 'A' checked by default
        self.stock_checkboxes['A'].setChecked(True)

        for checkbox in self.stock_checkboxes.values():
            stock_layout.addWidget(checkbox)
        return stock_layout

    def _setup_visualization_toggles(self, layout):
        for toggle_attr, label_text, default_state in self.VISUALIZATION_TOGGLES:
            checkbox = QCheckBox(label_text)
            checkbox.setChecked(default_state)
            setattr(self, toggle_attr, checkbox)
            layout.addWidget(checkbox)

    def _connect_signals(self):
        self.load_button.clicked.connect(self.load_and_plot_data)
        for toggle_attr, _, _ in self.VISUALIZATION_TOGGLES:
            toggle = getattr(self, toggle_attr)
            if toggle is not None:
                toggle.stateChanged.connect(self.update_plot_visibility)

    def _plot_market_data(self, market_data, stock):
        market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')

        if self.bid_price_check.isChecked():
            line, = self.ax_price.plot(market_data['timestamp'],
                                     market_data['bidPrice'],
                                     label=f'{stock} Bid Price')
            self.plot_lines[line] = f'{stock}_bid'

        if self.ask_price_check.isChecked():
            line, = self.ax_price.plot(market_data['timestamp'],
                                     market_data['askPrice'],
                                     label=f'{stock} Ask Price')
            self.plot_lines[line] = f'{stock}_ask'

        if self.prediction_check.isChecked():
            self.prediction_plotter.plot_predictions(
                market_data, 
                stock, 
                show_predictions=True
            )

        if self.model_prediction_check.isChecked():
            try:
                from Other.model import load_model_and_predict
                model_predictions = load_model_and_predict(market_data)
                if model_predictions is not None:
                    line, = self.ax_price.plot(
                        market_data['timestamp'],
                        model_predictions,
                        color='purple',
                        linestyle=':',
                        label=f'{stock} Model Prediction',
                        alpha=0.7
                    )
                    self.prediction_lines[line] = f'{stock}_model_prediction'
            except ImportError:
                print("Model prediction module not found")

        self._plot_standard_deviation(market_data, stock)


    def _plot_standard_deviation(self, market_data, stock):
        std_dev_configs = [
            (self.std_dev_30s_check, 30, 'blue'),
            (self.std_dev_60s_check, 60, 'red')
        ]

        for checkbox, window_seconds, color in std_dev_configs:
            if checkbox.isChecked():
                window_size = int(window_seconds * 1000)
                std_dev = market_data['bidPrice'].rolling(
                    window=window_size,
                    min_periods=1
                ).std()

                lower_bound = market_data['bidPrice'] - std_dev
                upper_bound = market_data['bidPrice'] + std_dev

                fill = self.ax_price.fill_between(
                    market_data['timestamp'],
                    lower_bound,
                    upper_bound,
                    alpha=0.2,
                    color=color,
                    label=f'{stock} {window_seconds}s Std Dev'
                )
                self.std_dev_fills[fill] = f'{stock}_{window_seconds}s'

    def _plot_predictions(self, market_data, stock):
        prediction_data = predict_price_changes(market_data)
        if prediction_data is not None and not prediction_data.empty:
            line, = self.ax_price.plot(
                prediction_data['timestamp'],
                prediction_data['predicted_price'],
                color='orange',
                linestyle='--',
                label=f'{stock} Predicted Price',
                alpha=0.7
            )
            self.prediction_lines[line] = f'{stock}_prediction'

    def _plot_trade_data(self, trade_data, stock):
        if self.trades_check.isChecked():
            trade_data['timestamp'] = pd.to_datetime(
                trade_data['timestamp'],
                format='%H:%M:%S.%f'
            )
            line, = self.ax_price.plot(
                trade_data['timestamp'],
                trade_data['price'],
                linestyle='-',
                marker='',
                label=f'{stock} Trade Price',
                alpha=0.7
            )
            self.plot_lines[line] = f'{stock}_trade'

    def _calculate_pnl(self, market_data, stock):
        """Calculate PNL based on bid price movements"""
        if market_data is None or market_data.empty:
            return None

        # Calculate theoretical position size
        initial_price = market_data['bidPrice'].iloc[0]
        position_size = self.INITIAL_INVESTMENT / initial_price

        # Calculate PNL
        pnl_data = pd.DataFrame()
        pnl_data['timestamp'] = market_data['timestamp']
        pnl_data['absolute_pnl'] = (market_data['bidPrice'] - initial_price) * position_size
        pnl_data['percent_pnl'] = (market_data['bidPrice'] / initial_price - 1) * 100

        return pnl_data

    def _plot_pnl(self, market_data, stock):
        pnl_data = self._calculate_pnl(market_data, stock)
        if pnl_data is None:
            return

        if self.pnl_percent_check.isChecked():
            line, = self.ax_pnl.plot(
                pnl_data['timestamp'],
                pnl_data['percent_pnl'],
                label=f'{stock} PNL %'
            )
            self.pnl_lines[line] = f'{stock}_pnl_percent'
        else:
            line, = self.ax_pnl.plot(
                pnl_data['timestamp'],
                pnl_data['absolute_pnl'],
                label=f'{stock} PNL $'
            )
            self.pnl_lines[line] = f'{stock}_pnl_absolute'

    def load_and_plot_data(self):
        # Clear previous plots
        self.ax_price.clear()
        self.ax_pnl.clear()
        self.plot_lines.clear()
        self.std_dev_fills.clear()
        self.prediction_lines.clear()
        self.pnl_lines.clear()
        self.minmax_lines.clear()
        gc.collect()

        period = self.period_combo.currentText()
        selected_stocks = [stock for stock, checkbox in self.stock_checkboxes.items()
                           if checkbox.isChecked()]

        for stock in selected_stocks:
            data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)

            market_data = load_market_data(data_dir, stock)
            if market_data is not None:
                self._plot_market_data(market_data, stock)

                if self.prediction_check.isChecked():
                    self._plot_predictions(market_data, stock)

                if self.pnl_check.isChecked():
                    self._plot_pnl(market_data, stock)

                del market_data

            trade_data = load_trade_data(data_dir, stock)
            if trade_data is not None:
                self._plot_trade_data(trade_data, stock)
                del trade_data

        self._update_plot_layout()
        gc.collect()

    def _update_plot_layout(self):
        # Price chart
        self.ax_price.set_xlabel('')
        self.ax_price.set_ylabel('Price')
        self.ax_price.set_title(f"{self.period_combo.currentText()} - Selected Stocks")
        if self.ax_price.get_lines() or self.ax_price.collections:
            self.ax_price.legend()

        # PNL chart
        if self.pnl_check.isChecked():
            self.ax_pnl.set_visible(True)
            self.ax_pnl.set_xlabel('Time')
            if self.pnl_percent_check.isChecked():
                self.ax_pnl.set_ylabel('PNL (%)')
            else:
                self.ax_pnl.set_ylabel('PNL ($)')
            if self.ax_pnl.get_lines():
                self.ax_pnl.legend()
        else:
            self.ax_pnl.set_visible(False)

        plt.tight_layout()
        self.canvas.draw()

    def update_plot_visibility(self):
        # Update original plot visibilities
        visibility_map = {
            'bid': self.bid_price_check.isChecked(),
            'ask': self.ask_price_check.isChecked(),
            'trade': self.trades_check.isChecked(),
            'model_prediction': self.model_prediction_check.isChecked()
        }

        for line, key in self.plot_lines.items():
            line.set_visible(any(
                vis_type in key
                for vis_type in visibility_map
                if visibility_map[vis_type]
            ))

        std_dev_visibility = {
            '30s': self.std_dev_30s_check.isChecked(),
            '60s': self.std_dev_60s_check.isChecked()
        }

        for fill, key in self.std_dev_fills.items():
            fill.set_visible(any(
                dev_type in key
                for dev_type in std_dev_visibility
                if std_dev_visibility[dev_type]
            ))

        for line in self.prediction_lines:
            line.set_visible(self.prediction_check.isChecked())
            
        for line in self.minmax_lines:
            line.set_visible(self.minmax_lines_check.isChecked())

        # Update PNL visibility
        self.ax_pnl.set_visible(self.pnl_check.isChecked())
        if self.pnl_check.isChecked():
            # Reload data to switch between percentage and absolute values
            self.load_and_plot_data()
        
        for key, line in self.prediction_lines.items():
            line.set_visible(self.prediction_check.isChecked())
            if f"{key.split('_')[0]}_confidence" in self.prediction_plotter.confidence_bands:
                self.prediction_plotter.confidence_bands[f"{key.split('_')[0]}_confidence"].set_visible(
                    self.prediction_check.isChecked()
                )

        self.canvas.draw()

    def closeEvent(self, event):
        plt.close(self.figure)
        self.plot_lines.clear()
        self.std_dev_fills.clear()
        self.prediction_lines.clear()
        self.pnl_lines.clear()
        self.minmax_lines.clear()
        gc.collect()
        super().closeEvent(event)