"""
pilot_pipeline.py
=================
Multi-Device Physiological Data Pipeline (All-in-One)
Author: Zhi Gao
Date: March 2026

Usage:
    Step 1 - Initialize project:
        python pilot_pipeline.py init --root E:/pilot_study

    Step 2 - Add a session:
        python pilot_pipeline.py add-session --root E:/pilot_study --sub sub-001 --ses ses-001

    Step 3 - Run pipeline (after placing raw data and creating session_log.json):
        python pilot_pipeline.py run --root E:/pilot_study --sub sub-001 --ses ses-001

    Step 4 - Run quality check only:
        python pilot_pipeline.py quality --root E:/pilot_study --sub sub-001 --ses ses-001
"""

import os
import sys
import json
import time
import logging
import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd
import yaml


# ============================================================================
#  Section 1: ParsedSignal - Standardized output from any device parser
# ============================================================================

@dataclass
class ParsedSignal:
    """
    Standardized output from a device parser.
    
    Attributes:
        device_id:      Short device identifier (e.g., "polar", "empatica")
        signal_type:    Signal name (e.g., "ecg", "eda", "eeg")
        data:           DataFrame with columns:
                            - timestamp_utc: datetime64[ns, UTC]
                            - value (or multiple value columns for multi-channel)
                            - quality_flag: int8 (0=valid, 1=suspect, 2=invalid)
        sampling_rate:  Sampling rate in Hz (None for event-based data)
        metadata:       Any additional device-specific metadata
    """
    device_id: str
    signal_type: str
    data: pd.DataFrame
    sampling_rate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """Check that the parsed data meets the required format."""
        errors = []
        required_columns = ["timestamp_utc", "quality_flag"]
        for col in required_columns:
            if col not in self.data.columns:
                errors.append(f"Missing required column: {col}")
        if "timestamp_utc" in self.data.columns:
            if not pd.api.types.is_datetime64_any_dtype(self.data["timestamp_utc"]):
                errors.append("timestamp_utc must be datetime64 type")
        if "quality_flag" in self.data.columns:
            invalid_flags = self.data["quality_flag"][~self.data["quality_flag"].isin([0, 1, 2])]
            if len(invalid_flags) > 0:
                errors.append(f"quality_flag contains invalid values: {invalid_flags.unique()}")
        value_cols = [c for c in self.data.columns if c not in ["timestamp_utc", "timestamp_local", "quality_flag"]]
        if len(value_cols) == 0:
            errors.append("No value columns found in data")
        return errors
    
    def summary(self) -> Dict[str, Any]:
        """Return a summary of the parsed signal."""
        info = {
            "device_id": self.device_id,
            "signal_type": self.signal_type,
            "sampling_rate": self.sampling_rate,
            "n_rows": len(self.data),
            "columns": list(self.data.columns),
        }
        if "timestamp_utc" in self.data.columns and len(self.data) > 0:
            info["time_start"] = str(self.data["timestamp_utc"].min())
            info["time_end"] = str(self.data["timestamp_utc"].max())
            info["duration_seconds"] = (self.data["timestamp_utc"].max() - self.data["timestamp_utc"].min()).total_seconds()
        if "quality_flag" in self.data.columns:
            flag_counts = self.data["quality_flag"].value_counts().to_dict()
            info["quality_flags"] = {
                "valid": flag_counts.get(0, 0),
                "suspect": flag_counts.get(1, 0),
                "invalid": flag_counts.get(2, 0),
            }
        return info


# ============================================================================
#  Section 2: BaseParser - Abstract base class for all device parsers
# ============================================================================

