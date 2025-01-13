import hashlib
import argparse
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import numpy as np
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


# Function to log errors
def log_error(message, logfile):
    """Log errors to the error log file."""
    with open(logfile, 'a') as log_file:
        log_file.write(message + '\n')


def read_tickers_from_file(file_path):
    """Read stock tickers from a text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r') as file:
        tickers = [line.split(',')[0].strip().upper() for line in file if line.strip()]
    return tickers


def valid_start_date(s: str) -> datetime:
    try:
        if s is None:
            return datetime.now() - relativedelta(days=365)
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")


def valid_end_date(s: str) -> datetime:
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
        print(f"Directory '{path}' created successfully.")


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

    logging.info(f"Saving analysis to file {report_hash}.csv")

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
                                    error_message = f"No {str(ke)} analysis found for {ticker}"
                                    print(error_message)
                                    log_error(error_message, f"logs/{report_hash}.log")
                                    analysis_output += ","

                    f.write(analysis_output + '\n')
                else:
                    print(f"{ticker} did not meet minimum score with {round(score, 2)}")

            f.close()

    except ValueError as e:
        logging.error("Failed to write analysis to file")


def backtest_to_file(analysis_data, backtest_data, setup, report_hash):

    logging.info(f"Saving backtest to file {report_hash}-bt.csv")
    slopes = {}

    try:
        with open(f"reports/{report_hash}-bt.csv", mode='a') as f:
            header = "Ticker,Analysis Recommendation"
            for analysis in setup['Analysis'].keys():

                for method in setup['Analysis'][analysis].keys():
                    if setup['Analysis'][analysis][method]['enabled']:
                        header += f",{method}_price_start,{method}_date_start,{method}_price_end,{method}_date_end"

            for trend_thold in setup['Thresholds']['Trend'].keys():
                if setup['Thresholds']['Trend'][trend_thold]['enabled']:
                    header += f",{trend_thold}_slope"
                    slopes.update({trend_thold: []})

            if setup['Risk']['Stop']['enabled']:
                header += f",gain,period,stop_date,effective_gain,effective_period\n"
            else:
                header += f",gain,period\n"
            f.write(header)

            for ticker in backtest_data.keys():
                # Get results recommendation for ticket
                price_start = []
                price_end = []
                date_start = []
                date_end = []


                for result_date in backtest_data[ticker]['results'].keys():
                    # Add result to file
                    recommendation = 'Buy' if analysis_data[ticker]['score'] > 0.0 else 'Sell'
                    result_output = f"{ticker},{recommendation}"

                    for analysis in setup['Analysis'].keys():
                        for method in setup['Analysis'][analysis].keys():
                            # Add Analysis Data
                            if setup['Analysis'][analysis][method]['enabled']:
                                try:
                                    date = analysis_data[ticker][method]['Date'].values[0].astype('datetime64[D]')
                                    result_output += f",{round(analysis_data[ticker][method]['Close'].values[0], 2)}," \
                                                     f"{date}"
                                    price_start.append(round(analysis_data[ticker][method]['Close'].values[0], 2))
                                    date_start.append(date)

                                    for trend_thold in setup['Thresholds']['Trend'].keys():
                                        if setup['Thresholds']['Trend'][trend_thold]['enabled']:
                                            slope = round(analysis_data[ticker][method][f"MA_Slope_{trend_thold}"].values[0],3)
                                            slopes[trend_thold].append(slope)

                                except KeyError as e:
                                    error_message = f"{str(e)} for {ticker} for backtest analysis"
                                    print(error_message)
                                    result_output += ',,'

                                # Add Backtest Data
                                try:
                                    date = backtest_data[ticker]['results'][result_date][method]['Date'].values[0].astype(
                                        'datetime64[D]')
                                    result_output += f",{round(backtest_data[ticker]['results'][result_date][method]['Close'].values[0], 2)}," \
                                                     f"{date}"
                                    price_end.append(round(backtest_data[ticker]
                                                           ['results'][result_date][method]['Close'].values[0], 2))
                                    date_end.append(date)
                                except KeyError as e:
                                    error_message = f"{str(e)} for {ticker} for backtest analysis"
                                    print(error_message)
                                    result_output += ',,'

                    # Add final slopes
                    for k in slopes.keys():
                        avg_slope = round(sum(slopes[k]) / len(slopes[k]), 3)
                        result_output += f",{avg_slope}"
                        slopes[k] = []  # Clear previous data

                    gain = round(100 * (max(price_end) - max(price_start)) / max(price_start), 2)

                    if recommendation == "Sell":
                        gain *= -1

                    period = str((max(date_end) - max(date_start))).replace("days", "")
                    result_output += f",{gain},{period}"

                    effective_gain = gain
                    effective_period = period

                    if setup['Risk']['Stop']['enabled'] and 'stop' in backtest_data[ticker]:

                        stop_date = backtest_data[ticker]['stop']['date']

                        if stop_date <= min(date_end):
                            effective_gain = setup['Risk']['Stop']['margin'] * 100 * (-1.0)
                            effective_period = np.datetime64(backtest_data[ticker]['stop']['date']) - max(date_start)
                            effective_period = str(effective_period).replace("days", "")

                    result_output += f",{stop_date},{effective_gain},{effective_period}"

                    f.write(result_output + '\n')
        f.close()
        print(f"Report saved in reports/{report_hash}-bt.csv")

    except ValueError as error:
        logging.error(str(error))


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

    for trend_period in setup['Thresholds']['Trend'].keys():
        if period < setup['Thresholds']['Trend'][trend_period]['period']:
            period = setup['Thresholds']['Trend'][trend_period]['period']

    if calendar_days:
        return int(period / 5) * 7 + (period % 5) + 7  # the last seven is an extra to cover holidays
    else:
        return period


def get_stock_selection_dates(start_date: datetime, setup, backtest=False):

    analysis_days = get_days_from_period(setup['Period']) + get_pre_analysis_period(setup)

    if backtest:
        end_date = start_date - relativedelta(hours=1) # Data up to day prior of backtest start_date
    else:
        end_date = datetime.today()

    start_date = end_date - relativedelta(days=analysis_days)

    return start_date, end_date

