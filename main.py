import yfinance as yf
from datetime import datetime, timedelta
import os
import argparse
import pandas as pd
from trend import detect_crossings
from utils.analysis import analysis_to_file
from utils.email import send_html_email, csv_to_html
from utils.loadSettings import LoadFromFile
from utils.utils import get_report_hash

pd.options.mode.chained_assignment = None


# Function to fetch stock data
def fetch_stock_data(ticker, period="1y"):
    """Fetch historical stock data for the given ticker."""
    stock_data = yf.download(ticker, period=period, multi_level_index=False)

    if stock_data.empty:
        raise ValueError(f"No data available for ticker {ticker}.")
    return stock_data


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
    parser.add_argument('-i', '--input', required=True, action=LoadFromFile,
                        help="Input file containing stock tickers in JSON format.")
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
        report_hash = get_report_hash(f"{args.email}" + str(analysis_settings) + current_datetime + str(args.input))
        report_name = f"reports/{report_hash}.csv"
        log_file = f"logs/{report_hash}.log"
        analysis_data = {}

        for ticker_code in ticker_list:
            ticker = ticker_code['Code']
            print(f"Analyzing {ticker}...")

            try:
                stock_data = fetch_stock_data(ticker, period=analysis_settings['Period'])
            except Exception as e:
                # Skip to next Ticket
                print(str(e))
                log_error(str(e), log_file)
                continue

            if analysis_settings['Trend']['sma_cross']['enabled']:
                try:
                    crossings = detect_crossings(stock_data,
                                                 short_window=analysis_settings['Trend']['sma_cross']['short'],
                                                 long_window=analysis_settings['Trend']['sma_cross']['long'],
                                                 eval_window=analysis_settings['Trend']['sma_cross']['eval_window'],
                                                 average_type="SMA")
                    if not crossings.empty:
                        print(f"Crossings found for {ticker}. Saving to analysis file.")
                        crossings.index = [ticker] * len(crossings)
                        try:
                            analysis_data[ticker]
                        except:
                            analysis_data.update({ticker: {}})

                        analysis_data[ticker].update({'sma_cross': {"date": crossings['Date'].values[0],
                                                                    "cross": crossings["Cross"].values[0]}})
                    else:
                        print(f"No SMA crossings detected for {ticker}.")
                except Exception as e:
                    error_message = f"Error analyzing {ticker}: {e}"
                    print(error_message)
                    log_error(error_message, log_file)

            if analysis_settings['Trend']['ema_cross']['enabled']:

                try:
                    crossings = detect_crossings(stock_data,
                                                 short_window=analysis_settings['Trend']['ema_cross']['short'],
                                                 long_window=analysis_settings['Trend']['ema_cross']['long'],
                                                 eval_window=analysis_settings['Trend']['ema_cross']['eval_window'],
                                                 average_type="EMA")
                    if not crossings.empty:
                        print(f"Crossings found for {ticker}. Saving to analysis file.")
                        crossings.index = [ticker] * len(crossings)
                        analysis_data[ticker].update({'ema_cross': {"date": crossings['Date'].values[0],
                                                                    "cross": crossings["Cross"].values[0]}})
                    else:
                        print(f"No EMA crossings detected for {ticker}.")
                except Exception as e:
                    error_message = f"Error analyzing {ticker}: {e}"
                    print(error_message)
                    log_error(error_message, log_file)

        # Create Report File
        analysis_to_file(analysis_data, analysis_settings, report_name)

        # Send Email
        if args.email:
            report_data = csv_to_html(report_name, position=analysis_settings['Position'])

            body = f"""<html> \
                   <head>
                    </head> 
                   <body><h2>Daily Stock Report</h2> 
                   <h3>Trend Analysis</h3>
                    {report_data}
                    </body></html>"""

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