class BaseParser(ABC):
    """
    Abstract base class for device parsers.
    Each device parser must inherit from BaseParser and implement parse().
    """
    
    def __init__(self, device_id: str, device_config: Dict[str, Any]):
        self.device_id = device_id
        self.config = device_config
        self.logger = logging.getLogger(f"parser.{device_id}")
    
    @abstractmethod
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        """Parse raw device files and return standardized signals."""
        pass
    
    def _to_utc(self, timestamps: pd.Series, session_meta: Dict[str, Any]) -> pd.Series:
        """Convert timestamps to UTC based on session timezone."""
        tz = session_meta.get("timezone", "UTC")
        if timestamps.dt.tz is None:
            localized = timestamps.dt.tz_localize(tz)
        else:
            localized = timestamps
        return localized.dt.tz_convert("UTC")
    
    def _list_files(self, raw_dir: Path, extensions: Optional[List[str]] = None) -> List[Path]:
        """List files in the raw directory, optionally filtered by extension."""
        if not raw_dir.exists():
            self.logger.warning(f"Raw directory does not exist: {raw_dir}")
            return []
        files = []
        for f in sorted(raw_dir.iterdir()):
            if f.is_file():
                if extensions is None or f.suffix.lower() in extensions:
                    files.append(f)
        self.logger.info(f"Found {len(files)} files in {raw_dir}")
        return files


# ============================================================================
#  Section 3: Device Parsers (stubs - fill in when real data is available)
# ============================================================================

class PolarParser(BaseParser):
    """Polar H10 (ECG/HRV). Chest strap, Bluetooth export."""
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing Polar H10 data from: {raw_dir}")
        files = self._list_files(raw_dir, [".csv", ".txt", ".json"])
        if not files:
            self.logger.warning("No Polar data files found")
            return []
        signals = []
        # TODO: Implement when real data format is confirmed
        # Typical: Polar Sensor Logger CSV -> timestamp + ECG values at ~130 Hz
        # Also: RR intervals for HRV
        self.logger.info(f"Polar parsing complete. Signals: {len(signals)}")
        return signals


class EmpaticaParser(BaseParser):
    """Empatica EmbracePlus (EDA/HR/Temp/Accel). Wrist-worn, cloud export."""
    
    SIGNAL_MAP = {
        "EDA": {"signal_type": "eda", "sampling_rate": 4},
        "HR": {"signal_type": "hr", "sampling_rate": 1},
        "TEMP": {"signal_type": "temp", "sampling_rate": 4},
        "ACC": {"signal_type": "accel", "sampling_rate": 64},
        "BVP": {"signal_type": "bvp", "sampling_rate": 64},
    }
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing Empatica data from: {raw_dir}")
        files = self._list_files(raw_dir, [".csv", ".zip"])
        if not files:
            self.logger.warning("No Empatica data files found")
            return []
        signals = []
        # TODO: Implement when real data format is confirmed
        # Typical E4 format: Line1=start_unix_ts, Line2=sampling_rate, Line3+=values
        # EmbracePlus may differ (check cloud export format)
        self.logger.info(f"Empatica parsing complete. Signals: {len(signals)}")
        return signals


class MuseParser(BaseParser):
    """Muse 2 (EEG). Headband, 4 channels: TP9/AF7/AF8/TP10 at 256 Hz."""
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing Muse 2 data from: {raw_dir}")
        files = self._list_files(raw_dir, [".csv", ".xdf", ".txt"])
        if not files:
            self.logger.warning("No Muse data files found")
            return []
        signals = []
        # TODO: Implement when real data format is confirmed
        # Mind Monitor CSV: TimeStamp + RAW_TP9/AF7/AF8/TP10 columns
        # Or Muse Direct CSV / XDF from LabRecorder
        self.logger.info(f"Muse parsing complete. Signals: {len(signals)}")
        return signals


class RespibanParser(BaseParser):
    """respiBAN (Respiration/ECG/IMU). Chest sensor, OpenSignals format."""
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing respiBAN data from: {raw_dir}")
        files = self._list_files(raw_dir, [".txt", ".csv", ".h5"])
        if not files:
            self.logger.warning("No respiBAN data files found")
            return []
        signals = []
        # TODO: Implement when real data format is confirmed
        # OpenSignals format: JSON header (sampling rate, start time) + tab-separated data
        # IMPORTANT: timestamps are RELATIVE (sample index), need start_time + index/rate
        self.logger.info(f"respiBAN parsing complete. Signals: {len(signals)}")
        return signals


