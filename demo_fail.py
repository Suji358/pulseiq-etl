import pandas as pd
from src.validate import validate

dates = {
    "employees": ["joining_date", "leaving_date"],
    "salary": ["effective_date"],
    "attendance": ["date"],
    "leave": ["start_date", "end_date"],
    "payroll": ["pay_month"],
}
floats = {
    "employees": ["tenure_years"],
    "salary": ["monthly_salary"],
    "leave": ["days"],
    "payroll": ["gross_pay", "deductions", "net_pay"],
}
clean = {}
for name, cols in dates.items():
    df = pd.read_csv(f"clean/{name}.csv", parse_dates=cols)
    for c in floats.get(name, []):
        df[c] = df[c].astype(float)
    clean[name] = df

validate(clean)
print("STEP 1: clean data -> validation PASSED")

clean["salary"].loc[0, "monthly_salary"] = -5000
print("STEP 2: injected a negative salary, validating again...")
validate(clean)