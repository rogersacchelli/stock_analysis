import pandas as pd

from constants import BUY, SELL


def portfolio_manager(signals_dict, setup):
    """
        Process raw trading signals for multiple tickers into executed trades, managing portfolio state.

        Parameters:
        - signals_dict: Dict where keys are ticker symbols and values are DataFrames with
                        columns ['date', 'signal', 'price'] (signal: 'buy', 'sell', 'hold')
        - setup: Setup file

        Returns:
        - trades_df: DataFrame with executed trades ['date', 'symbol', 'action', 'price', 'quantity', 'cash_remaining']
        """
    # Initialize portfolio state
    initial_cash = setup['Portfolio']['cash']             # Starting cash balance (default $10,000)
    position_size = setup['Portfolio']['position_size']   # Fraction of cash to use per trade per ticker (default 10%)
    holdings = {}  # Dict to track shares owned per ticker
    trades = []  # List to store trade records
    cash = initial_cash

    # Create a unified timeline of all signals
    all_signals = []
    for ticker, df in signals_dict.items():
        df = df.copy()  # Avoid modifying input
        df.reset_index(inplace=True)
        df['Symbol'] = ticker  # Add ticker column
        all_signals.append(df[['Date', 'Symbol', 'Action', 'Close']])

    # Combine and sort by date
    combined_signals = pd.concat(all_signals, ignore_index=True)
    combined_signals = combined_signals.sort_values('Date').reset_index(drop=True)

    # Iterate through each signal in chronological order
    for index, row in combined_signals.iterrows():
        date = row['Date']
        symbol = row['Symbol']
        signal = row['Action']
        price = row['Close']

        # Initialize holdings for this symbol if not present
        if symbol not in holdings:
            holdings[symbol] = 0

        # Handle BUY signal
        if signal == BUY and holdings[symbol] == 0:  # Only buy if not already holding
            # Calculate how much to spend (fixed % of initial cash or remaining cash)
            trade_value = min(cash, initial_cash * position_size)
            if trade_value >= price:  # Ensure enough cash for at least 1 share
                quantity = trade_value // price  # Integer shares only
                cost = quantity * price
                if cash >= cost:  # Double-check cash sufficiency
                    cash -= cost
                    holdings[symbol] += quantity
                    trades.append({
                        'date': date,
                        'symbol': symbol,
                        'action': 'buy',
                        'price': price,
                        'quantity': quantity,
                        'cash_remaining': cash
                    })

        # Handle SELL signal
        elif signal == SELL and holdings[symbol] > 0:  # Only sell if holding shares
            quantity = holdings[symbol]  # Sell all shares for this symbol
            proceeds = quantity * price
            cash += proceeds
            holdings[symbol] = 0
            trades.append({
                'date': date,
                'symbol': symbol,
                'action': 'sell',
                'price': price,
                'quantity': quantity,
                'cash_remaining': cash
            })

        # 'Hold' or invalid signals do nothing

    # Convert trades list to DataFrame
    trades_df = pd.DataFrame(trades)
    return trades_df


def calculate_trade_metrics(trades_df, setup):
    """
    Calculate trading metrics, handling multiple trades per symbol chronologically.

    Parameters:
    - trades_df: DataFrame with ['date', 'symbol', 'action', 'price', 'quantity', 'cash_remaining']
    - initial_cash: Starting cash balance (default $10,000)

    Returns:
    - dict: Metrics including 'win_ratio', 'total_profit', 'total_return', 'avg_trade_profit', 'max_drawdown'
    """

    initial_cash = setup['Portfolio']['cash']

    # Sort trades by date to ensure chronological order
    trades_df = trades_df.sort_values('date').reset_index(drop=True)

    # Track completed trades
    completed_trades = []
    open_positions = {}  # {symbol: {'price': float, 'quantity': float}}

    # Process trades chronologically
    for _, row in trades_df.iterrows():
        symbol = row['symbol']
        action = row['action']
        price = row['price']
        quantity = row['quantity']

        if action == 'buy':
            if symbol not in open_positions:
                open_positions[symbol] = {'price': price, 'quantity': quantity}
            else:
                # Average price for multiple buys (optional, assuming full sells for now)
                current = open_positions[symbol]
                total_qty = current['quantity'] + quantity
                avg_price = (current['price'] * current['quantity'] + price * quantity) / total_qty
                open_positions[symbol] = {'price': avg_price, 'quantity': total_qty}

        elif action == 'sell' and symbol in open_positions:
            buy_price = open_positions[symbol]['price']
            buy_qty = open_positions[symbol]['quantity']
            sell_qty = quantity
            if sell_qty <= buy_qty:  # Full or partial sell
                profit = (price - buy_price) * sell_qty
                completed_trades.append({
                    'symbol': symbol,
                    'profit': profit,
                    'quantity': sell_qty,
                    'is_win': price > buy_price
                })
                if sell_qty == buy_qty:
                    del open_positions[symbol]
                else:
                    open_positions[symbol]['quantity'] -= sell_qty

    # Calculate metrics
    trades_summary = pd.DataFrame(completed_trades)
    if trades_summary.empty:
        return {
            'win_ratio': 0.0, 'total_profit': 0.0, 'total_return': 0.0,
            'avg_trade_profit': 0.0, 'max_drawdown': 0.0
        }

    total_trades = len(trades_summary)
    winning_trades = trades_summary['is_win'].sum()
    win_ratio = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
    total_profit = trades_summary['profit'].sum()
    total_return = (total_profit / initial_cash) * 100 if initial_cash > 0 else 0.0
    avg_trade_profit = total_profit / total_trades if total_trades > 0 else 0.0

    # Maximum Drawdown (based on cash_remaining only for now)
    equity_curve = trades_df['cash_remaining'].tolist()
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        drawdown = (peak - equity) / peak * 100 if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    return {
        'win_ratio': win_ratio,
        'total_profit': total_profit,
        'total_return': total_return,
        'avg_trade_profit': avg_trade_profit,
        'max_drawdown': max_drawdown
    }

