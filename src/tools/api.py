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

DBPATH = 'sqlite:////home/tao/dev//trading/history.db'

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
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60balance_sheet_assets%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3C+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
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
    #print(balance_sheet_assets)
    return balance_sheet_assets


def get_balance_sheet_equity(ticker: str, end_date: str, period: str = "Quarter") -> list[BalanceSheetEquity]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60balance_sheet_equity%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3C+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
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
    #print(balance_sheet_equity)
    return balance_sheet_equity


def get_balance_sheet_liabilities(ticker: str, end_date: str, period: str = "Quarter") -> list[BalanceSheetLiabilities]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60balance_sheet_liabilities%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3C+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
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
    #print(balance_sheet_liabilities)
    return balance_sheet_liabilities



def get_cash_flow_statement(ticker: str, end_date: str, period: str = "Quarter") -> list[CashFlowStatement]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60cash_flow_statement%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3C+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
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
    #print(cash_flow_statement)
    return cash_flow_statement


def get_income_statement(ticker: str, end_date: str, period: str = "Quarter") -> list[IncomeStatement]:
    balance_sheet_api = f'https://www.dolthub.com/api/v1alpha1/post-no-preference/earnings/master?q=SELECT+*%0AFROM+%60income_statement%60%0AWHERE+act_symbol+%3D+%27{ticker}%27+and+period+%3D+%27{period}%27+and+date+%3C+%27{end_date}%27%0AORDER+BY+%60date%60+DESC%0ALIMIT+100%3B%0A'
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
    #print(income_statement)
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

    # Fetch financial statement data (returns lists of records by date DESC)
    balance_sheet_assets_list = get_balance_sheet_assets(ticker, end_date, period)
    balance_sheet_equity_list = get_balance_sheet_equity(ticker, end_date, period)
    balance_sheet_liabilities_list = get_balance_sheet_liabilities(ticker, end_date, period)
    cash_flow_statement_list = get_cash_flow_statement(ticker, end_date, period)
    income_statement_list = get_income_statement(ticker, end_date, period)

    if (not balance_sheet_assets_list or not balance_sheet_equity_list or 
        not balance_sheet_liabilities_list or not cash_flow_statement_list or 
        not income_statement_list):
        return []

    # Create dictionaries for quick date-based lookup
    assets_by_date = {asset.date: asset for asset in balance_sheet_assets_list}
    equity_by_date = {equity.date: equity for equity in balance_sheet_equity_list}
    liabilities_by_date = {liability.date: liability for liability in balance_sheet_liabilities_list}
    cash_flow_by_date = {cf.date: cf for cf in cash_flow_statement_list}
    income_by_date = {income.date: income for income in income_statement_list}
    
    # Find common dates across all statements (intersection)
    all_dates = (set(assets_by_date.keys()) & set(equity_by_date.keys()) & 
                set(liabilities_by_date.keys()) & set(cash_flow_by_date.keys()) & 
                set(income_by_date.keys()))
    
    if not all_dates:
        return []
    
    # Sort dates in descending order and limit to requested number
    sorted_dates = sorted(all_dates, reverse=True)[:limit]
    
    financial_metrics = []
    
    for i, date in enumerate(sorted_dates):
        try:
            # Get market price for this date
            try:
                prices = get_prices(ticker, date, date, api_key=api_key)
                if not prices:
                    # Try nearby dates
                    from datetime import datetime, timedelta
                    date_dt = datetime.strptime(date, '%Y-%m-%d')
                    for j in range(1, 8):
                        prev_date = (date_dt - timedelta(days=j)).strftime('%Y-%m-%d')
                        prices = get_prices(ticker, prev_date, prev_date, api_key=api_key)
                        if prices:
                            break
                
                market_price = prices[0].close if prices else 100.0
            except Exception as e:
                market_price = 100.0  # Fallback
            
            # Get financial statement data for this date
            assets = assets_by_date[date]
            equity = equity_by_date[date] 
            liabilities = liabilities_by_date[date]
            cash_flow = cash_flow_by_date[date]
            income = income_by_date[date]
            
            # Try to get previous year data for growth calculations
            previous_period_income = None
            previous_period_equity = None
            previous_period_cash_flow = None
            
            try:
                from datetime import datetime
                current_dt = datetime.strptime(date, '%Y-%m-%d')
                prev_year_dt = current_dt.replace(year=current_dt.year - 1)
                prev_year_date = prev_year_dt.strftime('%Y-%m-%d')
                
                previous_period_income = income_by_date.get(prev_year_date)
                previous_period_equity = equity_by_date.get(prev_year_date)
                previous_period_cash_flow = cash_flow_by_date.get(prev_year_date)
            except:
                pass  # No historical data available
            
            # Create calculator and compute metrics
            calculator = FinancialMetricsCalculator(market_price=market_price)
            financial_metric = calculator.calculate_metrics(
                ticker=ticker,
                assets=assets,
                equity=equity,
                liabilities=liabilities,
                cash_flow=cash_flow,
                income=income,
                previous_period_income=previous_period_income,
                previous_period_equity=previous_period_equity,
                previous_period_cash_flow=previous_period_cash_flow
            )
            
            financial_metrics.append(financial_metric)
            
        except Exception as e:
            print(f"Warning: Failed to calculate metrics for {date}: {e}")
            continue

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
    """Fetch line items from local model classes instead of external API."""
    
    # Convert period format
    if period == "ttm":
        period_query = "Quarter"
    else:
        period_query = "Year"
    
    try:
        # Fetch financial statement data
        balance_sheet_assets_list = get_balance_sheet_assets(ticker, end_date, period_query)
        balance_sheet_equity_list = get_balance_sheet_equity(ticker, end_date, period_query)
        balance_sheet_liabilities_list = get_balance_sheet_liabilities(ticker, end_date, period_query)
        cash_flow_statement_list = get_cash_flow_statement(ticker, end_date, period_query)
        income_statement_list = get_income_statement(ticker, end_date, period_query)
        
        if not any([balance_sheet_assets_list, balance_sheet_equity_list, 
                   balance_sheet_liabilities_list, cash_flow_statement_list, income_statement_list]):
            return []
        
        # Create dictionaries for quick date-based lookup
        assets_by_date = {asset.date: asset for asset in balance_sheet_assets_list}
        equity_by_date = {equity.date: equity for equity in balance_sheet_equity_list}
        liabilities_by_date = {liability.date: liability for liability in balance_sheet_liabilities_list}
        cash_flow_by_date = {cf.date: cf for cf in cash_flow_statement_list}
        income_by_date = {income.date: income for income in income_statement_list}
        
        # Find common dates across all statements
        all_dates = set()
        if assets_by_date: all_dates.update(assets_by_date.keys())
        if equity_by_date: all_dates.update(equity_by_date.keys()) 
        if liabilities_by_date: all_dates.update(liabilities_by_date.keys())
        if cash_flow_by_date: all_dates.update(cash_flow_by_date.keys())
        if income_by_date: all_dates.update(income_by_date.keys())
        
        if not all_dates:
            return []
        
        # Sort dates in descending order and limit
        sorted_dates = sorted(all_dates, reverse=True)[:limit]
        
        results = []
        for date in sorted_dates:
            # Get statements for this date
            assets = assets_by_date.get(date)
            equity = equity_by_date.get(date)
            liabilities = liabilities_by_date.get(date)
            cash_flow = cash_flow_by_date.get(date)
            income = income_by_date.get(date)
            
            # Create LineItem with base fields
            line_item_data = {
                "ticker": ticker,
                "report_period": date,
                "period": period,
                "currency": "USD"  # Default assumption
            }
            
            # Extract requested line items
            for line_item in line_items:
                value = _extract_line_item_value(line_item, assets, equity, liabilities, cash_flow, income)
                if value is not None:
                    line_item_data[line_item] = value
            
            # Create LineItem object (allows extra fields)
            line_item = LineItem(**line_item_data)
            results.append(line_item)
        
        return results
        
    except Exception as e:
        print(f"Error in search_line_items_new: {e}")
        return []


