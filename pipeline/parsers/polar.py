from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import BaseParser


class Parser(BaseParser):
    device_id = "polar"

    def parse(self, device_dir: Path) -> list[pd.DataFrame]:
        """Placeholder parser for polar.

        Next step: implement device-specific parsing after confirming export format.
        Return a list of standardized dataframes with at least:
        timestamp_utc, timestamp_local, value, channel, unit, quality_flag, quality_reason.
        """
        return []
