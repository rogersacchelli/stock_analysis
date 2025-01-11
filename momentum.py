import pandas as pd
import numpy as np
from datetime import datetime


def rsi(stock_data, setup, end_date: datetime, backtest=False):

    period = setup['Analysis']['Momentum']['rsi']['period']

    delta = stock_data['Close'].diff()
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    stock_data['RSI'] = 100 - (100 / (1 + rs))
    rsi_add_cross_signal(stock_data, setup)

    # Detect touches
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    if not backtest:
        output_window = setup['Analysis']['Momentum']['rsi']['output_window']
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def rsi_add_cross_signal(stock_data, setup):
    """
        Adds a 'cross' column to the DataFrame based on RSI values.
        - 'buy' when RSI < 30
        - 'sell' when RSI > 70
        - 'hold' otherwise

        :param stock_data: DataFrame containing 'RSI' column
        :param setup: Setup json file
        :return: DataFrame with added 'cross' column
    """

    conditions = [
        stock_data['RSI'] < setup['Analysis']['Momentum']['rsi']['lower'],
        stock_data['RSI'] > setup['Analysis']['Momentum']['rsi']['upper']
    ]
    choices = ['Buy', 'Sell']

    stock_data['Cross'] = np.select(conditions, choices, default=None)