class MasimoParser(BaseParser):
    """Masimo MightySat (SpO2/Pulse). Finger clip, app export."""
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing Masimo data from: {raw_dir}")
        files = self._list_files(raw_dir, [".csv", ".txt", ".xlsx"])
        if not files:
            self.logger.warning("No Masimo data files found")
            return []
        signals = []
        # TODO: Implement when real data format is confirmed
        # Masimo Personal Health app CSV: timestamp + SpO2 + pulse rate + PI
        self.logger.info(f"Masimo parsing complete. Signals: {len(signals)}")
        return signals


class GeneactivParser(BaseParser):
    """GENEActiv (Actigraphy/Light). Wrist-worn. NOT YET AVAILABLE."""
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing GENEActiv data from: {raw_dir}")
        files = self._list_files(raw_dir, [".csv", ".bin"])
        if not files:
            self.logger.warning("No GENEActiv data files found")
            return []
        signals = []
        # TODO: Implement when device is available
        self.logger.info(f"GENEActiv parsing complete. Signals: {len(signals)}")
        return signals


class OntrakParser(BaseParser):
    """OnTrak ABPM (Blood Pressure). Cuff-based. NOT YET AVAILABLE."""
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing OnTrak data from: {raw_dir}")
        files = self._list_files(raw_dir, [".csv", ".txt", ".xlsx"])
        if not files:
            self.logger.warning("No OnTrak data files found")
            return []
        signals = []
        # TODO: Implement when device is available
        self.logger.info(f"OnTrak parsing complete. Signals: {len(signals)}")
        return signals


class EmaParser(BaseParser):
    """EMA (Phone/REDCap). Event-based survey responses."""
    
    def parse(self, raw_dir: Path, session_meta: Dict[str, Any]) -> List[ParsedSignal]:
        self.logger.info(f"Parsing EMA data from: {raw_dir}")
        files = self._list_files(raw_dir, [".csv"])
        if not files:
            self.logger.warning("No EMA data files found")
            return []
        signals = []
        # TODO: Implement once REDCap EMA structure is finalized
        # REDCap CSV export: record_id + timestamp + survey item columns
        self.logger.info(f"EMA parsing complete. Signals: {len(signals)}")
        return signals


# Parser registry
PARSER_REGISTRY = {
    "polar": PolarParser,
    "empatica": EmpaticaParser,
    "muse": MuseParser,
    "respiban": RespibanParser,
    "masimo": MasimoParser,
    "geneactiv": GeneactivParser,
    "ontrak": OntrakParser,
    "ema": EmaParser,
}


def get_parser(device_id: str, device_config: Dict[str, Any]) -> BaseParser:
    """Factory: get the appropriate parser for a device."""
    if device_id not in PARSER_REGISTRY:
        raise ValueError(f"Unknown device: '{device_id}'. Available: {list(PARSER_REGISTRY.keys())}")
    return PARSER_REGISTRY[device_id](device_id, device_config)


# ============================================================================
#  Section 4: Quality Checker
# ============================================================================

