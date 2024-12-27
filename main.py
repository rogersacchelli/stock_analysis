import yfinance as yf
from datetime import datetime
import numpy as np
import os
import argparse
import configparser
import pandas as pd

from utils.email import send_html_email
from utils.loadSettings import LoadFromFile

pd.options.mode.chained_assignment = None


# Function to fetch stock data
def fetch_stock_data(ticker, period="1y"):
    """Fetch historical stock data for the given ticker."""
    stock_data = yf.download(ticker, period=period, multi_level_index=False)
    if stock_data.empty:
        raise ValueError(f"No data available for ticker {ticker}.")
    return stock_data


# Function to calculate moving averages and detect crossings
def detect_crossings(stock_data, short_window, long_window):
    """Detect days where SMA crosses."""
    stock_data['SMA20'] = stock_data['Close'].rolling(window=short_window).mean()
    stock_data['SMA200'] = stock_data['Close'].rolling(window=long_window).mean()

    # Identify crossing points
    stock_data['Prev_SMA20'] = stock_data['SMA20'].shift(1)
    stock_data['Prev_SMA200'] = stock_data['SMA200'].shift(1)
    stock_data['Cross'] = np.where(
        (stock_data['Prev_SMA20'] <= stock_data['Prev_SMA200']) & (stock_data['SMA20'] > stock_data['SMA200']),
        'Buy',
        np.where(
            (stock_data['Prev_SMA20'] >= stock_data['Prev_SMA200']) & (stock_data['SMA20'] < stock_data['SMA200']),
            'Sell',
            None
        )
    )

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column
    return crossings


# Function to read tickers from a file
def read_tickers_from_file(file_path):
    """Read stock tickers from a text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r') as file:
        tickers = [line.split(',')[0].strip().upper() for line in file if line.strip()]
    return tickers


# Function to log errors
def log_error(message, logfile):
    """Log errors to the error log file."""
    with open(logfile, 'a') as log_file:
        log_file.write(message + '\n')


# Function to save analysis data
def save_analysis_data(ticker, crossings, analysis_frame):
    """Save analysis data to a CSV file."""
    #if analysis_frame is None:
    return pd.concat([analysis_frame, crossings], ignore_index=True)
    #else:
    #    return pd.concat([analysis_frame, crossings], ignore_index=True)


# Function to load settings from a configuration file
def load_settings(config_file):
    """Load settings from a configuration file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    settings = {
        'smtp_server': config.get('Email', 'smtp_server'),
        'smtp_port': config.getint('Email', 'smtp_port'),
        'from_email': config.get('Email', 'from_email'),
        'from_password': config.get('Email', 'from_password')
    }
    return settings



# Main function
def main():
    parser = argparse.ArgumentParser(description="Analyze stock crossings of moving averages.")
    parser.add_argument('-i', '--input', required=True, help="Input file containing stock tickers.")
    parser.add_argument('-e', '--email', help="Email address to send results.")
    parser.add_argument('-c', '--config', required=True, action=LoadFromFile, help="Configuration File.")
    parser.add_argument('-a', '--analysis', required=True, action=LoadFromFile, help="Analysis Definition File.")
    args = parser.parse_args()

    settings = args.config
    analysis_settings = args.analysis

    try:
        tickers = read_tickers_from_file(args.input)
        print(f"Loaded {len(tickers)} tickers from the file.")

        # Get current date and time in the format YYYY-MM-DDTHH:MM:SS
        current_datetime = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        current_date = datetime.now().strftime('%d %m %Y')

        if analysis_settings['Trend']['sma_enabled']:

            all_crossings_sma = None

            for ticker in tickers:
                print(f"Analyzing {ticker}...")

                try:
                    stock_data = fetch_stock_data(ticker, period=analysis_settings['Trend']['sma_period'])
                    crossings = detect_crossings(stock_data, short_window=analysis_settings['Trend']['sma_short'],
                                                 long_window=analysis_settings['Trend']['sma_long'])
                    if not crossings.empty:
                        print(f"Crossings found for {ticker}. Saving to analysis file.")
                        crossings.index = [ticker]*len(crossings)
                        all_crossings_sma = pd.concat([all_crossings_sma, crossings])
                    else:
                        print(f"No crossings detected for {ticker}.")
                except Exception as e:
                    error_message = f"Error analyzing {ticker}: {e}"
                    print(error_message)
                    log_error(error_message, 'error_logfile.txt')

            # Compile results for email
            if all_crossings_sma is not None:
                all_crossings_sma.to_csv(f"analysis_{current_datetime}.csv", index=False)
                all_crossings_sma_html = all_crossings_sma.dropna().to_html(index=True)
                body = f"<html><body><h2>Stock Data Report</h2>{all_crossings_sma_html}</body></html>"
                if args.email:
                    send_html_email(sender_email=settings['from_email'], receiver_email=args.email,
                                    subject=f"Stock Analysis {current_date}", html_content=body,
                                    smtp_server=settings['smtp_server'], smtp_port=settings['smtp_port'],
                                    password=settings['from_password'])
            else:
                print("No results to send via email.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
