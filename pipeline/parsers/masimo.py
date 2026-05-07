from __future__ import annotations

from pathlib import Path
import pandas as pd

from pipeline.time_utils import to_utc, local_from_utc
from .base import BaseParser


class Parser(BaseParser):
    device_id = "masimo"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        frames: list[pd.DataFrame] = []

        paths = sorted(list(device_dir.glob("*.csv")) + list(device_dir.glob("*.xlsx")))

        for path in paths:
            if path.name.startswith("._"):
                continue

            try:
                if path.suffix.lower() == ".xlsx":
                    df = pd.read_excel(path)
                else:
                    df = pd.read_csv(path)
            except Exception as exc:
                print(f"[masimo] skipped {path.name}: {exc}")
                continue

            if df.empty:
                continue

            timestamp_col = self._find_col(df, ["时间戳", "timestamp", "Timestamp", "TimeStamp"])
            if timestamp_col is None:
                print(f"[masimo] skipped {path.name}: no timestamp column")
                continue

            timestamp_utc = to_utc(df[timestamp_col], local_timezone=self.timezone, unit="s")
            timestamp_local = local_from_utc(timestamp_utc, local_timezone=self.timezone)

            channel_map = self._build_channel_map(df)
            parts = []

            for col, item in channel_map.items():
                channel, unit = item
                values = pd.to_numeric(df[col].replace("--", pd.NA), errors="coerce")

                parts.append(pd.DataFrame({
                    "timestamp_utc": timestamp_utc,
                    "timestamp_local": timestamp_local,
                    "value": values,
                    "channel": channel,
                    "unit": unit,
                    "original_timestamp": df[timestamp_col],
                    "sample_index": range(len(df)),
                }))

            if parts:
                long_df = pd.concat(parts, ignore_index=True)
                frames.append(self.finish(long_df, "vitals", path.name))
            else:
                print(f"[masimo] skipped {path.name}: no usable vital columns")

        return frames

    def _find_col(self, df: pd.DataFrame, candidates: list[str]) -> str | None:
        lowered = {str(c).lower(): c for c in df.columns}

        for name in candidates:
            if name in df.columns:
                return name
            if name.lower() in lowered:
                return lowered[name.lower()]

        return None

    def _build_channel_map(self, df: pd.DataFrame) -> dict[str, tuple[str, str]]:
        mapping: dict[str, tuple[str, str]] = {}

        for col in df.columns:
            name = str(col).strip()
            lower = name.lower()

            if name == "O2 饱和度" or "spo2" in lower or "oxygen" in lower:
                mapping[col] = ("spo2", "%")

            elif name == "血流灌注指数" or "perfusion" in lower or lower == "pi":
                mapping[col] = ("perfusion_index", "")

            elif name == "Pleth 变异性" or "pvi" in lower or "pleth" in lower:
                mapping[col] = ("pleth_variability", "")

            elif name == "每分钟搏动次数":
                mapping[col] = ("pulse_rate", "bpm")

            elif name == "每分钟搏动次数.1":
                # This export has a duplicate Chinese header.
                # The values look like RRp / respiration rate, so we keep it separate.
                mapping[col] = ("respiration_rate_rpp", "brpm")

        return mapping
