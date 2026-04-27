from __future__ import annotations

from pathlib import Path
import pandas as pd

from pipeline.time_utils import to_utc
from .base import BaseParser


class Parser(BaseParser):
    device_id = "geneactiv"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        frames = []

        for path in sorted(device_dir.glob("*.csv")):
            try:
                df = pd.read_csv(
                    path,
                    skiprows=100,
                    header=None,
                    names=["time", "x", "y", "z", "lux", "button", "temperature"],
                )
            except Exception as exc:
                print(f"[geneactiv] skipped {path.name}: {exc}")
                continue

            if df.empty:
                continue

            ts_str = df["time"].astype(str).str.replace(r":(\d{3})$", r".\1", regex=True)
            timestamp_utc = to_utc(ts_str, local_timezone=self.timezone)
            timestamp_local = pd.to_datetime(ts_str, errors="coerce")

            groups = [
                ("actigraphy", {"x": "g", "y": "g", "z": "g"}),
                ("light", {"lux": "lux"}),
                ("button", {"button": ""}),
                ("temperature", {"temperature": "degC"}),
            ]

            for signal, cols in groups:
                parts = []
                for col, unit in cols.items():
                    parts.append(pd.DataFrame({
                        "timestamp_utc": timestamp_utc,
                        "timestamp_local": timestamp_local,
                        "value": pd.to_numeric(df[col], errors="coerce"),
                        "channel": col,
                        "unit": unit,
                        "original_timestamp": df["time"],
                        "sample_index": range(len(df)),
                    }))

                frames.append(self.finish(pd.concat(parts, ignore_index=True), signal, path.name))

        return frames
