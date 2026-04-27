from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("project_root", ".")
    cfg["project_root"] = str(Path(cfg["project_root"]).expanduser().resolve())
    return cfg


def get_path(cfg: dict[str, Any], key: str) -> Path:
    rel = cfg.get("paths", {}).get(key, key)
    return Path(cfg["project_root"]) / rel
