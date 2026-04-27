from __future__ import annotations

from pathlib import Path

import pandas as pd


def summarize_processed_files(processed_dir: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for p in processed_dir.glob("*.parquet"):
        try:
            df = pd.read_parquet(p, columns=["timestamp_utc", "quality_flag"])
            ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
            rows.append({
                "file": p.name,
                "n_rows": len(df),
                "start_utc": ts.min(),
                "end_utc": ts.max(),
                "valid_rows": int((df.get("quality_flag", 0) == 0).sum()) if "quality_flag" in df else None,
            })
        except Exception as exc:
            rows.append({"file": p.name, "error": str(exc)})
    return pd.DataFrame(rows)


def overlap_summary(summary: pd.DataFrame) -> dict:
    if summary.empty or "start_utc" not in summary or "end_utc" not in summary:
        return {"status": "no_processed_files"}
    valid = summary.dropna(subset=["start_utc", "end_utc"])
    if valid.empty:
        return {"status": "no_valid_time_ranges"}
    overlap_start = valid["start_utc"].max()
    overlap_end = valid["end_utc"].min()
    return {
        "status": "overlap_found" if overlap_start < overlap_end else "no_full_overlap",
        "overlap_start_utc": str(overlap_start),
        "overlap_end_utc": str(overlap_end),
        "duration_seconds": float((overlap_end - overlap_start).total_seconds()) if overlap_start < overlap_end else 0.0,
    }
