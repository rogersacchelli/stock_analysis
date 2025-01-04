from utils.utils import log_error
from data_aquisition import fetch_yahoo_stock_data
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from trend import *


def select_stocks_from_setup(stock_list, setup, limit, report_hash, start_date, end_date):

    analysis_data = {}
    log_file = f"logs/{report_hash}.log"

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    for ticker_code in stock_list:
        ticker = ticker_code['Code']
        print(f"Analyzing {ticker}...")

        ticker_score = 0.0
        total_score = 0.0

        try:
            stock_data = fetch_yahoo_stock_data(ticker, start_date=start_date, end_date=end_date,
                                                period=setup['Period'])
        except Exception as e:
            # Skip to next Ticket
            error_message = f"Error fetching data for {ticker} - {str(e)}"
            print(str(error_message))
            log_error(error_message, log_file)
            continue

        ##################################
        # Trend analysis
        ##################################
        for analysis in setup['Trend'].keys():

            if setup['Trend'][analysis]['enabled']:
                try:
                    if analysis == "sma_cross" or analysis == "ema_cross":
                        crossings = detect_ma_crossings(stock_data=stock_data,
                                                     short_window=setup['Trend']['sma_cross']['short'],
                                                     long_window=setup['Trend']['sma_cross']['long'],
                                                     output_window=setup['Trend']['sma_cross']['output_window'],
                                                     end_date=end_date,
                                                     average_type="SMA" if analysis == 'sma_cross' else "EMA")
                    elif analysis == "bollinger_bands":
                        crossings = detect_bollinger_crossings(stock_data=stock_data,
                                         period=setup['Trend'][analysis]['period'], 
                                         output_window=setup['Trend'][analysis]['output_window'],
                                         average_type=setup['Trend'][analysis]['avg_type'], end_date=end_date,
                                         std_dev=setup['Trend'][analysis]['std_dev'])
                        
                    elif analysis == "wr_rule":
                        crossings = detect_wr_crossings(stock_data=stock_data,
                                                       period=setup['Trend']['week_rule']['period'], end_date=end_date,
                                                       output_window=setup['Trend']['week_rule']['output_window'])
                    elif analysis == "macd":
                        crossings = detect_macd_trend(stock_data,
                                                           short_window=setup['Trend'][analysis]['short'],
                                                           long_window=setup['Trend'][analysis]['long'],
                                                           signal_window=setup['Trend'][analysis]['signal_window'],
                                                           output_window=setup['Trend'][analysis]['output_window'],
                                                           end_date=end_date)

                    # Add analysis to be computed on total result
                    total_score += setup['Trend'][analysis]['weight']

                    if not crossings.empty:
                        print(f"Crossings found for {ticker} using {analysis}. Saving analysis file.")
                        crossings.index = [ticker] * len(crossings)
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})
    
                        analysis_data[ticker].update({analysis: crossings})
                        if crossings['Cross'].values[0] == "Sell":
                            ticker_score += setup['Trend'][analysis]['weight']
                        else:
                            ticker_score += setup['Trend'][analysis]['weight']

                    else:
                        print(f"No {analysis} crossings detected for {ticker}.")
                except Exception as e:
                    error_message = f"Error analyzing {ticker}: {e}"
                    print(error_message)
                    log_error(error_message, log_file)

        # Keep Analysis if higher then thresholds
        if total_score > 0.0:
            final_score = ticker_score / total_score
            if final_score >= setup['Thresholds']['Trend']['Buy'] or \
                    final_score <= setup['Thresholds']['Trend']['Sell']:
                analysis_data[ticker].update({"score": ticker_score / total_score})
            else:
                analysis_data.pop(ticker, None)

        # Break loop if limit is exceeded
        limit -= 1
        if limit == 0:
            break

    return analysis_data


