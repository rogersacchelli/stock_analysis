import hashlib
import argparse
from datetime import datetime
import os


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


def valid_date(s: str) -> datetime or None:
    try:
        if s is None:
            return None
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
    # Iterate through dict printing analysis data

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Output file based on user settings
    with open(f"reports/{report_hash}.csv", mode='a') as f:

        header = "Ticker,Report Date"

        trend_total_weight = 0.0
        # Create Header based on analysis settings
        for trend in setup['Trend'].keys():
            if setup['Trend'][trend]['enabled']:
                if trend == "long_term":
                    header = f"{header},{trend.upper()} {setup['Trend'][trend]['period']}"

                if trend == "sma_cross" or trend == "ema_cross":
                    header = f"{header},{trend.upper()} {setup['Trend'][trend]['short']}/" \
                             f"{setup['Trend'][trend]['long']}"

                elif trend == "bollinger_bands" or trend == "week_rule":
                    header = f"{header},{setup['Trend'][trend]['period']} {trend.upper()}"

                elif trend == "macd":
                    header = f"{header},{setup['Trend'][trend]['signal_window']} {trend.upper()}"

        f.write(header + '\n')

        # Add data per ticker
        for ticker in analysis_data.keys():

            analysis_output = f"{ticker},{current_date}"

            for analysis in setup['Trend'].keys():
                if setup['Trend'][analysis]['enabled']:
                    try:
                        recommendation = analysis_data[ticker][analysis]['Cross'].values[0]
                        analysis_output += f",{recommendation}"

                    except KeyError as ke:
                        error_message = f"No {str(ke)} analysis found for {ticker}"
                        print(error_message)
                        log_error(error_message, f"logs/{report_hash}.log")
                        analysis_output += ","

            f.write(analysis_output + '\n')

        f.close()

def position_results_to_file(position_results, setup, hash):

    with open(f"reports/{hash}-position.csv", mode='w') as f:
        output = "Ticker,Date Start,Price Start,Last Close,Volume,Gain %,Period,Profit\n"
        f.write(output)

        for ticker in position_results.keys():
            for date in position_results[ticker].keys():
                price_start = position_results[ticker][date]['price_start']
                price_end = position_results[ticker][date]['price_end']
                gain = position_results[ticker][date]['gain']
                period = position_results[ticker][date]['period'].days
                volume = position_results[ticker][date]['volume']
                profit = round(volume * (gain/100.0) * price_start, 2)
                if (gain / 100.0) <= (1-setup['Risk']['Stop']['margin']):
                    output = f"**{ticker}**,{date},{price_start},{price_end},{volume},**{gain}**,{period}, {profit}\n"
                else:
                    output = f"{ticker},{date},{price_start},{price_end},{volume},{gain},{period}, {profit}\n"
                f.write(output)
    f.close()
