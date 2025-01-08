from risk import get_stop_data
from utils.utils import log_error, get_days_from_period
from data_aquisition import fetch_yahoo_stock_data
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from trend import *
from datetime import datetime


def select_stocks_from_setup(stock_list, setup, limit, report_hash, start_date=None, end_date=None):

    analysis_data = {}
    log_file = f"logs/{report_hash}.log"

    if end_date is None:
        end_date = datetime.now()

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
                    if analysis == "long_term":
                        crossings = detect_long_term_crossings(stock_data=stock_data,
                                                        period=setup['Trend'][analysis]['period'],
                                                        output_window=setup['Trend'][analysis]['output_window'],
                                                        end_date=end_date,
                                                        average_type="SMA" if
                                                            setup['Trend'][analysis]['avg_type'] == 'sma' else "EMA")

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
                        print(f"Crossings found for {ticker} using {analysis}.")
                        crossings.index = [ticker] * len(crossings)
                        try:
                            analysis_data[ticker]
                        except KeyError:
                            analysis_data.update({ticker: {}})

                        # Assign weights to results
    
                        analysis_data[ticker].update({analysis: crossings})
                        if crossings['Cross'].values[0] == "Sell":
                            ticker_score -= setup['Trend'][analysis]['weight']
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

                # Add Stop info if required
                if setup['Risk']['Stop']['enabled']:
                    analysis_data[ticker].update({"stop": {"date_start": stock_data['Close'].tail(1).index,
                                                           "price_start": stock_data['Close'].tail(1).values[0]}})
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

                    bt_crossings = None

                    if analysis == "long_term":
                        bt_crossings = detect_long_term_crossings(stock_data=ticker_hist_data,
                                                        period=setup['Trend'][analysis]['period'],
                                                        output_window=0,
                                                        end_date=end_date,
                                                        average_type="SMA" if
                                                            setup['Trend'][analysis]['avg_type'] == 'sma' else "EMA")

                    if analysis == 'sma_cross' or analysis == 'ema_cross':
                        # Get Crossing data
                        bt_crossings = detect_ma_crossings(ticker_hist_data,
                                                        short_window=setup['Trend'][analysis]['short'],
                                                        long_window=setup['Trend'][analysis]['long'],
                                                        output_window=0,
                                                        end_date=end_date,
                                                        average_type='EMA' if analysis == 'ema_cross' else 'SMA')

                    elif analysis == 'bollinger_bands':
                        bt_crossings = detect_bollinger_crossings(stock_data=ticker_hist_data,
                                                         period=setup['Trend'][analysis]['period'],
                                                         output_window=0,
                                                         average_type=setup['Trend'][analysis]['avg_type'],
                                                         end_date=end_date,
                                                         std_dev=setup['Trend'][analysis]['std_dev'])

                    elif analysis == 'week-rule':

                        bt_crossings = detect_wr_crossings(stock_data=ticker_hist_data,
                                                  period=setup['Trend'][analysis]['period'],
                                                  end_date=end_date,
                                                  output_window=0)

                    elif analysis == 'macd':
                        bt_crossings = detect_macd_trend(ticker_hist_data,
                                          short_window=setup['Trend'][analysis]['short'],
                                          long_window=setup['Trend'][analysis]['long'],
                                          signal_window=setup['Trend'][analysis]['signal_window'],
                                          output_window=0,
                                          end_date=end_date)

                    try:
                        backtest_data[ticker]
                    except KeyError:
                        backtest_data.update({ticker: {}})
                    backtest_data[ticker].update({analysis: bt_crossings})

            # Search for events along the crossings
            analysis_start_date = start_date + relativedelta(days=get_pre_analysis_period(setup))
            analysis_day = analysis_start_date

            """ 
            Stock selection assigns negative score values for stocks crossing down the analysis thresholds and
            positive values score for stocks crossing up the analysis thresholds. Backtest Recommendation must 
            seek for opposite recommendations of the analysis in order to correctly calculate gains.  
            """

            analysis_recommendation = 'Sell' if analysis_data[ticker]['score'] < 0.0 else 'Buy'
            backtest_recommendation = 'Sell' if analysis_recommendation == 'Buy' else 'Buy'

            # TODO: Pack Analyisis of the next recommendation into a single function
            # search through selected stocks common days of recommendation to them for backtesting dataset
            while analysis_day <= end_date:

                backtest_score = 0.0
                updates = {}

                for ticker_analysis in backtest_data[ticker].keys():

                    # discard 'results' key in backtest data
                    if ticker_analysis == 'results':
                        break

                    analysis_limit = analysis_day + relativedelta(days=setup['Trend'][ticker_analysis]['output_window'])
                    analysis_crossings = backtest_data[ticker][ticker_analysis]
                    analysis_crossings = analysis_crossings[(analysis_crossings['Cross'] == backtest_recommendation) &
                                                            (analysis_crossings['Date'] >= analysis_day) &
                                                            (analysis_crossings['Date'] <= analysis_limit)]
                    if not analysis_crossings.empty:
                        if backtest_recommendation == 'Buy':
                            backtest_score += setup['Trend'][ticker_analysis]['weight']
                        else:
                            backtest_score -= setup['Trend'][ticker_analysis]['weight']

                        updates.update({ticker_analysis: analysis_crossings})

                backtest_data[ticker]['results'][analysis_day] = updates

                final_score = backtest_score / total_backtest_score

                # The score of the first date which crosses the threshold for Buy/Sell is added to backtest data
                # If criteria is not met, date is pop out of results.
                if final_score >= setup['Thresholds']['Trend']['Buy']:
                    backtest_data[ticker]['results'][analysis_day].update({'score': final_score})
                    break
                elif final_score <= setup['Thresholds']['Trend']['Sell']:
                    backtest_data[ticker]['results'][analysis_day].update({'score': final_score})
                    break
                else:
                    backtest_data[ticker]['results'].pop(analysis_day)

                analysis_day = analysis_day + relativedelta(days=1)

            # TODO: Pack this to a function
            # Add Stop Data to prevent large losses if required
            if setup['Risk']['Stop']['enabled']:
                stop_date, stop_price = get_stop_data(ticker_hist_data, setup,
                                                      start_price=analysis_data[ticker]['stop']['price_start'],
                                                      start_date=analysis_start_date,
                                                      initial_recommendation=analysis_recommendation)

                if stop_price is not None:
                    backtest_data[ticker].update({'stop': {'price': stop_price, 'date': stop_date}})

        return backtest_data

    except Exception as e:
        error_message = f"Error handling backtest data - {str(e)}"
        print(error_message)
        log_error(error_message, log_file)