class QualityChecker:
    """Run quality checks on processed physiological data files."""
    
    def __init__(self, quality_config: Dict[str, Any]):
        self.config = quality_config
    
    def check_file(self, file_path: Path) -> Dict[str, Any]:
        """Run all quality checks on a processed data file."""
        stem = file_path.stem
        parts = stem.split("_")
        sub_id = parts[0] if len(parts) >= 1 else "unknown"
        ses_id = parts[1] if len(parts) >= 2 else "unknown"
        device_id = parts[2] if len(parts) >= 3 else "unknown"
        signal_type = "_".join(parts[3:]) if len(parts) >= 4 else "unknown"
        
        if file_path.suffix == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path, parse_dates=["timestamp_utc"])
        
        report = {
            "file": file_path.name,
            "participant_id": sub_id, "session_id": ses_id,
            "device_id": device_id, "signal_type": signal_type,
            "checks": {},
        }
        
        report["checks"]["completeness"] = self._check_completeness(df)
        report["checks"]["temporal"] = self._check_temporal(df, device_id)
        report["checks"]["range"] = self._check_range(df, signal_type)
        report["checks"]["flatline"] = self._check_flatline(df)
        
        statuses = [c.get("status", "unknown") for c in report["checks"].values()]
        report["overall_status"] = "fail" if "fail" in statuses else ("warn" if "warn" in statuses else "pass")
        return report
    
    def _check_completeness(self, df):
        n = len(df)
        result = {"total_rows": n, "columns": {}}
        for col in df.columns:
            miss = int(df[col].isna().sum())
            result["columns"][col] = {"missing_count": miss, "missing_pct": round(miss/n*100, 2) if n > 0 else 0}
        if "quality_flag" in df.columns:
            fc = df["quality_flag"].value_counts().to_dict()
            inv_pct = fc.get(2, 0) / n * 100 if n > 0 else 0
            result["status"] = "fail" if inv_pct > 50 else ("warn" if inv_pct > 10 else "pass")
        else:
            result["status"] = "pass"
        return result
    
    def _check_temporal(self, df, device_id):
        result = {}
        if "timestamp_utc" not in df.columns or len(df) < 2:
            return {"status": "pass", "note": "Insufficient data"}
        ts = pd.to_datetime(df["timestamp_utc"])
        result["is_monotonic"] = bool(ts.is_monotonic_increasing)
        result["duplicate_timestamps"] = int(ts.duplicated().sum())
        max_gap_cfg = self.config.get("max_gap_seconds", {})
        max_gap = max_gap_cfg.get(device_id) if isinstance(max_gap_cfg, dict) else None
        if max_gap:
            diffs = ts.diff().dt.total_seconds()
            gaps = diffs[diffs > max_gap]
            result["gap_count"] = int(len(gaps))
            result["max_gap_observed"] = float(diffs.max()) if len(diffs) > 0 else 0
        issues = []
        if not result.get("is_monotonic", True):
            issues.append("non-monotonic")
        if result.get("gap_count", 0) > 10:
            issues.append(f"{result['gap_count']} gaps")
        result["status"] = "fail" if not result.get("is_monotonic", True) else ("warn" if issues else "pass")
        return result
    
    def _check_range(self, df, signal_type):
        range_map = {
            "hr": ("hr_min", "hr_max"), "spo2": ("spo2_min", "spo2_max"),
            "eda": ("eda_min", "eda_max"), "temp": ("temp_min", "temp_max"),
        }
        result = {"signal_type": signal_type}
        if signal_type not in range_map:
            return {"status": "pass", "note": f"No range defined for {signal_type}"}
        mn_k, mx_k = range_map[signal_type]
        mn, mx = self.config.get(mn_k), self.config.get(mx_k)
        if mn is None or mx is None:
            return {"status": "pass"}
        val_cols = [c for c in df.columns if c not in ["timestamp_utc", "timestamp_local", "quality_flag"]]
        for col in val_cols:
            if pd.api.types.is_numeric_dtype(df[col]):
                below = int((df[col] < mn).sum())
                above = int((df[col] > mx).sum())
                oor_pct = (below + above) / len(df) * 100 if len(df) > 0 else 0
                result[col] = {"below": below, "above": above, "oor_pct": round(oor_pct, 2)}
        total_oor = sum(v.get("oor_pct", 0) for v in result.values() if isinstance(v, dict))
        result["status"] = "fail" if total_oor > 30 else ("warn" if total_oor > 5 else "pass")
        return result
    
    def _check_flatline(self, df, min_run=100):
        result = {}
        val_cols = [c for c in df.columns if c not in ["timestamp_utc", "timestamp_local", "quality_flag"]]
        detected = False
        for col in val_cols:
            if pd.api.types.is_numeric_dtype(df[col]) and len(df) > min_run:
                changes = df[col].diff().ne(0).cumsum()
                max_run = int(changes.groupby(changes).transform("count").max())
                result[col] = {"max_consecutive_identical": max_run, "flatline": max_run >= min_run}
                if max_run >= min_run:
                    detected = True
        result["status"] = "warn" if detected else "pass"
        return result


