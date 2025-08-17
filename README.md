# Stock Trading Automation System

## Overview
This project is a Python-based stock trading automation system designed to analyze stock market data, generate trading signals, and manage portfolios for automated trading. It leverages technical indicators such as Simple Moving Averages (SMA), Exponential Moving Averages (EMA), Relative Strength Index (RSI), and others to identify trading opportunities. The system supports backtesting, risk management, and email notifications for stock recommendations, making it a powerful tool for traders, developers, and researchers interested in algorithmic trading.

The project is modular, extensible, and highly configurable via two JSON files: `setup.json` for analysis and trading parameters, and `settings.json` for system settings like email configuration. It integrates with pandas for data manipulation, tabulate for reporting, and other libraries for technical analysis.

## Features
- **Technical Analysis**: Supports indicators like SMA/EMA crossings, RSI, Bollinger Bands, MACD, Stochastic Oscillator, and On-Balance Volume (OBV).
- **Portfolio Management**: Manages trades with customizable position sizing and cash allocation.
- **Risk Management**: Includes stop-loss mechanisms, Sharpe Ratio, and Sortino Ratio for risk assessment.
- **Backtesting**: Evaluates trading strategies against historical data with performance metrics.
- **Email Notifications**: Sends HTML-formatted stock recommendations using settings from `settings.json`.
- **Configurable Setup**: 
  - `setup.json`: Defines tickers, analysis parameters, risk thresholds, and portfolio settings.
  - `settings.json`: Configures system settings, such as email server details.
- **Modular Design**: Organized into separate modules (`main.py`, `trend.py`, `momentum.py`) for easy maintenance and extension.

## Project Structure
- **`main.py`**: Core script that orchestrates the trading system, including argument parsing, signal generation, backtesting, and email notifications.
- **`trend.py`**: Implements trend-based technical indicators (e.g., SMA/EMA crossings, Bollinger Bands, MACD, Stochastic Oscillator).
- **`momentum.py`**: Implements momentum-based indicators like RSI and ADX.
- **`setup.json`**: Configuration file for defining tickers, analysis parameters, risk settings, and portfolio details.
- **`settings.json`**: Configuration file for system settings, such as email server details (e.g., SMTP server, port, credentials).
- **Other Modules** (assumed, not provided in the code):
  - `features_extraction.py`: Handles feature extraction for machine learning or additional analysis.
  - `portfolio_manager.py`: Manages trading logic and portfolio metrics.
  - `risk.py`: Implements risk management strategies.
  - `utils/`:
    - `analysis.py`: Utility functions for stock signal generation and analysis.
    - `argument_parsing.py`: Parses command-line arguments.
    - `mail.py`: Handles email notifications using `settings.json`.
    - `utils.py`: General utility functions (e.g., directory creation, hashing).

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/rogersacchelli/stock_analysis.git
   cd stock_analysis
   ```

2. **Install Dependencies**:
   Ensure you have Python 3.11+ installed. Install required packages using:
   ```bash
   pip install -r requirements.txt
   ```
   Example `requirements.txt`:
   ```
   pandas
   numpy
   scipy
   tabulate
   ```

3. **Configure the System**:
   - **Update `setup.json`**: Specify tickers, analysis parameters (e.g., SMA periods, RSI thresholds), risk settings, and portfolio details.
   - **Update `settings.json`**: Configure email settings (e.g., SMTP server, port, credentials) for notifications.
     - Example: Set `from_email`, `from_password`, `smtp_server`, and `smtp_port` for your email provider.
     - Note: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) for `from_password`.

4. **Run the System**:
   ```bash
   python main.py --config settings.json --setup setup.json stocks/sp500_top100_volume.json --email your-email@example.com
   ```
   Use `python main.py --help` for a full list of command-line arguments.

## Usage
- **Run Analysis**: Execute `main.py` with appropriate arguments to generate trading signals and recommendations.
  ```bash
  python main.py --config settings.json --setup setup.json --backtest --start_date 2024-01-01 --end_date 2024-12-31
  ```
- **Backtesting**: Enable backtesting with the `--backtest` flag to evaluate strategy performance.
- **Email Notifications**: Use the `--email` flag to receive HTML-formatted recommendations, configured via `settings.json`.
- **Customization**:
  - Modify `setup.json` to enable/disable indicators, adjust periods, or change risk thresholds.
  - Update `settings.json` to configure email settings or other system parameters.

## Example Output
- **Console Output**: Tabulated stock recommendations (Symbol, Date, Close, Action) and backtest metrics.
- **Email Output**: HTML table with recommended trades, sent using the email configuration in `settings.json`.
- **Reports**: Saved in the `reports/` directory.

## Contributing
We warmly welcome contributions to make this project even better! Here are some ways you can contribute:
- **Add New Indicators**: Extend `trend.py` or `momentum.py` with additional technical indicators (e.g., VWAP, Ichimoku Cloud).
- **Enhance Risk Management**: Improve `risk.py` with advanced strategies (e.g., Value-at-Risk, volatility-based stops).
- **Optimize Performance**: Enhance efficiency for large datasets or real-time processing.
- **Integrate Data Sources**: Add support for real-time market data APIs (e.g., Yahoo Finance, Alpha Vantage).
- **Add Visualizations**: Implement charts for signals and portfolio performance (e.g., using Matplotlib or Plotly).
- **Improve Email Templates**: Enhance HTML formatting in `mail.py` for richer notifications.
- **Bug Fixes**: Identify and resolve issues in existing functionality.

### How to Contribute
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to your fork (`git push origin feature/your-feature`).
5. Open a Pull Request with a clear description of your changes.

Please adhere to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/0/code_of_conduct/) and follow PEP 8 style guidelines for Python code.

## Roadmap
- Integrate real-time data feeds for live trading.
- Add machine learning models for predictive signal generation.
- Develop a web-based dashboard for visualizing signals and performance.
- Support options and futures trading.
- Enhance email notifications with embedded charts and detailed metrics.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact
For questions, suggestions, or issues, please open a GitHub issue or contact the maintainers at [roger.sacchelli@gmail.com](mailto:roger.sacchelli@gmail.com).

## Acknowledgements
- Built with [pandas](https://pandas.pydata.org/), [numpy](https://numpy.org/), [scipy](https://scipy.org/), and [tabulate](https://pypi.org/project/tabulate/).
- Inspired by the open-source algorithmic trading community.

Thank you for your interest in this project! Join us in building a robust and feature-rich trading system.
