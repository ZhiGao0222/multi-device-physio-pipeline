from pathlib import Path
import argparse
import re
import pandas as pd


def clean_name(text):
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "value"


def first_value(df, col, default="unknown"):
    if col not in df.columns:
        return default
    vals = df[col].dropna().astype(str)
    if vals.empty:
        return default
    return vals.iloc[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--window", default="clean_window_0228_0240")
    parser.add_argument("--start-utc", default="2026-05-07 06:28:00+00:00")
    parser.add_argument("--end-utc", default="2026-05-07 06:40:00+00:00")
    args = parser.parse_args()

    in_dir = Path("aligned_data") / args.participant / args.session / args.window
    out_dir = Path("quality_reports") / args.participant / args.session / "clean_window_value_summary"
    out_dir.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start_utc)
    end = pd.Timestamp(args.end_utc)

    # Use 06:28:00 through 06:39:59.
    # This gives exactly 720 rows for a 12-minute window.
    seconds = pd.date_range(start=start, end=end - pd.Timedelta(seconds=1), freq="1s")

    one_sec_tables = []
    dictionary_rows = []

    files = sorted(in_dir.glob("*_clean_0228_0240.parquet"))

    if not files:
        raise FileNotFoundError(f"No clean-window parquet files found in {in_dir}")

    for path in files:
        df = pd.read_parquet(path)

        if "timestamp_utc" not in df.columns or "value" not in df.columns:
            print(f"Skipped {path.name}: missing timestamp_utc or value")
            continue

        df = df.copy()
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        device = first_value(df, "device_id", path.stem)
        signal = first_value(df, "signal_type", path.stem)

        if "channel" not in df.columns:
            df["channel"] = signal

        if "unit" not in df.columns:
            df["unit"] = ""

        for channel, sub in df.groupby("channel", dropna=False):
            channel = str(channel)
            valid = sub.dropna(subset=["timestamp_utc", "value"]).copy()

            if valid.empty:
                continue

            valid["second_utc"] = valid["timestamp_utc"].dt.floor("s")

            col_name = (
                clean_name(device)
                + "__"
                + clean_name(signal)
                + "__"
                + clean_name(channel)
                + "__mean"
            )

            one_sec = valid.groupby("second_utc")["value"].mean()
            one_sec = one_sec.reindex(seconds)

            one_sec_tables.append(one_sec.rename(col_name))

            unit_vals = valid["unit"].dropna().astype(str) if "unit" in valid.columns else []
            unit = unit_vals.iloc[0] if len(unit_vals) else ""

            dictionary_rows.append({
                "column_name": col_name,
                "device_id": device,
                "signal_type": signal,
                "channel": channel,
                "unit": unit,
                "source_file": path.name,
                "meaning": "Mean value within each 1-second bin",
            })

    if not one_sec_tables:
        raise RuntimeError("No 1-second tables were created.")

    out = pd.concat(one_sec_tables, axis=1)
    out.index.name = "second_utc"
    out = out.reset_index()

    out_path = out_dir / "clean_window_1s_values.csv"
    dict_path = out_dir / "clean_window_1s_column_dictionary.csv"

    out.to_csv(out_path, index=False)
    pd.DataFrame(dictionary_rows).to_csv(dict_path, index=False)

    print(f"Wrote 1-second values: {out_path}")
    print(f"Wrote column dictionary: {dict_path}")
    print("")
    print(f"Rows: {len(out)}")
    print(f"Columns: {len(out.columns)}")
    print("")
    print(out.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
