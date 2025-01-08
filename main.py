import argparse
import pandas as pd
from utils.analysis import *
from utils.email import send_html_email, csv_to_html
from utils.loadSettings import LoadFromFile
from utils.utils import get_hash, valid_date, create_directories_if_not_exist, log_error, position_results_to_file, \
    analysis_to_file

pd.options.mode.chained_assignment = None


# Function to read tickers from a file

def main():
    parser = argparse.ArgumentParser(description="Analyze stock crossings of moving averages.")
    parser.add_argument('-i', '--input', required=True, action=LoadFromFile,
                        help="Input file containing stock tickers in JSON format.")
    parser.add_argument('-e', '--email', help="Email address to send results.")
    parser.add_argument('-c', '--config', required=True, action=LoadFromFile, help="Configuration File.")
    parser.add_argument('-a', '--analysis', required=True, action=LoadFromFile, help="Analysis Definition File.")
    parser.add_argument('-l', '--limit', type=int, default=50, help="Limit the number of stocks processed.")
    parser.add_argument('-b', '--backtest', action="store_true",
                        help="Backtest mode provides recommended stocks prior to start date and assess the "
                             "recommendation over specified the specified period. If no dates are specified, "
                             "default period starts as 1y ago until now.")
    parser.add_argument('-sd', '--bt_start_date', type=valid_date, help="The start date which is intended to assess "
                                                                        "the recommended stocks - format YYYY-MM-DD")
    parser.add_argument('-ed', '--bt_end_date', type=valid_date, help="The end date of evaluation - format YYYY-MM-DD")
    args = parser.parse_args()

    config = args.config
    setup = args.analysis
    ticker_list = args.input
    limit = args.limit

    # Create required dirs if not exist

    # Example usage
    create_directories_if_not_exist("reports")
    create_directories_if_not_exist("logs")
    create_directories_if_not_exist("ticker_data")

    current_datetime = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    current_date = datetime.now().strftime('%d/%m/%Y')
    report_hash = get_hash(f"{args.email}" + str(setup) + current_datetime + str(args.input)
                           + str(args.backtest))
    report_name = f"reports/{report_hash}.csv"
    log_file = f"logs/{report_hash}.log"

    print(f"--------------------------------------------------------\n"
          f"Starting Report {report_hash}\n"
          f"--------------------------------------------------------\n")

    try:

        # Run Analysis
        analysis_data = {}

        if args.backtest:
            # If required backtest and no dates provided, default to last one year
            if args.bt_start_date is None:
                args.bt_start_date = (datetime.now() - relativedelta(years=1))
            if args.bt_end_date is None or args.bt_end_date == datetime.today():
                args.bt_end_date = (datetime.now() - relativedelta(days=1))

            # Determining the stocks for the backtest analysis requires setting the end-date as the start-date
            # Start date is the end-date minus the period required of assessment, defined on the setup period.
            recommendation_period = get_recommendation_period(args.bt_start_date, setup['Period'])

            # Get recommended stocks according to setup file
            analysis_data = select_stocks_from_setup(ticker_list, setup, limit, report_hash,
                                                     start_date=recommendation_period[0],
                                                     end_date=recommendation_period[1])

            # ----------------------- Backtest -----------------------

            backtest_start_date = get_backtest_start(start_date=args.bt_start_date, setup=setup)

            backtest_result = backtest(analysis_data=analysis_data,
                                       start_date=backtest_start_date,
                                       end_date=args.bt_end_date,
                                       setup=setup,
                                       report_hash=report_hash)

            # Save backtest to report
            backtest_to_file(analysis_data=analysis_data, backtest_data=backtest_result, setup=setup,
                             report_hash=report_hash)

        else:

            analysis_data = select_stocks_from_setup(ticker_list, setup, limit, report_hash)
            position_results = get_position_results(setup)
            position_results_to_file(position_results, setup, report_hash)

        # Save Analysis to Report File
        analysis_to_file(analysis_data, setup, report_hash)

        # Send Email if required and not backtest
        if args.email and not args.backtest:

            report_data = csv_to_html(report_name, position=list(setup['Position'].keys()))
            position_data = csv_to_html(f"reports/{report_hash}-position.csv", position=[])

            body = f"""<html> \
                   <head>
                    </head> 
                   <body><h2>Daily Stock Report</h2> 
                   <h3>Trend Analysis</h3>
                    {report_data}
                    <h3>Position Results</h3>
                    {position_data}
                    <p>** Lower or equal to stop margin</p>
                    </body></html>"""

            send_html_email(sender_email=config['Email']['from_email'], receiver_email=args.email,
                            subject=f"Stock Analysis {current_date}",
                            html_content=body,
                            smtp_server=config['Email']['smtp_server'],
                            smtp_port=config['Email']['smtp_port'],
                            password=config['Email']['from_password'])

        else:
            print("No results to send via email.")
    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(error_message)
        log_error(error_message, log_file)


if __name__ == "__main__":
    main()
