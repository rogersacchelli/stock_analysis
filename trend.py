import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta


def calculate_ema(data, period=14):
    return data.ewm(span=period, adjust=False).mean()


def calculate_sma(data, window=5):
    return data.rolling(window=window).mean()


def detect_crossings(stock_data, short_window, long_window, eval_window, average_type):
    """Detect days where SMA crosses."""

    if average_type == "SMA":
        stock_data[f"{average_type}_CROSS_{short_window}"] = calculate_sma(stock_data['Close'], short_window)
        stock_data[f"{average_type}_CROSS_{long_window}"] = calculate_sma(stock_data['Close'], long_window)
    elif average_type == "EMA":
        stock_data[f"{average_type}_CROSS_{short_window}"] = calculate_ema(stock_data['Close'], short_window)
        stock_data[f"{average_type}_CROSS_{long_window}"] = calculate_ema(stock_data['Close'], long_window)

    # Identify crossing points
    stock_data[f"Prev_{average_type}_CROSS_{short_window}"] = stock_data[f"{average_type}_CROSS_{short_window}"].shift(
        1)
    stock_data[f"Prev_{average_type}_CROSS_{long_window}"] = stock_data[f"{average_type}_CROSS_{long_window}"].shift(1)
    stock_data['Cross'] = np.where(
        (stock_data[f"Prev_{average_type}_CROSS_{short_window}"] <= stock_data[
            f"Prev_{average_type}_CROSS_{long_window}"]) & (
                stock_data[f"{average_type}_CROSS_{short_window}"] > stock_data[f"{average_type}_CROSS_{long_window}"]),
        'Buy',
        np.where(
            (stock_data[f"Prev_{average_type}_CROSS_{short_window}"] >= stock_data[
                f"Prev_{average_type}_CROSS_{long_window}"]) & (
                    stock_data[f"{average_type}_CROSS_{short_window}"] < stock_data[
                f"{average_type}_CROSS_{long_window}"]),
            'Sell',
            None
        )
    )

    today = np.datetime64('today', 'D')
    cutoff_date = today - np.timedelta64(eval_window, 'D')

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column
    last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date')
    return last_crossing.tail(1)


def detect_bollinger_crossings(stock_data, period, average_type, eval_window, std_dev):
    stock_data[f"BB_{average_type.upper()}_{eval_window}"] = stock_data['Close'].rolling(window=period).mean()
    stock_data['StdDev'] = stock_data['Close'].rolling(window=eval_window).std()
    stock_data['UpperBand'] = stock_data[f"BB_{average_type.upper()}_{eval_window}"] + (std_dev * stock_data['StdDev'])
    stock_data['LowerBand'] = stock_data[f"BB_{average_type.upper()}_{eval_window}"] - (std_dev * stock_data['StdDev'])

    # Calculate cutoff date
    today = np.datetime64('today', 'D')
    cutoff_date = today - np.timedelta64(eval_window, 'D')

    # Reset the index to ensure Date is a column
    stock_data.reset_index(inplace=True)

    # Detect touches
    bb_uppertouch = stock_data[(stock_data['Close'] >= stock_data['UpperBand']) & (stock_data['Date'] >= cutoff_date)]
    bb_lowertouch = stock_data[(stock_data['Close'] <= stock_data['LowerBand']) & (stock_data['Date'] >= cutoff_date)]

    return {"UpperTouch": bb_uppertouch, "LowerTouch": bb_lowertouch}
