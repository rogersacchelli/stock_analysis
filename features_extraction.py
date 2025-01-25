from datetime import datetime


def add_closing_price(stock_data, setup):

    period = setup['Features']['period']
    stock_data = stock_data.sort_values('Date')
    stock_data[f"Close_{period}"] = stock_data['Close'].shift(-period)
    stock_data.loc[stock_data.index[-period:], [f"Close_{period}"]] = None

    return stock_data


def save_features_to_file(data, report_hash):

    output_file = f"reports/{report_hash}_ds.csv"
    header = True
    with open(output_file, mode='w') as f:
        for ticker in data.keys():
            df = data[ticker]['stock_data'].dropna()
            df.to_csv(f, header=header, index=False)
            header = False
    f.close()