# ============================================================================
#  Section 5: Project Setup Functions
# ============================================================================

def cmd_init(args):
    """Initialize project folder structure."""
    root = Path(args.root)
    dirs = ["raw_data", "processed_data", "aligned_data", "quality_reports", "configs", "scripts", "docs", "logs"]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
        print(f"  Created: {root / d}")
    
    # Session log template
    template = {
        "participant_id": "sub-001",
        "session_id": "ses-001",
        "start_time_utc": "2026-03-20T14:00:00Z",
        "end_time_utc": "2026-03-21T14:00:00Z",
        "timezone": "America/New_York",
        "devices_used": ["polar", "empatica", "muse", "respiban", "masimo"],
        "notes": "",
        "operator": ""
    }
    tpl_path = root / "docs" / "session_log_template.json"
    with open(tpl_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print(f"\nProject initialized at: {root}")
    print("Next: copy pipeline_config.yaml to configs/ and edit project_root path")


def cmd_add_session(args):
    """Create folder structure for a participant session."""
    root = Path(args.root)
    devices = args.devices if args.devices else ["polar", "empatica", "muse", "respiban", "masimo"]
    session_dir = root / "raw_data" / args.sub / args.ses
    
    for device in devices:
        (session_dir / device).mkdir(parents=True, exist_ok=True)
        print(f"  Created: {session_dir / device}")
    
    for sub in ["processed_data", "aligned_data", "quality_reports"]:
        (root / sub / args.sub / args.ses).mkdir(parents=True, exist_ok=True)
    
    print(f"\nSession created: {args.sub}/{args.ses}")
    print(f"1. Put raw device files into: {session_dir}/{{device}}/")
    print(f"2. Create session_log.json in: {session_dir}/")


# ============================================================================
#  Section 6: Pipeline Runner
# ============================================================================

def setup_logging(log_dir: Path, sub_id: str, ses_id: str):
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_{sub_id}_{ses_id}_{ts}.log"
    
    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.DEBUG)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S"))
    
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s - %(message)s"))
    
    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.info(f"Log file: {log_file}")
    return logger


def cmd_run(args):
    """Run the full pipeline: parse -> quality check."""
    root = Path(args.root)
    config_path = root / "configs" / "pipeline_config.yaml"
    
    if not config_path.exists():
        print(f"ERROR: Config not found at {config_path}")
        print("Copy pipeline_config.yaml to configs/ and edit project_root")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config["project_root"] = str(root)
    
    logger = setup_logging(root / "logs", args.sub, args.ses)
    logger.info(f"Pipeline started: {args.sub} / {args.ses}")
    
    # Load session metadata
    session_raw = root / "raw_data" / args.sub / args.ses
    log_path = session_raw / "session_log.json"
    if not log_path.exists():
        logger.error(f"session_log.json not found in {session_raw}")
        sys.exit(1)
    with open(log_path, "r", encoding="utf-8") as f:
        session_meta = json.load(f)
    
    device_list = args.devices if args.devices else session_meta.get("devices_used", [])
    logger.info(f"Devices to process: {device_list}")
    
    # Stage 1: Parse
    proc_dir = root / "processed_data" / args.sub / args.ses
    proc_dir.mkdir(parents=True, exist_ok=True)
    all_signals = []
    
    for dev_id in device_list:
        dev_config = config.get("devices", {}).get(dev_id, {})
        dev_raw = session_raw / dev_id
        if not dev_raw.exists():
            logger.warning(f"No raw data dir for {dev_id}, skipping")
            continue
        try:
            parser = get_parser(dev_id, dev_config)
            signals = parser.parse(dev_raw, session_meta)
            for sig in signals:
                errors = sig.validate()
                if errors:
                    logger.error(f"Validation failed for {dev_id}/{sig.signal_type}: {errors}")
                    continue
                fname = f"{args.sub}_{args.ses}_{dev_id}_{sig.signal_type}.parquet"
                out_path = proc_dir / fname
                sig.data.to_parquet(out_path, compression="snappy", index=False)
                logger.info(f"Saved: {out_path} ({len(sig.data)} rows)")
                all_signals.append(sig)
        except Exception as e:
            logger.error(f"Error parsing {dev_id}: {e}", exc_info=True)
    
    logger.info(f"Parse complete. Total signals: {len(all_signals)}")
    
    # Stage 2: Quality Check
    report_dir = root / "quality_reports" / args.sub / args.ses
    report_dir.mkdir(parents=True, exist_ok=True)
    checker = QualityChecker(config.get("quality", {}))
    
    proc_files = list(proc_dir.glob("*.parquet")) + list(proc_dir.glob("*.csv"))
    reports = []
    for pf in proc_files:
        try:
            r = checker.check_file(pf)
            reports.append(r)
            logger.info(f"Quality [{r['overall_status']}]: {pf.name}")
        except Exception as e:
            logger.error(f"Quality check error for {pf.name}: {e}")
    
    report_path = report_dir / f"{args.sub}_{args.ses}_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, default=str)
    logger.info(f"Quality report: {report_path}")
    
    # Stage 3 & 4: Align & Export (TODO)
    logger.info("Alignment and Export stages not yet implemented (waiting for real data)")
    logger.info("Pipeline finished.")


