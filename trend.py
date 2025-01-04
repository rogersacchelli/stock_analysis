import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta


def calculate_ema(data, period=14):
    return data.ewm(span=period, adjust=False).mean()


def calculate_sma(data, window=5):
    return data.rolling(window=window).mean()


def detect_ma_crossings(stock_data, short_window, long_window, output_window, end_date, average_type='SMA'):
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

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    if output_window:
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def detect_bollinger_crossings(stock_data, period, average_type, output_window, end_date, std_dev):
    stock_data[f"BB_{average_type.upper()}_{output_window}"] = stock_data['Close'].rolling(window=period).mean()
    stock_data['StdDev'] = stock_data['Close'].rolling(window=period).std()
    stock_data['UpperBand'] = stock_data[f"BB_{average_type.upper()}_{output_window}"] + (std_dev * stock_data['StdDev'])
    stock_data['LowerBand'] = stock_data[f"BB_{average_type.upper()}_{output_window}"] - (std_dev * stock_data['StdDev'])

    stock_data['Cross'] = stock_data.apply(
        lambda row: 'Buy' if row['Close'] <= row['LowerBand'] else ('Sell' if row['Close'] >= row['UpperBand'] else None), axis=1)

    # Detect touches
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    if output_window:
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def detect_wr_crossings(stock_data, period, end_date, output_window):

    # Calculate prior 4-week highs and lows (shifted by 1 day)
    stock_data[f"{period}W_High"] = stock_data['High'].rolling(window=period * 5).max().shift(1)
    stock_data[f"{period}W_Low"] = stock_data['Low'].rolling(window=period * 5).min().shift(1)

    # Detect touches
    stock_data['Cross'] = stock_data.apply(
        lambda row: 'Buy' if row['Close'] > row[f"{period}W_High"] else (
            'Sell' if row['Close'] >= row[f"{period}W_Low"] else None), axis=1)

    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    if output_window:
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def detect_macd_trend(stock_data, short_window, long_window, signal_window, output_window, end_date):
    """
        Calculate MACD and Signal Line using SMA instead of EMA.
    """
    stock_data[f"EMA_{short_window}"] = stock_data['Close'].ewm(span=short_window, adjust=False).mean()
    stock_data[f"EMA_{long_window}"] = stock_data['Close'].ewm(span=long_window, adjust=False).mean()

    stock_data[f"MACD_{short_window}_{long_window}"] = stock_data[f"EMA_{short_window}"] - \
                                                       stock_data[f"EMA_{long_window}"]

    stock_data[f"MACD_SIGNAL_{signal_window}"] = stock_data[f"MACD_{short_window}_{long_window}"].rolling(window=
                                                                                                signal_window).mean()

    stock_data[f"MACD_Prev_{short_window}_{long_window}"] = stock_data[f"MACD_{short_window}_{long_window}"].shift(1)
    stock_data[f"MACD_Prev_SIGNAL_{signal_window}"] = stock_data[f"MACD_SIGNAL_{signal_window}"].shift(1)

    # Identify crossing points
    stock_data['Cross'] = np.where(
        (stock_data[f"MACD_Prev_{short_window}_{long_window}"] <= stock_data[f"MACD_Prev_SIGNAL_{signal_window}"]) &
        (stock_data[f"MACD_{short_window}_{long_window}"] > stock_data[f"MACD_SIGNAL_{signal_window}"]),
        'Buy',
        np.where(
            (stock_data[f"MACD_Prev_{short_window}_{long_window}"] >= stock_data[f"MACD_Prev_SIGNAL_{signal_window}"]) &
            (stock_data[f"MACD_{short_window}_{long_window}"] < stock_data[f"MACD_SIGNAL_{signal_window}"]),
            'Sell',
            None
        )
    )

    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    if output_window:
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings