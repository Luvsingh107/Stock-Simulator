"""Command-line interpreter for the Stock Simulator."""

from __future__ import annotations

import logging

from stock_simulator.models.user import User
from stock_simulator.services import market_data, portfolio, trading
from stock_simulator.utils.validation import parse_non_negative_float, parse_positive_int

logger = logging.getLogger(__name__)

HELP_TEXT = """
Commands:
  buy SYMBOL QTY [PRICE]     Buy shares (market if PRICE omitted or 0)
  sell SYMBOL QTY [PRICE]    Sell shares (market if PRICE omitted or 0)
  cancel buy|sell NUMBER     Cancel a pending order (see portfolio for numbers)
  portfolio                  Show holdings, orders, and analytics
  cash                       Show cash balance
  price SYMBOL               Show current stock price
  history [N]                Show last N transactions (default 10)
  orders [N]                 Show last N completed/cancelled orders (default 10)
  help                       Show this help message
  quit / exit                Save and exit the simulator

Tip: Omit PRICE or set it to 0 to trade at the current market price.
""".strip()


class CommandResult:
    """Result of handling a CLI command."""

    def __init__(self, should_exit: bool = False) -> None:
        self.should_exit = should_exit


def _parse_trade_args(words: list[str]) -> tuple[str, int, float] | None:
    """Parse symbol, quantity, and optional price from command words."""
    if len(words) < 3:
        print("Usage: buy|sell SYMBOL QTY [PRICE]")
        return None

    symbol = words[1].upper()
    amount, err = parse_positive_int(words[2])
    if err:
        print(err)
        return None

    price = 0.0
    if len(words) >= 4:
        parsed_price, err = parse_non_negative_float(words[3])
        if err:
            print(err)
            return None
        price = parsed_price

    return symbol, amount, price


def handle_command(command: str, user: User) -> CommandResult:
    """
    Parse and execute a user command.

    Returns CommandResult indicating whether the application should exit.
    """
    words = command.strip().split()
    if not words:
        return CommandResult()

    cmd = words[0].lower()

    match cmd:
        case "price":
            if len(words) != 2:
                print("Usage: price SYMBOL")
                return CommandResult()
            symbol = words[1].upper()
            try:
                quote = market_data.get_stock_quote(symbol)
                print(f"Price of {symbol}: ${quote.current_price:.2f}")
            except (ValueError, KeyError) as exc:
                print(f"Could not fetch price for {symbol}: {exc}")
            return CommandResult()

        case "buy":
            args = _parse_trade_args(words)
            if args is None:
                return CommandResult()
            symbol, amount, price = args
            if price == 0:
                try:
                    quote = market_data.get_stock_quote(symbol)
                    total = quote.current_price * amount
                    confirm = input(f"Total price will be ${total:.2f}. Confirm? (Y/N)\n\n> ").strip().upper()
                    if confirm != "Y":
                        print("Purchase cancelled.")
                        return CommandResult()
                except (ValueError, KeyError) as exc:
                    print(f"Could not fetch price for {symbol}: {exc}")
                    return CommandResult()
            trading.buy_stocks(user, amount, price, symbol)
            return CommandResult()

        case "sell":
            args = _parse_trade_args(words)
            if args is None:
                return CommandResult()
            symbol, amount, price = args
            trading.sell_stocks(user, amount, price, symbol)
            return CommandResult()

        case "portfolio":
            portfolio.display_portfolio(user)
            return CommandResult()

        case "cash":
            portfolio.display_cash(user)
            return CommandResult()

        case "history":
            limit = 10
            if len(words) > 1:
                parsed, err = parse_positive_int(words[1], "limit")
                if err:
                    print(err)
                    return CommandResult()
                limit = parsed
            portfolio.display_history(user, limit)
            return CommandResult()

        case "orders":
            limit = 10
            if len(words) > 1:
                parsed, err = parse_positive_int(words[1], "limit")
                if err:
                    print(err)
                    return CommandResult()
                limit = parsed
            portfolio.display_order_history(user, limit)
            return CommandResult()

        case "help":
            print(HELP_TEXT)
            return CommandResult()

        case "cancel":
            if len(words) != 3:
                print("Usage: cancel buy|sell NUMBER")
                return CommandResult()
            order_type = words[1].lower()
            if order_type not in ("buy", "sell"):
                print("Order type must be 'buy' or 'sell'.")
                return CommandResult()
            order_num, err = parse_positive_int(words[2], "order number")
            if err:
                print(err)
                return CommandResult()
            trading.cancel_order(user, order_type, order_num)
            return CommandResult()

        case "quit" | "exit":
            return CommandResult(should_exit=True)

        case _:
            print(f"Unknown command '{words[0]}'. Type 'help' for available commands.")
            return CommandResult()
