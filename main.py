import yfinance as yf
import pandas as pd
import numpy as np
import os

# File paths for logs and analysis data
ERROR_LOGFILE = "error_logfile.txt"
ANALYSIS_FILE = "analysis.csv"

# Function to fetch stock data
def fetch_stock_data(ticker, period="1y"):
    """Fetch historical stock data for the given ticker."""
    stock_data = yf.download(ticker, period=period)
    if stock_data.empty:
        raise ValueError(f"No data available for ticker {ticker}.")
    return stock_data

# Function to calculate moving averages and detect crossings
def detect_crossings(stock_data):
    """Detect days where SMA20 crosses SMA200."""
    stock_data['SMA20'] = stock_data['Close'].rolling(window=20).mean()
    stock_data['SMA200'] = stock_data['Close'].rolling(window=200).mean()

    # Identify crossing points
    stock_data['Prev_SMA20'] = stock_data['SMA20'].shift(1)
    stock_data['Prev_SMA200'] = stock_data['SMA200'].shift(1)
    stock_data['Cross'] = np.where(
        (stock_data['Prev_SMA20'] <= stock_data['Prev_SMA200']) & (stock_data['SMA20'] > stock_data['SMA200']),
        'Golden Cross (Buy)',
        np.where(
            (stock_data['Prev_SMA20'] >= stock_data['Prev_SMA200']) & (stock_data['SMA20'] < stock_data['SMA200']),
            'Death Cross (Sell)',
            None
        )
    )

    # Add a Date column and filter rows with crossings
    crossings = stock_data[stock_data['Cross'].notna()]
    crossings = crossings.reset_index()  # Reset index to access the Date column
    crossings = crossings.rename(columns={"Date": "Crossing Date"})
    return crossings

# Function to read tickers from a file
def read_tickers_from_file(file_path):
    """Read stock tickers from a text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'r') as file:
        tickers = [line.strip().upper() for line in file if line.strip()]
    return tickers

# Function to log errors
def log_error(message):
    """Log errors to the error log file."""
    with open(ERROR_LOGFILE, 'a') as log_file:
        log_file.write(message + '\n')

# Function to save analysis data
def save_analysis_data(ticker, crossings):
    """Save analysis data to a CSV file."""
    crossings['Ticker'] = ticker
    mode = 'a' if os.path.exists(ANALYSIS_FILE) else 'w'
    header = not os.path.exists(ANALYSIS_FILE)  # Write header only if file doesn't exist
    crossings.to_csv(ANALYSIS_FILE, mode=mode, header=header, index=False)

# Main function
def main():
    file_path = input("Enter the file path containing stock tickers: ").strip()
    try:
        tickers = read_tickers_from_file(file_path)
        print(f"Loaded {len(tickers)} tickers from the file.")

        for ticker in tickers:
            print(f"Analyzing {ticker}...")
            try:
                stock_data = fetch_stock_data(ticker)
                crossings = detect_crossings(stock_data)

                if not crossings.empty:
                    print(f"Crossings found for {ticker}. Saving to analysis file.")
                    save_analysis_data(ticker, crossings[['Crossing Date', 'Close', 'SMA20', 'SMA200', 'Cross']])
                else:
                    print(f"No crossings detected for {ticker}.")
            except Exception as e:
                error_message = f"Error analyzing {ticker}: {e}"
                print(error_message)
                log_error(error_message)
    except Exception as e:
        log_error(f"Error: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
