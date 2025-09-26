from pydantic import BaseModel


class Price(BaseModel):
    open: float
    close: float
    high: float
    low: float
    volume: int
    time: str


class PriceResponse(BaseModel):
    ticker: str
    prices: list[Price]


class FinancialMetrics(BaseModel):
    ticker: str
    report_period: str
    period: str
    currency: str
    market_cap: float | None
    enterprise_value: float | None
    price_to_earnings_ratio: float | None
    price_to_book_ratio: float | None
    price_to_sales_ratio: float | None
    enterprise_value_to_ebitda_ratio: float | None
    enterprise_value_to_revenue_ratio: float | None
    free_cash_flow_yield: float | None
    peg_ratio: float | None
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None
    return_on_equity: float | None
    return_on_assets: float | None
    return_on_invested_capital: float | None
    asset_turnover: float | None
    inventory_turnover: float | None
    receivables_turnover: float | None
    days_sales_outstanding: float | None
    operating_cycle: float | None
    working_capital_turnover: float | None
    current_ratio: float | None
    quick_ratio: float | None
    cash_ratio: float | None
    operating_cash_flow_ratio: float | None
    debt_to_equity: float | None
    debt_to_assets: float | None
    interest_coverage: float | None
    revenue_growth: float | None
    earnings_growth: float | None
    book_value_growth: float | None
    earnings_per_share_growth: float | None
    free_cash_flow_growth: float | None
    operating_income_growth: float | None
    ebitda_growth: float | None
    payout_ratio: float | None
    earnings_per_share: float | None
    book_value_per_share: float | None
    free_cash_flow_per_share: float | None


class FinancialMetricsResponse(BaseModel):
    financial_metrics: list[FinancialMetrics]


class LineItem(BaseModel):
    ticker: str
    report_period: str
    period: str
    currency: str

    # Allow additional fields dynamically
    model_config = {"extra": "allow"}


class LineItemResponse(BaseModel):
    search_results: list[LineItem]


class InsiderTrade(BaseModel):
    ticker: str
    issuer: str | None
    name: str | None
    title: str | None
    is_board_director: bool | None
    transaction_date: str | None
    transaction_shares: float | None
    transaction_price_per_share: float | None
    transaction_value: float | None
    shares_owned_before_transaction: float | None
    shares_owned_after_transaction: float | None
    security_title: str | None
    filing_date: str


class InsiderTradeResponse(BaseModel):
    insider_trades: list[InsiderTrade]


class CompanyNews(BaseModel):
    ticker: str
    title: str
    author: str
    source: str
    date: str
    url: str
    sentiment: str | None = None


class CompanyNewsResponse(BaseModel):
    news: list[CompanyNews]


class AlphaVantageTickerSentiment(BaseModel):
    ticker: str
    relevance_score: str
    ticker_sentiment_score: str
    ticker_sentiment_label: str

class AlphaVantageCompanyNews(BaseModel):
    title: str
    url: str
    time_published: str
    authors: list[str] = []  # Make optional with default empty list
    source: str
    overall_sentiment_score: float | None = None  # Make optional
    overall_sentiment_label: str | None = None  # Make optional
    ticker_sentiments: list[AlphaVantageTickerSentiment] = []  # Make optional with default empty list

class AlphaVantageCompanyNewsResponse(BaseModel):
    items: str
#    sentiment_score_definition: str
#    relevance_score_definition: str
    feed: list[AlphaVantageCompanyNews]

class CompanyFacts(BaseModel):
    ticker: str
    name: str
    cik: str | None = None
    industry: str | None = None
    sector: str | None = None
    category: str | None = None
    exchange: str | None = None
    is_active: bool | None = None
    listing_date: str | None = None
    location: str | None = None
    market_cap: float | None = None
    number_of_employees: int | None = None
    sec_filings_url: str | None = None
    sic_code: str | None = None
    sic_industry: str | None = None
    sic_sector: str | None = None
    website_url: str | None = None
    weighted_average_shares: int | None = None


class CompanyFactsResponse(BaseModel):
    company_facts: CompanyFacts


class Position(BaseModel):
    cash: float = 0.0
    shares: int = 0
    ticker: str


class Portfolio(BaseModel):
    positions: dict[str, Position]  # ticker -> Position mapping
    total_cash: float = 0.0


class AnalystSignal(BaseModel):
    signal: str | None = None
    confidence: float | None = None
    reasoning: dict | str | None = None
    max_position_size: float | None = None  # For risk management signals


class TickerAnalysis(BaseModel):
    ticker: str
    analyst_signals: dict[str, AnalystSignal]  # agent_name -> signal mapping


class AgentStateData(BaseModel):
    tickers: list[str]
    portfolio: Portfolio
    start_date: str
    end_date: str
    ticker_analyses: dict[str, TickerAnalysis]  # ticker -> analysis mapping


class AgentStateMetadata(BaseModel):
    show_reasoning: bool = False
    model_config = {"extra": "allow"}


class BalanceSheetAssets(BaseModel):
    date: str
    act_symbol: str
    period: str
    cash_and_equivalents: float | None = None
    receivables: float | None = None
    notes_receivable: float | None = None
    inventories: float | None = None
    other_current_assets: float | None = None
    total_current_assets: float | None = None
    net_property_and_equipment: float | None = None
    investments_and_advances: float | None = None
    other_non_current_assets: float | None = None
    deferred_charges: float | None = None
    intangibles: float | None = None
    deposits_and_other_assets: float | None = None
    total_assets: float | None = None


class BalanceSheetAssetsResponse(BaseModel):
    balance_sheet_assets: list[BalanceSheetAssets]


