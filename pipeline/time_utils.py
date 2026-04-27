from __future__ import annotations

from datetime import timezone
from typing import Optional

import pandas as pd
from zoneinfo import ZoneInfo


def to_utc(series: pd.Series, *, local_timezone: str = "America/New_York", unit: Optional[str] = None) -> pd.Series:
    """Convert timestamps to UTC.

    Handles ISO strings, local naive strings, and numeric epochs when unit is provided.
    """
    if unit:
        ts = pd.to_datetime(series, unit=unit, utc=True, errors="coerce")
        return ts

    ts = pd.to_datetime(series, errors="coerce")
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize(ZoneInfo(local_timezone), nonexistent="NaT", ambiguous="NaT")
    return ts.dt.tz_convert(timezone.utc)


def local_from_utc(series: pd.Series, *, local_timezone: str = "America/New_York") -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce").dt.tz_convert(ZoneInfo(local_timezone))
