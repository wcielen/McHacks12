import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QWidget, QFileDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Set up logging to only log errors
logging.basicConfig(level=logging.ERROR)

class MarketDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Get the absolute path of the script's directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.setWindowTitle("Market Data Viewer")
        self.setGeometry(100, 100, 800, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Create controls
        controls_layout = QHBoxLayout()
        self.period_combo = QComboBox()
        self.stock_combo = QComboBox()
        self.load_button = QPushButton("Load Data")
        controls_layout.addWidget(self.period_combo)
        controls_layout.addWidget(self.stock_combo)
        controls_layout.addWidget(self.load_button)
        
        # Create matplotlib figure and canvas
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        
        # Add widgets to main layout
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.canvas)
        
        # Connect signals
        self.load_button.clicked.connect(self.load_and_plot_data)
        
        # Initialize combo boxes
        self.initialize_combos()

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
        file_path = os.path.join(data_dir, f"trade_data__{stock}.csv")
        try:
            return pd.read_csv(file_path)
        except FileNotFoundError:
            logging.error(f"Trade data file not found: {file_path}")
            return None

    def plot_data(self, market_data, trade_data):
        self.ax.clear()
        
        # Plot market data
        if market_data is not None and not market_data.empty:
            try:
                market_data['timestamp'] = pd.to_datetime(market_data['timestamp'], format='%H:%M:%S.%f')
                self.ax.plot(market_data['timestamp'], market_data['bidPrice'], label='Bid Price')
                self.ax.plot(market_data['timestamp'], market_data['askPrice'], label='Ask Price')
            except Exception as e:
                logging.error(f"Error plotting market data: {e}")
        
        # Plot trade data
        if trade_data is not None and not trade_data.empty:
            try:
                trade_data['timestamp'] = pd.to_datetime(trade_data['timestamp'], format='%H:%M:%S.%f')
                self.ax.scatter(trade_data['timestamp'], trade_data['price'], color='red', label='Trade', s=trade_data.get('volume', 50))
            except Exception as e:
                logging.error(f"Error plotting trade data: {e}")
        
        # Set labels and title
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Price')
        
        # Only add legend if there are artists
        if len(self.ax.get_lines()) > 0 or len(self.ax.collections) > 0:
            self.ax.legend()
        
        self.ax.set_title(f"{self.period_combo.currentText()} - Stock {self.stock_combo.currentText()}")
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    viewer = MarketDataViewer()
    viewer.show()
    sys.exit(app.exec_())
