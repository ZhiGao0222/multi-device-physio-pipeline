from __future__ import annotations

from pathlib import Path
import pandas as pd

from pipeline.time_utils import to_utc
from .base import BaseParser


class Parser(BaseParser):
    device_id = "muse"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        frames = []

        for path in sorted(device_dir.glob("*.csv")):
            try:
                df = pd.read_csv(path)
            except Exception as exc:
                print(f"[muse] skipped {path.name}: {exc}")
                continue

            if "TimeStamp" not in df.columns:
                continue

            timestamp_utc = to_utc(df["TimeStamp"], local_timezone=self.timezone)
            timestamp_local = pd.to_datetime(df["TimeStamp"], errors="coerce")

            skip = {"TimeStamp", "Elements"}
            numeric_cols = [
                c for c in df.columns
                if c not in skip and pd.to_numeric(df[c], errors="coerce").notna().any()
            ]

            parts = []
            for col in numeric_cols:
                parts.append(pd.DataFrame({
                    "timestamp_utc": timestamp_utc,
                    "timestamp_local": timestamp_local,
                    "value": pd.to_numeric(df[col], errors="coerce"),
                    "channel": col,
                    "unit": "",
                    "original_timestamp": df["TimeStamp"],
                    "sample_index": range(len(df)),
                }))

            if parts:
                frames.append(self.finish(pd.concat(parts, ignore_index=True), "muse_features", path.name))

        return frames
