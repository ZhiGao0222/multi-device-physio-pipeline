from pathlib import Path
import argparse
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--start-utc", required=True)
    parser.add_argument("--end-utc", required=True)
    args = parser.parse_args()

    in_dir = Path("processed_data") / args.participant / args.session
    out_dir = Path("aligned_data") / args.participant / args.session / "clean_window_0228_0240"
    out_dir.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start_utc)
    end = pd.Timestamp(args.end_utc)

    rows = []

    for path in sorted(in_dir.glob("*.parquet")):
        df = pd.read_parquet(path)

        if "timestamp_utc" not in df.columns:
            rows.append({
                "file": path.name,
                "status": "skipped_no_timestamp_utc",
                "input_rows": len(df),
                "trimmed_rows": 0,
                "start_utc": "",
                "end_utc": "",
            })
            continue

        ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
        keep = (ts >= start) & (ts <= end)

        trimmed = df.loc[keep].copy()
        trimmed["timestamp_utc"] = ts.loc[keep]

        out_name = path.name.replace(".parquet", "_clean_0228_0240.parquet")
        out_path = out_dir / out_name
        trimmed.to_parquet(out_path, index=False)

        if len(trimmed) > 0:
            start_value = trimmed["timestamp_utc"].min()
            end_value = trimmed["timestamp_utc"].max()
        else:
            start_value = ""
            end_value = ""

        rows.append({
            "file": path.name,
            "status": "trimmed",
            "input_rows": len(df),
            "trimmed_rows": len(trimmed),
            "start_utc": start_value,
            "end_utc": end_value,
        })

    summary = pd.DataFrame(rows)
    summary_path = out_dir / "clean_window_summary.csv"
    summary.to_csv(summary_path, index=False)

    print(f"Wrote clean synchronized window to: {out_dir}")
    print(f"Wrote summary: {summary_path}")


if __name__ == "__main__":
    main()
