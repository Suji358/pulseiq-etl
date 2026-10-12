"""Paths and settings. Everything configurable comes from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(os.getenv("BASE_DIR", Path(__file__).resolve().parent.parent))
RAW_DIR = BASE_DIR / "raw"
CLEAN_DIR = BASE_DIR / "clean"
REJECTED_DIR = BASE_DIR / "rejected"
LOGS_DIR = BASE_DIR / "logs"

# Fixed reference date for tenure -> same input always gives same output
AS_OF_DATE = os.getenv("AS_OF_DATE", "2026-09-30")
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "csv").lower()  # csv | parquet

# table name -> raw file name
RAW_FILES = {
    "employees": "employees.csv",
    "salary": "salary.csv",
    "attendance": "attendance.csv",
    "leave": "leave.csv",
    "payroll": "payroll.csv",
}

# Columns every raw file must have (checked at extract time)
REQUIRED_COLUMNS = {
    "employees": ["employee_id", "name", "department", "joining_date", "leaving_date", "status"],
    "salary": ["employee_id", "monthly_salary", "effective_date"],
    "attendance": ["employee_id", "date", "status"],
    "leave": ["employee_id", "leave_type", "start_date", "end_date", "days"],
    "payroll": ["employee_id", "pay_month", "gross_pay", "deductions", "net_pay"],
}
