import json
import sys
import pandas as pd
import yfinance as yf
import pickle
import os


def load_pickle_if_exists(pickle_file='stock_data.pkl'):
    """Try to load existing pickle file; return None if not found."""
    if os.path.exists(pickle_file):
        try:
            with open(pickle_file, 'rb') as file:
                return pd.read_pickle(pickle_file)
        except Exception as e:
            print(f"Error loading pickle file {pickle_file}: {e}")
    return None


def main(json_file_path):
    # Try to load existing pickle file
    pickle_file = 'stock_data.pkl'
    df = load_pickle_if_exists(pickle_file)
    if df is not None:
        print(f"Loaded existing data from {pickle_file}")
        return df

    # If no pickle file, load JSON and fetch data from Yahoo Finance
    with open(json_file_path, 'r') as file:
        stock_list = json.load(file)

    # Prepare a list to hold the augmented data
    augmented_data = []

    for stock in stock_list:
        symbol = stock.get('Symbol')
        if not symbol:
            continue  # Skip if no symbol

        try:
            # Fetch stock info from Yahoo Finance
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Extract all available features from yfinance
            augmented_stock = {
                'Symbol': symbol,
                'Security': stock.get('Security'),
                'GICS Sector': stock.get('GICS Sector'),
                'GICS Sub-Industry': stock.get('GICS Sub-Industry'),
                'Headquarters Location': stock.get('Headquarters Location'),
                'Date added': stock.get('Date added'),
                'CIK': stock.get('CIK'),
                'Founded': stock.get('Founded'),
                **{key: value for key, value in info.items()}  # Include all yfinance info fields
            }

            augmented_data.append(augmented_stock)

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            # Add with original data and None for yfinance fields
            augmented_stock = {
                'Symbol': symbol,
                'Security': stock.get('Security'),
                'GICS Sector': stock.get('GICS Sector'),
                'GICS Sub-Industry': stock.get('GICS Sub-Industry'),
                'Headquarters Location': stock.get('Headquarters Location'),
                'Date added': stock.get('Date added'),
                'CIK': stock.get('CIK'),
                'Founded': stock.get('Founded')
            }
            augmented_data.append(augmented_stock)

    # Create a DataFrame from the augmented data
    df = pd.DataFrame(augmented_data)

    # Save the DataFrame to a pickle file
    try:
        df.to_pickle(pickle_file)
        print(f"DataFrame saved to {pickle_file}")
    except Exception as e:
        print(f"Error saving pickle file {pickle_file}: {e}")

    # Also save to CSV for easier inspection (optional)
    df.to_csv('augmented_stock_data.csv', index=False)
    print(f"DataFrame also saved to augmented_stock_data.csv")

    return df


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_json_file>")
        sys.exit(1)

    json_file_path = sys.argv[1]
    main(json_file_path)