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

        # Create Header based on analysis settings
        for trend in analysis_settings['Trend'].keys():
            if trend == "sma_cross" or trend == "ema_cross":
                header = f"{header},{trend.upper()} {analysis_settings['Trend'][trend]['short']}/" \
                         f"{analysis_settings['Trend'][trend]['long']}"

            elif trend == "bollinger_bands" or trend == "week_rule":
                header = f"{header},{analysis_settings['Trend'][trend]['period']} {trend.upper()}"

            elif trend == "macd":
                header = f"{header},{analysis_settings['Trend'][trend]['signal_window']} {trend.upper()}"

            header_cfg.update({trend: col})
            col += 1

        f.write(header + '\n')

        # Add data per ticket
        for ticket in analysis_data.keys():
            analysis_output = f"{ticket},{current_date}"
            for analysis in analysis_settings['Trend'].keys():
                try:
                    analysis_output += f",{analysis_data[ticket][analysis]['recommendation']}"
                except KeyError as ke:
                    error_message = f"No {str(ke)} analysis found for {ticket}"
                    print(error_message)
                    log_error(error_message, f"logs/{report_rash}.log")
                    analysis_output += ","

            f.write(analysis_output + '\n')

        f.close()