def _extract_line_item_value(
    line_item: str,
    assets: 'BalanceSheetAssets' = None,
    equity: 'BalanceSheetEquity' = None, 
    liabilities: 'BalanceSheetLiabilities' = None,
    cash_flow: 'CashFlowStatement' = None,
    income: 'IncomeStatement' = None
) -> float | None:
    """Extract a specific line item value from financial statement models."""
    
    # Direct field mappings
    field_mappings = {
        # Balance Sheet Assets
        "cash_and_equivalents": ("assets", "cash_and_equivalents"),
        "total_assets": ("assets", "total_assets"),
        "current_assets": ("assets", "total_current_assets"),
        "goodwill_and_intangible_assets": ("assets", "intangibles"),
        
        # Balance Sheet Equity
        "book_value_per_share": ("equity", "book_value_per_share"),
        "outstanding_shares": ("equity", "shares_outstanding"),
        "shareholders_equity": ("equity", "total_equity"),
        
        # Balance Sheet Liabilities
        "total_liabilities": ("liabilities", "total_liabilities"),
        "current_liabilities": ("liabilities", "total_current_liabilities"),
        
        # Cash Flow Statement
        "net_income": ("cash_flow", "net_income"),
        "depreciation_and_amortization": ("cash_flow", "depreciation_amortization_and_depletion"),
        "dividends_and_other_cash_distributions": ("cash_flow", "payment_of_dividends_and_other_distributions"),
        "issuance_or_purchase_of_equity_shares": ("cash_flow", "issuance_of_capital_stock"),
        
        # Income Statement  
        "revenue": ("income", "sales"),
        "gross_profit": ("income", "gross_profit"),
        "interest_expense": ("income", "interest_expense"),
    }
    
    # Check if it's a direct field mapping
    if line_item in field_mappings:
        model_name, field_name = field_mappings[line_item]
        model = locals().get(model_name)
        if model and hasattr(model, field_name):
            return getattr(model, field_name)
    
    # Handle calculated fields
    if line_item == "total_debt":
        return _calculate_total_debt(liabilities)
    elif line_item == "working_capital":
        return _calculate_working_capital(assets, liabilities)
    elif line_item == "capital_expenditure":
        return _calculate_capital_expenditure(cash_flow)
    elif line_item == "free_cash_flow":
        return _calculate_free_cash_flow(cash_flow)
    elif line_item == "operating_income":
        return _calculate_operating_income(income)
    elif line_item == "operating_expense":
        return _calculate_operating_expense(income)
    elif line_item == "ebit":
        return _calculate_ebit(income)
    elif line_item == "ebitda":
        return _calculate_ebitda(income)
    elif line_item == "earnings_per_share":
        return _calculate_earnings_per_share(income, equity)
    elif line_item == "gross_margin":
        return _calculate_gross_margin(income)
    elif line_item == "operating_margin":
        return _calculate_operating_margin(income)
    elif line_item == "debt_to_equity":
        return _calculate_debt_to_equity(liabilities, equity)
    
    # Also check for net_income in income statement as fallback
    if line_item == "net_income" and income and hasattr(income, "net_income"):
        return getattr(income, "net_income")
    
    return None


