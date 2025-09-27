import json
import os
import logging
import atexit
from pathlib import Path
from typing import Optional


class Cache:
    """In-memory cache for API responses with disk persistence.
    
    The cache automatically loads data on initialization and saves data on program exit.
    Data is only persisted to disk when save() is called manually or when the program exits.
    """

    def __init__(self, cache_file_path: str | None = None, auto_save_on_exit: bool = True):
        self._prices_cache: dict[str, list[dict[str, any]]] = {}
        self._financial_metrics_cache: dict[str, list[dict[str, any]]] = {}
        self._line_items_cache: dict[str, list[dict[str, any]]] = {}
        self._insider_trades_cache: dict[str, list[dict[str, any]]] = {}
        self._company_news_cache: dict[str, list[dict[str, any]]] = {}
        
        # Set default cache file path
        if cache_file_path is None:
            cache_dir = Path.home() / '.ai_hedge_fund_cache'
            cache_dir.mkdir(exist_ok=True)
            cache_file_path = str(cache_dir / 'market_data_cache.json')
        
        self._cache_file_path = cache_file_path
        self._auto_save_on_exit = auto_save_on_exit
        
        # Try to load existing cache
        self._load_from_disk()
        
        # Register exit handler to save cache when program exits
        if auto_save_on_exit:
            atexit.register(self._save_to_disk)

    def _save_to_disk(self):
        """Save cache data to disk as JSON."""
        try:
            cache_data = {
                'prices': self._prices_cache,
                'financial_metrics': self._financial_metrics_cache,
                'line_items': self._line_items_cache,
                'insider_trades': self._insider_trades_cache,
                'company_news': self._company_news_cache
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self._cache_file_path), exist_ok=True)
            
            with open(self._cache_file_path, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
                
            logging.debug(f"Cache saved to {self._cache_file_path}")
            
        except Exception as e:
            logging.error(f"Failed to save cache to disk: {e}")
    
    def _load_from_disk(self):
        """Load cache data from disk JSON file."""
        try:
            if os.path.exists(self._cache_file_path):
                with open(self._cache_file_path, 'r') as f:
                    cache_data = json.load(f)
                
                self._prices_cache = cache_data.get('prices', {})
                self._financial_metrics_cache = cache_data.get('financial_metrics', {})
                self._line_items_cache = cache_data.get('line_items', {})
                self._insider_trades_cache = cache_data.get('insider_trades', {})
                self._company_news_cache = cache_data.get('company_news', {})
                
                logging.info(f"Cache loaded from {self._cache_file_path}")
            else:
                logging.info("No existing cache file found, starting with empty cache")
                
        except Exception as e:
            logging.error(f"Failed to load cache from disk: {e}")
            # Continue with empty cache if loading fails
    
    def __enter__(self):
        """Context manager entry - returns self."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - saves cache to disk."""
        self._save_to_disk()
        return False  # Don't suppress exceptions
    
    def save(self):
        """Manually save cache to disk."""
        self._save_to_disk()
    
    def get_cache_info(self) -> dict:
        """Get information about the cache contents and file location."""
        return {
            'cache_file_path': self._cache_file_path,
            'file_exists': os.path.exists(self._cache_file_path),
            'prices_tickers': len(self._prices_cache),
            'financial_metrics_tickers': len(self._financial_metrics_cache),
            'line_items_tickers': len(self._line_items_cache),
            'insider_trades_tickers': len(self._insider_trades_cache),
            'company_news_tickers': len(self._company_news_cache),
            'total_tickers': len(set(
                list(self._prices_cache.keys()) + 
                list(self._financial_metrics_cache.keys()) +
                list(self._line_items_cache.keys()) +
                list(self._insider_trades_cache.keys()) +
                list(self._company_news_cache.keys())
            ))
        }
    
    def clear_cache(self):
        """Clear all cache data and remove the disk file."""
        self._prices_cache.clear()
        self._financial_metrics_cache.clear()
        self._line_items_cache.clear()
        self._insider_trades_cache.clear()
        self._company_news_cache.clear()
        
        try:
            if os.path.exists(self._cache_file_path):
                os.remove(self._cache_file_path)
                logging.info("Cache file removed from disk")
        except Exception as e:
            logging.error(f"Failed to remove cache file: {e}")

    def _merge_data(self, existing: list[dict] | None, new_data: list[dict], key_field: str) -> list[dict]:
        """Merge existing and new data, avoiding duplicates based on a key field."""
        if not existing:
            return new_data

        # Create a set of existing keys for O(1) lookup
        existing_keys = {item[key_field] for item in existing}

        # Only add items that don't exist yet
        merged = existing.copy()
        merged.extend([item for item in new_data if item[key_field] not in existing_keys])
        return merged

    def get_prices(self, ticker: str) -> list[dict[str, any]] | None:
        """Get cached price data if available."""
        return self._prices_cache.get(ticker)

    def set_prices(self, ticker: str, data: list[dict[str, any]]):
        """Append new price data to cache."""
        self._prices_cache[ticker] = self._merge_data(self._prices_cache.get(ticker), data, key_field="time")

    def get_financial_metrics(self, ticker: str) -> list[dict[str, any]]:
        """Get cached financial metrics if available."""
        return self._financial_metrics_cache.get(ticker)

    def set_financial_metrics(self, ticker: str, data: list[dict[str, any]]):
        """Append new financial metrics to cache."""
        self._financial_metrics_cache[ticker] = self._merge_data(self._financial_metrics_cache.get(ticker), data, key_field="report_period")

    def get_line_items(self, ticker: str) -> list[dict[str, any]] | None:
        """Get cached line items if available."""
        return self._line_items_cache.get(ticker)

    def set_line_items(self, ticker: str, data: list[dict[str, any]]):
        """Append new line items to cache."""
        self._line_items_cache[ticker] = self._merge_data(self._line_items_cache.get(ticker), data, key_field="report_period")

    def get_insider_trades(self, ticker: str) -> list[dict[str, any]] | None:
        """Get cached insider trades if available."""
        return self._insider_trades_cache.get(ticker)

    def set_insider_trades(self, ticker: str, data: list[dict[str, any]]):
        """Append new insider trades to cache."""
        self._insider_trades_cache[ticker] = self._merge_data(self._insider_trades_cache.get(ticker), data, key_field="filing_date")  # Could also use transaction_date if preferred

    def get_company_news(self, ticker: str) -> list[dict[str, any]] | None:
        """Get cached company news if available."""
        return self._company_news_cache.get(ticker)

    def set_company_news(self, ticker: str, data: list[dict[str, any]]):
        """Append new company news to cache."""
        self._company_news_cache[ticker] = self._merge_data(self._company_news_cache.get(ticker), data, key_field="date")


# Global cache instance
_cache = Cache()


def get_cache() -> Cache:
    """Get the global cache instance."""
    return _cache
