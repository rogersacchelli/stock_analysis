import hashlib
import argparse
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils.logging_config import logger
import os
import json

class LoadFromFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        with open(values, 'r') as config_file:
            config_dict = json.load(config_file)
        setattr(namespace, self.dest, config_dict)


def get_hash(data):

    md5_hash = hashlib.md5()
    # Update the hash object with the bytes of the data
    md5_hash.update(data.encode('utf-8'))
    # Get the hexadecimal digest of the hash
    hex_digest = md5_hash.hexdigest()

    return hex_digest


def read_tickers_from_file(file_path):
    """Read stock tickers from a text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r') as file:
        tickers = [line.split(',')[0].strip().upper() for line in file if line.strip()]
    return tickers


def valid_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")


def valid_start_date(s: str) -> datetime:
    try:
        if s is None:
            return datetime.now() - relativedelta(days=365)
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")


def valid_end_date(s: str | None) -> datetime:
    try:
        if s is None:
            return datetime.now()
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")


def search_file(directory, filename):
    for root, dirs, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None


def create_directories_if_not_exist(path):
    """
    Creates the specified directory path if it does not exist.

    Args:
    path (str): The directory path to create.
    """
    # Check if the directory exists, if not, create it
    if not os.path.exists(path):
        os.makedirs(path)
        logging.info(f"Directory '{path}' created successfully.")


def get_days_from_period(period):

    if 'd' in period:
        period = period.replace('d', '')
        return int(period) * 1

    elif 'w' in period:
        period = period.replace('w', '')
        return int(period) * 7

    elif "mo" in period:
        period = period.replace("mo", '')
        return int(period) * 30

    elif 'y' in period:
        period = period.replace('y', '')
        return int(period) * 365

    else:
        raise ValueError(f"Period format [{period}] not recognized. Valid forms: [d, w, m, y].")


def analysis_to_file(analysis_data, setup, report_hash):

    logger.info(f"Saving analysis to file {report_hash}.csv")

    try:

        current_date = datetime.now().strftime('%Y-%m-%d')

        # Output file based on user settings
        with open(f"reports/{report_hash}.csv", mode='a') as f:

            header = "Ticker,Report Date"

            # Create Header based on analysis settings
            analysis_list = ["Trend", "Momentum"]

            for analysis in setup['Analysis'].keys():
                for method in setup['Analysis'][analysis].keys():
                    if setup['Analysis'][analysis][method]['enabled']:
                        name = setup['Analysis'][analysis][method]['name']
                        header = f"{header},{name}"

            f.write(header + '\n')

            # Add data per ticker
            for ticker in analysis_data.keys():

                score = analysis_data[ticker]['score']

                if score >= setup['Thresholds']['Buy'] or score <= setup['Thresholds']['Sell']:
                    analysis_output = f"{ticker},{current_date}"

                    for analysis in setup['Analysis'].keys():
                        for method in setup['Analysis'][analysis].keys():
                            if setup['Analysis'][analysis][method]['enabled']:
                                try:
                                    recommendation = analysis_data[ticker][method]['Cross'].values[0]
                                    analysis_output += f",{recommendation}"
                                except KeyError as ke:
                                    logger.debug(f"No {str(ke)} analysis found for {ticker}")
                                    analysis_output += ","

                    f.write(analysis_output + '\n')

            f.close()

    except ValueError as e:
        logger.error(f"Failed to write analysis to file str({e})")


def position_results_to_file(position_results, setup, hash):

    with open(f"reports/{hash}-position.csv", mode='w') as f:
        output = "Ticker,Date Start,Price Start,Last Close,Volume,Gain %,Period,Profit [USD]\n"
        f.write(output)

        for ticker in position_results.keys():
            for date in position_results[ticker].keys():
                price_start = position_results[ticker][date]['price_start']
                price_end = position_results[ticker][date]['price_end']
                gain = position_results[ticker][date]['gain']
                period = position_results[ticker][date]['period'].days
                volume = position_results[ticker][date]['volume']
                profit = round(volume * (gain/100.0) * price_start, 2)
                if (gain / 100.0) <= (setup['Risk']['Stop']['margin'] * -1.00):
                    output = f"**{ticker}**,{date},{price_start},{price_end},{volume},**{gain}**,{period}, {profit}\n"
                else:
                    output = f"{ticker},{date},{price_start},{price_end},{volume},{gain},{period}, {profit}\n"
                f.write(output)
    f.close()


def get_pre_analysis_period(setup, calendar_days=True):
    # Get the lengthiest period analysis from setup
    period = 0

    for analysis in setup['Analysis'].keys():
        for method in setup['Analysis'][analysis].keys():
            if 'period' in setup['Analysis'][analysis][method] and setup['Analysis'][analysis][method]['enabled']:
                if period < setup['Analysis'][analysis][method]['period']:
                    period = setup['Analysis'][analysis][method]['period']
            elif 'long' in setup['Analysis'][analysis][method]:
                if period < setup['Analysis'][analysis][method]['long']:
                    period = setup['Analysis'][analysis][method]['long']

    for ft in setup['Filters'].keys():
        for f in setup['Filters'][ft].keys():
            if period < setup['Filters'][ft][f]['period'] and setup['Filters'][ft][f]['enabled']:
                period = setup['Filters'][ft][f]['period']

    if calendar_days:
        return int(period / 5) * 7 + (period % 5) + 7  # the last seven is an extra to cover holidays
    else:
        return period


def get_stock_selection_dates(start_date: datetime, setup, backtest=False):

    analysis_days = get_days_from_period(setup['Period']) + get_pre_analysis_period(setup)

    if backtest:
        end_date = start_date - relativedelta(hours=1)  # Data up to day prior of backtest start_date
    else:
        end_date = datetime.combine(datetime.now().date(), datetime.min.time())+relativedelta(hours=23)

    start_date = end_date - relativedelta(days=analysis_days)

    return start_date, end_date


def store_filter_data(filter_data, method, analysis_ticker_data, setup):

    try:
        # Add filter data
        for ft in setup['Filters'].keys():
            for filter in setup['Filters'][ft].keys():
                if filter not in filter_data[ft]:
                    filter_data[ft][filter] = []

                if ft == "Trend":
                    # Loop all Trend filters
                    slope = round(analysis_ticker_data[method][f"MA_Slope_{filter}"].values[0], 3)
                    filter_data[ft][filter].append(slope)
                elif ft == "Momentum":
                    if filter == "adx":
                        adx = round(analysis_ticker_data[method]["ADX"].values[0], 3)
                        dip = round(analysis_ticker_data[method]["+DI"].values[0], 3)
                        dim = round(analysis_ticker_data[method]["-DI"].values[0], 3)

                        filter_data[ft][filter].append([adx, dip, dim])

    except ValueError as error:
        logger.error(f"{str(error)}")


def get_filter_data(filter_data, result_output):

    try:
        for ft in filter_data.keys():
            for filter in filter_data[ft].keys():
                if filter == "adx":
                    adx = 0.0
                    dip = 0.0
                    dim = 0.0
                    n = 0

                    for v in filter_data[ft][filter]:
                        adx += v[0]
                        dip += v[1]
                        dim += v[2]
                        n += 1

                    adx = round(adx/n, 3)
                    dip = round(dip/n, 3)
                    dim = round(dim/n, 3)
                    result_output += f",{adx},{dip},{dim}"

                    # clear data
                    filter_data[ft][filter] = []
                else:
                    total = sum(filter_data[ft][filter])
                    l = len(filter_data[ft][filter])
                    v = round(total / float(l), 3)
                    result_output += f",{v}"
                    filter_data[ft][filter] = []  # Clear previous data
        return result_output
    except ValueError as error:
        logger.error(f"{str(error)}")


