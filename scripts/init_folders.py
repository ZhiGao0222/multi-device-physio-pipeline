from __future__ import annotations

import argparse
from pathlib import Path

DEVICES = ["polar", "empatica", "muse", "geneactiv", "respiban", "masimo", "ontrak", "ema"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--participant", default="sub-000")
    parser.add_argument("--session", default="ses-001")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    for top in ["raw_data", "processed_data", "aligned_data", "quality_reports", "configs", "docs", "logs"]:
        (root / top).mkdir(parents=True, exist_ok=True)

    session_dir = root / "raw_data" / args.participant / args.session
    for device in DEVICES:
        (session_dir / device).mkdir(parents=True, exist_ok=True)

    session_log = session_dir / "session_log.json"
    if not session_log.exists():
        session_log.write_text(
            '{\n'
            f'  "participant_id": "{args.participant}",\n'
            f'  "session_id": "{args.session}",\n'
            '  "timezone": "America/New_York",\n'
            '  "devices_used": [],\n'
            '  "operator": "ZG",\n'
            '  "notes": "Technical self-test only."\n'
            '}\n',
            encoding="utf-8",
        )
    print(f"Initialized folders under {root}")


if __name__ == "__main__":
    main()
