import pandas as pd

def audit_dengue():
    # 1. Spatial extract
    df_sp = pd.read_csv("data/raw/opendengue_india_spatial.csv")
    ind_sp = df_sp[df_sp["ISO_A0"] == "IND"]

    print("=" * 80)
    print("OPENDENGUE INDIA SPATIAL EXTRACT AUDIT")
    print("=" * 80)
    print(f"Total rows in file: {len(df_sp):,}")
    print(f"Total India (IND) rows: {len(ind_sp):,}")
    print("India Temporal Resolutions (T_res):", ind_sp["T_res"].value_counts().to_dict())
    print("India Spatial Resolutions (S_res):", ind_sp["S_res"].value_counts().to_dict())
    print("India Unique States (Admin 1):", ind_sp["adm_1_name"].nunique())

    # Check annual state rows
    annual_states = ind_sp[ind_sp["T_res"] == "Year"]
    print(f"\nTotal Annual State-level rows: {len(annual_states)}")
    print(f"Calendar span in annual data: {annual_states['Year'].min()} - {annual_states['Year'].max()}")
    print(f"Unique years in annual data: {sorted(annual_states['Year'].unique())}")
    print(f"Total unique years: {annual_states['Year'].nunique()}")

    # Check 8 focus states
    focus_states = ["Delhi", "Kerala", "Tamil Nadu", "Maharashtra", "Karnataka", "Gujarat", "Rajasthan", "West Bengal"]
    print("\nDetailed Focus States Breakdown (1997-2024 expected, 28 calendar years):")
    for s in focus_states:
        s_df = annual_states[annual_states["adm_1_name"].str.upper() == s.upper()].sort_values("Year")
        years = s_df["Year"].tolist()
        missing = [y for y in range(1997, 2025) if y not in years]
        duplicates = len(s_df) - len(set(years))
        print(f"  {s:15s}: valid_obs={len(s_df)}, unique_years={len(set(years))}, span={years[0] if years else None}-{years[-1] if years else None}, missing={missing}, duplicates={duplicates}")

    # Check monthly rows
    monthly_sp = ind_sp[ind_sp["T_res"] == "Month"].sort_values("calendar_start_date")
    print(f"\nMonthly India rows in Spatial Extract: {len(monthly_sp)}")
    for _, r in monthly_sp.iterrows():
        print(f"  {r['calendar_start_date']} to {r['calendar_end_date']}: cases={int(r['dengue_total'])}, S_res={r['S_res']}, UUID={r['UUID']}")

    # 2. Temporal extract
    df_temp = pd.read_csv("data/raw/opendengue_india_temporal.csv")
    ind_temp = df_temp[df_temp["ISO_A0"] == "IND"]
    print("\n" + "=" * 80)
    print("OPENDENGUE INDIA TEMPORAL EXTRACT AUDIT")
    print("=" * 80)
    print(f"Total rows in temporal extract: {len(df_temp):,}")
    print(f"Total India (IND) rows: {len(ind_temp):,}")
    print("Temporal Resolutions (T_res):", ind_temp["T_res"].value_counts().to_dict())
    print("Spatial Resolutions (S_res):", ind_temp["S_res"].value_counts().to_dict())

    monthly_temp = ind_temp[ind_temp["T_res"] == "Month"].sort_values("calendar_start_date")
    print(f"\nMonthly India rows in Temporal Extract: {len(monthly_temp)}")
    for idx, (_, r) in enumerate(monthly_temp.iterrows(), 1):
        print(f"  Month {idx:02d}: {r['calendar_start_date']} to {r['calendar_end_date']} -> cases={int(r['dengue_total'])}, UUID={r['UUID']}")

if __name__ == "__main__":
    audit_dengue()