class BalanceSheetEquity(BaseModel):
    act_symbol: str
    date: str
    period: str
    preferred_stock: float | None = None
    common_stock: float | None = None
    capital_surplus: float | None = None
    retained_earnings: float | None = None
    other_equity: float | None = None
    treasury_stock: float | None = None
    total_equity: float | None = None
    total_liabilities_and_equity: float | None = None
    shares_outstanding: float | None = None
    book_value_per_share: float | None = None


class BalanceSheetEquityResponse(BaseModel):
    balance_sheet_equity: list[BalanceSheetEquity]


class BalanceSheetLiabilities(BaseModel):
    act_symbol: str
    date: str
    period: str
    notes_payable: float | None = None
    accounts_payable: float | None = None
    current_portion_long_term_debt: float | None = None
    current_portion_capital_leases: float | None = None
    accrued_expenses: float | None = None
    income_taxes_payable: float | None = None
    other_current_liabilities: float | None = None
    total_current_liabilities: float | None = None
    mortgages: float | None = None
    deferred_taxes_or_income: float | None = None
    convertible_debt: float | None = None
    long_term_debt: float | None = None
    non_current_capital_leases: float | None = None
    other_non_current_liabilities: float | None = None
    minority_interest: float | None = None
    total_liabilities: float | None = None


class BalanceSheetLiabilitiesResponse(BaseModel):
    balance_sheet_liabilities: list[BalanceSheetLiabilities]


class CashFlowStatement(BaseModel):
    act_symbol: str
    date: str
    period: str
    net_income: float | None = None
    depreciation_amortization_and_depletion: float | None = None
    net_change_from_assets: float | None = None
    net_cash_from_discontinued_operations: float | None = None
    other_operating_activities: float | None = None
    net_cash_from_operating_activities: float | None = None
    property_and_equipment: float | None = None
    acquisition_of_subsidiaries: float | None = None
    investments: float | None = None
    other_investing_activities: float | None = None
    net_cash_from_investing_activities: float | None = None
    issuance_of_capital_stock: float | None = None
    issuance_of_debt: float | None = None
    increase_short_term_debt: float | None = None
    payment_of_dividends_and_other_distributions: float | None = None
    other_financing_activities: float | None = None
    net_cash_from_financing_activities: float | None = None
    effect_of_exchange_rate_changes: float | None = None
    net_change_in_cash_and_equivalents: float | None = None
    cash_at_beginning_of_period: float | None = None
    cash_at_end_of_period: float | None = None
    diluted_net_eps: float | None = None


class CashFlowStatementResponse(BaseModel):
    cash_flow_statements: list[CashFlowStatement]


class IncomeStatement(BaseModel):
    act_symbol: str
    date: str
    period: str
    sales: float | None = None
    cost_of_goods: float | None = None
    gross_profit: float | None = None
    selling_administrative_depreciation_amortization_expenses: float | None = None
    income_after_depreciation_and_amortization: float | None = None
    non_operating_income: float | None = None
    interest_expense: float | None = None
    pretax_income: float | None = None
    income_taxes: float | None = None
    minority_interest: float | None = None
    investment_gains: float | None = None
    other_income: float | None = None
    income_from_continuing_operations: float | None = None
    extras_and_discontinued_operations: float | None = None
    net_income: float | None = None
    income_before_depreciation_and_amortization: float | None = None
    depreciation_and_amortization: float | None = None
    average_shares: float | None = None
    diluted_eps_before_non_recurring_items: float | None = None
    diluted_net_eps: float | None = None


class IncomeStatementResponse(BaseModel):
    income_statements: list[IncomeStatement]


class CompanyOverview(BaseModel):
    Symbol: str
    AssetType: str
    Name: str
    Description: str
    CIK: str
    Exchange: str
    Currency: str
    Country: str
    Sector: str
    Industry: str
    Address: str
    OfficialSite: str
    FiscalYearEnd: str
    LatestQuarter: str
    MarketCapitalization: float
    EBITDA: float
    PERatio: float
    PEGRatio: float
    BookValue: float
    DividendPerShare: float
    DividendYield: float
    EPS: float
    RevenuePerShareTTM: float
    ProfitMargin: float
    OperatingMarginTTM: float
    ReturnOnAssetsTTM: float
    ReturnOnEquityTTM: float
    RevenueTTM: float
    GrossProfitTTM: float
    DilutedEPSTTM: float
    QuarterlyEarningsGrowthYOY: float
    QuarterlyRevenueGrowthYOY: float
    AnalystTargetPrice: float
    AnalystRatingStrongBuy: int
    AnalystRatingBuy: int
    AnalystRatingHold: int
    AnalystRatingSell: int
    AnalystRatingStrongSell: int
    TrailingPE: float
    ForwardPE: float
    PriceToSalesRatioTTM: float
    PriceToBookRatio: float
    EVToRevenue: float
    EVToEBITDA: float
    Beta: float
    field_52WeekHigh: float = None  # Using alias for field starting with number
    field_52WeekLow: float = None   # Using alias for field starting with number
    field_50DayMovingAverage: float = None  # Using alias for field starting with number
    field_200DayMovingAverage: float = None # Using alias for field starting with number
    SharesOutstanding: int
    SharesFloat: int
    PercentInsiders: float
    PercentInstitutions: float
    DividendDate: str
    ExDividendDate: str
    
    model_config = {
        "extra": "allow",
        "field_aliases": {
            "field_52WeekHigh": "52WeekHigh",
            "field_52WeekLow": "52WeekLow", 
            "field_50DayMovingAverage": "50DayMovingAverage",
            "field_200DayMovingAverage": "200DayMovingAverage"
        }
    }