def backtest_to_file(analysis_data, backtest_data, setup, report_hash):

    with open(f"reports/{report_hash}-bt.csv", mode='a') as f:
        header = "Ticker,Analysis Recommendation"
        for trend in setup['Trend'].keys():
            if setup['Trend'][trend]['enabled']:
                header += f",{trend}_price_start,{trend}_date_start,{trend}_price_end,{trend}_date_end"
        if setup['Risk']['Stop']['enabled']:
            header += f",gain,period,stop_date,effective_gain,effective_period\n"
        else:
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
                recommendation = 'Buy' if analysis_data[ticker]['score'] > 0.0 else 'Sell'
                result_output = f"{ticker},{recommendation}"
                for analysis in setup['Trend'].keys():
                    # Add Analysis Data
                    if setup['Trend'][analysis]['enabled']:
                        try:
                            date = analysis_data[ticker][analysis]['Date'].values[0].astype('datetime64[D]')
                            result_output += f",{round(analysis_data[ticker][analysis]['Close'].values[0], 2)},"\
                                             f"{date}"
                            price_start.append(round(analysis_data[ticker][analysis]['Close'].values[0], 2))
                            date_start.append(date)
                        except KeyError as e:
                            error_message = f"{str(e)} for {ticker} for backtest analysis"
                            print(error_message)
                            result_output += ',,'
                        # Add Backtest Data
                        try:
                            date = backtest_data[ticker]['results'][result_date][analysis]['Date'].values[0].astype('datetime64[D]')
                            result_output += f",{round(backtest_data[ticker]['results'][result_date][analysis]['Close'].values[0], 2)}," \
                                             f"{date}"
                            price_end.append(round(backtest_data[ticker]
                                                   ['results'][result_date][analysis]['Close'].values[0], 2))
                            date_end.append(date)
                        except KeyError as e:
                            error_message = f"{str(e)} for {ticker} for backtest analysis"
                            print(error_message)
                            result_output += ',,'

                gain = round(100 * (max(price_end) - max(price_start)) / max(price_start), 2)

                if recommendation == "Sell":
                    gain *= -1

                period = str((max(date_end) - max(date_start))).replace("days", "")
                result_output += f",{gain},{period}"

                effective_gain = gain
                effective_period = period

                if setup['Risk']['Stop']['enabled'] and 'stop' in backtest_data[ticker]:

                    stop_date = backtest_data[ticker]['stop']['date']

                    if stop_date <= min(date_end):
                        effective_gain = setup['Risk']['Stop']['margin']*100*(-1.0)
                        effective_period = np.datetime64(backtest_data[ticker]['stop']['date']) - max(date_start)
                        effective_period = str(effective_period).replace("days", "")

                result_output += f",{stop_date},{effective_gain},{effective_period}"

                f.write(result_output + '\n')
    f.close()


def get_recommendation_period(start_date, period):

    # String date format to datetime
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")

    backtest_end_date = start_date - relativedelta(days=1)

    period_days = get_days_from_period(period)

    backtest_start_date = backtest_end_date - relativedelta(days=period_days)

    return [backtest_start_date, backtest_end_date]


def get_pre_analysis_period(setup, calendar_days=True):

    # Get the lengthiest period analysis from setup
    period = 0
    for analysis in setup['Trend'].keys():
        if 'period' in setup['Trend'][analysis] and setup['Trend'][analysis]['enabled']:
            if period < setup['Trend'][analysis]['period']:
                period = setup['Trend'][analysis]['period']
        elif 'long' in setup['Trend'][analysis]:
            if period < setup['Trend'][analysis]['long']:
                period = setup['Trend'][analysis]['long']

    if calendar_days:
        return int(period / 5) * 7 + (period % 5) + 7  # the last seven is an extra to cover holidays
    else:
        return period


def get_backtest_start(start_date: datetime, setup):

    start_date = start_date - relativedelta(days=get_pre_analysis_period(setup))
    return start_date


def get_position_results(setup):

    results = {}
    for ticker in setup['Position'].keys():

        results.update({ticker: {}})

        for date in setup['Position'][ticker].keys():

            # Get the latest price for stock
            # "Ticker,Price Start,Price End,Date Start,Gain,Period\n"
            date_start = datetime.strptime(date, "%Y-%m-%d")
            end_date = datetime.today()
            stock_data = fetch_yahoo_stock_data(ticker, start_date=None, end_date=end_date, period='1d')

            price_start = setup['Position'][ticker][date]['price']
            volume = setup['Position'][ticker][date]['volume']

            price_end = round(stock_data['Close'].tail(1).values[0], 2)
            gain = round(100 * (price_end - price_start) / price_start, 2)
            position_period = datetime.now() - date_start

            results[ticker].update({date: {"price_start": price_start, "price_end": price_end, "gain": gain,
                                           "volume": volume, "period": position_period}})

    return results



