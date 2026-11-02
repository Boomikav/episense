import pandas as pd

df = pd.read_csv("data/raw/opendengue_india_temporal.csv")
print("=== TEMPORAL CSV INDIA ===")
print(df["T_res"].value_counts())
print(df[df["adm_1_name"].isna()][["calendar_start_date", "calendar_end_date", "Year", "dengue_total", "T_res", "UUID"]])
print("\nUnique adm_1_name:", df["adm_1_name"].dropna().unique())
print("\nTotal rows by T_res:")
for tres, group in df.groupby("T_res"):
    print(f"  {tres}: {len(group)} rows, Year min={group['Year'].min()}, max={group['Year'].max()}")
    if tres == "Month":
        print("Month records:")
        print(group[["calendar_start_date", "calendar_end_date", "Year", "dengue_total", "adm_1_name"]].head(25))

print("\nLet's check Month records in df:")
months = df[df["T_res"] == "Month"]
print(f"Months count: {len(months)}")
if len(months) > 0:
    print(months[["calendar_start_date", "calendar_end_date", "Year", "dengue_total", "adm_1_name"]])
