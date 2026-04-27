from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from pipeline.align import overlap_summary, summarize_processed_files
from pipeline.config import get_path, load_config
from pipeline.inventory import collect_inventory
from pipeline.quality import add_basic_quality_flags
from pipeline.report import write_csv, write_json


def run_inventory(cfg: dict, participant: str, session: str):
    raw_root = get_path(cfg, "raw_data")
    qr_root = get_path(cfg, "quality_reports") / participant / session
    session_dir = raw_root / participant / session
    devices = cfg.get("devices", {}).keys()
    inv = collect_inventory(session_dir, devices)
    write_csv(inv, qr_root / "data_inventory.csv")
    print(f"Wrote inventory: {qr_root / 'data_inventory.csv'}")
    return inv


def run_parse(cfg: dict, participant: str, session: str):
    raw_root = get_path(cfg, "raw_data")
    processed_dir = get_path(cfg, "processed_data") / participant / session
    processed_dir.mkdir(parents=True, exist_ok=True)
    session_dir = raw_root / participant / session

    for device in cfg.get("devices", {}).keys():
        device_dir = session_dir / device
        if not device_dir.exists():
            continue
        module = importlib.import_module(f"pipeline.parsers.{device}")
        parser = module.Parser(cfg, participant, session)
        frames = parser.parse(device_dir)
        for i, df in enumerate(frames):
            df = add_basic_quality_flags(df)
            signal = df["signal_type"].iloc[0] if "signal_type" in df and len(df) else f"signal{i}"
            out = processed_dir / f"{participant}_{session}_{device}_{signal}.parquet"
            df.to_parquet(out, index=False)
            print(f"Wrote {out}")


def run_alignment(cfg: dict, participant: str, session: str):
    processed_dir = get_path(cfg, "processed_data") / participant / session
    aligned_dir = get_path(cfg, "aligned_data") / participant / session
    summary = summarize_processed_files(processed_dir)
    write_csv(summary, aligned_dir / "processed_file_summary.csv")
    write_json(overlap_summary(summary), aligned_dir / "alignment_summary.json")
    print(f"Wrote alignment summary under {aligned_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--participant", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--stage", choices=["inventory", "parse", "align", "all"], default="all")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.stage in ["inventory", "all"]:
        run_inventory(cfg, args.participant, args.session)
    if args.stage in ["parse", "all"]:
        run_parse(cfg, args.participant, args.session)
    if args.stage in ["align", "all"]:
        run_alignment(cfg, args.participant, args.session)


if __name__ == "__main__":
    main()
