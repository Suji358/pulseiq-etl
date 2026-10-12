"""Generate MESSY fake HR data in raw/ so you can practise before the real files arrive.

    docker compose run etl python -m src.make_sample_data
    (or)  py -m src.make_sample_data
"""
import random
from datetime import date, timedelta

import pandas as pd

from .config import RAW_DIR

random.seed(42)  # same fake data every time
RAW_DIR.mkdir(parents=True, exist_ok=True)

DEPTS = ["Engineering", "HR", "Sales", "Finance", "Support"]
NAMES = ["Anitha Raj", "Karthik S", "Priya Nair", "Vimal Kumar", "Divya M", "Arun Prakash",
         "Meena K", "Suresh B", "Lakshmi R", "Ramesh T", "Nisha Dev", "Gopal V", "Kavya S",
         "Harish N", "Revathi P", "Manoj K", "Sneha G", "Bala C", "Deepa L", "Naveen R"]


def fmt(d: date) -> str:
    return random.choice([d.isoformat(), d.strftime("%d/%m/%Y"), d.strftime("%d-%m-%Y"), d.strftime("%d %b %Y")])


emp, sal, att, lea, pay = [], [], [], [], []
for i, name in enumerate(NAMES, start=1):
    eid = f"E{i:03d}"
    join = date(2019, 1, 1) + timedelta(days=random.randint(0, 2300))
    leave = join + timedelta(days=random.randint(200, 1500)) if i % 6 == 0 else None
    emp.append([eid.lower() if i % 7 == 0 else eid, f"  {name.upper()} " if i % 4 == 0 else name,
                random.choice(DEPTS) if i % 9 else "", fmt(join), fmt(leave) if leave else "",
                "Resigned" if leave else "active"])
    base = random.randint(25, 90) * 1000
    sal.append([eid, f"{base:,}" if i % 5 == 0 else str(base), fmt(join)])
    for m in range(1, 7):
        gross = base
        ded = round(base * 0.12)
        pay.append([eid, f"2026-{m:02d}-01", gross, ded, gross - ded])
    for d in range(1, 11):
        att.append([eid, fmt(date(2026, 8, d)), random.choice(["Present", "present", "Absent", "Half Day"])])
    lea.append([eid, random.choice(["casual", "Sick", "EARNED"]), "2026-07-10", "2026-07-12", 3])

# ---- deliberate problems, so you can see the pipeline catching them ----
emp.append(["E002", "Karthik S", "Sales", "2020-05-01", "", "Active"])          # duplicate ID, conflicting
emp.append(["E021", "Bad Dates", "HR", "2024-09-01", "2023-01-01", "Resigned"]) # joining after leaving
emp.append(["E022", "No Date", "HR", "not a date", "", "Active"])               # invalid joining date
emp.append(["", "No Id", "HR", "2022-01-01", "", "Active"])                     # missing employee id
sal.append(["E003", "-5000", "2024-01-01"])                                      # negative salary
sal.append(["E004", "abc", "2024-01-01"])                                        # not a number
sal.append(["E999", "40000", "2024-01-01"])                                      # employee does not exist
att.append(["E001", "31/02/2026", "Present"])                                    # impossible date
att.append(att[0])                                                                # exact duplicate row
lea.append(["E005", "Sick", "2026-08-10", "2026-08-05", 2])                      # start after end
pay.append(["E006", "2026-03-01", 50000, 6000, 99999])                           # net pay does not add up
pay.append(["E007", "2026-04-01", -100, 0, -100])                                # negative amount
pay.append(["E021", "2026-04-01", 40000, 4800, 35200])                           # employee rejected (bad dates)

pd.DataFrame(emp, columns=["employee_id", "name", "department", "joining_date", "leaving_date", "status"]).to_csv(RAW_DIR / "employees.csv", index=False)
pd.DataFrame(sal, columns=["employee_id", "monthly_salary", "effective_date"]).to_csv(RAW_DIR / "salary.csv", index=False)
pd.DataFrame(att, columns=["employee_id", "date", "status"]).to_csv(RAW_DIR / "attendance.csv", index=False)
pd.DataFrame(lea, columns=["employee_id", "leave_type", "start_date", "end_date", "days"]).to_csv(RAW_DIR / "leave.csv", index=False)
pd.DataFrame(pay, columns=["employee_id", "pay_month", "gross_pay", "deductions", "net_pay"]).to_csv(RAW_DIR / "payroll.csv", index=False)
print(f"Sample raw files written to {RAW_DIR}")
