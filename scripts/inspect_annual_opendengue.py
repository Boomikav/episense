import pandas as pd

df = pd.read_csv("data/raw/opendengue_india_spatial.csv")
df_ind = df[df["adm_0_name"] == "INDIA"]
print("India rows in spatial:", len(df_ind))
print("T_res in India:", df_ind["T_res"].value_counts())
print("Years in India spatial:", sorted(df_ind["Year"].unique()))

# Check state-level annual series
print("\nState-level annual series:")
state_summary = []
for state, grp in df_ind.groupby("adm_1_name"):
    years = sorted(grp["Year"].dropna().unique())
    # find max consecutive years
    consec = 0
    max_consec = 0
    prev = None
    for y in years:
        if prev is None or y == prev + 1:
            consec += 1
        else:
            consec = 1
        max_consec = max(max_consec, consec)
        prev = y
    state_summary.append({
        "state": state,
        "n_years": len(years),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "max_consecutive_years": max_consec,
        "years": years
    })

df_states = pd.DataFrame(state_summary)
print(df_states.sort_values(by="n_years", ascending=False).to_string())
