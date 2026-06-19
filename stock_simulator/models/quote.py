"""Stock quote data model."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StockQuote:
    """Market quote for a single stock symbol."""

    dataframe: pd.DataFrame
    current_price: float
    period_high: float
    period_low: float
