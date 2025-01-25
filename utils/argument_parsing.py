import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils.utils import LoadFromFile


def argument_parsing():

    parser = argparse.ArgumentParser(description="Analyze stock crossings of moving averages.")

    group = parser.add_mutually_exclusive_group()

    parser.add_argument('-i', '--input', required=True, action=LoadFromFile,
                        help="Input file containing stock tickers in JSON format.")
    parser.add_argument('-e', '--email', help="Email address to send results.")
    parser.add_argument('-es', '--subject',default="Report Analysis", help="Email subject to send results.")
    parser.add_argument('-c', '--config', required=True, action=LoadFromFile, help="Configuration File.")
    parser.add_argument('-s', '--setup', required=True, action=LoadFromFile, help="Setup definition File.")
    parser.add_argument('-p', '--position', action=LoadFromFile, help="Setup position File.")
    parser.add_argument('-l', '--limit', type=int, default=500, help="Limit the number of stocks processed.")
    group.add_argument('-f', '--features', action="store_true", default=False,
                       help="Create features file for Machine Learning Training")
    parser.add_argument('-v', '--verbose', default=False, action="store_true", help="Verbose mode.")
    group.add_argument('-b', '--backtest', action="store_true",
                       help="Backtest mode provides recommended stocks prior to start date and assess the "
                             "recommendation over specified the specified period. If no dates are specified, "
                             "default period starts as 1y ago until now.")
    parser.add_argument('-sd', '--start_date', type=valid_date,
                        default=datetime.combine(datetime.now().date(), datetime.min.time())-relativedelta(years=1),
                        help="The start date which is intended to assess the stocks for backtest or "
                             "feature extraction - format YYYY-MM-DD")
    parser.add_argument('-ed', '--end_date', type=valid_date,
                        default=datetime.combine(datetime.now().date(), datetime.min.time())+relativedelta(hours=23),
                        help="The end date of evaluation - format YYYY-MM-DD")
    return parser.parse_args()


def valid_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")