def backtest(analysis_data, start_date, end_date, setup, report_hash):

    log_file = f"logs/{report_hash}.log"
    backtest_data = {}
    backtest_data = defaultdict(lambda: defaultdict(dict), backtest_data)

    try:
        for ticker in analysis_data.keys():
            print(f"Backtesting {ticker}")

            ticker_hist_data = fetch_yahoo_stock_data(ticker, start_date=start_date, end_date=end_date)
            total_backtest_score = 0.0

            ###################################
            # Trend Analysis
            ###################################
            for analysis in setup['Trend']:
                if setup['Trend'][analysis]['enabled']:

                    total_backtest_score += setup['Trend'][analysis]['weight']

                    if analysis == 'sma_cross' or analysis == 'ema_cross':
                        # Get Crossing data
                        ma_crossings = detect_ma_crossings(ticker_hist_data,
                                                        short_window=setup['Trend'][analysis]['short'],
                                                        long_window=setup['Trend'][analysis]['long'],
                                                        output_window=0,
                                                        end_date=end_date,
                                                        average_type='EMA' if analysis == 'ema_cross' else 'SMA')
                        try:
                            backtest_data[ticker]
                        except KeyError:
                            backtest_data.update({ticker: {}})

                        backtest_data[ticker].update({analysis: ma_crossings})

                    elif analysis == 'bollinger_bands':
                        bb_crossings = detect_bollinger_crossings(stock_data=ticker_hist_data,
                                                         period=setup['Trend'][analysis]['period'],
                                                         output_window=0,
                                                         average_type=setup['Trend'][analysis]['avg_type'],
                                                         end_date=end_date,
                                                         std_dev=setup['Trend'][analysis]['std_dev'])
                        try:
                            backtest_data[ticker]
                        except KeyError:
                            backtest_data.update({ticker: {}})
                        backtest_data[ticker].update({analysis: bb_crossings})

                    elif analysis == 'week-rule':

                        rw_crossings = detect_wr_crossings(stock_data=ticker_hist_data,
                                                  period=setup['Trend'][analysis]['period'],
                                                  end_date=end_date,
                                                  output_window=0)
                        try:
                            backtest_data[ticker]
                        except KeyError:
                            backtest_data.update({ticker: {}})
                        backtest_data[ticker].update({analysis: rw_crossings})

                    elif analysis == 'macd':
                        macd_crossings = detect_macd_trend(ticker_hist_data,
                                          short_window=setup['Trend'][analysis]['short'],
                                          long_window=setup['Trend'][analysis]['long'],
                                          signal_window=setup['Trend'][analysis]['signal_window'],
                                          output_window=0,
                                          end_date=end_date,
                                          lower_thold=setup['Trend'][analysis]['lower_thold'],
                                          upper_thold=setup['Trend'][analysis]['upper_thold'])
                        try:
                            backtest_data[ticker]
                        except KeyError:
                            backtest_data.update({ticker: {}})
                        backtest_data[ticker].update({analysis: macd_crossings})

            # Search for events along the crossings
            analysis_day = datetime.strptime(start_date, "%Y-%m-%d")
            recommendation = 'Buy' if analysis_data[ticker]['score'] < 0.0 else 'Sell'

            while analysis_day <= datetime.strptime(end_date, "%Y-%m-%d"):

                backtest_score = 0.0
                updates = {}

                for ticker_analysis in backtest_data[ticker].keys():
                    if ticker_analysis == 'results':
                        break
                    analysis_limit = analysis_day + relativedelta(days=setup['Trend'][ticker_analysis]['output_window'])
                    analysis_crossings = backtest_data[ticker][ticker_analysis]
                    analysis_crossings = analysis_crossings[(analysis_crossings['Cross'] == recommendation) &
                                                            (analysis_crossings['Date'] >= analysis_day) &
                                                            (analysis_crossings['Date'] <= analysis_limit)]
                    if not analysis_crossings.empty:
                        if recommendation == 'Buy':
                            backtest_score += setup['Trend'][ticker_analysis]['weight']
                        else:
                            backtest_score -= setup['Trend'][ticker_analysis]['weight']

                        updates.update({ticker_analysis: analysis_crossings})

                backtest_data[ticker]['results'][analysis_day] = updates

                final_score = backtest_score / total_backtest_score

                if final_score >= setup['Thresholds']['Trend']['Buy']:
                    backtest_data[ticker]['results'][analysis_day].update({'score': final_score})
                    break
                elif final_score <= setup['Thresholds']['Trend']['Sell']:
                    backtest_data[ticker]['results'][analysis_day].update({'score': final_score})
                    break
                else:
                    backtest_data[ticker]['results'].pop(analysis_day)

                analysis_day = analysis_day + relativedelta(days=1)

        return backtest_data

    except Exception as e:
        error_message = f"Error handling backtest data - {str(e)}"
        print(error_message)
        log_error(error_message, log_file)


