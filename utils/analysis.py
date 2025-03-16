from momentum import rsi, add_adx
import logging
from utils.logging_config import logger
from risk import get_stop_data
from utils.utils import get_pre_analysis_period, store_filter_data, get_filter_data, get_ticker_list, \
    get_stock_selection_dates
from data_aquisition import fetch_yahoo_stock_data
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from trend import *
from datetime import datetime
from constants import Trade


def get_stock_signals(stock_list, setup, limit, start_date=None, end_date=None):

    signal_data = {}

    # Compute extended dates to improve metrics calculation
    analysis_start_date, analysis_end_date = get_stock_selection_dates(start_date, end_date, setup=setup)

    stock_data = fetch_yahoo_stock_data(get_ticker_list(stock_list),
                                        start_date=analysis_start_date,
                                        end_date=analysis_end_date)

    for ticker in stock_data.columns.levels[0]:
        # Extract data for this ticker into a new DataFrame
        df = stock_data[ticker]

        # Add arithmetic return
        df['1d_Return'] = df['Close'].pct_change(fill_method=None)

        # Add slope information to stock data
        add_moving_average_slope(df, setup)

        # Add ADX
        add_adx(df, setup)

        # Add OBV
        calculate_obv(df, setup)

        # Add Stochastic data
        add_stochastic_oscillator(df, setup)

        # Add Events Data
        # Long Term Crossing
        detect_long_term_crossings(stock_data=df, setup=setup, end_date=end_date)

        # MA Crossing
        detect_ma_crossings(stock_data=df, end_date=end_date, setup=setup)

        # Bollinger Bands
        detect_bollinger_crossings(stock_data=df, end_date=end_date, setup=setup)

        # Week Rule
        detect_wr_crossings(stock_data=df, setup=setup, end_date=end_date)

        # MACD Crossing
        detect_macd_trend(df, setup=setup, end_date=end_date)

        # Drop NA and remove auxiliary data
        df.dropna(inplace=True)
        df = df[df.index >= start_date]

        # Calculate score
        set_score_action(df, setup)

        if len(df[df['Action'] != HOLD]):
            signal_data[ticker] = df

        # Break loop if limit is exceeded
        limit -= 1
        if limit == 0:
            break

    return signal_data


def set_score_action(data, setup):
    """Calculates a normalized score for data based on analysis setup and assigns a trading action.

        Args:
            data (pandas.DataFrame): DataFrame containing method-specific cross values (e.g., 'method_Cross').
            setup (dict): Configuration dictionary with analysis methods, weights, and thresholds.
                Expected structure:
                - 'Analysis': Nested dict with analysis types, methods, and their 'enabled' status and 'weight'.
                - 'Thresholds': Dict with 'Buy' and 'Sell' threshold values.

        Returns:
            pandas.DataFrame: Modified DataFrame with 'Score' and 'Action' columns.
                - 'Score': Normalized score based on weighted method results.
                - 'Action': Trading action ('BUY', 'SELL', or 'HOLD') based on score thresholds.

        Raises:
            KeyError: If required keys (e.g., 'Analysis', 'Thresholds') are missing in setup or data.
            ZeroDivisionError: If total_score is zero due to no enabled methods or zero weights.
        """
    data['Score'] = 0.0
    total_score = 0.0

    for analysis in setup['Analysis'].keys():
        for method in setup['Analysis'][analysis].keys():
            if setup['Analysis'][analysis][method]['enabled']:
                if f'{method}_Cross' in data.keys():
                    # Assign weights to results
                    score = data[f"{method}_Cross"].apply(lambda x: setup['Analysis'][analysis][method]['weight'] * x)
                    data['Score'] += score

    for analysis in setup['Analysis'].keys():
        for method in setup['Analysis'][analysis].keys():
            if setup['Analysis'][analysis][method]['enabled']:
                total_score += setup['Analysis'][analysis][method]['weight']

    data['Score'] = data['Score'] / total_score

    buy_thold = setup['Thresholds']['Buy']
    sell_thold = setup['Thresholds']['Sell']

    data['Action'] = data['Score'].apply(lambda x: BUY if x >= buy_thold else SELL if x <= sell_thold else HOLD)


def add_moving_average_slope(stock_data, setup):

    # Add MA Period and calculate slope to data
    for ma in setup['Filters']['Trend'].keys():

        if not setup['Filters']['Trend'][ma]['enabled']:
            continue
        period = setup['Filters']['Trend'][ma]['period']
        slope = setup['Filters']['Trend'][ma]['slope_period']

        calculate_ma_slope(stock_data, ma_period=period, slope_period=slope, moving_average_type=ma)


def analysis_filter(data, setup, method):

    try:
        # Check if data crossed trend limits
        recommendation = data[f"{method}_Cross"].values[0]

        for ft in setup['Filters'].keys():
            for filter in setup['Filters'][ft].keys():
                if setup['Filters'][ft][filter]['enabled']:
                    if ft == 'Trend':
                        limit = setup['Filters'][ft][filter]['slope']
                        slope = data[f"MA_Slope_{filter}"].values[0]
                        if recommendation == "Buy" and slope < limit:
                            return True
                        elif recommendation == "Sell" and slope > limit:
                            return True
                    if ft == "Momentum":
                        if filter == "adx":
                            adx_range = setup['Filters'][ft][filter]['adx']
                            dip_range = setup['Filters'][ft][filter]['di+']
                            dim_range = setup['Filters'][ft][filter]['di-']
                            adx_value = data['ADX']
                            dip_value = data['DI+']
                            dim_value = data['DI-']
                            if recommendation == "Buy":
                                if adx_value > adx_range[1] or adx_value < adx_range[0]:
                                    return True
                                if dip_value > dip_range[1] or dim_value < dim_range[0]:
                                    return True
        return False
    except ValueError as e:
        logger.error(f"Failed to validate if data meets thresholds limitations - {str(e)}")


