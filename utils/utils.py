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

