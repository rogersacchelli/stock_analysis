from momentum import rsi, add_adx
import logging
from risk import get_stop_data
from utils.utils import log_error, get_pre_analysis_period, store_filter_data, get_filter_data
from data_aquisition import fetch_yahoo_stock_data
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from trend import *
from datetime import datetime


def select_stocks_from_setup(stock_list, setup, limit, report_hash, start_date=None, end_date=None):
    analysis_data = {}
    log_file = f"logs/{report_hash}.log"

    for ticker_code in stock_list:
        ticker = ticker_code['Code']
        print(f"Analyzing {ticker}...")

        try:
            stock_data = fetch_yahoo_stock_data(ticker, start_date=start_date, end_date=end_date)
        except Exception as e:
            # Skip to next Ticket
            error_message = f"Error fetching data for {ticker} - {str(e)}"
            print(str(error_message))
            log_error(error_message, log_file)
            continue

        # Add slope information to stock data
        add_moving_average_slope(stock_data, setup)
        # Add ADX
        stock_data = add_adx(stock_data, setup)

        for analysis in setup['Analysis'].keys():
            for method in setup['Analysis'][analysis].keys():

                if setup['Analysis'][analysis][method]['enabled']:
                    try:
                        if analysis == "Trend":
                            if method == "long_term":
                                crossings = detect_long_term_crossings(stock_data=stock_data,
                                                                       setup=setup,
                                                                       end_date=end_date)

                            if method == "sma_cross" or method == "ema_cross":

                                crossings = detect_ma_crossings(stock_data=stock_data, end_date=end_date, setup=setup,
                                                                method=method)

                            elif method == "bollinger_bands":
                                crossings = detect_bollinger_crossings(stock_data=stock_data, setup=setup,
                                                                       end_date=end_date)

                            elif method == "wr_rule":
                                crossings = detect_wr_crossings(stock_data=stock_data, setup=setup, end_date=end_date)

                            elif method == "macd":
                                crossings = detect_macd_trend(stock_data, setup=setup, end_date=end_date)

                        # Momentum
                        elif analysis == "Momentum":
                            if method == 'rsi':
                                crossings = rsi(stock_data, setup, end_date=end_date)

                        if not crossings.empty and not analysis_filter(crossings, setup):
                            print(f"Crossings found for {ticker} using {analysis}.")

                            crossings.index = [ticker] * len(crossings)
                            try:
                                analysis_data[ticker]
                            except KeyError:
                                analysis_data.update({ticker: {}})

                            analysis_data[ticker].update({method: crossings})

                    except Exception as e:
                        error_message = f"Error analyzing {ticker}: {e}"
                        print(error_message)
                        log_error(error_message, log_file)

        # Keep Analysis if higher then thresholds
        if ticker in analysis_data:
            calculate_score(analysis_data[ticker], setup)

            if setup['Risk']['Stop']['enabled']:
                analysis_data[ticker].update({"stop": {"date_start": stock_data['Close'].tail(1).index,
                                                       "price_start": stock_data['Close'].tail(1).values[0]}})

        # Break loop if limit is exceeded
        limit -= 1
        if limit == 0:
            break

    return analysis_data


