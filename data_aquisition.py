import datetime
import pickle
from dateutil.relativedelta import relativedelta
import yfinance as yf

from utils.utils import get_hash, search_file, get_days_from_period


def fetch_yahoo_stock_data(ticker, start_date, end_date: datetime, period="1y"):
    """Fetch historical stock data for the given ticker."""

    if start_date is None:
        # if start_date is None, it means the latest data during the period selected, so use start_date as period
        stock_data = load_pickled_stock_data(ticker=ticker, start_date=period,
                                             end_date=end_date)

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


def load_pickled_stock_data(ticker, start_date: datetime, end_date: datetime):

    if isinstance(start_date, str):
        days = get_days_from_period(start_date)
        start_date = (end_date - relativedelta(days=days)).strftime("%Y-%m-%d")

    end_date = end_date.strftime("%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")

    filename = f"{ticker}_{start_date}_{end_date}.pkl"

    if search_file('ticker_data', filename) is not None:
        with open(f"ticker_data/{filename}", "rb") as f:
            return pickle.load(f)
    else:
        return None


def save_pickled_stock_data(ticker, start_date: datetime, end_date: datetime, data):

    if isinstance(start_date, str):
        days = get_days_from_period(start_date)
        start_date = end_date - relativedelta(days=days)

    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    filename = f"{ticker}_{start_date}_{end_date}.pkl"

    if search_file('ticker_data', filename) is None:
        with open(f"ticker_data/{filename}", "wb") as file:
            pickle.dump(data, file)




