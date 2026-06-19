"""Tests for market data caching."""

from unittest.mock import patch

import pandas as pd

from stock_simulator.models.quote import StockQuote
from stock_simulator.services import market_data


def test_stock_quote_fields():
    data = pd.DataFrame({"Close": [100.0], "High": [110.0], "Low": [90.0]})
    quote = StockQuote(dataframe=data, current_price=100.0, period_high=110.0, period_low=90.0)
    assert quote.current_price == 100.0
    assert quote.period_high == 110.0
    assert quote.period_low == 90.0


def test_cache_returns_consistent_quote():
    quote = StockQuote(
        dataframe=pd.DataFrame({"Close": [50.0], "High": [55.0], "Low": [45.0]}),
        current_price=50.0,
        period_high=55.0,
        period_low=45.0,
    )
    market_data.clear_cache()
    with patch.object(market_data, "pull_this_week_data", return_value=quote) as mock_pull:
        first = market_data.get_stock_quote("AAPL")
        second = market_data.get_stock_quote("AAPL")
        assert first.current_price == 50.0
        assert second.current_price == 50.0
        assert mock_pull.call_count == 1
