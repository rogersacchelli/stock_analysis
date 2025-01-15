import pandas as pd
import numpy as np


def rsi(stock_data, setup, end_date, backtest=False):

    # Get period from setup
    period = setup['Analysis']['Momentum']['rsi']['period']

    # Calculate daily changes
    delta = stock_data['Close'].diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Initialize smoothed averages
    avg_gain = gain.rolling(window=period, min_periods=1).mean()  # Initial SMA for the first calculation
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    # Use SMA for smoothing
    for i in range(period, len(gain)):
        avg_gain.iloc[i] = ((avg_gain.iloc[i - 1] * (period - 1)) + gain.iloc[i]) / period
        avg_loss.iloc[i] = ((avg_loss.iloc[i - 1] * (period - 1)) + loss.iloc[i]) / period

    # Calculate RS and RSI
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

    return rsi



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


def add_adx(df, setup):
    """
    Calculate ADX, +DI, and -DI for the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with 'High', 'Low', and 'Close' columns.
        period (int): Period for ADX calculation (default is 14).

    Returns:
        pd.DataFrame: DataFrame with ADX, +DI, and -DI columns added.
    """

    period = setup['Filters']['Momentum']['adx']['period']

    # Calculate True Range (TR)
    df['High-Low'] = df['High'] - df['Low']
    df['High-Close'] = abs(df['High'] - df['Close'].shift(1))
    df['Low-Close'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['High-Low', 'High-Close', 'Low-Close']].max(axis=1)

    # Calculate +DM and -DM
    df['+DM'] = np.where((df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']),
                         np.maximum(df['High'] - df['High'].shift(1), 0), 0)
    df['-DM'] = np.where((df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)),
                         np.maximum(df['Low'].shift(1) - df['Low'], 0), 0)

    # Smooth TR, +DM, -DM with Wilder's smoothing
    df['TR_SMA'] = df['TR'].rolling(window=period).sum()
    df['+DM_SMA'] = df['+DM'].rolling(window=period).sum()
    df['-DM_SMA'] = df['-DM'].rolling(window=period).sum()

    # Calculate +DI and -DI
    df['+DI'] = (df['+DM_SMA'] / df['TR_SMA']) * 100
    df['-DI'] = (df['-DM_SMA'] / df['TR_SMA']) * 100

    # Calculate DX
    df['DX'] = (abs(df['+DI'] - df['-DI']) / abs(df['+DI'] + df['-DI'])) * 100

    # Calculate ADX
    df['ADX'] = df['DX'].rolling(window=period).mean()

    # Clean up intermediate columns
    df = df.drop(columns=['High-Low', 'High-Close', 'Low-Close', 'TR', '+DM', '-DM',
                          'TR_SMA', '+DM_SMA', '-DM_SMA', 'DX'])
    return df
