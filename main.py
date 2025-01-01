from datetime import datetime
import argparse
import pandas as pd
from utils.analysis import analysis_to_file, select_stocks_from_setup, backtest
from utils.email import send_html_email, csv_to_html
from utils.loadSettings import LoadFromFile
from utils.utils import get_report_hash, log_error, valid_date

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
                        help="Backtest mode evaluates the recommendations over specified period of time")
    parser.add_argument('-sd', '--bt_start_date', type=valid_date, help="The Start Date - format YYYY-MM-DD")
    parser.add_argument('-ed', '--bt_end_date', type=valid_date, help="The End Date - format YYYY-MM-DD")
    args = parser.parse_args()

    config = args.config
    setup = args.analysis
    ticker_list = args.input
    limit = args.limit

    current_datetime = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    current_date = datetime.now().strftime('%d/%m/%Y')
    report_hash = get_report_hash(f"{args.email}" + str(setup) + current_datetime + str(args.input)
                                  + str(args.backtest))
    report_name = f"reports/{report_hash}.csv"
    log_file = f"logs/{report_hash}.log"

    print(f"--------------------------------------------------------\n"
          f"Starting Report {report_hash}\n"
          f"--------------------------------------------------------\n")

    try:

        # Run Analysis
        analysis_data = select_stocks_from_setup(ticker_list, setup, limit, report_hash)
        # Save Analysis to Report File
        analysis_to_file(analysis_data, setup, report_hash)

        # Run Backtest if required
        if args.backtest:
            print("Starting backtest")

            backtest_result = backtest(analysis_data=analysis_data, start_date=args.bt_start_date,
                                       end_date=args.bt_end_date, setup=setup, report_hash=report_hash)

            # Save backtest results to file
            # TODO: Implement backest results to file

        # Send Email if requires
        if args.email:
            report_data = csv_to_html(report_name, position=analysis_settings['Position'])

            body = f"""<html> \
                   <head>
                    </head> 
                   <body><h2>Daily Stock Report</h2> 
                   <h3>Trend Analysis</h3>
                    {report_data}
                    </body></html>"""

            send_html_email(sender_email=config['Email']['from_email'], receiver_email=args.email,
                            subject=f"Stock Analysis {current_date}",
                            html_content=body,
                            smtp_server=config['Email']['smtp_server'],
                            smtp_port=config['Email']['smtp_port'],
                            password=config['Email']['from_password'])

            # TODO: Send backtest result to mail

        else:
            print("No results to send via email.")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