def analysis_to_file(analysis_data, setup, report_hash):
    # Iterate through dict printing analysis data

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Output file based on user settings
    with open(f"reports/{report_hash}.csv", mode='a') as f:

        header = "Ticker,Report Date"

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

        f.write(header + '\n')

        # Add data per ticker
        for ticker in analysis_data.keys():

            analysis_output = f"{ticker},{current_date}"

            for analysis in setup['Trend'].keys():
                try:
                    recommendation = analysis_data[ticker][analysis]['Cross'].values[0]
                    analysis_output += f",{recommendation}"

                except KeyError as ke:
                    error_message = f"No {str(ke)} analysis found for {ticker}"
                    print(error_message)
                    log_error(error_message, f"logs/{report_hash}.log")
                    analysis_output += ","

            #ticker_final_score = ticker_score / trend_total_weight
            #if (ticker_final_score >= setup['Thresholds']['Trend']['Buy'] or
            #        ticker_final_score <= setup['Thresholds']['Trend']['Sell']):
            f.write(analysis_output + '\n')

        f.close()


def backtest_to_file(analysis_data, backtest_data, setup, report_hash):

    with open(f"reports/{report_hash}.bt", mode='a') as f:
        header = "Ticker,Recommendation"
        for trend in setup['Trend'].keys():
            if setup['Trend'][trend]['enabled']:
                header += f",{trend}_price_start,{trend}_date_start,{trend}_price_end,{trend}_date_end"
        header += f",gain,period\n"
        f.write(header)

        for ticker in backtest_data.keys():
            # Get results recommendation for ticket
            price_start = []
            price_end = []
            date_start = []
            date_end = []

            for result_date in backtest_data[ticker]['results'].keys():
                # Add result to file
                recommendation = 'Buy' if backtest_data[ticker]['results'][result_date]['score'] > 0.0 else 'Sell'
                result_output = f"{ticker},{recommendation}"
                for analysis in setup['Trend'].keys():
                    # Add Analysis Data
                    try:
                        date = analysis_data[ticker][analysis]['Date'].values[0].astype('datetime64[D]')
                        result_output += f",{round(analysis_data[ticker][analysis]['Close'].values[0],3)},"\
                                         f"{date}"
                        price_start.append(round(analysis_data[ticker][analysis]['Close'].values[0],3))
                        date_start.append(date)
                    except KeyError as e:
                        error_message = f"{str(e)} for {ticker} for backtest analysis"
                        print(error_message)
                        result_output += ',,'
                    # Add Backtest Data
                    try:
                        date = backtest_data[ticker]['results'][result_date][analysis]['Date'].values[0].astype('datetime64[D]')
                        result_output += f",{round(backtest_data[ticker]['results'][result_date][analysis]['Close'].values[0],3)}," \
                                         f"{date}"
                        price_end.append(round(backtest_data[ticker]
                                               ['results'][result_date][analysis]['Close'].values[0],3))
                        date_end.append(date)
                    except KeyError as e:
                        error_message = f"{str(e)} for {ticker} for backtest analysis"
                        print(error_message)
                        result_output += ',,'
                gain = round(max(price_end)/max(price_start) - 1 if recommendation == "Sell" else \
                    1 - max(price_end)/max(price_start),3)*100
                period = str((max(date_end)-max(date_start))).replace("days","")
                result_output += f",{gain},{period}\n"
                f.write(result_output)

    f.close()


def get_backtest_dates(start_date, period):

    backtest_end_date = datetime.strptime(start_date, "%Y-%m-%d") - relativedelta(days=1)

    if 'd' in period:
        period = period.replace('d', '')
        period_days = int(period) * 1
        backtest_start_date = backtest_end_date - relativedelta(days=period_days)
    elif 'w' in period:
        period = period.replace('w', '')
        period_days = int(period) * 7
        backtest_start_date = backtest_end_date - relativedelta(days=period_days)
    elif "mo" in period:
        period = period.replace("mo", '')
        period_days = int(period) * 30
        backtest_start_date = backtest_end_date - relativedelta(days=period_days)
    elif 'y' in period:
        period = period.replace('y', '')
        period_days = int(period) * 365
        backtest_start_date = backtest_end_date - relativedelta(days=period_days)
    else:
        raise ValueError(f"Period format [{period}] not recognized. Valid forms: [d, w, m, y].")

    return [backtest_start_date, backtest_end_date]

