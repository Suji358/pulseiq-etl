"""Run the pipeline:  extract -> transform -> validate -> load -> run log.

    docker compose run etl
"""
import json
import logging
import sys
from datetime import datetime, timezone

from .config import AS_OF_DATE, LOGS_DIR, OUTPUT_FORMAT
from .extract import ExtractError, extract
from .load import load
from .transform import transform
from .validate import ValidationFailed, validate


def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO, format=fmt,
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOGS_DIR / "etl.log")],
    )


def write_run_log(summary: dict):
    with open(LOGS_DIR / "run_log.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def main() -> int:
    setup_logging()
    log = logging.getLogger("etl.main")
    started = datetime.now(timezone.utc)
    summary = {"started_at_utc": started.isoformat(timespec="seconds"),
               "as_of_date": AS_OF_DATE, "output_format": OUTPUT_FORMAT, "status": "running"}
    try:
        raw = extract()
        clean, rejected = transform(raw)
        for name in raw:
            log.info("%-10s rows_in=%d rows_out=%d rejected=%d",
                     name, len(raw[name]), len(clean[name]), len(rejected[name]))
        validate(clean)
        checksums = load(clean, rejected)

        summary["tables"] = {
            n: {"rows_in": len(raw[n]), "rows_out": len(clean[n]), "rows_rejected": len(rejected[n]),
                "exact_duplicates_dropped": len(raw[n]) - len(clean[n]) - len(rejected[n]),
                "reject_reasons": rejected[n]["reject_reason"].value_counts().to_dict()}
            for n in raw
        }
        summary["output_checksums"] = checksums  # identical on every run with the same input
        summary["status"] = "success"
        code = 0
    except (ExtractError, ValidationFailed) as e:
        log.error("PIPELINE FAILED:\n%s", e)
        summary["status"], summary["error"] = "failed", str(e)
        code = 1
    summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_run_log(summary)
    log.info("Run %s. See logs/run_log.json", summary["status"].upper())
    return code


if __name__ == "__main__":
    sys.exit(main())
