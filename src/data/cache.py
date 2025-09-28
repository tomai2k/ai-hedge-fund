import json
import os
import logging
import atexit
from pathlib import Path
from typing import Optional, Dict
from collections import defaultdict
from datetime import datetime


class APIStats:
    """Track API endpoint calls and cache hit/miss statistics."""
    
    def __init__(self):
        self._endpoint_calls: Dict[str, int] = defaultdict(int)
        self._cache_hits: Dict[str, int] = defaultdict(int)
        self._cache_misses: Dict[str, int] = defaultdict(int)
        self._start_time = datetime.now()
        self._last_reset = datetime.now()
    
    def record_cache_hit(self, endpoint: str, cache_key: str = None):
        """Record a cache hit for an endpoint."""
        self._endpoint_calls[endpoint] += 1
        self._cache_hits[endpoint] += 1
        logging.debug(f"Cache HIT for {endpoint}" + (f" (key: {cache_key})" if cache_key else ""))
    
    def record_cache_miss(self, endpoint: str, cache_key: str = None):
        """Record a cache miss for an endpoint."""
        self._endpoint_calls[endpoint] += 1
        self._cache_misses[endpoint] += 1
        logging.debug(f"Cache MISS for {endpoint}" + (f" (key: {cache_key})" if cache_key else ""))
    
    def get_stats(self) -> Dict:
        """Get comprehensive statistics."""
        total_calls = sum(self._endpoint_calls.values())
        total_hits = sum(self._cache_hits.values())
        total_misses = sum(self._cache_misses.values())
        
        endpoint_stats = {}
        for endpoint in set(list(self._endpoint_calls.keys())):
            calls = self._endpoint_calls[endpoint]
            hits = self._cache_hits[endpoint]
            misses = self._cache_misses[endpoint]
            hit_rate = (hits / calls * 100) if calls > 0 else 0
            
            endpoint_stats[endpoint] = {
                'calls': calls,
                'hits': hits,
                'misses': misses,
                'hit_rate_percent': round(hit_rate, 2)
            }
        
        return {
            'summary': {
                'total_calls': total_calls,
                'total_hits': total_hits,
                'total_misses': total_misses,
                'overall_hit_rate_percent': round((total_hits / total_calls * 100) if total_calls > 0 else 0, 2),
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds(),
                'last_reset': self._last_reset.isoformat()
            },
            'endpoints': endpoint_stats
        }
    
    def get_summary(self) -> str:
        """Get a formatted summary string of statistics."""
        stats = self.get_stats()
        summary = stats['summary']
        
        lines = [
            "=== API Cache Statistics ===",
            f"Total API Calls: {summary['total_calls']}",
            f"Cache Hits: {summary['total_hits']}",
            f"Cache Misses: {summary['total_misses']}",
            f"Overall Hit Rate: {summary['overall_hit_rate_percent']}%",
            f"Uptime: {int(summary['uptime_seconds'])} seconds",
            "",
            "Per-Endpoint Statistics:"
        ]
        
        for endpoint, data in stats['endpoints'].items():
            lines.append(f"  {endpoint}:")
            lines.append(f"    Calls: {data['calls']}, Hits: {data['hits']}, Misses: {data['misses']}")
            lines.append(f"    Hit Rate: {data['hit_rate_percent']}%")
        
        return "\n".join(lines)
    
    def reset_stats(self):
        """Reset all statistics."""
        self._endpoint_calls.clear()
        self._cache_hits.clear()
        self._cache_misses.clear()
        self._last_reset = datetime.now()
        logging.info("API statistics reset")
    
    def get_top_endpoints(self, limit: int = 5) -> list:
        """Get the most frequently called endpoints."""
        sorted_endpoints = sorted(
            self._endpoint_calls.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_endpoints[:limit]


class Cache:
    """In-memory cache for API responses with disk persistence.
    
    The cache automatically loads data on initialization and saves data on program exit.
    Data is only persisted to disk when save() is called manually or when the program exits.
    """

    def __init__(self, cache_file_path: str | None = None, auto_save_on_exit: bool = True):
        self._financial_metrics_cache: dict[str, list[dict[str, any]]] = {}
        self._line_items_cache: dict[str, list[dict[str, any]]] = {}
        self._insider_trades_cache: dict[str, list[dict[str, any]]] = {}
        self._company_news_cache: dict[str, list[dict[str, any]]] = {}
        
        # Initialize API statistics
        self._api_stats = APIStats()
        
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
        print(self._api_stats.get_summary())
        """Save cache data to disk as JSON."""
        try:
            cache_data = {
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
    
    def print_api_stats(self):
        """Print API statistics to console immediately."""
        print(self._api_stats.get_summary())
    
    def get_cache_info(self) -> dict:
        """Get information about the cache contents and file location."""
        return {
            'cache_file_path': self._cache_file_path,
            'file_exists': os.path.exists(self._cache_file_path),
            'financial_metrics_tickers': len(self._financial_metrics_cache),
            'line_items_tickers': len(self._line_items_cache),
            'insider_trades_tickers': len(self._insider_trades_cache),
            'company_news_tickers': len(self._company_news_cache),
            'total_tickers': len(set(
                list(self._financial_metrics_cache.keys()) +
                list(self._line_items_cache.keys()) +
                list(self._insider_trades_cache.keys()) +
                list(self._company_news_cache.keys())
            ))
        }
    
    # API Statistics Methods
    def get_api_stats(self) -> Dict:
        """Get API call and cache hit/miss statistics."""
        return self._api_stats.get_stats()
    
    def get_api_stats_summary(self) -> str:
        """Get a formatted summary of API statistics."""
        return self._api_stats.get_summary()
    
    def reset_api_stats(self):
        """Reset API call statistics."""
        self._api_stats.reset_stats()
    
    def get_top_api_endpoints(self, limit: int = 5) -> list:
        """Get the most frequently called API endpoints."""
        return self._api_stats.get_top_endpoints(limit)
    
    def record_cache_miss(self, endpoint: str, cache_key: str = None):
        """Record a cache miss for tracking API statistics."""
        self._api_stats.record_cache_miss(endpoint, cache_key)
    
    def clear_cache(self):
        """Clear all cache data and remove the disk file."""
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

    def get_financial_metrics(self, ticker: str) -> list[dict[str, any]]:
        """Get cached financial metrics if available."""
        result = self._financial_metrics_cache.get(ticker)
        if result is not None:
            self._api_stats.record_cache_hit('get_financial_metrics', ticker)
        return result

    def set_financial_metrics(self, ticker: str, data: list[dict[str, any]]):
        """Append new financial metrics to cache."""
        self._financial_metrics_cache[ticker] = self._merge_data(self._financial_metrics_cache.get(ticker), data, key_field="report_period")

    def get_line_items(self, ticker: str) -> list[dict[str, any]] | None:
        """Get cached line items if available."""
        result = self._line_items_cache.get(ticker)
        if result is not None:
            self._api_stats.record_cache_hit('get_line_items', ticker)
        return result

    def set_line_items(self, ticker: str, data: list[dict[str, any]]):
        """Append new line items to cache."""
        self._line_items_cache[ticker] = self._merge_data(self._line_items_cache.get(ticker), data, key_field="report_period")

    def get_insider_trades(self, ticker: str) -> list[dict[str, any]] | None:
        """Get cached insider trades if available."""
        result = self._insider_trades_cache.get(ticker)
        if result is not None:
            self._api_stats.record_cache_hit('get_insider_trades', ticker)
        return result

    def set_insider_trades(self, ticker: str, data: list[dict[str, any]]):
        """Append new insider trades to cache."""
        self._insider_trades_cache[ticker] = self._merge_data(self._insider_trades_cache.get(ticker), data, key_field="filing_date")  # Could also use transaction_date if preferred

    def get_company_news(self, ticker: str) -> list[dict[str, any]] | None:
        """Get cached company news if available."""
        result = self._company_news_cache.get(ticker)
        if result is not None:
            self._api_stats.record_cache_hit('get_company_news', ticker)
        return result

    def set_company_news(self, ticker: str, data: list[dict[str, any]]):
        """Append new company news to cache."""
        self._company_news_cache[ticker] = self._merge_data(self._company_news_cache.get(ticker), data, key_field="date")


# Global cache instance
_cache = Cache()


def get_cache() -> Cache:
    """Get the global cache instance."""
    return _cache
