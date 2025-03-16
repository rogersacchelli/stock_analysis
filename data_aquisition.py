import logging
import pickle
import yfinance as yf

from utils.utils import get_hash, search_file


def fetch_yahoo_stock_data(stock_list, start_date, end_date):
    """Fetch historical stock data for the given ticker."""

    # If no pickled data is found, then download it
    stock_data_hash = get_hash(f"{str(stock_list)}_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}")

    stock_data = load_pickled_stock_data(stock_data_hash)

    if stock_data is None:
        stock_data = yf.download(stock_list, start=start_date, end=end_date,
                                 group_by='ticker', auto_adjust=True)

        save_pickled_stock_data(hash_value=stock_data_hash, data=stock_data)

    if stock_data.empty:
        raise ValueError(f"Failed to fetch yahoo data!")
        logging.ERROR(f"Failed to fetch yahoo data!")
    return stock_data


def load_pickled_stock_data(hash_value):

    filename = f"{hash_value}.pkl"

    if search_file('ticker_data', filename) is not None:
        with open(f"ticker_data/{filename}", "rb") as f:
            return pickle.load(f)
    else:
        return None


def save_pickled_stock_data(hash_value, data):

    filename = f"{hash_value}.pkl"

    if search_file('ticker_data', filename) is None:
        with open(f"ticker_data/{filename}", "wb") as file:
            pickle.dump(data, file)




