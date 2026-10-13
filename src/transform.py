"""TRANSFORM: fix types, standardise, de-duplicate, handle missing values, add helper columns.

Every function returns (clean_df, rejected_df). A rejected row keeps its original raw
values plus a `reject_reason` column. Nothing is silently dropped.

BUSINESS RULE (joining date after leaving date):
  We do NOT drop it and we do NOT "fix" it (swapping dates). We cannot know which of the
  two dates is wrong. The row is REJECTED with reason `joining_after_leaving`, saved in
  rejected/, and counted in the run log, so HR can correct the source and re-run.
  Every other table's rows for that employee are rejected too (`unknown_employee`),
  so no payroll or attendance is calculated for someone with unreliable dates.
"""
import numpy as np
import pandas as pd

from .config import AS_OF_DATE

DATE_FORMATS_NOTE = "Accepts 2024-03-15, 15/03/2024, 15-03-2024, 15 Mar 2024 (day first)."


# ---------- helpers ----------
def _text(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def _date(s: pd.Series) -> pd.Series:
    s = _text(s).replace({"": None, "nan": None, "NaT": None, "None": None})
    # ISO dates (2026-03-01) first, so they are never read day-first by mistake
    iso = pd.to_datetime(s, format="ISO8601", errors="coerce")
    other = pd.to_datetime(s.where(iso.isna()), format="mixed", dayfirst=True, errors="coerce")
    return iso.fillna(other).astype("datetime64[ns]")


def _number(s: pd.Series) -> pd.Series:
    s = _text(s).str.replace(",", "", regex=False).replace({"": None})
    return pd.to_numeric(s, errors="coerce").astype("float64")


def _split(df: pd.DataFrame, raw: pd.DataFrame, rules: list[tuple[str, pd.Series]]):
    """rules = ordered (reason, bad_mask). First failing rule gives the reason."""
    reason = pd.Series("", index=df.index, dtype=object)
    for name, bad in rules:
        reason = reason.mask((reason == "") & bad.fillna(True), name)
    rejected = raw.loc[df.index[reason != ""]].copy()
    rejected["reject_reason"] = reason[reason != ""].values
    return df[reason == ""].copy(), rejected


def _month_year(df: pd.DataFrame, col: str, prefix: str = "") -> pd.DataFrame:
    df[f"{prefix}year"] = df[col].dt.year.astype("int64")
    df[f"{prefix}month"] = df[col].dt.month.astype("int64")
    return df


# ---------- employees ----------
def transform_employees(raw: pd.DataFrame):
    df = raw.copy()
    df["employee_id"] = _text(df["employee_id"]).str.upper()
    df["name"] = _text(df["name"]).str.title()
    df["department"] = _text(df["department"]).str.title().replace({"": "Unknown", "Nan": "Unknown"})
    df["department"] = df["department"].replace({"Hr": "HR", "It": "IT"})
    df["status"] = _text(df["status"]).str.title().replace({"": "Unknown"})
    df["joining_date"] = _date(df["joining_date"])
    df["leaving_date"] = _date(df["leaving_date"])  # blank = still working (stays NaT)

    # exact duplicate rows are harmless: drop them without rejecting
    df = df.drop_duplicates()
    raw = raw.loc[df.index]

    dup_id = df.duplicated("employee_id", keep="first")  # conflicting rows, same ID
    leaving_present = _text(raw["leaving_date"]) != ""
    clean, rejected = _split(df, raw, [
        ("missing_employee_id", df["employee_id"] == ""),
        ("future_leaving_date", df["leaving_date"] > pd.Timestamp(AS_OF_DATE)),
        ("invalid_joining_date", df["joining_date"].isna()),
        ("invalid_leaving_date", leaving_present & df["leaving_date"].isna()),
        ("joining_after_leaving", df["joining_date"] > df["leaving_date"]),
        ("duplicate_employee_id", dup_id),
    ])

    as_of = pd.Timestamp(AS_OF_DATE)
    end = clean["leaving_date"].fillna(as_of)
    clean["tenure_years"] = ((end - clean["joining_date"]).dt.days / 365.25).round(2)
    clean["join_year"] = clean["joining_date"].dt.year.astype("int64")
    clean["join_month"] = clean["joining_date"].dt.month.astype("int64")
    clean["is_active"] = clean["leaving_date"].isna()
    return clean.sort_values("employee_id").reset_index(drop=True), rejected


# ---------- child tables ----------
def _known(df, valid_ids):
    return ~df["employee_id"].isin(valid_ids)


def transform_salary(raw: pd.DataFrame, valid_ids: set):
    df = raw.copy()
    df["employee_id"] = _text(df["employee_id"]).str.upper()
    df["monthly_salary"] = _number(df["monthly_salary"])
    df["effective_date"] = _date(df["effective_date"])
    df = df.drop_duplicates()
    raw = raw.loc[df.index]
    clean, rejected = _split(df, raw, [
        ("unknown_employee", _known(df, valid_ids)),
        ("invalid_salary", df["monthly_salary"].isna()),
        ("negative_or_zero_salary", df["monthly_salary"] <= 0),
        ("invalid_effective_date", df["effective_date"].isna()),
        ("duplicate_salary_record", df.duplicated(["employee_id", "effective_date"], keep="first")),
    ])
    clean = _month_year(clean, "effective_date", "effective_")
    return clean.sort_values(["employee_id", "effective_date"]).reset_index(drop=True), rejected


def transform_attendance(raw: pd.DataFrame, valid_ids: set):
    df = raw.copy()
    df["employee_id"] = _text(df["employee_id"]).str.upper()
    df["date"] = _date(df["date"])
    df["status"] = _text(df["status"]).str.title().replace({"": "Unknown", "Half-Day": "Half Day"})
    exact_dup = df.duplicated(keep="first")
    rejected_exact = raw.loc[exact_dup].copy()
    rejected_exact["reject_reason"] = "exact_duplicate_row"
    df = df.loc[~exact_dup].copy()
    raw = raw.loc[df.index]
    clean, rejected = _split(df, raw, [
        ("unknown_employee", _known(df, valid_ids)),
        ("invalid_date", df["date"].isna()),
        ("invalid_status", ~df["status"].isin(["Present", "Absent", "Half Day", "Leave", "Holiday", "Unknown"])),
        ("duplicate_attendance_record", df.duplicated(["employee_id", "date"], keep="first")),
    ])    
    rejected = pd.concat([rejected, rejected_exact], axis=0)
    clean = _month_year(clean, "date")
    return clean.sort_values(["employee_id", "date"]).reset_index(drop=True), rejected


def transform_leave(raw: pd.DataFrame, valid_ids: set):
    df = raw.copy()
    df["employee_id"] = _text(df["employee_id"]).str.upper()
    df["leave_type"] = _text(df["leave_type"]).str.title().replace({"": "Unknown"})
    df["start_date"] = _date(df["start_date"])
    df["end_date"] = _date(df["end_date"])
    df["days"] = _number(df["days"])
    df = df.drop_duplicates()
    raw = raw.loc[df.index]
    clean, rejected = _split(df, raw, [
        ("unknown_employee", _known(df, valid_ids)),
        ("invalid_start_or_end_date", df["start_date"].isna() | df["end_date"].isna()),
        ("start_after_end", df["start_date"] > df["end_date"]),
        ("invalid_days", df["days"].isna() | (df["days"] <= 0)),
    ])
    clean = _month_year(clean, "start_date", "start_")
    return clean.sort_values(["employee_id", "start_date"]).reset_index(drop=True), rejected


def transform_payroll(raw: pd.DataFrame, valid_ids: set):
    df = raw.copy()
    df["employee_id"] = _text(df["employee_id"]).str.upper()
    df["pay_month"] = _date(df["pay_month"]).dt.to_period("M").dt.to_timestamp()
    for c in ["gross_pay", "deductions", "net_pay"]:
        df[c] = _number(df[c])
    df = df.drop_duplicates()
    raw = raw.loc[df.index]
    clean, rejected = _split(df, raw, [
        ("unknown_employee", _known(df, valid_ids)),
        ("invalid_pay_month", df["pay_month"].isna()),
        ("invalid_amount", df[["gross_pay", "deductions", "net_pay"]].isna().any(axis=1)),
        ("negative_amount", (df[["gross_pay", "deductions", "net_pay"]] < 0).any(axis=1)),
        ("net_pay_mismatch", (df["gross_pay"] - df["deductions"] - df["net_pay"]).abs() > 1),
        ("duplicate_payroll_record", df.duplicated(["employee_id", "pay_month"], keep="first")),
    ])
    clean = _month_year(clean, "pay_month")
    return clean.sort_values(["employee_id", "pay_month"]).reset_index(drop=True), rejected


def transform(tables: dict[str, pd.DataFrame]):
    clean, rejected = {}, {}
    clean["employees"], rejected["employees"] = transform_employees(tables["employees"])
    valid_ids = set(clean["employees"]["employee_id"])
    for name, fn in [("salary", transform_salary), ("attendance", transform_attendance),
                     ("leave", transform_leave), ("payroll", transform_payroll)]:
        clean[name], rejected[name] = fn(tables[name], valid_ids)
    return clean, rejected
