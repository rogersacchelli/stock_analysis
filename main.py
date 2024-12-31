import yfinance as yf
from datetime import datetime
import argparse
import pandas as pd
from trend import detect_crossings, detect_bollinger_crossings, detect_wr_crossings, detect_macd_trend
from utils.analysis import analysis_to_file
from utils.email import send_html_email, csv_to_html
from utils.loadSettings import LoadFromFile
from utils.utils import get_report_hash, log_error

pd.options.mode.chained_assignment = None


# Function to fetch stock data
def fetch_stock_data(ticker, period="1y"):
    """Fetch historical stock data for the given ticker."""
    stock_data = yf.download(ticker, period=period, multi_level_index=False)

    if stock_data.empty:
        raise ValueError(f"No data available for ticker {ticker}.")
    return stock_data


# Function to read tickers from a file

def main():
    parser = argparse.ArgumentParser(description="Analyze stock crossings of moving averages.")
    parser.add_argument('-i', '--input', required=True, action=LoadFromFile,
                        help="Input file containing stock tickers in JSON format.")
    parser.add_argument('-e', '--email', help="Email address to send results.")
    parser.add_argument('-c', '--config', required=True, action=LoadFromFile, help="Configuration File.")
    parser.add_argument('-a', '--analysis', required=True, action=LoadFromFile, help="Analysis Definition File.")
    parser.add_argument('-l', '--limit', type=int, default=50, help="Limit the number of stocks processed.")
    args = parser.parse_args()

    settings = args.config
    analysis_settings = args.analysis

    try:
        ticker_list = args.input

        current_datetime = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        current_date = datetime.now().strftime('%d/%m/%Y')
        report_hash = get_report_hash(f"{args.email}" + str(analysis_settings) + current_datetime + str(args.input))
        report_name = f"reports/{report_hash}.csv"
        log_file = f"logs/{report_hash}.log"
        analysis_data = {}

        print(f"--------------------------------------------------------\n"
              f"Starting Report {report_hash}\n"
              f"--------------------------------------------------------\n")

        for ticker_code in ticker_list:
            ticker = ticker_code['Code']
            print(f"Analyzing {ticker}...")

            try:
                stock_data = fetch_stock_data(ticker, period=analysis_settings['Period'])
            except Exception as e:
                # Skip to next Ticket
                error_message = f"Error fetching data for {ticker} - {str(e)}"
                print(str(error_message))
                log_error(error_message, log_file)
                continue

            if analysis_settings['Trend']['sma_cross']['enabled']:
                try:
                    crossings = detect_crossings(stock_data=stock_data,
                                                 short_window=analysis_settings['Trend']['sma_cross']['short'],
                                                 long_window=analysis_settings['Trend']['sma_cross']['long'],
                                                 output_window=analysis_settings['Trend']['sma_cross']['output_window'],
                                                 average_type="SMA")
                    if not crossings.empty:
                        print(f"Crossings found for {ticker}. Saving to analysis file.")
                        crossings.index = [ticker] * len(crossings)
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})

                        analysis_data[ticker].update({'sma_cross': {"date": crossings['Date'].values[0],
                                                                    "recommendation": crossings["Cross"].values[0]}})
                    else:
                        print(f"No SMA crossings detected for {ticker}.")
                except Exception as e:
                    error_message = f"Error analyzing {ticker}: {e}"
                    print(error_message)
                    log_error(error_message, log_file)

            if analysis_settings['Trend']['ema_cross']['enabled']:

                try:
                    crossings = detect_crossings(stock_data=stock_data,
                                                 short_window=analysis_settings['Trend']['ema_cross']['short'],
                                                 long_window=analysis_settings['Trend']['ema_cross']['long'],
                                                 output_window=analysis_settings['Trend']['ema_cross']['output_window'],
                                                 average_type="EMA")
                    if not crossings.empty:
                        print(f"Crossings found for {ticker}. Saving to analysis file.")
                        crossings.index = [ticker] * len(crossings)
                        analysis_data[ticker].update({'ema_cross': {"date": crossings['Date'].values[0],
                                                                    "recommendation": crossings["Cross"].values[0]}})
                    else:
                        print(f"No EMA crossings detected for {ticker}.")
                except Exception as e:
                    error_message = f"Error analyzing {ticker}: {e}"
                    print(error_message)
                    log_error(error_message, log_file)

            if analysis_settings['Trend']['bollinger_bands']['enabled']:
                # Detect Price touches on lower or upper band
                try:
                    bands_touch = detect_bollinger_crossings(stock_data=stock_data,
                                        period=analysis_settings['Trend']['bollinger_bands']['period'],
                                        output_window=analysis_settings['Trend']['bollinger_bands']['output_window'],
                                        average_type=analysis_settings['Trend']['bollinger_bands']['avg_type'],
                                        std_dev=analysis_settings['Trend']['bollinger_bands']['std_dev'])

                    if not bands_touch['LowerTouch'].empty:
                        # Buy Opportunity
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})
                        analysis_data[ticker].update({"bollinger_bands": {"recommendation": "Buy"}})
                    elif not bands_touch['UpperTouch'].empty:
                        # Sell Opportunity
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})
                        analysis_data[ticker].update({"bollinger_bands": {"recommendation": "Sell"}})
                    else:
                        print(f"No bands crossing detected for {ticker}")
                except Exception as e:
                    print(str(e))
                    log_error(str(e), log_file)

            if analysis_settings['Trend']['week_rule']['enabled']:
                try:
                    data = stock_data
                    wr_crossing = detect_wr_crossings(stock_data=data,
                                    period=analysis_settings['Trend']['week_rule']['period'],
                                    output_window=analysis_settings['Trend']['week_rule']['output_window'])

                    if not wr_crossing['Buy'].empty:
                        # Buy Opportunity
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})
                        analysis_data[ticker].update({"week_rule": {"recommendation": "Buy"}})

                    elif not wr_crossing['Sell'].empty:
                        # Sell Opportunity
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})
                        analysis_data[ticker].update({"week_rule": {"recommendation": "Sell"}})
                    else:
                        print(f"No WR crossing detected for {ticker}")

                except Exception as e:
                    error_message = f"{str(e)} handling Week Rule for "
                    print(error_message)
                    log_error(error_message, log_file)

            if analysis_settings['Trend']['macd']['enabled']:
                try:
                    macd_crossings = detect_macd_trend(stock_data,
                                                   short_window=analysis_settings['Trend']['macd']['short'],
                                                   long_window=analysis_settings['Trend']['macd']['long'],
                                                   signal_window=analysis_settings['Trend']['macd']['signal_window'],
                                                   output_window=analysis_settings['Trend']['macd']['output_window'],
                                                   lower_thold=analysis_settings['Trend']['macd']['lower_thold'],
                                                   upper_thold=analysis_settings['Trend']['macd']['upper_thold'])
                    if not macd_crossings['Buy'].empty:
                        # Buy Opportunity
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})
                        analysis_data[ticker].update({"macd": {"recommendation": "Buy"}})

                    elif not wr_crossing['Sell'].empty:
                        # Sell Opportunity
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})
                        analysis_data[ticker].update({"macd": {"recommendation": "Sell"}})
                    else:
                        print(f"No MACD crossing detected for {ticker}")

                except Exception as e:
                    error_message = f"Error {e}, handling MACD analysis for {ticker}"
                    print(error_message)
                    log_error(error_message, log_file)

            # Break loop if limit is exceeded
            args.limit -= 1
            if args.limit == 0:
                break

        # Create Report File
        analysis_to_file(analysis_data, analysis_settings, report_hash)

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
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
