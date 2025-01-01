import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta


def calculate_ema(data, period=14):
    return data.ewm(span=period, adjust=False).mean()


def calculate_sma(data, window=5):
    return data.rolling(window=window).mean()


def detect_ma_crossings(stock_data, short_window, long_window, output_window, average_type='SMA'):
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
    cutoff_date = today - np.timedelta64(output_window, 'D')

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column
    last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date')
    return last_crossing.tail(1)


def detect_bollinger_crossings(stock_data, period, average_type, output_window, std_dev):
    stock_data[f"BB_{average_type.upper()}_{output_window}"] = stock_data['Close'].rolling(window=period).mean()
    stock_data['StdDev'] = stock_data['Close'].rolling(window=period).std()
    stock_data['UpperBand'] = stock_data[f"BB_{average_type.upper()}_{output_window}"] + (std_dev * stock_data['StdDev'])
    stock_data['LowerBand'] = stock_data[f"BB_{average_type.upper()}_{output_window}"] - (std_dev * stock_data['StdDev'])

    # Calculate cutoff date
    today = np.datetime64('today', 'D')
    cutoff_date = today - np.timedelta64(output_window, 'D')

    # Detect touches
    bb_lowertouch = stock_data[(stock_data['Close'] <= stock_data['LowerBand'])]
    bb_lowertouch = bb_lowertouch.reset_index()
    bb_lowertouch_crossings = bb_lowertouch[bb_lowertouch['Date'] >= cutoff_date].sort_values(by='Date')

    bb_uppertouch = stock_data[(stock_data['Close'] >= stock_data['UpperBand'])]
    bb_uppertouch = bb_uppertouch.reset_index()
    bb_uppertouch_crossings = bb_uppertouch[bb_uppertouch['Date'] >= cutoff_date].sort_values(by='Date')

    return {"UpperTouch": bb_uppertouch_crossings, "LowerTouch": bb_lowertouch_crossings}


def detect_wr_crossings(stock_data, period, output_window):

    # Calculate prior 4-week highs and lows (shifted by 1 day)
    stock_data[f"{period}W_High"] = stock_data['High'].rolling(window=period * 5).max().shift(1)
    stock_data[f"{period}W_Low"] = stock_data['Low'].rolling(window=period * 5).min().shift(1)

    # Calculate cutoff date
    today = np.datetime64('today', 'D')
    cutoff_date = today - np.timedelta64(output_window, 'D')

    # Detect touches
    wr_upper = stock_data[(stock_data['Close'] > stock_data[f"{period}W_High"])]
    wr_upper.reset_index(inplace=True)
    wr_upper_crossings = wr_upper[wr_upper['Date'] >= cutoff_date].sort_values(by='Date')

    wr_lower = stock_data[(stock_data['Close'] > stock_data[f"{period}W_High"])]
    wr_lower.reset_index(inplace=True)
    wr_lower_crossings = wr_lower[wr_lower['Date'] >= cutoff_date].sort_values(by='Date')

    # Return crossings
    return {"Buy": wr_upper_crossings, "Sell": wr_lower_crossings}


def detect_macd_trend(stock_data, short_window, long_window, signal_window, output_window, lower_thold, upper_thold):
    """
        Calculate MACD and Signal Line using SMA instead of EMA.
    """
    stock_data[f"EMA_{short_window}"] = stock_data['Close'].ewm(span=short_window, adjust=False).mean()
    stock_data[f"EMA_{long_window}"] = stock_data['Close'].ewm(span=long_window, adjust=False).mean()

    stock_data[f"MACD_{short_window}_{long_window}"] = stock_data[f"EMA_{short_window}"] - \
                                                       stock_data[f"EMA_{long_window}"]

    stock_data[f"MACD_SIGNAL_{signal_window}"] = stock_data[f"MACD_{short_window}_{long_window}"].rolling(window=
                                                                                                signal_window).mean()

    stock_data["MACD_LOWER_THOLD"] = lower_thold
    stock_data["MACD_UPPER_THOLD"] = upper_thold

    macd_lower = stock_data[(stock_data[f"MACD_{short_window}_{long_window}"] <= stock_data['MACD_LOWER_THOLD'])]
    macd_lower = macd_lower.reset_index()
    macd_upper = stock_data[(stock_data[f"MACD_{short_window}_{long_window}"] >= stock_data['MACD_UPPER_THOLD'])]
    macd_upper = macd_upper.reset_index()

    today = np.datetime64('today', 'D')
    cutoff_date = today - np.timedelta64(output_window, 'D')

    # Reset the index to ensure Date is a column
    macd_lower_crossings = macd_lower[macd_lower['Date'] >= cutoff_date].sort_values(by='Date')
    macd_upper_crossings = macd_upper[macd_upper['Date'] >= cutoff_date].sort_values(by='Date')

    return {'Buy': macd_lower_crossings, 'Sell': macd_upper_crossings}
