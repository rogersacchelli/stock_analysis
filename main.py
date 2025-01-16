import argparse
import pandas as pd
from utils.analysis import *
from utils.mail import mail_analysis
from utils.utils import get_hash, create_directories_if_not_exist, position_results_to_file, \
    analysis_to_file, get_stock_selection_dates, valid_end_date, LoadFromFile, valid_start_date, valid_date

pd.options.mode.chained_assignment = None


def main():

    logging.basicConfig(filename='logs/error.log', level=logging.ERROR,
                        format='%(asctime)s:%(levelname)s:%(funcName)s:%(message)s')

    parser = argparse.ArgumentParser(description="Analyze stock crossings of moving averages.")
    parser.add_argument('-i', '--input', required=True, action=LoadFromFile,
                        help="Input file containing stock tickers in JSON format.")
    parser.add_argument('-e', '--email', help="Email address to send results.")
    parser.add_argument('-es','--subject',default="Report Analysis", help="Email subject to send results.")
    parser.add_argument('-c', '--config', required=True, action=LoadFromFile, help="Configuration File.")
    parser.add_argument('-s', '--setup', required=True, action=LoadFromFile, help="Setup definition File.")
    parser.add_argument('-l', '--limit', type=int, default=500, help="Limit the number of stocks processed.")
    parser.add_argument('-b', '--backtest', action="store_true",
                        help="Backtest mode provides recommended stocks prior to start date and assess the "
                             "recommendation over specified the specified period. If no dates are specified, "
                             "default period starts as 1y ago until now.")
    parser.add_argument('-sd', '--bt_start_date',type=valid_date, default=datetime.today()-relativedelta(years=1),
                        help="The start date which is intended to assess the recommended stocks - format YYYY-MM-DD")
    parser.add_argument('-ed', '--bt_end_date', type=valid_date, default=datetime.today(),
                        help="The end date of evaluation - format YYYY-MM-DD")
    args = parser.parse_args()

    config = args.config
    setup = args.setup
    ticker_list = args.input
    limit = args.limit

    # Create required dirs if not exist
    create_directories_if_not_exist("reports")
    create_directories_if_not_exist("logs")
    create_directories_if_not_exist("ticker_data")

    current_datetime = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    report_hash = get_hash(f"{args.email}" + str(setup) + current_datetime + str(args.input)
                           + str(args.backtest))

    print(f"--------------------------------------------------------\n"
          f"Starting Report {report_hash}\n"
          f"--------------------------------------------------------\n")

    # Get Start and End Date for stocks selection
    analysis_start_date, analysis_end_date = get_stock_selection_dates(args.bt_start_date, setup=setup,
                                                     backtest=args.backtest)

    # Get recommended stocks according to setup file
    analysis_data = select_stocks_from_setup(ticker_list, setup, limit, report_hash,
                                             start_date=analysis_start_date, end_date=analysis_end_date)

    if args.backtest:
        try:

            # ----------------------- Backtest -----------------------
            backtest_start_date = args.bt_start_date
            backtest_end_date = args.bt_end_date + relativedelta(hours=23) # include trading info of the day

            # Run backtest
            backtest_result = backtest(analysis_data=analysis_data, start_date=backtest_start_date,
                                       end_date=backtest_end_date, setup=setup)

            # Save backtest to report file
            backtest_to_file(analysis_data=analysis_data, backtest_data=backtest_result, setup=setup,
                             report_hash=report_hash)

        except ValueError as ve:
            logging.error(str(ve))
            print(f"Backtest failed - {str(ve)}")

        print("Backtest Completed")

    else:
        position_results = get_position_results(setup)
        position_results_to_file(position_results, setup, report_hash)

    # Save Analysis to Report File
    analysis_to_file(analysis_data, setup, report_hash)

    # Send Email if required and not backtest
    if args.email and not args.backtest:

        mail_analysis(report_hash, setup, config, args.email, subject=args.subject)

    else:
        print("No results to send via email.")


if __name__ == "__main__":
    main()
