import yfinance as yf
import time

tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "MMM"]
start_date = "2023-01-01"
end_date = "2025-08-13"

try:
    data = yf.download(tickers, start=start_date, end=end_date, threads=False, group_by='ticker', auto_adjust=True)
    print(data)
except Exception as e:
    print(f"Error: {e}")