def backtest(analysis_data, start_date, end_date, setup, report_hash):

    backtest_data = {}
    backtest_data = defaultdict(lambda: defaultdict(dict), backtest_data)

    try:
        for ticker in analysis_data.keys():
            print(f"Backtesting {ticker}")

            bt_start_date = start_date - relativedelta(days=get_pre_analysis_period(setup))
            ticker_hist_data = fetch_yahoo_stock_data(ticker, start_date=bt_start_date, end_date=end_date)
            total_backtest_score = 0.0

            # Backtest Crossing Events Collection

            for analysis in setup['Analysis'].keys():
                for method in setup['Analysis'][analysis].keys():
                    bt_crossings = None
                    if setup['Analysis'][analysis][method]['enabled']:
                        total_backtest_score += setup['Analysis'][analysis][method]['weight']
                        if analysis == "Trend":

                            if method == "long_term":
                                bt_crossings = detect_long_term_crossings(stock_data=ticker_hist_data, setup=setup,
                                                                          end_date=end_date, backtest=True)

                            if method == 'sma_cross' or analysis == 'ema_cross':
                                # Get Crossing data
                                bt_crossings = detect_ma_crossings(ticker_hist_data, setup=setup, end_date=end_date,
                                                                   backtest=True, method=method)

                            elif method == 'bollinger_bands':
                                bt_crossings = detect_bollinger_crossings(stock_data=ticker_hist_data,
                                                                          setup=setup, end_date=end_date,
                                                                          backtest=True)

                            elif method == 'week_rule':

                                bt_crossings = detect_wr_crossings(stock_data=ticker_hist_data, end_date=end_date,
                                                                   setup=setup, backtest=True)

                            elif method == 'macd':
                                bt_crossings = detect_macd_trend(ticker_hist_data, setup=setup, end_date=end_date,
                                                                 backtest=True)
                        elif analysis == "Momentum":
                            if method == "rsi":
                                bt_crossings = rsi(ticker_hist_data, setup=setup, end_date=end_date, backtest=True)

                        try:
                            backtest_data[ticker]
                        except KeyError:
                            backtest_data.update({ticker: {}})

                        backtest_data[ticker].update({method: bt_crossings})

            # Search for events along the crossings
            analysis_start_date = start_date
            analysis_day = analysis_start_date

            """ 
            Stock selection assigns negative score values for stocks crossing down the analysis thresholds and
            positive values score for stocks crossing up the analysis thresholds. Backtest Recommendation must 
            seek for opposite recommendations of the analysis in order to correctly calculate gains.  
            """

            analysis_recommendation = 'Sell' if analysis_data[ticker]['score'] < 0.0 else 'Buy'
            backtest_recommendation = 'Sell' if analysis_recommendation == 'Buy' else 'Buy'

            # TODO: Pack Analysis of the next recommendation into a single function
            # search through selected stocks common days of recommendation to them for backtesting dataset
            while analysis_day <= end_date:

                backtest_score = 0.0
                updates = {}

                for analysis in setup['Analysis'].keys():
                    for method in setup['Analysis'][analysis].keys():
                        if method in backtest_data[ticker].keys():

                            analysis_limit = analysis_day + \
                                             relativedelta(days=setup['Analysis'][analysis][method]['output_window'])

                            analysis_crossings = backtest_data[ticker][method]
                            analysis_crossings = analysis_crossings[(analysis_crossings['Cross'] == backtest_recommendation) &
                                                                    (analysis_crossings['Date'] >= analysis_day) &
                                                                    (analysis_crossings['Date'] <= analysis_limit)]
                        if not analysis_crossings.empty:
                            if backtest_recommendation == 'Buy':
                                backtest_score += setup['Analysis'][analysis][method]['weight']
                            else:
                                backtest_score -= setup['Analysis'][analysis][method]['weight']

                            updates.update({method: analysis_crossings})

                backtest_data[ticker]['results'][analysis_day] = updates

                final_score = backtest_score / total_backtest_score

                # The score of the first date which crosses the threshold for Buy/Sell is added to backtest data
                # If criteria is not met, date is pop out of results.
                if final_score >= setup['Thresholds']['Buy']:
                    backtest_data[ticker]['results'][analysis_day].update({'score': final_score})
                    break
                elif final_score <= setup['Thresholds']['Sell']:
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

    except ValueError as e:
        error_message = f"Error handling backtest data - {str(e)}"
        print(error_message)
        logging.error(error_message)


def create_backtest_report_heading(setup, filter_data):

    header = "Ticker,Analysis Recommendation"
    for analysis in setup['Analysis'].keys():

        for method in setup['Analysis'][analysis].keys():
            if setup['Analysis'][analysis][method]['enabled']:
                header += f",{method}_price_start,{method}_date_start,{method}_price_end,{method}_date_end"

    # Filter heading
    for ft in setup['Filters'].keys():
        filter_data.update({ft: {}})
        for filter in setup['Filters'][ft].keys():
            if ft == "Trend":
                header += f",{ft.lower()}_{filter}"
                filter_data[ft].update({filter: []})
            elif ft == "Momentum":
                if filter == "adx":
                    filter_data[ft].update({filter: {"ADX": [], "+DI": [], "-DI": []}})
                    header += f",{filter},{filter}_d+,{filter}_d-"

    if setup['Risk']['Stop']['enabled']:
        header += f",gain,period,stop_date,effective_gain,effective_period\n"
    else:
        header += f",gain,period\n"

    return header


