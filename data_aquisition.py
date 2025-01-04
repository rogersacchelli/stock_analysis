import datetime
import pickle

import yfinance as yf

from utils.utils import get_hash, search_file


def fetch_yahoo_stock_data(ticker, start_date, end_date, period="1y"):
    """Fetch historical stock data for the given ticker."""

    if end_date is None:
        # if end_date is None, it means the latest data during the period selected, so use start_date as period
        stock_data = load_pickled_stock_data(ticker=ticker, start_date=period,
                                             end_date=datetime.datetime.now().strftime("%Y-%m-%d"))

        # If no pickled data is found, then download it
        if stock_data is None:
            stock_data = yf.download(ticker, period=period, multi_level_index=False)
            save_pickled_stock_data(ticker=ticker, start_date=period, end_date=end_date, data=stock_data)
    else:
        stock_data = load_pickled_stock_data(ticker=ticker, start_date=start_date, end_date=end_date)

        if stock_data is None:
            stock_data = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False)
            save_pickled_stock_data(ticker=ticker, start_date=start_date, end_date=end_date, data=stock_data)

    if stock_data.empty:
        raise ValueError(f"No data available for ticker {ticker}.")
    return stock_data


def load_pickled_stock_data(ticker, start_date, end_date):

    hash = get_hash(f"{ticker}-{start_date}-{end_date}")
    pickle_file = f"{hash}.pkl"

    if search_file('ticker_data', pickle_file) is not None:
        with open(f"ticker_data/{pickle_file}", "rb") as f:
            return pickle.load(f)
    else:
        return None


def save_pickled_stock_data(ticker, start_date, end_date, data):
    hash = get_hash(f"{ticker}-{start_date}-{end_date}")
    pickle_file = f"{hash}.pkl"

    if search_file('ticker_data', pickle_file) is None:
        with open(f"ticker_data/{pickle_file}", "wb") as file:
            pickle.dump(data, file)




