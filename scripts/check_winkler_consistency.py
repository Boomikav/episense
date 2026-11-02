import pandas as pd
import numpy as np

# Rows from docs/forecasting_metric_reconciliation.md
data = [
    ('Delhi', 2023, 1, 16866, 2617.26, 266.00, 5840.84, 5574.84, False, 446581.24, 14248.74),
    ('Delhi', 2024, 2, 10585, 5104.94, 1452.80, 11816.67, 10363.87, True, 10363.87, 5480.06),
    ('Kerala', 2023, 1, 17426, 2374.66, 946.10, 6162.61, 5216.51, False, 455752.11, 15051.34),
    ('Kerala', 2024, 2, 20674, 2398.31, 975.50, 7443.58, 6468.08, False, 535684.88, 18275.69),
    ('Tamil Nadu', 2023, 1, 9121, 3448.27, 1214.90, 9227.07, 8012.17, True, 8012.17, 5672.73),
    ('Tamil Nadu', 2024, 2, 27378, 4242.81, 1682.90, 12317.91, 10635.01, False, 613038.61, 23135.19),
    ('Maharashtra', 2023, 1, 19034, 8925.32, 3396.20, 18467.04, 15070.84, False, 37749.24, 10108.68),
    ('Maharashtra', 2024, 2, 19385, 9070.30, 3464.20, 19758.73, 16294.53, True, 16294.53, 10314.70),
    ('Karnataka', 2023, 1, 19300, 5196.23, 1920.70, 10929.84, 9009.14, False, 343815.54, 14103.77),
    ('Karnataka', 2024, 2, 32886, 8625.83, 3975.60, 17977.15, 14001.55, False, 610355.55, 24260.17),
    ('Gujarat', 2023, 1, 7222, 4087.47, 1061.80, 11894.28, 10832.48, True, 10832.48, 3134.53),
    ('Gujarat', 2024, 2, 7891, 7859.92, 2518.60, 23175.54, 20656.94, True, 20656.94, 31.08),
    ('Rajasthan', 2023, 1, 13924, 9080.32, 3043.00, 18724.27, 15681.27, True, 15681.27, 4843.68),
    ('Rajasthan', 2024, 2, 12514, 14384.58, 5591.60, 30571.68, 24980.08, True, 24980.08, 1870.58),
]

cols = ['state', 'year', 'step', 'y', 'y_hat', 'L', 'U', 'rep_w', 'rep_cov', 'rep_wink', 'rep_ae']
df = pd.DataFrame(data, columns=cols)

df['computed_w'] = df['U'] - df['L']
df['computed_cov'] = (df['y'] >= df['L']) & (df['y'] <= df['U'])
df['computed_ae'] = np.abs(df['y'] - df['y_hat'])

alpha = 0.05
mult = 2.0 / alpha  # 40.0

df['penalty'] = 0.0
for i, r in df.iterrows():
    if r['y'] < r['L']:
        df.at[i, 'penalty'] = mult * (r['L'] - r['y'])
    elif r['y'] > r['U']:
        df.at[i, 'penalty'] = mult * (r['y'] - r['U'])

df['computed_wink'] = df['computed_w'] + df['penalty']
df['diff_wink'] = df['computed_wink'] - df['rep_wink']
df['diff_w'] = df['computed_w'] - df['rep_w']
df['diff_ae'] = df['computed_ae'] - df['rep_ae']
df['diff_cov'] = df['computed_cov'] != df['rep_cov']

print("Row-by-Row Comparison:")
for _, r in df.iterrows():
    print(f"{r['state']:12} {r['year']} | y={r['y']:5d} | [L={r['L']:8.2f}, U={r['U']:8.2f}] | Width: rep={r['rep_w']:8.2f}, comp={r['computed_w']:8.2f} | Cov: rep={r['rep_cov']!s:5}, comp={r['computed_cov']!s:5} | AE: rep={r['rep_ae']:8.2f}, comp={r['computed_ae']:8.2f} | Winkler: rep={r['rep_wink']:10.2f}, comp={r['computed_wink']:10.2f}, diff={r['diff_wink']:.4f}")

print("\n--- Summary Consistency Checks ---")
print(f"Max absolute difference in Width        : {df['diff_w'].abs().max():.6f}")
print(f"Max absolute difference in Absolute Error: {df['diff_ae'].abs().max():.6f}")
print(f"Any Coverage mismatch                   : {df['diff_cov'].any()}")
print(f"Max absolute difference in Winkler Score : {df['diff_wink'].abs().max():.6f}")
print(f"Sum of Winkler Scores                   : {df['computed_wink'].sum():.2f}")
print(f"Sample Size (N)                         : {len(df)}")
print(f"Reported Mean Winkler Score             : 224985.61")
print(f"Recomputed Mean Winkler Score           : {df['computed_wink'].mean():.2f}")
print(f"Difference in Mean Winkler Score        : {df['computed_wink'].mean() - 224985.61:.6f}")
print(f"Recomputed Median Winkler Score         : {df['computed_wink'].median():.2f}")
print(f"Recomputed Mean Width                   : {df['computed_w'].mean():.2f}")
print(f"Recomputed Median Width                 : {df['computed_w'].median():.2f}")
print(f"Recomputed MAE                          : {df['computed_ae'].mean():.2f}")
print(f"Recomputed Empirical Coverage           : {df['computed_cov'].mean()*100:.1f}% ({df['computed_cov'].sum()}/{len(df)})")
