"""EXTRACT: read the raw files exactly as they are (all text), log row counts."""
import logging

import pandas as pd

from .config import RAW_DIR, RAW_FILES, REQUIRED_COLUMNS

log = logging.getLogger("etl.extract")


class ExtractError(Exception):
    pass


def extract() -> dict[str, pd.DataFrame]:
    tables = {}
    for name, filename in RAW_FILES.items():
        path = RAW_DIR / filename
        if not path.exists():
            raise ExtractError(f"Missing raw file: {path}")
        # dtype=str: do not let pandas guess types. Cleaning happens in transform.
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        df.columns = [c.strip().lower() for c in df.columns]
        missing = [c for c in REQUIRED_COLUMNS[name] if c not in df.columns]
        if missing:
            raise ExtractError(f"{filename} is missing columns: {missing}")
        log.info("Extracted %-10s rows=%d", name, len(df))
        tables[name] = df[REQUIRED_COLUMNS[name]].copy()
    return tables
