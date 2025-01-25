import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QComboBox, QWidget, QPushButton)
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

logging.basicConfig(level=logging.ERROR)

class MarketDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 800, 600)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
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
        
        for stock in ['A', 'B', 'C', 'D', 'E']:
            self.stock_combo.addItem(stock)

    def auto_load_data(self):
        period = self.period_combo.currentText()
        stock = self.stock_combo.currentText()
        
        data_dir = os.path.join(self.base_dir, 'TrainingData', period, stock)
        
        market_data = self.load_market_data(data_dir, stock)
        trade_data = self.load_trade_data(data_dir, stock)
        
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
        self.ax.clear()
        
        if market_data is not None and not market_data.empty:
            try:
                market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')
                self.ax.plot(market_data['timestamp'], market_data['bidPrice'], label='Bid Price')
                self.ax.plot(market_data['timestamp'], market_data['askPrice'], label='Ask Price')
            except Exception as e:
                logging.error(f"Error plotting market data: {e}")
        
        if trade_data is not None and not trade_data.empty:
            try:
                trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')
                self.ax.scatter(trade_data['timestamp'], trade_data['price'], color='red', label='Trade', s=trade_data.get('volume', 50))
            except Exception as e:
                logging.error(f"Error plotting trade data: {e}")
        
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')
        
        if len(self.ax.get_lines()) > 0 or len(self.ax.collections) > 0:
            self.ax.legend()
        
        self.ax.set_title(f"{self.period_combo.currentText()} - Stock {self.stock_combo.currentText()}")
        
        plt.tight_layout()
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = MarketDataViewer()
    viewer.show()
    sys.exit(app.exec_())
