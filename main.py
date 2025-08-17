import pandas as pd
from features_extraction import save_features_to_file
from portfolio_manager import portfolio_manager, calculate_trade_metrics, calculate_ticker_gain
from risk import get_stock_from_rm
from utils.analysis import *
from utils.argument_parsing import argument_parsing
from utils.mail import mail_analysis
from utils.utils import get_hash, create_directories_if_not_exist
from tabulate import tabulate

pd.options.mode.chained_assignment = None


def main():

    args = argument_parsing()

    config = args.config
    position = args.position
    features = args.features
    backtest = args.backtest
    setup = args.setup
    ticker_list = args.input
    limit = args.limit

    # Create required dirs if not exist
    create_directories_if_not_exist("reports")
    create_directories_if_not_exist("logs")
    create_directories_if_not_exist("ticker_data")
    create_directories_if_not_exist("models")

    current_datetime = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    report_hash = get_hash(f"{args.email}" + str(setup) + current_datetime + str(args.input) + str(args.backtest))

    print(f"--------------------------------------------------------\n"
          f"Starting Report {report_hash}\n"
          f"--------------------------------------------------------\n")

    # Get recommended stocks according to setup file
    signal_data = get_stock_signals(ticker_list, setup, limit,
                                    start_date=args.start_date,
                                    end_date=args.end_date)

    # Add Risk Management
    signal_data_filtered = get_stock_from_rm(signal_data, setup)

    # ----------- Backtest ------------ #

    if backtest:

        # Add Signal Data to Position Manager
        trades = portfolio_manager(signal_data_filtered, setup)
        benchmark_index = calculate_ticker_gain('^SPX', args.start_date, args.end_date)
        metrics = calculate_trade_metrics(trades, benchmark_index, setup)

        # Prepare data for tabulate
        headers = list(metrics.keys())
        row = [list(metrics.values())]  # Wrap values in a list for single-row table

        # Print table
        print(tabulate(row, headers=headers, tablefmt="grid", floatfmt=".2f"))


if __name__ == "__main__":
    main()
