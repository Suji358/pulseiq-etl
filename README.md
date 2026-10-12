# PulseIQ ETL (Task 1)

Extract -> Transform -> Validate -> Load for HR data (employees, salary, attendance, leave, payroll).

## Run (one command)
1. Put the 5 raw CSV files in `raw/` (or create fake ones: `docker compose run etl python -m src.make_sample_data`).
2. Optional: `copy .env.example .env`
3. `docker compose run --build etl`

## Output
- `clean/`    clean, validated files (CSV, or Parquet with OUTPUT_FORMAT=parquet)
- `rejected/` rows that broke a rule, each with a `reject_reason`
- `logs/run_log.json`  start/finish time, rows in / out / rejected, reject reasons, file checksums
- `logs/etl.log`       full text log

## Rules
- Validation failure stops the run with exit code 1 and a clear message.
- Output is overwritten each run. Same input gives the same output (compare `output_checksums` in the run log).
- Joining date after leaving date: row is rejected and flagged, not dropped silently and not auto-fixed.
  We cannot know which date is wrong, so HR must correct the source.
- Leaving date after the reference date (AS_OF_DATE) is rejected as `future_leaving_date`.

## Validation demo

docker compose run --rm -v "$PWD/demo_fail.py:/app/demo_fail.py" -v "$PWD/clean:/app/clean" etl python demo_fail.py

This injects a negative salary into the clean data and shows the pandera validation failing loudly.

## Without Docker (Windows)
```
py -m pip install -r requirements.txt
py -m src.make_sample_data
py -m src.main
```
