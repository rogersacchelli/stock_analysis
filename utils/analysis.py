from utils.utils import log_error
from data_aquisition import fetch_yahoo_stock_data
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from trend import *


def select_stocks_from_setup(stock_list, setup, limit, report_hash):

    analysis_data = {}
    log_file = f"logs/{report_hash}.log"

    for ticker_code in stock_list:
        ticker = ticker_code['Code']
        print(f"Analyzing {ticker}...")

        try:
            stock_data = fetch_yahoo_stock_data(ticker, start_date=None, end_date=None, period=setup['Period'])
        except Exception as e:
            # Skip to next Ticket
            error_message = f"Error fetching data for {ticker} - {str(e)}"
            print(str(error_message))
            log_error(error_message, log_file)
            continue

        if setup['Trend']['sma_cross']['enabled']:
            try:
                crossings = detect_ma_crossings(stock_data=stock_data,
                                             short_window=setup['Trend']['sma_cross']['short'],
                                             long_window=setup['Trend']['sma_cross']['long'],
                                             output_window=setup['Trend']['sma_cross']['output_window'],
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

        if setup['Trend']['ema_cross']['enabled']:

            try:
                crossings = detect_ma_crossings(stock_data=stock_data,
                                             short_window=setup['Trend']['ema_cross']['short'],
                                             long_window=setup['Trend']['ema_cross']['long'],
                                             output_window=setup['Trend']['ema_cross']['output_window'],
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

        if setup['Trend']['bollinger_bands']['enabled']:
            # Detect Price touches on lower or upper band
            try:
                bands_touch = detect_bollinger_crossings(stock_data=stock_data,
                                                         period=setup['Trend']['bollinger_bands']['period'],
                                                         output_window=setup['Trend']['bollinger_bands'][
                                                             'output_window'],
                                                         average_type=setup['Trend']['bollinger_bands'][
                                                             'avg_type'],
                                                         std_dev=setup['Trend']['bollinger_bands'][
                                                             'std_dev'])

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

        if setup['Trend']['week_rule']['enabled']:
            try:
                data = stock_data
                wr_crossing = detect_wr_crossings(stock_data=data,
                                                  period=setup['Trend']['week_rule']['period'],
                                                  output_window=setup['Trend']['week_rule'][
                                                      'output_window'])

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

        if setup['Trend']['macd']['enabled']:
            try:
                macd_crossings = detect_macd_trend(stock_data,
                                                   short_window=setup['Trend']['macd']['short'],
                                                   long_window=setup['Trend']['macd']['long'],
                                                   signal_window=setup['Trend']['macd']['signal_window'],
                                                   output_window=setup['Trend']['macd']['output_window'],
                                                   lower_thold=setup['Trend']['macd']['lower_thold'],
                                                   upper_thold=setup['Trend']['macd']['upper_thold'])
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
        limit -= 1
        if limit == 0:
            break

        return analysis_data


def backtest(analysis_data, start_date, end_date, setup, report_hash):

    log_file = f"logs/{report_hash}.log"
    backtest_data = {}
    try:
        for ticker in analysis_data.keys():
            print(f"Backtesting {ticker}")

            if start_date is None:
                start_date = (datetime.now() - relativedelta(years=1)).strftime("%Y-%m-%d")
            if end_date is None or end_date == datetime.now().strftime("%Y-%m-%d"):
                end_date = (datetime.now() - relativedelta(days=1)).strftime("%Y-%m-%d")

            ticker_hist_data = fetch_yahoo_stock_data(ticker, start_date=start_date, end_date=end_date)

            for analysis in setup['Trend']:
                if setup['Trend'][analysis]['enabled']:
                    if analysis == 'sma_cross' or analysis == 'ema_cross':
                        # Get Crossing data
                        crossings = detect_ma_crossings(ticker_hist_data, short_window=setup['Trend'][analysis]['short'],
                                                     long_window=setup['Trend'][analysis]['short'],
                                                     average_type='EMA' if analysis == 'ema_cross' else 'SMA')
                        #
                    elif analysis == 'bollinger_bands':
                        pass
                    elif analysis == 'week-rule':
                        pass
                    elif analysis == 'macd':
                        pass

            # Evaluate through Analysis Options


    except Exception as e:
        error_message = f"Error handling backtest data - {str(e)}"
        print(error_message)
        log_error(error_message, log_file)

def analysis_to_file(analysis_data, setup, report_rash):
    # Iterate through dict printing analysis data

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Output file based on user settings
    with open(f"reports/{report_rash}.csv", mode='a') as f:

        header = "Ticker, Report Date"
        header_cfg = {}
        col = 0
        trend_total_weight = 0.0
        # Create Header based on analysis settings
        for trend in setup['Trend'].keys():
            if trend == "sma_cross" or trend == "ema_cross":
                header = f"{header},{trend.upper()} {setup['Trend'][trend]['short']}/" \
                         f"{setup['Trend'][trend]['long']}"

            elif trend == "bollinger_bands" or trend == "week_rule":
                header = f"{header},{setup['Trend'][trend]['period']} {trend.upper()}"

            elif trend == "macd":
                header = f"{header},{setup['Trend'][trend]['signal_window']} {trend.upper()}"
            trend_total_weight += setup['Trend'][trend]['weight']
            header_cfg.update({trend: col})
            col += 1

        f.write(header + '\n')

        # Add data per ticker
        for ticker in analysis_data.keys():

            analysis_output = f"{ticker},{current_date}"
            ticker_score = 0.0

            for analysis in setup['Trend'].keys():
                try:
                    recommendation = analysis_data[ticker][analysis]['recommendation']
                    analysis_output += f",{recommendation}"
                    if recommendation == 'Buy':
                        ticker_score += setup['Trend'][analysis]['weight']
                    else:
                        ticker_score -= setup['Trend'][analysis]['weight']

                except KeyError as ke:
                    error_message = f"No {str(ke)} analysis found for {ticker}"
                    print(error_message)
                    log_error(error_message, f"logs/{report_rash}.log")
                    analysis_output += ","

            ticker_final_score = ticker_score / trend_total_weight
            if (ticker_final_score >= setup['Thresholds']['Trend']['Buy'] or
                    ticker_final_score <= setup['Thresholds']['Trend']['Sell']):
                f.write(analysis_output + '\n')
            else:
                print(
                    f"{ticker} not included since its score {ticker_final_score} does not meet threshold settings.")

        f.close()
