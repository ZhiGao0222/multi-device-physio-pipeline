from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.time_utils import local_from_utc


class BaseParser(ABC):
    device_id: str = "base"

    def __init__(self, cfg: dict[str, Any], participant_id: str, session_id: str):
        self.cfg = cfg
        self.participant_id = participant_id
        self.session_id = session_id
        self.timezone = cfg.get("timezone", "America/New_York")

    @abstractmethod
    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        raise NotImplementedError

    def finish(self, df: pd.DataFrame, signal_type: str, source_file: str, unit: str = "") -> pd.DataFrame:
        out = df.copy()
        out["participant_id"] = self.participant_id
        out["session_id"] = self.session_id
        out["device_id"] = self.device_id
        out["signal_type"] = signal_type
        out["source_file"] = source_file

        if "timestamp_local" not in out.columns and "timestamp_utc" in out.columns:
            out["timestamp_local"] = local_from_utc(out["timestamp_utc"], local_timezone=self.timezone)
        if "channel" not in out.columns:
            out["channel"] = signal_type
        if "unit" not in out.columns:
            out["unit"] = unit
        if "quality_flag" not in out.columns:
            out["quality_flag"] = 0
        if "quality_reason" not in out.columns:
            out["quality_reason"] = ""

        cols = [
            "participant_id", "session_id", "device_id", "signal_type", "channel",
            "timestamp_utc", "timestamp_local", "value", "unit",
            "quality_flag", "quality_reason", "source_file",
        ]
        extras = [c for c in out.columns if c not in cols]
        return out[cols + extras]
