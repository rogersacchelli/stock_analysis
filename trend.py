import numpy as np
from scipy import stats
from constants import *


def calculate_ema(data, period=14):
    return data.ewm(span=period, adjust=False).mean()


def calculate_sma(data, window=5):
    return data.rolling(window=window).mean()


def detect_long_term_crossings(stock_data, setup, end_date, backtest=False):

    method = 'long_term'
    period = setup['Analysis']['Trend'][method]['period']
    output_window = setup['Analysis']['Trend'][method]['output_window']
    average_type = setup['Analysis']['Trend'][method]['avg_type']

    if average_type == "SMA":
        stock_data[f"LT_MA"] = calculate_sma(stock_data['Close'], period)
    else:
        stock_data[f"LT_MA"] = calculate_ema(stock_data['Close'], period)

    stock_data[f"Prev_Close"] = stock_data[f"Close"].shift(1)
    stock_data[f"Prev_LT_MA"] = stock_data[f"LT_MA"].shift(1)

    stock_data[f"{method}_Cross"] = np.where(
        (stock_data[f"Prev_Close"] <= stock_data[f"Prev_LT_MA"]) &
        (stock_data[f"Close"] > stock_data[f"LT_MA"]), BUY,
        np.where(
            (stock_data[f"Prev_Close"] >= stock_data[f"Prev_LT_MA"]) & (
                    stock_data[f"Close"] < stock_data[f"LT_MA"]), SELL,
            HOLD
        )
    )

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data[f"{method}_Cross"] != HOLD]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    stock_data.drop(['Prev_LT_MA'], axis=1, inplace=True)

    if not backtest:
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def detect_ma_crossings(stock_data, setup, end_date, method, backtest=False):
    """Detect days where SMA crosses."""

    short_window = setup['Analysis']['Trend'][method]['short']
    long_window = setup['Analysis']['Trend'][method]['long']

    if method == "sma_cross":
        average_type = "SMA" if method == "sma_cross" else "EMA"

    if average_type == "SMA":
        stock_data[f"Cross_Short"] = calculate_sma(stock_data['Close'], short_window)
        stock_data[f"Cross_Long"] = calculate_sma(stock_data['Close'], long_window)
    elif average_type == "EMA":
        stock_data[f"Cross_Short"] = calculate_ema(stock_data['Close'], short_window)
        stock_data[f"Cross_Long"] = calculate_ema(stock_data['Close'], long_window)

    # Identify crossing points
    stock_data[f"Prev_Cross_Short"] = stock_data[f"Cross_Short"].shift(1)
    stock_data[f"Prev_Cross_Long"] = stock_data[f"Cross_Long"].shift(1)

    stock_data[f"{method}_Cross"] = np.where(
        (stock_data[f"Prev_Cross_Short"] <= stock_data[f"Prev_Cross_Long"]) &
        (stock_data[f"Cross_Short"] > stock_data[f"Cross_Long"]), BUY,
        np.where(
            (stock_data[f"Prev_Cross_Short"] >= stock_data[f"Prev_Cross_Long"])
            & (stock_data[f"Cross_Short"] < stock_data[f"Cross_Long"]), SELL, HOLD
        )
    )

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data[f"{method}_Cross"] != HOLD]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    stock_data.drop(['Prev_Cross_Short', 'Prev_Cross_Long'], axis=1, inplace=True)

    if not backtest:
        today = np.datetime64(end_date)
        output_window = setup['Analysis']['Trend'][method]['output_window']
        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def detect_bollinger_crossings(stock_data, setup, end_date, backtest=False):

    method = "bollinger_bands"
    period = setup['Analysis']['Trend'][method]['period']
    std_dev = setup['Analysis']['Trend'][method]['std_dev']
    output_window = setup['Analysis']['Trend'][method]['output_window']

    stock_data[f"BB"] = stock_data['Close'].rolling(window=period).mean()
    stock_data['StdDev'] = stock_data['Close'].rolling(window=period).std()
    stock_data['Upper_Band'] = stock_data[f"BB"] + (std_dev * stock_data['StdDev'])
    stock_data['Lower_Band'] = stock_data[f"BB"] - (std_dev * stock_data['StdDev'])

    stock_data['Prev_Close'] = stock_data['Close'].shift(1)
    stock_data['Prev_Lower_Band'] = stock_data['Lower_Band'].shift(1)
    stock_data['Prev_Upper_Band'] = stock_data['Upper_Band'].shift(1)

    stock_data[f"{method}_Cross"] = HOLD
    stock_data.loc[
        (stock_data['Close'] <= stock_data['Lower_Band']) &
        (stock_data['Prev_Close'] > stock_data['Prev_Lower_Band']), f"{method}_Cross"] = BUY
    stock_data.loc[
        (stock_data['Close'] >= stock_data['Upper_Band']) &
        (stock_data['Prev_Close'] < stock_data['Prev_Upper_Band']), f"{method}_Cross"] = SELL

    # Detect touches
    crossings = stock_data[stock_data[f"{method}_Cross"] != HOLD]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    stock_data.drop(['BB', 'Upper_Band', 'Lower_Band', 'Prev_Lower_Band', 'Prev_Upper_Band'], axis=1, inplace=True)

    if not backtest:
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def detect_wr_crossings(stock_data, setup, end_date, backtest=False):

    method = "week_rule"
    period = setup['Analysis']['Trend'][method]['period']

    # Calculate prior 4-week highs and lows (shifted by 1 day)
    stock_data[f"W_High"] = stock_data['High'].rolling(window=period * 5).max().shift(1)
    stock_data[f"W_Low"] = stock_data['Low'].rolling(window=period * 5).min().shift(1)

    # Detect touches
    stock_data['WR_Cross'] = stock_data.apply(
        lambda row: BUY if row['Close'] > row[f"W_High"] else (
            SELL if row['Close'] >= row[f"W_Low"] else None), axis=1)

    crossings = stock_data[stock_data[f"{method}_Cross"] != HOLD]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    stock_data.drop(['W_High', 'W_Low'], axis=1, inplace=True)

    if not backtest:
        output_window = setup['Analysis']['Trend']['week_rule']['output_window']
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def detect_macd_trend(stock_data, setup, end_date, backtest=False):
    """
        Calculate MACD and Signal Line using SMA instead of EMA.
    """

    method = "macd"
    short_window = setup['Analysis']['Trend'][method]['short']
    long_window = setup['Analysis']['Trend'][method]['long']
    signal_window = setup['Analysis']['Trend'][method]['signal_window']
    output_window = setup['Analysis']['Trend'][method]['signal_window']

    stock_data[f"EMA_short"] = stock_data['Close'].ewm(span=short_window, adjust=False).mean()
    stock_data[f"EMA_long"] = stock_data['Close'].ewm(span=long_window, adjust=False).mean()

    stock_data[f"MACD_short_long"] = stock_data[f"EMA_short"] - stock_data[f"EMA_long"]

    stock_data[f"MACD_SIGNAL_WINDOW"] = stock_data[f"MACD_short_long"].rolling(window=signal_window).mean()

    stock_data[f"MACD_Prev_short_long"] = stock_data[f"MACD_short_long"].shift(1)
    stock_data[f"MACD_Prev_SIGNAL_WINDOW"] = stock_data[f"MACD_SIGNAL_WINDOW"].shift(1)

    # Identify crossing points
    stock_data[f"{method}_Cross"] = np.where(
        (stock_data[f"MACD_Prev_short_long"] <= stock_data[f"MACD_Prev_SIGNAL_WINDOW"]) &
        (stock_data[f"MACD_short_long"] > stock_data[f"MACD_SIGNAL_WINDOW"]),
        BUY,
        np.where(
            (stock_data[f"MACD_Prev_short_long"] >= stock_data[f"MACD_Prev_SIGNAL_WINDOW"]) &
            (stock_data[f"MACD_short_long"] < stock_data[f"MACD_SIGNAL_WINDOW"]),
            SELL,
            HOLD
        )
    )

    crossings = stock_data[stock_data[f"{method}_Cross"] != HOLD]
    crossings = crossings.reset_index()  # Reset index to access the Date column

    stock_data.drop(['EMA_short', 'EMA_short', 'MACD_short_long', 'MACD_Prev_short_long', 'MACD_SIGNAL_WINDOW',
                     'MACD_Prev_SIGNAL_WINDOW'], axis=1, inplace=True)

    if not backtest:
        today = np.datetime64(end_date)

        cutoff_date = today - np.timedelta64(output_window, 'D')
        last_crossing = crossings[crossings['Date'] >= cutoff_date].sort_values(by='Date').tail(1)
        return last_crossing
    else:
        return crossings


def calculate_ma_slope(stock_data, ma_period, slope_period, moving_average_type):
    """
    Calculate the slope of the moving average over the last 'slope_period'
    values of an 'ma_period' moving average for a given stock symbol.

    Parameters:
    - stock_data: df, stock_data collected
    - ma_period: int, the moving average period
    - slope_period: int, period over which to calculate the slope (should be <= ma_period)
    - start_date: str, starting date for data in 'YYYY-MM-DD' format
    - end_date: str, ending date for data in 'YYYY-MM-DD' format

    Returns:
    - pandas.Series: Slope of the moving average for each period
    """
    # Calculate moving averages
    stock_data[f"MA_{moving_average_type}"] = stock_data['Close'].rolling(window=ma_period).mean()

    # Calculate slope using linear regression for each window of 'slope_period'
    def slope_calc(window):
        if len(window) == slope_period:
            x = np.arange(slope_period)
            slope, _, _, _, _ = stats.linregress(x, window)
            return slope
        return np.nan

    # Apply slope calculation to each moving average window
    stock_data[f"MA_Slope_{moving_average_type}"] = stock_data[f"MA_{moving_average_type}"].rolling(
        window=slope_period).apply(slope_calc, raw=False)
