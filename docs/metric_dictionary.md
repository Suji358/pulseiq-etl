# PulseIQ Metric Dictionary (v0.1)

One definition per metric, so everyone calculates it the same way.
Source tables are the **clean** files written by the ETL.

| # | Metric | Business meaning | Formula | Source (table.column) | Grain | Notes |
|---|--------|------------------|---------|-----------------------|-------|-------|
| 1 | **Headcount** | Employees working at a point in time | Count of employees where `joining_date <= D` and (`leaving_date` is empty or `leaving_date > D`) | employees.joining_date, employees.leaving_date | month-end / department | Rejected employees are excluded until HR fixes them |
| 2 | **Attrition Rate (monthly)** | Share of people who left in a month | Leavers in month / average headcount of month × 100 | employees.leaving_date | month / department | Average headcount = (opening + closing) / 2 |
| 3 | **Average Monthly Salary** | Typical pay level | Mean of latest `monthly_salary` per employee on or before date D | salary.monthly_salary, salary.effective_date | month / department | Latest record per employee only; avoids double counting raises |
| 4 | **Absenteeism Rate** | Share of working days missed | Absent days (+ 0.5 × Half Day) / total attendance records × 100 | attendance.status | month / department | "Leave" and "Holiday" are excluded from the denominator |
| 5 | **Average Tenure (years)** | How long people stay | Mean of `tenure_years` for active employees | employees.tenure_years | as-of date | Uses leaving date if present, else AS_OF_DATE |

## Data quality rules these metrics depend on
- `employee_id` is unique and upper-case.
- No salary, gross, deductions or net pay is negative.
- `joining_date <= leaving_date` (violations are rejected, not fixed).
- Every attendance / leave / salary / payroll row belongs to a known employee.
