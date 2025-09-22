import datetime
import os
import pandas as pd
import requests
import time

from src.data.cache import get_cache
from src.data.models import (
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    FinancialMetricsResponse,
    Price,
    PriceResponse,
    LineItem,
    LineItemResponse,
    InsiderTrade,
    InsiderTradeResponse,
    CompanyFactsResponse,
    AlphaVantageCompanyNewsResponse,
    BalanceSheetEquity,
    BalanceSheetAssets,
    BalanceSheetAssetsResponse,
    BalanceSheetLiabilities,
    CashFlowStatement,
    IncomeStatement,
)
from src.data.financial_metrics_calculator import FinancialMetricsCalculator

from datetime import timedelta, datetime

# Global cache instance
_cache = get_cache()

DBPATH = 'sqlite:///../trading/history.db'

def _get_ticker_daily_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Get ticker daily data from the database."""
    start_date_object = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_object = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    query = 'SELECT * FROM "' + ticker + '" WHERE Date > ? AND Date <= ? ORDER BY Date ASC'
    try:
        data = pd.read_sql(query, DBPATH, params = (start_date_object, end_date_object))
        if len(data) == 0:
            return pd.DataFrame()
        else:
            data['Date'] = pd.to_datetime(data['Date'])
            return data
    except Exception as e:
        print(f"Error getting ticker daily data: {e}")
        return pd.DataFrame()


def _make_api_request(url: str, headers: dict, method: str = "GET", json_data: dict = None, max_retries: int = 3) -> requests.Response:
    """
    Make an API request with rate limiting handling and moderate backoff.
    
    Args:
        url: The URL to request
        headers: Headers to include in the request
        method: HTTP method (GET or POST)
        json_data: JSON data for POST requests
        max_retries: Maximum number of retries (default: 3)
    
    Returns:
        requests.Response: The response object
    
    Raises:
        Exception: If the request fails with a non-429 error
    """
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        else:
            response = requests.get(url, headers=headers)
        
        if response.status_code == 429 and attempt < max_retries:
            # Linear backoff: 60s, 90s, 120s, 150s...
            delay = 60 + (30 * attempt)
            print(f"Rate limited (429). Attempt {attempt + 1}/{max_retries + 1}. Waiting {delay}s before retrying...")
            time.sleep(delay)
            continue
        
        # Return the response (whether success, other errors, or final 429)
        return response


def get_prices(ticker: str, start_date: str, end_date: str, api_key: str = None) -> list[Price]:
    """Fetch price data from cache or API."""
    # Create a cache key that includes all parameters to ensure exact matches
    cache_key = f"{ticker}_{start_date}_{end_date}"
    
    # Check cache first - simple exact match
    if cached_data := _cache.get_prices(cache_key):
        return [Price(**price) for price in cached_data]

    # Check if data is already in the database
    df = _get_ticker_daily_data(ticker, start_date, end_date)
    if not df.empty:
        # Convert Date column from datetime to date string format (YYYY-MM-DD)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        # Rename Date column to time
        df = df.rename(columns={'Date': 'time', 'Open': 'open', 'Close': 'close', 'High': 'high', 'Low': 'low', 'Volume': 'volume'})
        prices_dict = df.to_dict(orient="records")
        prices = [Price(**price) for price in prices_dict]
        _cache.set_prices(cache_key, [p.model_dump() for p in prices])
        return prices

    return []

#references:
#https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60balance_sheet_assets%60%0AWHERE+act_symbol+%3D+%27AMD%27+and+period+%3D+%27Quarter%27+and+date+%3E+%272010-01-01%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A

def get_balance_sheet_assets(ticker: str, end_date: str, period: str = "Quarter") -> list[BalanceSheetAssets]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60balance_sheet_assets%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3E+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
    response = _make_api_request(balance_sheet_api, headers={})
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    
    # Check if query was successful
    if data.get("query_execution_status") != "Success":
        raise Exception(f"Query failed: {data.get('query_execution_message', 'Unknown error')}")
    
    # Extract rows from DoltHub response format
    rows = data.get("rows", [])
    if not rows:
        return []
    
    # Convert rows to BalanceSheetAssets objects
    balance_sheet_assets = []
    for row in rows:
        try:
            asset = BalanceSheetAssets(**row)
            balance_sheet_assets.append(asset)
        except Exception as e:
            print(f"Warning: Failed to parse row {row.get('date', 'unknown')}: {e}")
            continue
    
    return balance_sheet_assets


def get_balance_sheet_equity(ticker: str, end_date: str, period: str = "Quarter") -> list[BalanceSheetEquity]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60balance_sheet_equity%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3E+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
    response = _make_api_request(balance_sheet_api, headers={})
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    
    # Check if query was successful
    if data.get("query_execution_status") != "Success":
        raise Exception(f"Query failed: {data.get('query_execution_message', 'Unknown error')}")
    
    # Extract rows from DoltHub response format
    rows = data.get("rows", [])
    if not rows:
        return []
    
    # Convert rows to BalanceSheetEquity objects
    balance_sheet_equity = []
    for row in rows:
        try:
            equity = BalanceSheetEquity(**row)
            balance_sheet_equity.append(equity)
        except Exception as e:
            print(f"Warning: Failed to parse row {row.get('date', 'unknown')}: {e}")
            continue
    
    return balance_sheet_equity


def get_balance_sheet_liabilities(ticker: str, end_date: str, period: str = "Quarter") -> list[BalanceSheetLiabilities]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60balance_sheet_liabilities%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3E+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
    response = _make_api_request(balance_sheet_api, headers={})
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    
    # Check if query was successful
    if data.get("query_execution_status") != "Success":
        raise Exception(f"Query failed: {data.get('query_execution_message', 'Unknown error')}")
    
    # Extract rows from DoltHub response format
    rows = data.get("rows", [])
    if not rows:
        return []
    
    # Convert rows to BalanceSheetLiabilities objects
    balance_sheet_liabilities = []
    for row in rows:
        try:
            liability = BalanceSheetLiabilities(**row)
            balance_sheet_liabilities.append(liability)
        except Exception as e:
            print(f"Warning: Failed to parse row {row.get('date', 'unknown')}: {e}")
            continue
    
    return balance_sheet_liabilities



def get_cash_flow_statement(ticker: str, end_date: str, period: str = "Quarter") -> list[CashFlowStatement]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60cash_flow_statement%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3E+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
    response = _make_api_request(balance_sheet_api, headers={})
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    
    # Check if query was successful
    if data.get("query_execution_status") != "Success":
        raise Exception(f"Query failed: {data.get('query_execution_message', 'Unknown error')}")
    
    # Extract rows from DoltHub response format
    rows = data.get("rows", [])
    if not rows:
        return []
    
    # Convert rows to CashFlowStatement objects
    cash_flow_statement = []
    for row in rows:
        try:
            cash_flow = CashFlowStatement(**row)
            cash_flow_statement.append(cash_flow)
        except Exception as e:
            print(f"Warning: Failed to parse row {row.get('date', 'unknown')}: {e}")
            continue
    
    return cash_flow_statement


def get_income_statement(ticker: str, end_date: str, period: str = "Quarter") -> list[IncomeStatement]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60income_statement%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3E+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
    response = _make_api_request(balance_sheet_api, headers={})
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    
    # Check if query was successful
    if data.get("query_execution_status") != "Success":
        raise Exception(f"Query failed: {data.get('query_execution_message', 'Unknown error')}")
    
    # Extract rows from DoltHub response format
    rows = data.get("rows", [])
    if not rows:
        return []
    
    # Convert rows to IncomeStatement objects
    income_statement = []
    for row in rows:
        try:
            income = IncomeStatement(**row)
            income_statement.append(income)
        except Exception as e:
            print(f"Warning: Failed to parse row {row.get('date', 'unknown')}: {e}")
            continue
    
    return income_statement


def get_financial_metrics(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[FinancialMetrics]:
    """Fetch financial metrics from cache or API."""
    # Create a cache key that includes all parameters to ensure exact matches
    cache_key = f"{ticker}_{period}_{end_date}_{limit}"
    
    # Check cache first - simple exact match
    if cached_data := _cache.get_financial_metrics(cache_key):
        return [FinancialMetrics(**metric) for metric in cached_data]

    # If not in cache, fetch from API
    if period == "ttm":
        period = "Quarter"
    else:
        period = "Year"

    balance_sheet_assets = get_balance_sheet_assets(ticker, end_date, period)
    balance_sheet_equity = get_balance_sheet_equity(ticker, end_date, period)
    balance_sheet_liabilities = get_balance_sheet_liabilities(ticker, end_date, period)
    cash_flow_statement = get_cash_flow_statement(ticker, end_date, period)
    income_statement = get_income_statement(ticker, end_date, period)

    financial_metrics = FinancialMetricsCalculator.calculate_metrics(
        ticker,
        balance_sheet_assets,
        balance_sheet_equity,
        balance_sheet_liabilities,
        cash_flow_statement,
        income_statement)

    if not financial_metrics:
        return []

    # Cache the results as dicts using the comprehensive cache key
    _cache.set_financial_metrics(cache_key, [m.model_dump() for m in financial_metrics])
    return financial_metrics


def search_line_items(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[LineItem]:
    """Fetch line items from API."""
    # If not in cache or insufficient data, fetch from API
    headers = {}
    financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if financial_api_key:
        headers["X-API-KEY"] = financial_api_key

    url = "https://api.financialdatasets.ai/financials/search/line-items"

    body = {
        "tickers": [ticker],
        "line_items": line_items,
        "end_date": end_date,
        "period": period,
        "limit": limit,
    }
    response = _make_api_request(url, headers, method="POST", json_data=body)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")
    data = response.json()
    response_model = LineItemResponse(**data)
    search_results = response_model.search_results
    if not search_results:
        return []

    # Cache the results
    return search_results[:limit]

APIKEY='FK8PO265QYZSBYE1'

def get_insider_trades(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[InsiderTrade]:
    """Fetch insider trades from cache or API."""
    # Create a cache key that includes all parameters to ensure exact matches
    cache_key = f"{ticker}_{start_date or 'none'}_{end_date}_{limit}"
    
    # Check cache first - simple exact match
    if cached_data := _cache.get_insider_trades(cache_key):
        return [InsiderTrade(**trade) for trade in cached_data]

    # If not in cache, fetch from API
    current_end_date = end_date

    url = f"https://www.alphavantage.co/query?function=INSIDER_TRANSACTIONS&symbol={ticker}&apikey="+APIKEY
    response = _make_api_request(url, headers={})
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    trades = data['data']
    print("got data", trades)
    if not trades:
        return []
    # Convert the raw data to InsiderTrade objects with field mapping
    insider_trades = []
    for trade_data in trades:
        if trade_data.get("transaction_date") > current_end_date:
            continue
        if start_date and trade_data.get("transaction_date") < start_date:
            break

        insider_trade = InsiderTrade(
                    ticker=trade_data.get("ticker"),
                    issuer=None,  # Not provided in your data
                    name=trade_data.get("executive"),  # Map executive to name
                    title=trade_data.get("executive_title"),  # Map executive_title to title
                    is_board_director=None,  # Not provided in your data
                    transaction_date=trade_data.get("transaction_date"),
                    transaction_shares=float(trade_data.get("shares", 0)) if trade_data.get("shares") else None,
                    transaction_price_per_share=float(trade_data.get("share_price", 0)) if trade_data.get("share_price") else None,
                    transaction_value=None,  # Not provided, could calculate if needed
                    shares_owned_before_transaction=None,  # Not provided in your data
                    shares_owned_after_transaction=None,  # Not provided in your data
                    security_title=trade_data.get("security_type"),  # Map security_type to security_title
                    filing_date=trade_data.get("transaction_date")  # Use transaction_date as filing_date fallback
                )
        insider_trades.append(insider_trade)
        if len(insider_trades) >= limit:
            break

    if not insider_trades:
        return []

    # Cache the results using the comprehensive cache key
    _cache.set_insider_trades(cache_key, [trade.model_dump() for trade in insider_trades])
    return insider_trades


def get_company_news(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[CompanyNews]:
    """Fetch company news from cache or API."""
    # Convert start_date from YYYY-MM-DD to YYYYMMDDTHHMM format with HHMM=0000
    formatted_start_date = None
    if start_date:
        # Parse YYYY-MM-DD format and convert to YYYYMMDDTHHMM
        formatted_start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y%m%dT0000")
    if len(end_date) > 0:
        formatted_end_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%Y%m%dT0000")
    
    # Create a cache key that includes all parameters to ensure exact matches
    cache_key = f"{ticker}_{start_date or 'none'}_{end_date}_{limit}"
    
    # Check cache first - simple exact match
    if cached_data := _cache.get_company_news(cache_key):
        return [CompanyNews(**news) for news in cached_data]

    # If not in cache, fetch from API
    # Build URL for AlphaVantage NEWS_SENTIMENT API
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={APIKEY}"
    if formatted_start_date:
        url += f"&time_from={formatted_start_date}"
    if formatted_end_date:
        url += f"&time_to={formatted_end_date}"
    url += f"&limit={limit}"

    response = _make_api_request(url, headers={})
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {ticker} - {response.status_code} - {response.text}")

    data = response.json()
    alpha_response = AlphaVantageCompanyNewsResponse(**data)
    
    # Convert AlphaVantage news to CompanyNews format
    all_news = []
    for news_item in alpha_response.feed:
        # Find the ticker sentiment that matches our requested ticker
        matching_ticker_sentiment = None
        for ticker_sentiment in news_item.ticker_sentiments:
            if ticker_sentiment.ticker == ticker:
                matching_ticker_sentiment = ticker_sentiment
                break
        
        # Only include news items that mention our ticker
        if matching_ticker_sentiment:
            converted_news = CompanyNews(
                ticker=ticker,
                title=news_item.title,
                author=news_item.authors[0], # Use the first author as the author
                source=news_item.source,
                date=news_item.time_published,
                url=news_item.url,
                sentiment=matching_ticker_sentiment.ticker_sentiment_label
            )
            all_news.append(converted_news)

    if not all_news:
        return []

    # Cache the results using the comprehensive cache key
    _cache.set_company_news(cache_key, [news.model_dump() for news in all_news])
    return all_news


def _get_balance_sheet_equity_data(ticker: str, target_date: str) -> BalanceSheetEquity | None:
    """Load balance sheet equity data from CSV file."""
    try:
        # Construct CSV file path based on ticker (assuming naming convention)
        csv_path = f"src/data/balance_sheet_equity_{ticker.lower()}.csv"
        if not os.path.exists(csv_path):
            print(f"Balance sheet equity CSV not found: {csv_path}")
            return None
        
        equity_df = pd.read_csv(csv_path)
        
        # Find the closest date match (prefer exact match, then most recent before target_date)
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        # Filter for quarterly data first, then try any period
        quarterly_data = equity_df[equity_df['period'] == 'Quarter'].copy()
        if not quarterly_data.empty:
            quarterly_data['date_dt'] = pd.to_datetime(quarterly_data['date'])
            # Find exact match first
            exact_match = quarterly_data[quarterly_data['date'] == target_date]
            if not exact_match.empty:
                return BalanceSheetEquity(**exact_match.iloc[0].to_dict())
            
            # Find most recent date before target_date
            before_target = quarterly_data[quarterly_data['date_dt'] <= target_dt]
            if not before_target.empty:
                latest_row = before_target.loc[before_target['date_dt'].idxmax()]
                return BalanceSheetEquity(**latest_row.to_dict())
        
        # Fallback to any available data
        if not equity_df.empty:
            equity_df['date_dt'] = pd.to_datetime(equity_df['date'])
            before_target = equity_df[equity_df['date_dt'] <= target_dt]
            if not before_target.empty:
                latest_row = before_target.loc[before_target['date_dt'].idxmax()]
                return BalanceSheetEquity(**latest_row.to_dict())
        
        return None
    except Exception as e:
        print(f"Error loading balance sheet equity data: {e}")
        return None


def get_market_cap(
    ticker: str,
    end_date: str,
    api_key: str = None,
) -> float | None:
    """Calculate market cap using FinancialMetricsCalculator model (market_price * shares_outstanding)."""
    try:
        # Get current stock price from the most recent available data
        prices = get_prices(ticker, end_date, end_date, api_key=api_key)
        if not prices:
            # Try to get prices from a few days back if exact date not available
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            for i in range(1, 8):  # Try up to 7 days back
                prev_date = (end_dt - timedelta(days=i)).strftime('%Y-%m-%d')
                prices = get_prices(ticker, prev_date, prev_date, api_key=api_key)
                if prices:
                    break
        
        if not prices:
            print(f"Could not find price data for {ticker} around {end_date}")
            return None
        
        current_price = prices[0].close  # Use closing price
        
        # Get shares outstanding from balance sheet equity data
        equity_data = _get_balance_sheet_equity_data(ticker, end_date)
        if not equity_data or not equity_data.shares_outstanding:
            print(f"Could not find shares outstanding for {ticker} around {end_date}")
            return None
        
        # Calculate market cap using FinancialMetricsCalculator logic
        calculator = FinancialMetricsCalculator(market_price=current_price)
        market_cap = calculator._calculate_market_cap(equity_data.shares_outstanding)
        
        return market_cap
    
    except Exception as e:
        print(f"Error calculating market cap for {ticker}: {e}")
        return None


def prices_to_df(prices: list[Price]) -> pd.DataFrame:
    """Convert prices to a DataFrame."""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df


# Update the get_price_data function to use the new functions
def get_price_data(ticker: str, start_date: str, end_date: str, api_key: str = None) -> pd.DataFrame:
    prices = get_prices(ticker, start_date, end_date, api_key=api_key)
    return prices_to_df(prices)
