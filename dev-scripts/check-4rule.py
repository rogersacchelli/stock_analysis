import yfinance as yf
import pandas as pd


def check_4_week_rule_for_tickers(tickers, start_date, end_date):
    """
    Loops through a list of tickers and checks if they have any periods
    of 4-week rule breaking (buy or sell signals), using correctly shifted data.

    Parameters:
        tickers (list): List of stock tickers (e.g., ['AAPL', 'MSFT']).
        start_date (str): Start date for the analysis (YYYY-MM-DD).
        end_date (str): End date for the analysis (YYYY-MM-DD).

    Returns:
        dict: Dictionary with ticker as key and whether it broke the 4-week rule as value.
    """
    results = {}

    for ticker in tickers:
        # Fetch historical data
        data = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False)

        # Check if data is fetched successfully
        if data.empty:
            results[ticker] = "No data available"
            continue

        # Calculate prior 4-week highs and lows (shifted by 1 day)
        data['4W_High'] = data['High'].rolling(window=20).max().shift(1)
        data['4W_Low'] = data['Low'].rolling(window=20).min().shift(1)

        # Check if any rule-breaking occurred
        rule_broken = (
            (data['Close'] > data['4W_High']).any() or  # Buy signal
            (data['Close'] < data['4W_Low']).any()      # Sell signal
        )

        # Store result
        results[ticker] = "Rule Broken" if rule_broken else "No Rule Breaking"

    return results


# Example usage
if __name__ == "__main__":
    # Define parameters
    ticker_list = ['AAPL', 'MSFT', 'TSLA', 'GOOGL']
    start = '2020-01-01'
    end = '2023-12-31'

    # Analyze tickers
    rule_breaking_summary = check_4_week_rule_for_tickers(ticker_list, start, end)

    # Print results
    for ticker, status in rule_breaking_summary.items():
        print(f"{ticker}: {status}")
