import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import argparse
from tabulate import tabulate
import os


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
        return data

    print(f"Downloading data for {symbol}...")
    data = yf.download(symbol, start=start, end=end, interval=interval)
    data = data.dropna()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    data.to_pickle(filepath)
    print(f"Saved data to {filepath}")
    return data


def run_simulation(symbol, data, buy_indices, max_bars, tp_pct, sl_pct):
    """
    Run simulations for a single strategy on a symbol.
    """
    gains = []
    sl_count = 0
    tp_count = 0
    expired_count = 0
    total_len = len(data)

    for buy_idx in buy_indices:
        buy_price = data['Close'].iloc[buy_idx]
        stop_price = buy_price * (1 - sl_pct / 100)
        tp_price = buy_price * (1 + tp_pct / 100)

        closed = False
        for i in range(1, max_bars + 1):
            sim_idx = buy_idx + i
            if sim_idx >= total_len:
                break
            high = data['High'].iloc[sim_idx]
            low = data['Low'].iloc[sim_idx]

            if high >= tp_price:
                gain = tp_pct
                closed = True
                tp_count += 1
                break
            if low <= stop_price:
                gain = (stop_price - buy_price) / buy_price * 100
                closed = True
                sl_count += 1
                break

        if not closed:
            close_idx = min(buy_idx + max_bars, total_len - 1)
            close_price = data['Close'].iloc[close_idx]
            gain = (close_price - buy_price) / buy_price * 100
            expired_count += 1

        gains.append(gain)

    return gains, sl_count, tp_count, expired_count


def main():
    parser = argparse.ArgumentParser(description='Assess stop loss strategies performance.')
    parser.add_argument('--symbols', nargs='+', default=['AAPL'], help='List of symbols (default: AAPL)')
    parser.add_argument('--start', type=str, default=None, help='Start date YYYY-MM-DD')
    parser.add_argument('--end', type=str, default=None, help='End date YYYY-MM-DD')
    parser.add_argument('--interval', type=str, default='1d', help='Data interval (default: 1d)')
    parser.add_argument('--n', type=int, default=100, help='Number of random buy dates/simulations (default: 100)')
    parser.add_argument('--max_bars', type=int, default=30, help='Maximum bars to hold (default: 30)')
    parser.add_argument('--risk_reward_ratios', nargs='+', type=float, default=[2.0],
                        help='Risk/reward ratios (default: 2.0)')
    parser.add_argument('--stop_losses', nargs='+', type=float, default=[5.0, 10.0, 15.0],
                        help='Stop loss percentages (default: 5 10 15)')
    parser.add_argument('--ema_period', type=int, default=20, help='EMA period (default: 20)')
    parser.add_argument('--slope_period', type=int, default=3, help='Slope period (default: 3)')
    parser.add_argument('--slope_threshold', type=float, default=0.0, help='Minimum EMA slope threshold (default: 0.0)')
    parser.add_argument('--export_csv', action='store_true', default=False,
                        help='Export results to CSV (default: False)')

    args = parser.parse_args()

    if args.start is None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        args.start = start_date.strftime('%Y-%m-%d')
    if args.end is None:
        args.end = datetime.now().strftime('%Y-%m-%d')

    results = []

    for symbol in args.symbols:
        data = download_data(symbol, args.start, args.end, args.interval)

        if len(data) == 0:
            print(f"No data for {symbol}")
            continue

        total_len = len(data)
        if total_len <= args.max_bars:
            print(f"Not enough data for {symbol}")
            continue

        # Compute EMA and slope
        data['EMA'] = data['Close'].ewm(span=args.ema_period).mean()
        data['EMA_slope'] = data['EMA'].diff(periods=args.slope_period)

        # Possible buy indices: enough history for EMA and slope, slope > threshold, enough room after
        min_start_idx = args.slope_period
        possible_buy_indices = [i for i in range(min_start_idx, total_len - args.max_bars)
                                if data['EMA_slope'].iloc[i] > args.slope_threshold]

        num_possible = len(possible_buy_indices)
        if num_possible == 0:
            print(f"No possible buy dates for {symbol} with EMA slope > {args.slope_threshold}")
            continue

        actual_n = min(args.n, num_possible)
        buy_indices = random.sample(possible_buy_indices, actual_n)

        print(f"Running simulations for {symbol} with {actual_n} filtered buy dates...")

        for rr in args.risk_reward_ratios:
            for sl_pct in args.stop_losses:
                tp_pct = sl_pct * rr
                gains, sl_count, tp_count, expired_count = run_simulation(symbol, data, buy_indices, args.max_bars,
                                                                          tp_pct, sl_pct)
                avg_gain = np.mean(gains)
                std_gain = np.std(gains)
                win_rate = (tp_count / (sl_count + tp_count) * 100) if (sl_count + tp_count) > 0 else 0
                margin_pct = round((win_rate / 100 - 1 / rr) * 100, 2)
                results.append({
                    'Symbol': symbol,
                    'SL %': round(sl_pct, 2),
                    'TP %': round(tp_pct, 2),
                    'RR': f"{rr}:1",
                    'Avg Gain %': round(avg_gain, 2),
                    'Std Dev %': round(std_gain, 2),
                    'Num Sims': actual_n,
                    'Num SL': sl_count,
                    'Num TP': tp_count,
                    'Num Expired': expired_count,
                    'Win Rate %': round(win_rate, 2),
                    'Margin %': margin_pct
                })

    if results:
        df = pd.DataFrame(results)
        print("\nResults:")
        print(tabulate(df, headers='keys', tablefmt='grid', floatfmt='.2f'))
        if args.export_csv:
            csv_filename = "simulation_results.csv"
            df.to_csv(csv_filename, index=False)
            print(f"Exported results to {csv_filename}")
    else:
        print("No results to display.")


if __name__ == "__main__":
    main()