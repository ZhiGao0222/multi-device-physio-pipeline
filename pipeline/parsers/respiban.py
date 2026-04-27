from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from pipeline.time_utils import to_utc
from .base import BaseParser


class Parser(BaseParser):
    device_id = "respiban"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        frames = []

        for path in sorted(device_dir.glob("*.txt")):
            try:
                header = self._read_header(path)
                col_names = self._columns_from_header(header)
                df = pd.read_csv(path, sep=r"\s+", comment="#", header=None, names=col_names, engine="python")
            except Exception as exc:
                print(f"[respiban] skipped {path.name}: {exc}")
                continue

            if df.empty or "RESPI" not in df.columns:
                continue

            if "timestamp" in df.columns:
                timestamp_utc = to_utc(df["timestamp"], local_timezone=self.timezone, unit="ms")
                signal = "respiration_timestamped"
                original = df["timestamp"]
            else:
                timestamp_utc = self._timestamps_from_nseq(df, header)
                signal = "respiration_raw_nseq"
                original = df.iloc[:, 0]

            timestamp_local = pd.to_datetime(timestamp_utc, utc=True).dt.tz_convert(self.timezone)

            out = pd.DataFrame({
                "timestamp_utc": timestamp_utc,
                "timestamp_local": timestamp_local,
                "value": pd.to_numeric(df["RESPI"], errors="coerce"),
                "channel": "RESPI",
                "unit": "raw",
                "original_timestamp": original,
                "sample_index": range(len(df)),
            })

            frames.append(self.finish(out, signal, path.name, "raw"))

        return frames

    def _read_header(self, path: Path) -> dict:
        header = {}
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("# {"):
                    header = json.loads(line[2:].strip())
                if "EndOfHeader" in line:
                    break
        return header

    def _columns_from_header(self, header: dict) -> list[str]:
        try:
            first = next(iter(header.values()))
            return first.get("column", ["timestamp", "RESPI"])
        except Exception:
            return ["timestamp", "RESPI"]

    def _timestamps_from_nseq(self, df: pd.DataFrame, header: dict) -> pd.Series:
        try:
            first = next(iter(header.values()))
            start = pd.to_datetime(f"{first['date']} {first['time']}", errors="coerce")
            fs = float(first.get("sampling rate", 400))
        except Exception:
            start = pd.Timestamp.now()
            fs = 400.0

        nseq = pd.to_numeric(df.iloc[:, 0], errors="coerce").ffill().fillna(1)
        seconds = (nseq - nseq.iloc[0]) / fs
        return pd.to_datetime(start + pd.to_timedelta(seconds, unit="s")).dt.tz_localize(self.timezone).dt.tz_convert("UTC")