def cmd_quality(args):
    """Run quality check only on existing processed data."""
    root = Path(args.root)
    config_path = root / "configs" / "pipeline_config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    proc_dir = root / "processed_data" / args.sub / args.ses
    report_dir = root / "quality_reports" / args.sub / args.ses
    report_dir.mkdir(parents=True, exist_ok=True)
    
    checker = QualityChecker(config.get("quality", {}))
    proc_files = list(proc_dir.glob("*.parquet")) + list(proc_dir.glob("*.csv"))
    
    if not proc_files:
        print(f"No processed files in {proc_dir}")
        return
    
    reports = []
    for pf in proc_files:
        r = checker.check_file(pf)
        reports.append(r)
        print(f"  [{r['overall_status'].upper()}] {pf.name}")
    
    report_path = report_dir / f"{args.sub}_{args.ses}_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, default=str)
    print(f"\nReport saved: {report_path}")


# ============================================================================
#  Section 7: Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Device Physiological Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pilot_pipeline.py init --root E:/pilot_study
  python pilot_pipeline.py add-session --root E:/pilot_study --sub sub-001 --ses ses-001
  python pilot_pipeline.py run --root E:/pilot_study --sub sub-001 --ses ses-001
  python pilot_pipeline.py quality --root E:/pilot_study --sub sub-001 --ses ses-001
        """
    )
    sub = parser.add_subparsers(dest="command")
    
    # init
    p_init = sub.add_parser("init", help="Initialize project folder structure")
    p_init.add_argument("--root", required=True, help="Project root directory")
    
    # add-session
    p_add = sub.add_parser("add-session", help="Create folders for a session")
    p_add.add_argument("--root", required=True)
    p_add.add_argument("--sub", required=True, help="e.g., sub-001")
    p_add.add_argument("--ses", required=True, help="e.g., ses-001")
    p_add.add_argument("--devices", nargs="+", default=None)
    
    # run
    p_run = sub.add_parser("run", help="Run full pipeline (parse + quality)")
    p_run.add_argument("--root", required=True)
    p_run.add_argument("--sub", required=True)
    p_run.add_argument("--ses", required=True)
    p_run.add_argument("--devices", nargs="+", default=None)
    
    # quality
    p_qc = sub.add_parser("quality", help="Quality check only")
    p_qc.add_argument("--root", required=True)
    p_qc.add_argument("--sub", required=True)
    p_qc.add_argument("--ses", required=True)
    
    args = parser.parse_args()
    
    if args.command == "init":
        cmd_init(args)
    elif args.command == "add-session":
        cmd_add_session(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "quality":
        cmd_quality(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
