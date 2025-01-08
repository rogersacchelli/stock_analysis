from datetime import datetime


def get_stop_data(stock_data, setup, start_price, start_date: datetime, initial_recommendation):
    # Search for Stops based on setup and add info to ticker

    if initial_recommendation == 'Buy':
        for date, row in stock_data.iterrows():
            if (row['Close'] <= start_price * (1.0 - setup['Risk']['Stop']['margin'])) and date >= start_date:
                return date.date(), row['Close']
    else:
        for date, row in stock_data.iterrows():
            if row['Close'] >= start_price * (1.0 + setup['Risk']['Stop']['margin']) and date >= start_date:
                return date.date(), row['Close']

    return None, None
