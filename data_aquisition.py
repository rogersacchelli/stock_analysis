import yfinance as yf


def fetch_yahoo_stock_data(ticker, start_date, end_date, period="1y"):
    """Fetch historical stock data for the given ticker."""

    if end_date is None:
        stock_data = yf.download(ticker, period=period, multi_level_index=False)
    else:
        stock_data = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False)

    if stock_data.empty:
        raise ValueError(f"No data available for ticker {ticker}.")
    return stock_data


