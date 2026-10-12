"""LOAD (for now): write clean + rejected files. Always overwrite, so running twice is harmless."""
import hashlib
import logging

import pandas as pd

from .config import CLEAN_DIR, OUTPUT_FORMAT, REJECTED_DIR

log = logging.getLogger("etl.load")


def _write(df: pd.DataFrame, path_no_ext):
    if OUTPUT_FORMAT == "parquet":
        path = path_no_ext.with_suffix(".parquet")
        df.to_parquet(path, index=False)
    else:
        path = path_no_ext.with_suffix(".csv")
        df.to_csv(path, index=False, date_format="%Y-%m-%d")
    return path


def load(clean: dict[str, pd.DataFrame], rejected: dict[str, pd.DataFrame]) -> dict[str, str]:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    # remove files from an earlier run so stale output never survives
    for folder in (CLEAN_DIR, REJECTED_DIR):
        for f in folder.glob("*"):
            if f.is_file() and f.name != ".gitkeep":
                f.unlink()
    checksums = {}
    for name, df in clean.items():
        p = _write(df, CLEAN_DIR / name)
        checksums[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        log.info("Wrote %s (%d rows)", p, len(df))
    for name, df in rejected.items():
        p = _write(df, REJECTED_DIR / f"rejected_{name}")
        log.info("Wrote %s (%d rows)", p, len(df))
    return checksums
