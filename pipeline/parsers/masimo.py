from __future__ import annotations

from pathlib import Path
import pandas as pd

from pipeline.time_utils import to_utc, local_from_utc
from .base import BaseParser


class Parser(BaseParser):
    device_id = "masimo"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        frames = []

        for path in sorted(device_dir.glob("*.xlsx")):
            try:
                df = pd.read_excel(path)
            except Exception as exc:
                print(f"[masimo] skipped {path.name}: {exc}")
                continue

            if "时间戳" not in df.columns:
                continue

            timestamp_utc = to_utc(df["时间戳"], local_timezone=self.timezone, unit="s")
            timestamp_local = local_from_utc(timestamp_utc, local_timezone=self.timezone)

            mapping = {}
            for col in df.columns:
                if col == "O2 饱和度":
                    mapping[col] = ("spo2", "%")
                elif col == "血流灌注指数":
                    mapping[col] = ("perfusion_index", "")
                elif col == "Pleth 变异性":
                    mapping[col] = ("pleth_variability", "")
                elif "搏动" in str(col):
                    mapping[col] = ("pulse_rate", "bpm")

            parts = []
            for col, item in mapping.items():
                channel, unit = item
                vals = pd.to_numeric(df[col].replace("--", pd.NA), errors="coerce")
                parts.append(pd.DataFrame({
                    "timestamp_utc": timestamp_utc,
                    "timestamp_local": timestamp_local,
                    "value": vals,
                    "channel": channel,
                    "unit": unit,
                    "original_timestamp": df["时间戳"],
                    "sample_index": range(len(df)),
                }))

            if parts:
                frames.append(self.finish(pd.concat(parts, ignore_index=True), "vitals", path.name))

        return frames
