# Multi-Device Physiological Monitoring Pipeline

This repository contains code and documentation for a pilot pipeline that parses physiological device exports, normalizes timestamps to UTC, performs basic quality checks, and produces alignment summaries.

## Scope

The pipeline is designed for code and documentation only. Raw participant data, device exports, credentials, access keys, REDCap exports, and project-idea slides should **not** be committed to GitHub.

## Current device registry

- Polar H10: ECG / HRV
- Empatica EmbracePlus: EDA / HR / Temp / Accel
- Muse 2: EEG / Mind Monitor features
- GENEActiv: actigraphy / light
- respiBAN: respiration / ECG / IMU
- Masimo MightySat: SpO2 / pulse
- OnTrak ABPM: blood pressure
- EMA / REDCap: subjective responses

## Recommended folder structure

```text
project_root/
  raw_data/              # original exports, never committed
    sub-000/
      ses-001/
        polar/
        empatica/
        muse/
        geneactiv/
        respiban/
        masimo/
        ema/
        session_log.json
  processed_data/        # parsed and UTC-normalized files, never committed
  aligned_data/          # multi-device aligned outputs, never committed
  quality_reports/       # QC and inventory summaries, never committed
  configs/
  scripts/
  pipeline/
  docs/
  logs/                  # pipeline logs, never committed
```

## First run

1. Create a Python environment.
2. Install requirements:

```bash
pip install -r requirements.txt
```

3. Create local data folders:

```bash
python scripts/init_folders.py --project-root .
```

4. Place test data under `raw_data/sub-000/ses-001/<device>/`.

5. Run inventory/QC/alignment smoke test:

```bash
python scripts/run_pipeline.py --config configs/pipeline_config.yaml --participant sub-000 --session ses-001 --stage all
```

## Notes

- `sub-000` should be used for technical/self-test data only.
- Formal participants should start from `sub-001`.
- Timestamps should be converted to UTC before alignment.
- Failed or suspicious samples should be flagged, not silently deleted.
