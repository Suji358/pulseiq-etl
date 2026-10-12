"""VALIDATE: pandera rules on the cleaned data. Any failure STOPS the pipeline (exit code 1).

Row-level problems are already moved to rejected/ by transform. These schemas are the
safety net: if anything bad still reaches here, the pipeline fails loudly instead of
writing bad data.
"""
import logging

import pandas as pd
import pandera.pandas as pa

log = logging.getLogger("etl.validate")


class ValidationFailed(Exception):
    pass


SCHEMAS = {
    "employees": pa.DataFrameSchema({
        "employee_id": pa.Column(str, unique=True, nullable=False),
        "name": pa.Column(str, nullable=False),
        "department": pa.Column(str, nullable=False),
        "joining_date": pa.Column("datetime64[ns]", nullable=False),
        "leaving_date": pa.Column("datetime64[ns]", nullable=True),
        "tenure_years": pa.Column(float, pa.Check.ge(0)),
    }, checks=pa.Check(
        lambda df: df["leaving_date"].isna() | (df["joining_date"] <= df["leaving_date"]),
        error="joining_date must not be after leaving_date",
    ), coerce=False),
    "salary": pa.DataFrameSchema({
        "employee_id": pa.Column(str),
        "monthly_salary": pa.Column(float, pa.Check.gt(0), nullable=False),
        "effective_date": pa.Column("datetime64[ns]", nullable=False),
    }, unique=["employee_id", "effective_date"]),
    "attendance": pa.DataFrameSchema({
        "employee_id": pa.Column(str),
        "date": pa.Column("datetime64[ns]", nullable=False),
        "status": pa.Column(str),
    }, unique=["employee_id", "date"]),
    "leave": pa.DataFrameSchema({
        "employee_id": pa.Column(str),
        "start_date": pa.Column("datetime64[ns]", nullable=False),
        "end_date": pa.Column("datetime64[ns]", nullable=False),
        "days": pa.Column(float, pa.Check.gt(0)),
    }, checks=pa.Check(lambda df: df["start_date"] <= df["end_date"], error="start_date after end_date")),
    "payroll": pa.DataFrameSchema({
        "employee_id": pa.Column(str),
        "pay_month": pa.Column("datetime64[ns]", nullable=False),
        "gross_pay": pa.Column(float, pa.Check.ge(0)),
        "deductions": pa.Column(float, pa.Check.ge(0)),
        "net_pay": pa.Column(float, pa.Check.ge(0)),
    }, unique=["employee_id", "pay_month"]),
}


def validate(clean: dict[str, pd.DataFrame]) -> None:
    problems = []
    for name, schema in SCHEMAS.items():
        try:
            schema.validate(clean[name], lazy=True)  # lazy: report ALL problems at once
            log.info("Validation passed for %s", name)
        except pa.errors.SchemaErrors as e:
            problems.append(f"[{name}] {len(e.failure_cases)} failure(s):\n{e.failure_cases.head(10).to_string()}")
    # cross-table rule: every child row must belong to a known employee
    ids = set(clean["employees"]["employee_id"])
    for name in ["salary", "attendance", "leave", "payroll"]:
        orphans = ~clean[name]["employee_id"].isin(ids)
        if orphans.any():
            problems.append(f"[{name}] {int(orphans.sum())} rows have an unknown employee_id")
    if problems:
        raise ValidationFailed("\n\n".join(problems))