def _calculate_total_debt(liabilities: 'BalanceSheetLiabilities' = None) -> float | None:
    """Calculate total debt from balance sheet liabilities."""
    if not liabilities:
        return None
    
    debt_components = [
        liabilities.notes_payable or 0,
        liabilities.current_portion_long_term_debt or 0,
        liabilities.long_term_debt or 0,
        liabilities.convertible_debt or 0
    ]
    
    return sum(debt_components) if any(debt_components) else None


def _calculate_working_capital(assets: 'BalanceSheetAssets' = None, liabilities: 'BalanceSheetLiabilities' = None) -> float | None:
    """Calculate working capital = current assets - current liabilities."""
    if not assets or not liabilities:
        return None
    
    current_assets = assets.total_current_assets
    current_liabs = liabilities.total_current_liabilities
    
    if current_assets is not None and current_liabs is not None:
        return current_assets - current_liabs
    return None


def _calculate_capital_expenditure(cash_flow: 'CashFlowStatement' = None) -> float | None:
    """Calculate capital expenditure from cash flow statement."""
    if not cash_flow:
        return None
    
    # Property and equipment investments are usually negative (outflows)
    return abs(cash_flow.property_and_equipment) if cash_flow.property_and_equipment else None


def _calculate_free_cash_flow(cash_flow: 'CashFlowStatement' = None) -> float | None:
    """Calculate free cash flow = operating cash flow - capital expenditures."""
    if not cash_flow:
        return None
    
    operating_cf = cash_flow.net_cash_from_operating_activities
    capex = abs(cash_flow.property_and_equipment or 0)
    
    if operating_cf is not None:
        return operating_cf - capex
    return None


