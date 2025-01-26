import os
import pandas as pd
import logging

logging.basicConfig(level=logging.ERROR)

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