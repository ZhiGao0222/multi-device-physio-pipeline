from __future__ import annotations

from pathlib import Path
import pandas as pd

from pipeline.time_utils import to_utc
from .base import BaseParser


class Parser(BaseParser):
    device_id = "empatica"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        frames = []

        for path in sorted(device_dir.glob("*.csv")):
            if "metadata" in path.name.lower():
                continue

            try:
                df = pd.read_csv(path)
            except Exception as exc:
                print(f"[empatica] skipped {path.name}: {exc}")
                continue

            if "timestamp_iso" not in df.columns:
                continue

            signal = self._signal_from_name(path.name)
            timestamp_utc = to_utc(df["timestamp_iso"], local_timezone=self.timezone)
            timestamp_local = pd.to_datetime(timestamp_utc, utc=True).dt.tz_convert(self.timezone)

            if "missing_value_reason" in df.columns:
                reason = df["missing_value_reason"].fillna("").astype(str)
            else:
                reason = pd.Series([""] * len(df))

            value_cols = [
                c for c in df.columns
                if c not in {"timestamp_unix", "timestamp_iso", "participant_full_id", "missing_value_reason"}
                and pd.to_numeric(df[c], errors="coerce").notna().any()
            ]

            parts = []
            for col in value_cols:
                qflag = reason.ne("").astype("int8") * 2
                qreason = reason.where(reason.eq(""), "empatica_missing:" + reason)

                parts.append(pd.DataFrame({
                    "timestamp_utc": timestamp_utc,
                    "timestamp_local": timestamp_local,
                    "value": pd.to_numeric(df[col], errors="coerce"),
                    "channel": col,
                    "unit": self._unit_for(col),
                    "quality_flag": qflag,
                    "quality_reason": qreason,
                    "original_timestamp": df["timestamp_iso"],
                }))

            if parts:
                frames.append(self.finish(pd.concat(parts, ignore_index=True), signal, path.name))

        return frames

    def _signal_from_name(self, name: str) -> str:
        stem = Path(name).stem
        parts = stem.split("_")
        raw = parts[-1] if parts else stem
        return raw.replace("-", "_")

    def _unit_for(self, col: str) -> str:
        col_l = col.lower()
        if "bpm" in col_l:
            return "bpm"
        if "celsius" in col_l:
            return "degC"
        if "usiemens" in col_l:
            return "uS"
        if "brpm" in col_l:
            return "brpm"
        if col_l.endswith("_g"):
            return "g"
        if "ms" in col_l:
            return "ms"
        if "percentage" in col_l:
            return "%"
        return ""