def _calculate_operating_income(income: 'IncomeStatement' = None) -> float | None:
    """Calculate operating income."""
    if not income:
        return None
    
    # Try income_after_depreciation_and_amortization first
    if income.income_after_depreciation_and_amortization is not None:
        return income.income_after_depreciation_and_amortization
    
    # Fallback: gross_profit - operating expenses
    gross_profit = income.gross_profit
    operating_expenses = income.selling_administrative_depreciation_amortization_expenses
    
    if gross_profit is not None and operating_expenses is not None:
        return gross_profit - operating_expenses
    
    return None


def _calculate_operating_expense(income: 'IncomeStatement' = None) -> float | None:
    """Calculate operating expenses."""
    if not income:
        return None
    
    return income.selling_administrative_depreciation_amortization_expenses


def _calculate_ebit(income: 'IncomeStatement' = None) -> float | None:
    """Calculate EBIT = Net Income + Interest + Taxes."""
    if not income:
        return None
    
    net_income = income.net_income
    interest_expense = income.interest_expense or 0
    income_taxes = income.income_taxes or 0
    
    if net_income is not None:
        return net_income + interest_expense + income_taxes
    
    return None


def _calculate_ebitda(income: 'IncomeStatement' = None) -> float | None:
    """Calculate EBITDA = EBIT + Depreciation & Amortization."""
    if not income:
        return None
    
    ebit = _calculate_ebit(income)
    depreciation = income.depreciation_and_amortization or 0
    
    if ebit is not None:
        return ebit + depreciation
    
    return None


def _calculate_earnings_per_share(income: 'IncomeStatement' = None, equity: 'BalanceSheetEquity' = None) -> float | None:
    """Calculate earnings per share = net income / shares outstanding."""
    if not income or not equity:
        return None
    
    net_income = income.net_income
    shares = equity.shares_outstanding
    
    if net_income is not None and shares is not None and shares > 0:
        return net_income / shares
    
    return None


def _calculate_gross_margin(income: 'IncomeStatement' = None) -> float | None:
    """Calculate gross margin = gross profit / revenue."""
    if not income:
        return None
    
    gross_profit = income.gross_profit
    sales = income.sales
    
    if gross_profit is not None and sales is not None and sales > 0:
        return gross_profit / sales
    
    return None


def _calculate_operating_margin(income: 'IncomeStatement' = None) -> float | None:
    """Calculate operating margin = operating income / revenue."""
    if not income:
        return None
    
    operating_income = _calculate_operating_income(income)
    sales = income.sales
    
    if operating_income is not None and sales is not None and sales > 0:
        return operating_income / sales
    
    return None


def _calculate_debt_to_equity(liabilities: 'BalanceSheetLiabilities' = None, equity: 'BalanceSheetEquity' = None) -> float | None:
    """Calculate debt to equity ratio = total debt / total equity."""
    if not liabilities or not equity:
        return None
    
    total_debt = _calculate_total_debt(liabilities)
    total_equity = equity.total_equity
    
    if total_debt is not None and total_equity is not None and total_equity > 0:
        return total_debt / total_equity
    
    return None


