import os
import pandas as pd
import logging
from typing import Optional, Iterator, Dict
from datetime import datetime
import numpy as np
from pathlib import Path
from functools import lru_cache
import pickle
from hashlib import md5

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MarketDataLoader:
    CHUNK_SIZE = 500000  #Play around with this!!! the optimal value will depend on hardware :)
    DTYPE_MAP = {
        'timestamp': 'str',
        'bidPrice': 'float32',
        'askPrice': 'float32',
        'bidQuantity': 'int32',
        'askQuantity': 'int32'
    }
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._setup_cache()
    
    def _setup_cache(self) -> None:
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
    def _get_data_hash(self, data_dir: str, stock: str) -> str:
        files = self._get_file_list(data_dir, stock)
        hash_content = []
        
        for file in files: #might be flawed, tried to make a unique hash based on file metadata
            file_path = Path(data_dir) / file
            try:
                mtime = os.path.getmtime(file_path)
                size = os.path.getsize(file_path)
                hash_content.append(f"{file}:{mtime}:{size}")
            except OSError:
                continue
                
        return md5(":".join(hash_content).encode()).hexdigest()
    
    @staticmethod
    def _parse_timestamp(df: pd.DataFrame) -> pd.DataFrame:
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='%H:%M:%S.%f')
        return df
    
    def _get_cached_path(self, data_dir: str, stock: str) -> Optional[Path]:
        if not self.cache_dir:
            return None
        data_hash = self._get_data_hash(data_dir, stock)
        return self.cache_dir / f"market_data_{stock}_{data_hash}.pkl"
    
    @lru_cache(maxsize=32) #caps to 32 file lists to avoid repeated directry scns
    def _get_file_list(self, data_dir: str, stock: str) -> list:
        try:
            return sorted(
                f for f in os.listdir(data_dir)
                if f.startswith(f"market_data_{stock}") and f.endswith('.csv')
            )
        except FileNotFoundError:
            logging.error(f"Directory not found: {data_dir}")
            return []
    
    def load_market_data_chunks(self, data_dir: str, stock: str) -> Iterator[pd.DataFrame]:
        files = self._get_file_list(data_dir, stock)
        if not files:
            return
        
        for file in files:
            file_path = Path(data_dir) / file
            try:
                for chunk in pd.read_csv(
                    file_path,
                    dtype=self.DTYPE_MAP,
                    chunksize=self.CHUNK_SIZE,
                    engine='c'
                ):
                    chunk = self._parse_timestamp(chunk)
                    #downcasts to smaller data types (if possible) should optimize memory :)
                    for col in chunk.select_dtypes(include=['float64']).columns:
                        chunk[col] = pd.to_numeric(chunk[col], downcast='float')
                    for col in chunk.select_dtypes(include=['int64']).columns:
                        chunk[col] = pd.to_numeric(chunk[col], downcast='integer')
                    yield chunk
                    
            except Exception as e:
                logging.error(f"Error reading file {file_path}: {e}")
    
    def load_market_data(self, data_dir: str, stock: str) -> Optional[pd.DataFrame]:
        cached_path = self._get_cached_path(data_dir, stock)
        
        if cached_path and cached_path.exists():
            try:
                with cached_path.open('rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logging.error(f"Error reading cache {cached_path}: {e}")
        
        chunks = []
        total_size = 0
        max_memory = 7e9  #limits max memory (7Gb)
        
        for chunk in self.load_market_data_chunks(data_dir, stock):
            chunk_size = chunk.memory_usage(deep=True).sum()
            if total_size + chunk_size > max_memory:
                logging.warning("Memory limit reached, spooky shenanigans could happen now :(")
                break
            chunks.append(chunk)
            total_size += chunk_size
            
        if not chunks:
            return None
            
        result = pd.concat(chunks, ignore_index=True)
        
        # Cache results
        if cached_path:
            try:
                with cached_path.open('wb') as f:
                    pickle.dump(result, f, protocol=4) 
            except Exception as e:
                logging.error(f"Error writing cache {cached_path}: {e}")
        
        return result

    @staticmethod
    def load_trade_data(data_dir: str, stock: str) -> Optional[pd.DataFrame]: #basically the same thing as load_market_data, could make the code more modular, unfortunately I don't fell like doing that rn
        file_path = Path(data_dir) / f"trade_data_{stock}.csv"
        
        try:
            df = pd.read_csv(
                file_path,
                dtype={
                    'timestamp': 'str',
                    'price': 'float32',
                    'quantity': 'int32'
                },
                engine='c'
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%H:%M:%S.%f')
            
            for col in df.select_dtypes(include=['float64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='float')
            for col in df.select_dtypes(include=['int64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='integer')
                
            return df
        except FileNotFoundError:
            logging.error(f"Trade data file not found: {file_path}")
            return None
        except Exception as e:
            logging.error(f"Error reading trade data {file_path}: {e}")
            return None