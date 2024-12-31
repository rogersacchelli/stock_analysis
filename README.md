# Stock Analysis Tool

This Stock Analysis Tool is a Python-based application designed to analyze stock data using various techniques. It generates detailed reports, optionally sending results via email.

## Features

- Fetch historical stock data using Yahoo Finance.
- Analyze stock data for:
  - SMA (Simple Moving Average) crossings.
  - EMA (Exponential Moving Average) crossings.
  - Bollinger Band.
  - 4 Week Rule.
  - MACD.
- Generate reports in CSV format.
- Optionally send analysis reports via email.

## Requirements

- Python 3.8+
- Required Python libraries:
  - `yfinance`
  - `pandas`
  - `argparse`
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

3. Ensure the `reports/` and `logs/` directories exist:
   ```bash
   mkdir -p reports logs
   ```

## Usage

### Command-Line Arguments

- `-i`, `--input`: Input file containing stock tickers in JSON format (required).
- `-e`, `--email`: Email address to send results (optional).
- `-c`, `--config`: Configuration file for application settings (required).
- `-a`, `--analysis`: Analysis definition file (required).
- `-l`, `--limit`: Limit the number of stocks processed (optional, default: 50).

### Example Command

```bash
python main.py \
  -i tickers.json \
  -e user@example.com \
  -c config.json \
  -a analysis.json \
  -l 100
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
    "sma_cross": {
      "enabled": true,
      "short": 20,
      "long": 50,
      "eval_window": 5
    },
    "ema_cross": {
      "enabled": true,
      "short": 12,
      "long": 26,
      "eval_window": 5
    },
    "bollinger_bands": {
      "enabled": true,
      "period": 20,
      "eval_window": 5,
      "avg_type": "SMA",
      "std_dev": 2
    },
    "week_rule": {
      "enabled": true,
      "period": 14,
      "eval_window": 5
    }
  }
}
```

## Output

- **Reports**: Generated CSV files are saved in the `reports/` directory.
- **Logs**: Error logs are saved in the `logs/` directory.
- **Email**: If an email address is provided, the results are sent via email.

## Error Handling

- Errors during data fetching or analysis are logged to the `logs/` directory.
- Stocks with errors are skipped without terminating the script.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is licensed under the Apache License 2.0.

