import os
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QWidget, QCheckBox)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib.pyplot as plt
from data_loader import MarketDataLoader
from price_prediction import predict_price_changes
import pandas as pd
from typing import Dict, Optional
import gc
from concurrent.futures import ThreadPoolExecutor

from trading_strategy import TradingStrategy, calculate_trading_metrics


class MarketDataViewer(QMainWindow):
    STOCKS = ['A', 'B', 'C', 'D', 'E']
    VISUALIZATION_TOGGLES = [
        ('bid_price_check', "Bid Price", True),
        ('ask_price_check', "Ask Price", True),
        ('trades_check', "Trades", True),
        ('prediction_check', "Price Prediction", True),
        ('min_max_check', "Min/Max Lines", False),
        ('std_dev_30s_check', "30s Std Dev", False),
        ('std_dev_60s_check', "60s Std Dev", False),
        ('pnl_check', "Show PNL", True),
        ('pnl_percent_check', "PNL as %", True)
    ]
    INITIAL_INVESTMENT = 1_000_000

    def __init__(self, cache_dir: Optional[str] = None):
        super().__init__()
        self.last_selected_stocks = set()
        self.last_selected_period = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.plot_elements: Dict = {}
        self.data_loader = MarketDataLoader(cache_dir=cache_dir)
        self._setup_ui()
        self._connect_signals()
        self.last_prediction_state = self.prediction_check.isChecked()
        self.last_pnl_state = self.pnl_check.isChecked()
        self.last_pnl_percent_state = self.pnl_percent_check.isChecked()
        self.last_bid_price_state = self.bid_price_check.isChecked()
        self.last_ask_price_state = self.ask_price_check.isChecked()
        self.last_trades_state = self.trades_check.isChecked()

    def _setup_ui(self):
        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 1200, 900)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        main_layout.addLayout(self._create_controls_layout())
        main_layout.addLayout(self._create_stock_layout())
        main_layout.addLayout(self._create_toggle_layout())

        self.figure, (self.ax_price, self.ax_pnl) = plt.subplots(2, 1, figsize=(12, 9), height_ratios=[2, 1])
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

    def _create_controls_layout(self):
        layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.period_combo.addItems([f"Period{i}" for i in range(1, 21)]) #should put a space between text and number
        self.period_combo.setCurrentText("Period1")

        self.load_button = QPushButton("Load Data")
        layout.addWidget(self.period_combo)
        layout.addWidget(self.load_button)
        return layout

    def _create_stock_layout(self):
        layout = QHBoxLayout()
        self.stock_checkboxes = {stock: QCheckBox(stock) for stock in self.STOCKS}
        self.stock_checkboxes['A'].setChecked(True)
        for checkbox in self.stock_checkboxes.values():
            layout.addWidget(checkbox)
        return layout

    def _create_toggle_layout(self):
        layout = QHBoxLayout()
        for toggle_attr, label_text, default_state in self.VISUALIZATION_TOGGLES:
            checkbox = QCheckBox(label_text)
            checkbox.setChecked(default_state)
            setattr(self, toggle_attr, checkbox)
            layout.addWidget(checkbox)
        return layout

    def _connect_signals(self):
        self.load_button.clicked.connect(self.load_and_plot_data)
        for toggle_attr, _, _ in self.VISUALIZATION_TOGGLES:
            toggle = getattr(self, toggle_attr)
            toggle.stateChanged.connect(self.update_plot_visibility)

    def load_and_plot_data(self):
        period = self.period_combo.currentText()
        selected_stocks = [stock for stock, checkbox in self.stock_checkboxes.items()
                           if checkbox.isChecked()]
        
        prediction_toggle_changed = self.prediction_check.isChecked() != self.last_prediction_state
        predictions_need_update = (selected_stocks != self.last_selected_stocks) or \
                            (period != self.last_selected_period) or \
                            prediction_toggle_changed
        
        pnl_toggle_changed = self.pnl_check.isChecked() != self.last_pnl_state or self.pnl_percent_check.isChecked() != self.last_pnl_percent_state
        pnl_need_update = (selected_stocks != self.last_selected_stocks) or \
                            (period != self.last_selected_period) or \
                            pnl_toggle_changed
        
        bid_price_toggle_changed = self.bid_price_check.isChecked() != self.last_bid_price_state
        bid_price_need_update = (selected_stocks != self.last_selected_stocks) or \
                                    (period != self.last_selected_period) or \
                                    bid_price_toggle_changed
        
        ask_price_toggle_changed = self.ask_price_check.isChecked() != self.last_ask_price_state
        ask_price_need_update = (selected_stocks != self.last_selected_stocks) or \
                                    (period != self.last_selected_period) or \
                                    ask_price_toggle_changed
        
        trades_toggle_changed = self.trades_check.isChecked() != self.last_trades_state
        trades_need_update = (selected_stocks != self.last_selected_stocks) or \
                                    (period != self.last_selected_period) or \
                                    trades_toggle_changed


        self._clear_plots(not predictions_need_update, not pnl_need_update, not bid_price_need_update, not ask_price_need_update, not trades_need_update)

        with ThreadPoolExecutor() as executor:
            futures = []

            for stock in selected_stocks:
                data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)

                market_data = self.data_loader.load_market_data(data_dir, stock)
                if market_data is not None:
                    if self.bid_price_check.isChecked() and bid_price_need_update:
                        futures.append(executor.submit(self._plot_bid_price, market_data, stock))
                    if not bid_price_need_update:
                        print("bids already updated")
                    if self.ask_price_check.isChecked() and ask_price_need_update:
                        futures.append(executor.submit(self._plot_ask_price, market_data, stock))
                    if not ask_price_need_update:
                        print("asks already updated")

                    # Run plot_predictions and calculate_and_plot_pnl in parallel
                    if self.prediction_check.isChecked()  and predictions_need_update: #should check if it actually changed
                        futures.append(executor.submit(self._plot_predictions, market_data, stock))
                    if not predictions_need_update:
                        print("predictions already updated")

                    if self.pnl_check.isChecked() and pnl_need_update: #same here no need to recalc if it hasn't changed
                        futures.append(executor.submit(self._calculate_and_plot_pnl, market_data, stock))
                    if not pnl_need_update:
                        print("pnl already updated")

                    del market_data
                    gc.collect()
                if self.trades_check.isChecked() and trades_need_update:
                    trade_data = self.data_loader.load_trade_data(data_dir, stock)
                    if trade_data is not None:
                        futures.append(executor.submit(self._plot_trade_data,trade_data, stock))
                        del trade_data
                        gc.collect()
                if not trades_need_update:
                    print("trades already updated")
                

            # Wait for all futures to complete
            for future in futures: #is this necessary????
                future.result()  

        self._update_plot_layout()

        # Update tracking variables
        self.last_selected_stocks = selected_stocks
        self.last_selected_period = period
        self.last_prediction_state = self.prediction_check.isChecked()
        self.last_pnl_state = self.pnl_check.isChecked()
        self.last_pnl_percent_state = self.pnl_percent_check.isChecked()
        self.last_bid_price_state = self.bid_price_check.isChecked()
        self.last_ask_price_state = self.ask_price_check.isChecked()
        self.last_trades_state = self.trades_check.isChecked()


    def _plot_market_data(self, market_data: pd.DataFrame, stock: str):
        if market_data is None:
            return

        if self.bid_price_check.isChecked():
            line, = self.ax_price.plot(market_data['timestamp'],
                                       market_data['bidPrice'],
                                       label=f'{stock} Bid Price')
            self.plot_elements[f'{stock}_bid'] = line

        if self.ask_price_check.isChecked():
            line, = self.ax_price.plot(market_data['timestamp'],
                                       market_data['askPrice'],
                                       label=f'{stock} Ask Price')
            self.plot_elements[f'{stock}_ask'] = line

        self._plot_standard_deviation(market_data, stock) #Std and min/max could also be done in parallel
        self._plot_min_max_lines(market_data, stock)
    
    def _plot_bid_price(self, market_data: pd.DataFrame, stock: str):
        if market_data is None:
            return

        if self.bid_price_check.isChecked():
            line, = self.ax_price.plot(market_data['timestamp'],
                                       market_data['bidPrice'],
                                       label=f'{stock} Bid Price')
            self.plot_elements[f'{stock}_bid'] = line

    def _plot_ask_price(self, market_data: pd.DataFrame, stock: str):
        if market_data is None:
            return
            
        if self.ask_price_check.isChecked():
            line, = self.ax_price.plot(market_data['timestamp'],
                                       market_data['askPrice'],
                                       label=f'{stock} Ask Price')
            self.plot_elements[f'{stock}_ask'] = line

    def _plot_min_max_lines(self, market_data: pd.DataFrame, stock: str):
        if not self.min_max_check.isChecked():
            return

        min_price = market_data['bidPrice'].min() # We could definitely find both in one sweep, could even find them when we initially plot the graph or use Dask
        max_price = market_data['askPrice'].max()

        min_line = self.ax_price.axhline(y=min_price, color='red', linestyle=':',
                                         label=f'{stock} Min Price ({min_price:.2f})')
        max_line = self.ax_price.axhline(y=max_price, color='green', linestyle=':',
                                         label=f'{stock} Max Price ({max_price:.2f})')

        self.plot_elements[f'{stock}_min'] = min_line
        self.plot_elements[f'{stock}_max'] = max_line

    def _plot_standard_deviation(self, market_data: pd.DataFrame, stock: str):
        std_dev_configs = [
            (self.std_dev_30s_check, 30, 'blue'),
            (self.std_dev_60s_check, 60, 'red')
        ]

        for checkbox, window_seconds, color in std_dev_configs:
            if not checkbox.isChecked():
                continue

            window_size = int(window_seconds * 1000)
            std_dev = market_data['bidPrice'].rolling(window=window_size, min_periods=1).std() #I think Panda's has a faster rolling algo
            lower_bound = market_data['bidPrice'] - std_dev
            upper_bound = market_data['bidPrice'] + std_dev

            fill = self.ax_price.fill_between( #I tested this, it is remarkably slow at filling, could consider downsampling or asynchronus ploting
                market_data['timestamp'],
                lower_bound,
                upper_bound,
                alpha=0.2,
                color=color,
                label=f'{stock} {window_seconds}s Std Dev'
            )
            self.plot_elements[f'{stock}_{window_seconds}s_std'] = fill

    def _plot_predictions(self, market_data: pd.DataFrame, stock: str): #I don't think we need to extract timestamp and predicted_price multiple times, we could just extract the whole thing once
        print("calculating predictions")
        prediction_data = predict_price_changes(market_data)
        if prediction_data is None or prediction_data.empty:
            return

        line, = self.ax_price.plot(
            prediction_data['timestamp'], #here we reaccess it every time, could just take out the thing above
            prediction_data['predicted_price'],
            color='orange',
            linestyle='--',
            label=f'{stock} Predicted Price',
            alpha=0.7
        )
        
        last_timestamp = market_data['timestamp'].iloc[-1]
        next_timestamp = last_timestamp + pd.Timedelta(microseconds=1)
        last_predicted_price = prediction_data['predicted_price'].iloc[-1]
        next_predicted_price = last_predicted_price

        print("plotting a dot")
        dot, = self.ax_price.plot(
            [last_timestamp, next_timestamp],
            [last_predicted_price, next_predicted_price],
            color='purple',
            linestyle=':',
            marker='o',
            markersize=5,
            label=f'{stock} Next Prediction'
        )
        self.plot_elements[f'{stock}_prediction'] = line
        self.plot_elements[f'{stock}_prediction_dot'] = dot
        del prediction_data

    def _plot_trade_data(self, trade_data: pd.DataFrame, stock: str):
        if not self.trades_check.isChecked() or trade_data is None:
            return

        line, = self.ax_price.plot(
            trade_data['timestamp'], # same here, I think it be slightly better if we extracted the info first, we could also down sample tbh
            trade_data['price'],
            linestyle='-',
            marker='',
            label=f'{stock} Trade Price',
            alpha=0.7
        )
        self.plot_elements[f'{stock}_trade'] = line

    def _calculate_and_plot_pnl(self, market_data: pd.DataFrame, stock: str): #only the y-axis really changes between % and total, don't need to replot the graph, just change the label and axis
        print("calculating pnl")
        if not self.pnl_check.isChecked() or market_data is None:
            return

        strategy = TradingStrategy()
        pnl_data = strategy.calculate_pnl(market_data)
        metrics = calculate_trading_metrics(pnl_data)

        if pnl_data is None or pnl_data.empty:
            print(f"No PnL data for {stock}")
            return

        if self.pnl_percent_check.isChecked():
            if pnl_data['pnl_percentage'].isna().all():
                print(f"PnL percentage contains NaN values for {stock}")
                return
            line, = self.ax_pnl.plot(
                pnl_data['timestamp'],
                pnl_data['pnl_percentage'],
                label=f'{stock} PnL % (Sharpe: {metrics["sharpe_ratio"]:.2f}, Win: {metrics["win_rate"]:.1f}%)'
            )
            ylabel = 'PnL (%)'
        else:
            if pnl_data['pnl'].isna().all():
                print(f"PnL values contain NaN for {stock}")
                return
            line, = self.ax_pnl.plot(
                pnl_data['timestamp'],
                pnl_data['pnl'],
                label=f'{stock} PnL $ (Max DD: {metrics["max_drawdown"]:.1f}%, Return: {metrics["return_percentage"]:.1f}%)'
            )
            ylabel = 'PnL ($)'

        self.plot_elements[f'{stock}_pnl'] = line
        self.ax_pnl.set_ylabel(ylabel)

        self.ax_pnl.relim()
        self.ax_pnl.autoscale_view()



    def _clear_plots(self, keep_predictions=False, keep_pnl=False, keep_bid_price=False, keep_ask_price=False, keep_trades=False):
        #self.ax_price.cla()
        #self.ax_pnl.cla()
        for key in list(self.plot_elements.keys()):
            if keep_predictions and 'prediction' in key:
                print("found predictions")
                continue
            if keep_pnl and 'pnl' in key:
                print("found pnl")
                continue
            if keep_bid_price and 'bid' in key:
                print("found bids")
                continue
            if keep_ask_price and 'ask' in key:
                print("found who asked")
                continue
            if keep_trades and 'trade' in key:
                print("found trades")
                continue

            print(f"Removing {key}")
            try:
                self.plot_elements[key].remove()
            except NotImplementedError:
                pass
            del self.plot_elements[key]
        gc.collect()

    def _update_plot_layout(self):
        self.ax_price.set_xlabel('')
        self.ax_price.set_ylabel('Price')
        self.ax_price.set_title(f"{self.period_combo.currentText()} - Selected Stocks")
        if self.ax_price.get_lines() or self.ax_price.collections:
            self.ax_price.legend() #shouldnot have to remake the legend if it hasn't changed

        self.ax_pnl.set_visible(self.pnl_check.isChecked())
        if self.pnl_check.isChecked():
            self.ax_pnl.set_xlabel('Time')
            if self.ax_pnl.get_lines():
                self.ax_pnl.legend()

        plt.tight_layout()
        self.canvas.draw() #could draw_idle instead...?

    def update_plot_visibility(self):
        needs_reload = False
        if any(attr in ('pnl_check', 'pnl_percent_check')
               for attr, _, _ in self.VISUALIZATION_TOGGLES
               if getattr(self, attr).isChecked()):
            needs_reload = True

        if needs_reload:
            self.load_and_plot_data()
        else:
            self._update_plot_layout()

    def closeEvent(self, event):
        self._clear_plots()
        plt.close(self.figure)
        super().closeEvent(event)