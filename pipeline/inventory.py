from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def collect_inventory(session_dir: Path, device_names: Iterable[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for device in device_names:
        device_dir = session_dir / device
        if not device_dir.exists():
            rows.append({
                "device": device,
                "status": "missing_folder",
                "source_file": "",
                "suffix": "",
                "size_bytes": 0,
            })
            continue
        files = [p for p in device_dir.rglob("*") if p.is_file() and not p.name.startswith("._") and p.name != ".DS_Store"]
        if not files:
            rows.append({
                "device": device,
                "status": "empty_folder",
                "source_file": "",
                "suffix": "",
                "size_bytes": 0,
            })
            continue
        for p in files:
            rows.append({
                "device": device,
                "status": "found",
                "source_file": str(p.relative_to(session_dir)),
                "suffix": p.suffix.lower(),
                "size_bytes": p.stat().st_size,
            })
    return pd.DataFrame(rows)
