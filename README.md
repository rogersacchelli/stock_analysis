# Stock Analysis Tool

This Stock Analysis Tool is a Python-based application designed to analyze stock data using various trend detection techniques. It generates detailed reports, optionally sending results via email, and includes a backtesting feature to evaluate historical performance.

## Features

- Fetch historical stock data using Yahoo Finance.
- Analyze stock data for:
  - SMA (Simple Moving Average) crossings.
  - EMA (Exponential Moving Average) crossings.
  - Bollinger Band touches.
  - Weekly Rule crossings.
  - **Long-Term Trending Analysis**: Checks if the price has crossed a long-term moving average.
  - **MACD Analysis**: Evaluates Moving Average Convergence Divergence (MACD) signals.
- Generate reports in CSV format.
- Optionally send analysis reports via email.
- Backtest stock recommendations over a specified period.

## Requirements

- Python 3.8+
- Required Python libraries:
  - `yfinance`
  - `pandas`
  - `argparse`
  - `dateutil`
  - Other dependencies listed in the `requirements.txt` file.
- JSON configuration files for tickers, analysis, and application settings.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repository_folder>
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Command-Line Arguments

- `-i`, `--input`: Input file containing stock tickers in JSON format (required).
- `-e`, `--email`: Email address to send results (optional).
- `-c`, `--config`: Configuration file for application settings (required).
- `-a`, `--analysis`: Analysis definition file (required).
- `-l`, `--limit`: Limit the number of stocks processed (optional, default: 50).
- `-b`, `--backtest`: Enables backtesting mode to evaluate recommendations over a specified period (optional).
- `-sd`, `--bt_start_date`: Start date for backtesting in YYYY-MM-DD format (optional).
- `-ed`, `--bt_end_date`: End date for backtesting in YYYY-MM-DD format (optional).

### Example Command

```bash
python main.py \
  -i tickers.json \
  -e user@example.com \
  -c config.json \
  -a analysis.json \
  -l 100 \
  -b \
  -sd 2023-01-01 \
  -ed 2023-12-31
```

### Input Files

#### Tickers File (`tickers.json`)
A JSON file containing stock tickers:
```json
[
  { "Code": "AAPL" },
  { "Code": "GOOGL" },
  { "Code": "MSFT" }
]
```

#### Configuration File (`config.json`)
Contains application settings, such as email server configuration:
```json
{
  "Email": {
    "from_email": "example@example.com",
    "from_password": "password",
    "smtp_server": "smtp.example.com",
    "smtp_port": 587
  }
}
```

#### Analysis Definition File (`analysis.json`)
Specifies analysis parameters:
```json
{
  "Period": "1y",
   "Trend": {
    "long_term": {
      "enabled": 1,
      "period": 40,
      "rate": 0.01,
      "output_window": 5,
      "avg_type": "sma",
      "weight": 1.0
    },
    "sma_cross": {
      "enabled": 1,
      "long": 20,
      "short": 5,
      "output_window": 5,
      "weight": 1.0
    },
    "ema_cross": {
      "enabled": 0,
      "long": 20,
      "short": 5,
      "output_window": 5,
      "weight": 1.0
    },
    "bollinger_bands": {
      "enabled": 1,
      "avg_type": "sma",
      "period": 20,
      "output_window": 3,
      "std_dev": 2,
      "weight": 1.0
    },
    "week_rule": {
      "enabled": 0,
      "period": 4,
      "output_window": 5,
      "weight": 1.0
    },
    "macd": {
      "enabled": 1,
      "average_type": "ema",
      "short": 5,
      "long": 20,
      "signal_window": 9,
      "output_window": 5,
      "weight": 2.0
    }
  }
}
```

## Output

- **Reports**: Generated CSV files are saved in the `reports/` directory.
- **Logs**: Error logs are saved in the `logs/` directory.
- **Ticker Data**: Fetched stock data is saved in the `ticker_data/` directory.
- **Email**: If an email address is provided and not in backtest mode, the results are sent via email.

## Backtesting

- Enable backtesting with the `-b` flag.
- Specify the start and end dates using `-sd` and `-ed`.
- Backtest results are included in the generated reports.

## Error Handling

- Errors during data fetching or analysis are logged to the `logs/` directory.
- Stocks with errors are skipped without terminating the script.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is licensed under the Apache 2.0 License.