def get_backtest_result(ticker, backtest_stock_data, analysis_stock_data, setup):

    filter_data = {}
    filter_data = defaultdict(lambda: defaultdict(dict), filter_data)

    price_start = []
    price_end = []
    date_start = []
    date_end = []

    for result_date in backtest_stock_data['results'].keys():
        # Add result to file
        recommendation = 'Buy' if analysis_stock_data['score'] > 0.0 else 'Sell'
        result_output = f"{ticker},{recommendation}"

        for analysis in setup['Analysis'].keys():
            for method in setup['Analysis'][analysis].keys():
                # Add Analysis Data
                if setup['Analysis'][analysis][method]['enabled']:
                    try:
                        date = analysis_stock_data[method]['Date'].values[0].astype('datetime64[D]')
                        result_output += f",{round(analysis_stock_data[method]['Close'].values[0], 2)}," \
                                         f"{date}"
                        price_start.append(round(analysis_stock_data[method]['Close'].values[0], 2))
                        date_start.append(date)

                        # Store filter variables data
                        store_filter_data(filter_data, method, analysis_stock_data, setup)

                    except KeyError as e:
                        error_message = f"{str(e)} for {ticker} for backtest analysis"
                        print(error_message)
                        result_output += ',,'

                    # Add Backtest Data
                    try:
                        date = backtest_stock_data['results'][result_date][method]['Date'].values[0].astype(
                            'datetime64[D]')
                        result_output += f",{round(backtest_stock_data['results'][result_date][method]['Close'].values[0], 2)}," \
                                         f"{date}"
                        price_end.append(round(backtest_stock_data
                                               ['results'][result_date][method]['Close'].values[0], 2))
                        date_end.append(date)
                    except KeyError as e:
                        error_message = f"{str(e)} for {ticker} for backtest analysis"
                        print(error_message)
                        result_output += ',,'

        # Add final slopes
        result_output = get_filter_data(filter_data, result_output)

        gain = round(100 * (max(price_end) - max(price_start)) / max(price_start), 2)

        if recommendation == "Sell":
            gain *= -1

        period = str((max(date_end) - max(date_start))).replace("days", "")
        result_output += f",{gain},{period}"

        effective_gain = gain
        effective_period = period

        if setup['Risk']['Stop']['enabled'] and 'stop' in backtest_stock_data:

            stop_date = backtest_stock_data['stop']['date']

            if stop_date <= min(date_end):
                effective_gain = setup['Risk']['Stop']['margin'] * 100 * (-1.0)
                effective_period = np.datetime64(backtest_stock_data['stop']['date']) - max(date_start)
                effective_period = str(effective_period).replace("days", "")

            result_output += f",{stop_date},{effective_gain},{effective_period}"

    return result_output


def backtest_to_file(analysis_data, backtest_data, setup, report_hash):

    logging.info(f"Saving backtest to file {report_hash}-bt.csv")
    filter_data = {}

    try:
        with open(f"reports/{report_hash}-bt.csv", mode='a') as f:

            header = create_backtest_report_heading(setup, filter_data)
            f.write(header)

            for ticker in backtest_data.keys():

                result_output = get_backtest_result(ticker=ticker,
                                                    backtest_stock_data=backtest_data[ticker],
                                                    analysis_stock_data=analysis_data[ticker],
                                                    setup=setup)

                f.write(result_output + '\n')
        f.close()
        print(f"Report saved in reports/{report_hash}-bt.csv")

    except ValueError as error:
        logging.error(str(error))


def get_position_results(setup):
    results = {}
    for ticker in setup['Position'].keys():

        try:

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
        except Exception as e:
            error_message = f"Failed to get position results for {ticker}"
            print(error_message)

    return results


def calculate_score(data, setup):

    score = 0.0
    total_score = 0.0

    for analysis in setup['Analysis'].keys():
        for method in setup['Analysis'][analysis].keys():
            if setup['Analysis'][analysis][method]['enabled']:
                total_score += setup['Analysis'][analysis][method]['weight']
                if method in data.keys():
                    # Assign weights to results
                    total_score += setup['Analysis'][analysis][method]['weight']

                    if data[method]['Cross'].values[0] == "Sell":
                        score -= setup['Analysis'][analysis][method]['weight']
                    else:
                        score += setup['Analysis'][analysis][method]['weight']

    score = score / total_score
    data.update({"score": score})


def add_moving_average_slope(stock_data, setup):

    # Add MA Period and calculate slope to data
    for ma in setup['Filters']['Trend'].keys():
        period = setup['Filters']['Trend'][ma]['period']
        slope = setup['Filters']['Trend'][ma]['slope_period']

        calculate_ma_slope(stock_data, ma_period=period, slope_period=slope, name=ma)


def analysis_filter(data, setup):

    try:
        # Check if data crossed trend limits
        for ft in setup['Filters'].keys():
            for filter in setup['Filters'][ft].keys():
                if setup['Filters'][ft][filter]['enabled']:
                    if ft == 'Trend':
                        limit = setup['Filters'][ft][filter]['slope']
                        recommendation = data['Cross'].values[0]
                        slope = data[f"MA_Slope_{filter}"].values[0]

                        if recommendation == "Buy" and slope < limit:
                            return True
                        elif recommendation == "Sell" and slope > limit:
                            return True

        return False
    except ValueError as e:
        error_message = f"Failed to validate if data meets thresholds limitations - {str(e)}"
        logging.error(error_message)