import pandas as pd

spatial_csv = "data/raw/opendengue_india_spatial.csv"
temporal_csv = "data/raw/opendengue_india_temporal.csv"

print("=== SPATIAL CSV ===")
df_sp = pd.read_csv(spatial_csv)
print(f"Columns: {list(df_sp.columns)}")
print(f"Total rows: {len(df_sp)}")
print(f"Year min: {df_sp['Year'].min()}, Year max: {df_sp['Year'].max()}")
print(f"Admin0: {df_sp['adm_0_name'].unique()}")
print(f"Admin1 count: {df_sp['adm_1_name'].nunique()}")
print(df_sp.head(10))

print("\n=== TEMPORAL CSV ===")
df_temp = pd.read_csv(temporal_csv)
print(f"Columns: {list(df_temp.columns)}")
print(f"Total rows: {len(df_temp)}")
print(df_temp.head(20))
