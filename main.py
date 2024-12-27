import yfinance as yf
from datetime import datetime, timedelta
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
def detect_crossings(stock_data, short_window, long_window, eval_window):
    """Detect days where SMA crosses."""
    stock_data[f"SMA_CROSS_{short_window}"] = stock_data['Close'].rolling(window=short_window).mean()
    stock_data[f"SMA_CROSS_{long_window}"] = stock_data['Close'].rolling(window=long_window).mean()

    # Identify crossing points
    stock_data[f"Prev_SMA_CROSS_{short_window}"] = stock_data[f"SMA_CROSS_{short_window}"].shift(1)
    stock_data[f"Prev_SMA_CROSS_{long_window}"] = stock_data[f"SMA_CROSS_{long_window}"].shift(1)
    stock_data['Cross'] = np.where(
        (stock_data[f"Prev_SMA_CROSS_{short_window}"] <= stock_data[f"Prev_SMA_CROSS_{long_window}"]) & (stock_data[f"SMA_CROSS_{short_window}"] > stock_data[f"SMA_CROSS_{long_window}"]),
        'Buy',
        np.where(
            (stock_data[f"Prev_SMA_CROSS_{short_window}"] >= stock_data[f"Prev_SMA_CROSS_{long_window}"]) & (stock_data[f"SMA_CROSS_{short_window}"] < stock_data[f"SMA_CROSS_{long_window}"]),
            'Sell',
            None
        )
    )

    today = np.datetime64('today', 'D')
    cutoff_date = today - np.timedelta64(eval_window, 'D')

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column
    return crossings[crossings['Date'] >= cutoff_date]


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



# Main function
def main():
    parser = argparse.ArgumentParser(description="Analyze stock crossings of moving averages.")
    parser.add_argument('-i', '--input', required=True, action=LoadFromFile, help="Input file containing stock tickers in JSON format.")
    parser.add_argument('-e', '--email', help="Email address to send results.")
    parser.add_argument('-c', '--config', required=True, action=LoadFromFile, help="Configuration File.")
    parser.add_argument('-a', '--analysis', required=True, action=LoadFromFile, help="Analysis Definition File.")
    args = parser.parse_args()

    settings = args.config
    analysis_settings = args.analysis

    try:
        ticker_list = args.input

        # Get current date and time in the format YYYY-MM-DDTHH:MM:SS
        current_datetime = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        current_date = datetime.now().strftime('%d/%m/%Y')

        if analysis_settings['Trend']['sma_cross_enabled']:

            all_crossings_sma = None

            for ticker_code in ticker_list:
                ticker = ticker_code['Code']
                print(f"Analyzing {ticker}...")

                try:
                    stock_data = fetch_stock_data(ticker, period=analysis_settings['Trend']['sma_cross_period'])
                    crossings = detect_crossings(stock_data, short_window=analysis_settings['Trend']['sma_cross_short'],
                                                 long_window=analysis_settings['Trend']['sma_cross_long'],
                                                 eval_window=analysis_settings['Trend']['sma_cross_eval_window'])
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
                all_crossings_sma_cross_html = all_crossings_sma.dropna().to_html(index=True)
                body = f"<html><body><h2>Stock Data Report</h2>" \
                       f"<h3>Trend Analysis - SMA Cross</h3>\
                        {all_crossings_sma_cross_html}\
                        </body></html>"
                if args.email:
                    send_html_email(sender_email=settings['Email']['from_email'], receiver_email=args.email,
                                    subject=f"Stock Analysis {current_date}",
                                    html_content=body,
                                    smtp_server=settings['Email']['smtp_server'],
                                    smtp_port=settings['Email']['smtp_port'],
                                    password=settings['Email']['from_password'])
            else:
                print("No results to send via email.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
