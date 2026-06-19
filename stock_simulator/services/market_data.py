"""Yahoo Finance market data with thread-safe caching."""

from __future__ import annotations

import datetime
import threading
import time
from typing import Any

import pandas as pd
import yfinance as yf

from stock_simulator.models.quote import StockQuote

_cache: dict[str, dict[str, Any]] = {}
_cache_lock = threading.Lock()
DEFAULT_CACHE_DURATION = 900  # 15 minutes


def _normalize_history(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize a yfinance history DataFrame to a consistent column layout."""
    if data.empty:
        return data
    data = data.copy()
    data.reset_index(inplace=True)
    datetime_col = "Datetime" if "Datetime" in data.columns else "Date"
    data["Date"] = pd.to_datetime(data[datetime_col]).dt.date
    data["Time"] = pd.to_datetime(data[datetime_col]).dt.time
    columns = ["Date", "Time", "Open", "High", "Low", "Close", "Volume"]
    available = [col for col in columns if col in data.columns]
    return data[available]


def _quote_from_dataframe(data: pd.DataFrame) -> StockQuote:
    """Build a StockQuote from normalized OHLCV data."""
    if data.empty:
        raise ValueError("No market data available for the requested symbol.")
    current_price = float(data["Close"].iloc[-1])
    period_high = float(data["High"].max())
    period_low = float(data["Low"].min())
    return StockQuote(
        dataframe=data,
        current_price=current_price,
        period_high=period_high,
        period_low=period_low,
    )


def pull_this_week_data(stock_symbol: str) -> StockQuote:
    """Fetch the last week's 5-minute bars for a symbol."""
    current_time = datetime.datetime.now()
    one_week_ago = current_time - datetime.timedelta(days=7)
    ticker = yf.Ticker(stock_symbol)
    data = ticker.history(interval="5m", start=one_week_ago, end=current_time)
    data = _normalize_history(data)
    return _quote_from_dataframe(data)


def get_stock_quote(stock_symbol: str, cache_duration: int = DEFAULT_CACHE_DURATION) -> StockQuote:
    """Return a cached or freshly fetched quote for a symbol."""
    symbol = stock_symbol.upper()
    current_time = time.time()

    with _cache_lock:
        cached = _cache.get(symbol)
        if cached and current_time - cached["timestamp"] <= cache_duration:
            return cached["quote"]

    quote = pull_this_week_data(symbol)

    with _cache_lock:
        _cache[symbol] = {"quote": quote, "timestamp": current_time}

    return quote


def get_max_stock_value(ticker: str, start_date: str | datetime.datetime, end_date: str | datetime.datetime) -> float:
    """Return the maximum closing price for a symbol over a date range."""
    stock_data = yf.download(
        ticker,
        interval="5m",
        start=start_date,
        end=end_date,
        progress=False,
        auto_adjust=True,
    )
    if stock_data.empty:
        return get_stock_quote(ticker).current_price
    close_col = "Close" if "Close" in stock_data.columns else "Adj Close"
    return float(stock_data[close_col].max())


def get_min_stock_value(ticker: str, start_date: str | datetime.datetime, end_date: str | datetime.datetime) -> float:
    """Return the minimum closing price for a symbol over a date range."""
    stock_data = yf.download(
        ticker,
        interval="5m",
        start=start_date,
        end=end_date,
        progress=False,
        auto_adjust=True,
    )
    if stock_data.empty:
        return get_stock_quote(ticker).current_price
    close_col = "Close" if "Close" in stock_data.columns else "Adj Close"
    return float(stock_data[close_col].min())


def clear_cache() -> None:
    """Clear the in-memory quote cache (used in tests)."""
    with _cache_lock:
        _cache.clear()
