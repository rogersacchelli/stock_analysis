from datetime import datetime
from constants import *

import numpy as np

def get_stop_data(stock_data, setup, start_price, start_date: datetime, initial_recommendation):
    # Search for Stops based on setup and add info to ticker

    if initial_recommendation == 'Buy':
        for date, row in stock_data.iterrows():
            if (row['Close'] <= start_price * (1.0 - setup['Risk']['Stop']['margin'])) and date >= start_date:
                return date.date(), row['Close']
    else:
        for date, row in stock_data.iterrows():
            if row['Close'] >= start_price * (1.0 + setup['Risk']['Stop']['margin']) and date >= start_date:
                return date.date(), row['Close']

    return None, None


def add_shape_ratio(data, risk_free, setup):

    # Constants
    TRADING_DAYS = setup['Risk']['SharpeRatio']['TradingDays']
    LOOKBACK_PERIOD = setup['Risk']['SharpeRatio']['LoopbackPeriod']

    # Ensure data is clean and aligned
    #if data['daily_return'].isna().any() or risk_free['Close'].isna().any():
    #    raise ValueError("Input data contains NaN values. Please clean the data.")

    # Calculate rolling metrics
    std = data['daily_return'].rolling(LOOKBACK_PERIOD).std().dropna()
    daily_return = data['daily_return'].rolling(LOOKBACK_PERIOD).mean().dropna()

    # Convert risk-free rate to daily (assuming risk_free['Close'] is an annual rate in percentage)
    risk_free_daily = (risk_free['Close'] / 100) / TRADING_DAYS
    risk_free_daily = risk_free_daily.rolling(LOOKBACK_PERIOD).mean().dropna()

    # Align indices
    common_index = std.index.intersection(daily_return.index).intersection(risk_free_daily.index)
    if common_index.empty:
        raise ValueError("No common index found after alignment. Check data consistency.")

    # Calculate annualized excess return and standard deviation
    excess_return = daily_return.loc[common_index] - risk_free_daily.loc[common_index]
    annualized_excess_return = excess_return * np.sqrt(TRADING_DAYS)
    annualized_std = std.loc[common_index] * np.sqrt(TRADING_DAYS)

    # Calculate annualized Sharpe Ratio
    data.loc[common_index, 'sharpe_ratio'] = annualized_excess_return / annualized_std

    # Optional: Handle edge cases where std is zero to avoid division errors
    data.loc[common_index, 'sharpe_ratio'] = data.loc[common_index, 'sharpe_ratio'].replace([np.inf, -np.inf], np.nan)


def add_sortino_ratio(df, risk_free):
    """
    Add Sortino ratio to a DataFrame with stock price data from Yahoo Finance,
    using a risk-free rate from a DataFrame.

    Parameters:
    - df (pd.DataFrame): DataFrame with 'Adj Close' column from yfinance.
    - risk_free_df (pd.DataFrame): DataFrame with a column of daily risk-free rates.
    - risk_free_col (str): Name of the column in risk_free_df with risk-free rates (default: 'Rate').
    - lookback_period (int): Number of days for rolling Sortino calculation (default: 30).
    - trading_days (int): Number of trading days in a year (default: 252).

    Returns:
    - pd.DataFrame: Original DataFrame with a new 'Sortino_Ratio' column.

    Raises:
    - ValueError: If risk_free_df index does not match df index or risk_free_col is missing.
    """

    # Initialize Sortino ratio column
    df['sortino_ratio'] = np.nan

    lookback_period = 20
    trading_days = 252

    # Extract risk-free rate series
    daily_rf = (1 + risk_free['Close']) ** (1 / trading_days) - 1

    # Calculate rolling Sortino ratio
    for i in range(lookback_period, len(df)):
        # Get returns and risk-free rates for the lookback period
        returns = df['daily_return'].iloc[i - lookback_period:i]
        rf_window = daily_rf.iloc[i - lookback_period:i]

        # Excess returns (returns - risk-free rate)
        excess_returns = returns - rf_window

        # Mean excess return
        mean_excess_return = excess_returns.mean()

        # Downside deviation (negative excess returns only)
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = np.sqrt(np.mean(downside_returns ** 2)) if len(downside_returns) > 0 else np.nan

        # Sortino ratio: (mean excess return) / downside deviation
        # Annualize by multiplying by sqrt(trading_days)
        if downside_deviation and not np.isnan(downside_deviation) and downside_deviation != 0:
            sortino = (mean_excess_return / downside_deviation) * np.sqrt(trading_days)
        else:
            sortino = np.nan

        df.iloc[i, df.columns.get_loc('sortino_ratio')] = sortino

    return df


def get_stock_from_rm(df, setup):

    for ticker in df.keys():

        data = df[ticker]

        # Sharpe Ratio Filter
        if setup['Risk']['SharpeRatio']['enabled']:
            sharpe_ratio_buy = setup['Risk']['SharpeRatio']['min']
            data = data[data['sharpe_ratio'] >= sharpe_ratio_buy]
            df[ticker] = data

        # Moving Average Filter
        for ma in setup['Filters']['Trend'].keys():
            if setup['Filters']['Trend'][ma]['enabled']:
                if ma == 'ma_cross':

                    # Buy if slope is higher than
                    buy_short = setup['Filters']['Trend'][ma]['slope']['buy']['short']
                    buy_long = setup['Filters']['Trend'][ma]['slope']['buy']['long']
                    sell_short = setup['Filters']['Trend'][ma]['slope']['sell']['short']
                    sell_long = setup['Filters']['Trend'][ma]['slope']['sell']['long']

                    # Filter Buying signals
                    data = data[(data[f"ma_cross_Cross"] == HOLD) | (data[f"ma_cross_Cross"] == SELL) | ((
                           (data[f"ma_cross_Cross"] == BUY) & (data[f"MA_Slope_{ma}_short"] >= buy_short)) & (
                           (data[f"ma_cross_Cross"] == BUY) & (data[f"MA_Slope_{ma}_long"] >= buy_long)))]

                    # Filter Sell signals
                    data = data[(data[f"ma_cross_Cross"] == HOLD) | (data[f"ma_cross_Cross"] == BUY) | ((
                            (data[f"ma_cross_Cross"] == SELL) & (data[f"MA_Slope_{ma}_short"] <= sell_short)) & (
                            (data[f"ma_cross_Cross"] == SELL) & (data[f"MA_Slope_{ma}_long"] <= sell_long)))]

                else:
                    pass
                    # TODO: IMPLEMENT FILTER FOR MOVING AVERAGES

    return df