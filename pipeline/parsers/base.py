from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


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

    def standardize(self, df: pd.DataFrame, signal_type: str, source_file: str) -> pd.DataFrame:
        df = df.copy()
        df["participant_id"] = self.participant_id
        df["session_id"] = self.session_id
        df["device_id"] = self.device_id
        df["signal_type"] = signal_type
        df["source_file"] = source_file
        df.setdefault("channel", signal_type)
        df.setdefault("unit", "")
        df.setdefault("quality_flag", 0)
        df.setdefault("quality_reason", "")
        return df
