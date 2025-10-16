import argparse
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import linregress
from tabulate import tabulate
import json
import os
import smtplib
from email.mime.text import MIMEText

def download_data(symbol, start, end, interval='1d'):
    """
    Download historical data for a symbol, with caching.
    """
    DATA_DIR = "yf_cache"
    os.makedirs(DATA_DIR, exist_ok=True)

    filename = f"{symbol}-{start}-{end}_{interval}.pkl"
    filepath = os.path.join(DATA_DIR, filename)

    if os.path.exists(filepath):
        print(f"Loading cached data for {symbol} from {filepath}")
        data = pd.read_pickle(filepath)
        if not data.empty:
            return data
        else:
            # If cached but empty, remove it
            os.remove(filepath)
            print(f"Removed empty cache for {symbol}")

    print(f"Downloading data for {symbol}...")
    data = yf.download(symbol, start=start, end=end, interval=interval, multi_level_index=False, progress=False,
                       auto_adjust=False)

    if not data.empty:
        data = data.dropna()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        data.to_pickle(filepath)
        print(f"Saved data to {filepath}")
        return data
    else:
        print(f"No data downloaded for {symbol}")
        return pd.DataFrame()

def send_email(smtp_server, smtp_port, from_email, to_email, password, table_str):
    subject = 'Stock Comparison Results'
    body = f'<html><body><pre style="font-family: monospace; white-space: pre-wrap;">Comparison Metrics:\n\n{table_str}</pre></body></html>'

    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    parser = argparse.ArgumentParser(description='Compare stock correlations to a reference symbol.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--symbols', nargs='+', help='List of stock symbols (first is reference)')
    group.add_argument('--json-file', type=str, help='Path to JSON file containing list of stock symbols (first is reference)')
    parser.add_argument('--interval', default='1d', help='Data interval (default: 1d)')
    parser.add_argument('--last-n-days', type=int, help='Number of last days to fetch data (overrides start date)')
    parser.add_argument('--start', help='Start date (YYYY-MM-DD), default: last 3 months')
    parser.add_argument('--end', help='End date (YYYY-MM-DD), default: today')
    parser.add_argument('--send-email', action='store_true', help='Send results via email')
    parser.add_argument('--email-to', type=str, help='Recipient email address')
    parser.add_argument('--settings-file', type=str, help='Path to JSON settings file for email configuration')
    parser.add_argument('--min-relative-gain', type=float, help='Minimum relative gain (%) to include in results')
    args = parser.parse_args()

    if args.symbols:
        symbols = args.symbols
        use_json = False
    else:
        with open(args.json_file, 'r') as f:
            stock_data = json.load(f)
        symbols = [item['Symbol'] for item in stock_data]
        use_json = True

    if len(symbols) < 2:
        raise ValueError("At least two symbols are required (one reference and one to compare).")

    reference = symbols[0]
    others = symbols[1:]

    end_date = args.end or datetime.now().strftime('%Y-%m-%d')
    if args.last_n_days:
        start_date = (datetime.now() - timedelta(days=args.last_n_days)).strftime('%Y-%m-%d')
        period_str = f"Last {args.last_n_days} days ({start_date} to {end_date})"
    elif args.start:
        start_date = args.start
        period_str = f"{start_date} to {end_date}"
    else:
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        period_str = f"Last 3 months ({start_date} to {end_date})"

    if use_json:
        ref_info = stock_data[0]
        print(f"Reference symbol: {reference} (Company: {ref_info['Security']}, Sector: {ref_info['GICS Sector']})")
    else:
        print(f"Reference symbol: {reference}")
    print(f"Period: {period_str}")
    print(f"Interval: {args.interval}")
    print()

    # Download close prices for all symbols
    price_series = {}
    for sym in symbols:
        data = download_data(sym, start_date, end_date, args.interval)
        if not data.empty and 'Close' in data.columns:
            price_series[sym] = data['Close']
        # else: skip silently, message already printed in download_data

    if not price_series:
        raise ValueError("No data available for any symbols.")

    prices = pd.concat(price_series, axis=1)

    if reference not in prices.columns:
        raise ValueError(f"No data available for reference symbol {reference}")

    # Filter others to only those with data
    others = [s for s in others if s in prices.columns]
    if not others:
        print("No comparable symbols with sufficient data.")
        return

    # Remove rows with any NaN entries
    prices = prices.dropna()

    if prices.empty or len(prices) < 2:
        raise ValueError("Insufficient data points for analysis.")

    # Compute daily returns
    returns = prices.pct_change().dropna()

    # Reference returns
    ref_ret = returns[reference]

    # Reference gains and vol
    gain_ref = (prices[reference].iloc[-1] / prices[reference].iloc[0] - 1) * 100
    vol_ref = returns[reference].std() * np.sqrt(252) * 100  # Annualized volatility

    results = []
    for sym in others:
        stock_ret = returns[sym]

        # Correlation
        corr = stock_ret.corr(ref_ret)

        # Linear regression for beta and R-squared
        slope, intercept, r_value, p_value, std_err = linregress(ref_ret, stock_ret)
        beta = slope
        r2 = r_value ** 2

        # Gains
        gain_stock = (prices[sym].iloc[-1] / prices[sym].iloc[0] - 1) * 100
        relative_gain = gain_stock - gain_ref

        # Annualized volatility
        vol_stock = stock_ret.std() * np.sqrt(252) * 100

        row = {
            'Symbol': sym,
            'Correlation': corr,
            'Beta': beta,
            'R-squared': r2,
            'Relative Gain (%)': relative_gain,
            'Annualized Vol (%)': vol_stock
        }
        if use_json:
            info = next(item for item in stock_data if item['Symbol'] == sym)
            row['Security'] = info['Security']
            row['GICS Sector'] = info['GICS Sector']

        results.append(row)

    # Create and display table using tabulate
    df = pd.DataFrame(results)
    if args.min_relative_gain is not None:
        df = df[df['Relative Gain (%)'] > args.min_relative_gain]
    if not df.empty:
        df = df.sort_values(by='Relative Gain (%)', ascending=False).reset_index(drop=True)
        print("Comparison Metrics:")
        table_str = tabulate(df.round(4), headers='keys', tablefmt='psql', showindex=False)
        print(table_str)

        # Send email if requested
        if args.send_email:
            if not args.email_to:
                raise ValueError("--email-to is required when --send-email is used.")
            if not args.settings_file:
                raise ValueError("--settings-file is required when --send-email is used.")
            with open(args.settings_file, 'r') as f:
                settings = json.load(f)
            email_settings = settings['Email']
            from_email = email_settings['from_email']
            from_password = email_settings['from_password']
            smtp_server = email_settings['smtp_server']
            smtp_port = email_settings['smtp_port']
            send_email(smtp_server, smtp_port, from_email, args.email_to, from_password, table_str)
    else:
        print("No results meet the minimum relative gain threshold.")

if __name__ == '__main__':
    main()