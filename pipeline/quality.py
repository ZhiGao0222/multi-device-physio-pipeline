from __future__ import annotations

import pandas as pd


def add_basic_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add baseline quality columns without deleting records."""
    out = df.copy()
    if "quality_flag" not in out.columns:
        out["quality_flag"] = 0
    if "quality_reason" not in out.columns:
        out["quality_reason"] = ""

    if "timestamp_utc" in out.columns:
        bad_ts = pd.to_datetime(out["timestamp_utc"], errors="coerce").isna()
        out.loc[bad_ts, "quality_flag"] = 2
        out.loc[bad_ts, "quality_reason"] = out.loc[bad_ts, "quality_reason"].astype(str) + ";missing_or_invalid_timestamp"

        ts = pd.to_datetime(out["timestamp_utc"], utc=True, errors="coerce")
        non_mono = ts.diff().dt.total_seconds().fillna(0) < 0
        out.loc[non_mono, "quality_flag"] = 2
        out.loc[non_mono, "quality_reason"] = out.loc[non_mono, "quality_reason"].astype(str) + ";timestamp_not_monotonic"

    if "value" in out.columns:
        bad_value = out["value"].isna()
        out.loc[bad_value, "quality_flag"] = 2
        out.loc[bad_value, "quality_reason"] = out.loc[bad_value, "quality_reason"].astype(str) + ";missing_value"

    return out
