from __future__ import annotations

from pathlib import Path
import pandas as pd

from pipeline.time_utils import to_utc
from .base import BaseParser


class Parser(BaseParser):
    device_id = "polar"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        frames = []

        for path in sorted(device_dir.glob("*.txt")):
            name = path.name.lower()

            try:
                df = pd.read_csv(path, sep=";", engine="python")
            except Exception as exc:
                print(f"[polar] skipped {path.name}: {exc}")
                continue

            if "Phone timestamp" not in df.columns:
                continue

            timestamp_utc = to_utc(df["Phone timestamp"], local_timezone=self.timezone)
            timestamp_local = pd.to_datetime(df["Phone timestamp"], errors="coerce")

            if "ecg" in name:
                value_col = next((c for c in df.columns if "ecg" in c.lower()), None)
                if value_col is None:
                    continue

                out = pd.DataFrame({
                    "timestamp_utc": timestamp_utc,
                    "timestamp_local": timestamp_local,
                    "value": pd.to_numeric(df[value_col], errors="coerce"),
                    "channel": "ecg",
                    "unit": "uV",
                    "original_timestamp": df["Phone timestamp"],
                    "sample_index": range(len(df)),
                })
                frames.append(self.finish(out, "ecg", path.name, "uV"))

            elif "acc" in name:
                acc_cols = [c for c in df.columns if c in ["X [mg]", "Y [mg]", "Z [mg]"]]
                parts = []

                for col in acc_cols:
                    ch = col.split()[0].lower()
                    parts.append(pd.DataFrame({
                        "timestamp_utc": timestamp_utc,
                        "timestamp_local": timestamp_local,
                        "value": pd.to_numeric(df[col], errors="coerce"),
                        "channel": ch,
                        "unit": "mg",
                        "original_timestamp": df["Phone timestamp"],
                        "sample_index": range(len(df)),
                    }))

                if parts:
                    frames.append(self.finish(pd.concat(parts, ignore_index=True), "acc", path.name, "mg"))

        return frames