def search_line_items_old(
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
    
    # Check for Alpha Vantage API error responses
    if "Information" in data:
        print(f"Alpha Vantage API Error: {data['Information']}")
        return []  # Return empty list for API errors
    
    if "Error Message" in data:
        print(f"Alpha Vantage API Error: {data['Error Message']}")
        return []  # Return empty list for API errors
        
    # Check for rate limit messages
    if "Note" in data and "API call frequency" in str(data.get("Note", "")):
        print(f"Alpha Vantage Rate Limit: {data['Note']}")
        return []  # Return empty list for rate limits
    
    # Check if data field exists
    if "data" not in data:
        print(f"Expected 'data' field not found in Alpha Vantage response. Keys: {list(data.keys())}")
        return []
    
    trades = data['data']
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
    formatted_end_date = None
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
    
    # Check for Alpha Vantage API error responses
    if "Information" in data:
        print(f"Alpha Vantage API Error: {data['Information']}")
        return []  # Return empty list for API errors
    
    if "Error Message" in data:
        print(f"Alpha Vantage API Error: {data['Error Message']}")
        return []  # Return empty list for API errors
        
    # Check for rate limit messages
    if "Note" in data and "API call frequency" in str(data.get("Note", "")):
        print(f"Alpha Vantage Rate Limit: {data['Note']}")
        return []  # Return empty list for rate limits
    
    try:
        alpha_response = AlphaVantageCompanyNewsResponse(**data)
    except Exception as e:
        print(f"Error parsing Alpha Vantage response: {e}")
        print(f"Response data keys: {list(data.keys())}")
        if "feed" in data and len(data["feed"]) > 0:
            print(f"First feed item keys: {list(data['feed'][0].keys())}")
            print(f"Sample feed item: {data['feed'][0]}")
        return []  # Return empty list for parsing errors
    
    # Convert AlphaVantage news to CompanyNews format
    all_news = []
    for news_item in alpha_response.feed:
        # Find the ticker sentiment that matches our requested ticker
        matching_ticker_sentiment = None
        if news_item.ticker_sentiments:  # Check if ticker_sentiments is not empty
            for ticker_sentiment in news_item.ticker_sentiments:
                if ticker_sentiment.ticker == ticker:
                    matching_ticker_sentiment = ticker_sentiment
                    break
        
        # Include news items even if no specific ticker sentiment is found
        # Use overall sentiment as fallback
        sentiment = None
        if matching_ticker_sentiment:
            sentiment = matching_ticker_sentiment.ticker_sentiment_label
        elif news_item.overall_sentiment_label:
            sentiment = news_item.overall_sentiment_label
        
        # Get author safely
        author = news_item.authors[0] if news_item.authors else "Unknown"
        
        converted_news = CompanyNews(
            ticker=ticker,
            title=news_item.title,
            author=author,
            source=news_item.source,
            date=news_item.time_published,
            url=news_item.url,
            sentiment=sentiment
        )
        all_news.append(converted_news)

    if not all_news:
        print("No news found")
        return []

    # Cache the results using the comprehensive cache key
    _cache.set_company_news(cache_key, [news.model_dump() for news in all_news])
    return all_news


def _get_balance_sheet_equity_data(ticker: str, target_date: str) -> BalanceSheetEquity | None:
    """Load balance sheet equity data from API."""
    try:
        # Convert target_date to datetime for comparison
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        # Try quarterly data first (most common case)
        try:
            quarterly_equity = get_balance_sheet_equity(ticker, target_date, period="Quarter")
            if quarterly_equity:
                # Find the best match from quarterly data
                best_match = _find_closest_equity_data(quarterly_equity, target_dt)
                if best_match:
                    return best_match
        except Exception as e:
            print(f"Error fetching quarterly balance sheet equity for {ticker}: {e}")
        
        # Fallback to annual data if quarterly not available
        try:
            annual_equity = get_balance_sheet_equity(ticker, target_date, period="Year")
            if annual_equity:
                # Find the best match from annual data
                best_match = _find_closest_equity_data(annual_equity, target_dt)
                if best_match:
                    return best_match
        except Exception as e:
            print(f"Error fetching annual balance sheet equity for {ticker}: {e}")
        
        return None
    except Exception as e:
        print(f"Error loading balance sheet equity data for {ticker}: {e}")
        return None


def _find_closest_equity_data(equity_list: list[BalanceSheetEquity], target_dt: datetime) -> BalanceSheetEquity | None:
    """Find the closest balance sheet equity data to the target date (before or on target date)."""
    if not equity_list:
        return None
    
    # Filter for dates on or before target date
    valid_entries = []
    for equity in equity_list:
        try:
            equity_dt = datetime.strptime(equity.date, '%Y-%m-%d')
            if equity_dt <= target_dt:
                valid_entries.append((equity, equity_dt))
        except Exception:
            continue  # Skip entries with invalid dates
    
    if not valid_entries:
        return None
    
    # Sort by date descending and return the most recent one
    valid_entries.sort(key=lambda x: x[1], reverse=True)
    return valid_entries[0][0]


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
