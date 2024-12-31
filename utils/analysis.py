from datetime import datetime
from utils.utils import log_error


def analysis_to_file(analysis_data, analysis_settings, report_rash):
    # Iterate through dict printing analysis data

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Output file based on user settings
    with open(f"reports/{report_rash}.csv", mode='a') as f:

        header = "Ticker, Report Date"
        header_cfg = {}
        col = 0
        trend_total_weight = 0.0
        # Create Header based on analysis settings
        for trend in analysis_settings['Trend'].keys():
            if trend == "sma_cross" or trend == "ema_cross":
                header = f"{header},{trend.upper()} {analysis_settings['Trend'][trend]['short']}/" \
                         f"{analysis_settings['Trend'][trend]['long']}"

            elif trend == "bollinger_bands" or trend == "week_rule":
                header = f"{header},{analysis_settings['Trend'][trend]['period']} {trend.upper()}"

            elif trend == "macd":
                header = f"{header},{analysis_settings['Trend'][trend]['signal_window']} {trend.upper()}"
            trend_total_weight += analysis_settings['Trend'][trend]['weight']
            header_cfg.update({trend: col})
            col += 1

        f.write(header + '\n')

        # Add data per ticker
        for ticker in analysis_data.keys():

            analysis_output = f"{ticker},{current_date}"
            ticker_score = 0.0

            for analysis in analysis_settings['Trend'].keys():
                try:
                    recommendation = analysis_data[ticker][analysis]['recommendation']
                    analysis_output += f",{recommendation}"
                    if recommendation == 'Buy':
                        ticker_score += analysis_settings['Trend'][analysis]['weight']
                    else:
                        ticker_score -= analysis_settings['Trend'][analysis]['weight']

                except KeyError as ke:
                    error_message = f"No {str(ke)} analysis found for {ticker}"
                    print(error_message)
                    log_error(error_message, f"logs/{report_rash}.log")
                    analysis_output += ","

            ticker_final_score = ticker_score / trend_total_weight
            if (ticker_final_score >= analysis_settings['Thresholds']['Trend']['Buy'] or
                    ticker_final_score <= analysis_settings['Thresholds']['Trend']['Sell']):
                f.write(analysis_output + '\n')
            else:
                print(
                    f"{ticker} not included since its score {ticker_final_score} does not meet threshold settings.")

        f.close()
