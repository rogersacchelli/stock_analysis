from datetime import datetime


def analysis_to_file(analysis_data, analysis_settings, report_name):
    # Iterate through dict printing analysis data

    current_date = datetime.now().strftime('%Y-%m-%d')

    # Output file based on user settings
    with open(report_name, mode='a') as f:

        header = "Ticker, Report Date"
        header_cfg = {}
        col = 0

        # Create Header based on analysis settings
        for trend in analysis_settings['Trend'].keys():
            if trend == "sma_cross" or "ema_cross":
                header = f"{header},{trend.upper()} {analysis_settings['Trend'][trend]['short']}/" \
                         f"{analysis_settings['Trend'][trend]['long']}"
                header_cfg.update({trend: col})
                col += 1

        f.write(header + '\n')

        # Add data per ticket
        for ticket in analysis_data.keys():
            analysis_output = f"{ticket},{current_date},"
            for analysis in analysis_data[ticket].keys():
                analysis_output = f"{analysis_output}" + ','*header_cfg[analysis] +\
                                  analysis_data[ticket][analysis]['cross']
            f.write(analysis_output + '\n')

        f.close()

