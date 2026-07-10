"""
01_compute_metrics.py

Computes every metric referenced in the README from the three raw Genpact
CSVs. Run this first — 02_make_charts.py reads its output from data/processed/.

Input:  data/raw/train.csv, data/raw/meal_info.csv, data/raw/fulfilment_center_info.csv
Output: data/processed/*.csv  (one file per metric group)
"""
import pandas as pd
import numpy as np
import os

RAW = "data/raw/"
OUT = "data/processed/"
os.makedirs(OUT, exist_ok=True)

train = pd.read_csv(RAW + "train.csv")
meals = pd.read_csv(RAW + "meal_info.csv")
centers = pd.read_csv(RAW + "fulfilment_center_info.csv")

df = train.merge(meals, on="meal_id", how="left").merge(centers, on="center_id", how="left")
df["discount_pct"] = (df["base_price"] - df["checkout_price"]) / df["base_price"] * 100
df["revenue"] = df["checkout_price"] * df["num_orders"]
df["log_price"] = np.log(df["checkout_price"])
df["log_orders"] = np.log(df["num_orders"])
df["discount_bin"] = pd.cut(df["discount_pct"], bins=[-999, 0, 5, 15, 30, 999],
                             labels=["no_disc", "0-5%", "5-15%", "15-30%", "30%+"])

# ============ 1. price elasticity per meal x center pair ============
# log-log slope of price vs orders; requires enough price variation to be meaningful
elas_rows = []
for (meal_id, center_id), g in df.groupby(["meal_id", "center_id"]):
    if g["checkout_price"].nunique() >= 10 and len(g) >= 20:
        slope = np.polyfit(g["log_price"], g["log_orders"], 1)[0]
        elas_rows.append({
            "meal_id": meal_id, "center_id": center_id, "elasticity": slope,
            "category": g["category"].iloc[0], "cuisine": g["cuisine"].iloc[0],
            "center_type": g["center_type"].iloc[0], "op_area": g["op_area"].iloc[0],
        })
elas_df = pd.DataFrame(elas_rows)
elas_df.to_csv(OUT + "pair_elasticity.csv", index=False)

cat_elas = elas_df.groupby("category")["elasticity"].agg(["median", "mean", "count"]).sort_values("median")
cat_elas.to_csv(OUT + "category_elasticity.csv")

meal_elas = elas_df.groupby(["meal_id", "category"])["elasticity"].agg(["median", "std", "count"]).reset_index()
meal_elas.to_csv(OUT + "meal_elasticity.csv", index=False)

cat_spread = meal_elas.groupby("category")["median"].agg(["min", "max", "count"])
cat_spread["range"] = cat_spread["max"] - cat_spread["min"]
cat_spread.sort_values("range", ascending=False).to_csv(OUT + "category_spread.csv")

elas_by_center_type = elas_df.groupby("center_type")["elasticity"].agg(["mean", "median", "count"])
elas_by_center_type.to_csv(OUT + "elasticity_by_centertype.csv")

# ============ 2. revenue by discount bin, for the 4 comparison categories ============
rev4 = df[df.category.isin(["Seafood", "Pizza", "Extras", "Biryani"])].groupby(
    ["category", "discount_bin"], observed=True).agg(
    avg_orders=("num_orders", "mean"), avg_revenue=("revenue", "mean"), n=("id", "count")).reset_index()
rev4.to_csv(OUT + "revenue_by_discount_4cats.csv", index=False)

# ============ 3. promo channel lift, price held roughly constant (discount <=5%) ============
low_disc = df[df["discount_pct"] <= 5].copy()
combo = low_disc.groupby(["emailer_for_promotion", "homepage_featured"])["num_orders"].agg(["mean", "count"])
combo.to_csv(OUT + "promo_combo_lift.csv")

# ============ 4. promo lift by category, vs. that category's elasticity ============
low_disc["any_promo"] = ((low_disc["emailer_for_promotion"] == 1) | (low_disc["homepage_featured"] == 1)).astype(int)
cat_lift = low_disc.groupby(["category", "any_promo"])["num_orders"].mean().unstack()
cat_lift["lift"] = cat_lift[1] / cat_lift[0]
cat_n = low_disc.groupby(["category", "any_promo"])["num_orders"].count().unstack()
cat_lift["n_promo"] = cat_n[1]
cat_lift["n_nopromo"] = cat_n[0]
compare = cat_lift[["lift", "n_promo", "n_nopromo"]].join(cat_elas["median"].rename("median_elasticity")).dropna()
compare.to_csv(OUT + "elasticity_vs_promolift.csv")

# worked-example pair used in the report to show the promo-lift calculation step by step
promolift_examples = low_disc[low_disc.category.isin(["Seafood", "Beverages"])].groupby(
    ["category", "any_promo"])["num_orders"].agg(["mean", "count"]).reset_index()
promolift_examples.to_csv(OUT + "promolift_worked_example.csv", index=False)

# ============ 5. Beverages deep dive ============
bev = df[df.category == "Beverages"].groupby(["meal_id", "cuisine"]).agg(
    avg_price=("checkout_price", "mean"), avg_orders=("num_orders", "mean"),
    avg_discount=("discount_pct", "mean")).reset_index()
bev = bev.merge(meal_elas[meal_elas.category == "Beverages"][["meal_id", "median"]]
                 .rename(columns={"median": "elasticity"}), on="meal_id")
bev.sort_values("elasticity").to_csv(OUT + "beverages_detail.csv", index=False)

HIGH_ELASTIC_BEV = [1207, 2322, 1230]  # Continental-cuisine, high elasticity tier
bevall = df[df.category == "Beverages"].copy()
bevall["tier"] = np.where(bevall.meal_id.isin(HIGH_ELASTIC_BEV), "high_elastic(Continental)", "low_elastic(rest)")
bevall.groupby(["tier", "discount_bin"], observed=True)["revenue"].mean().unstack().to_csv(OUT + "beverages_tier_revenue.csv")
bevall.groupby("tier")["discount_pct"].mean().to_csv(OUT + "beverages_tier_discount.csv")

# ============ 6. Rice Bowl deep dive ============
rb = df[df.category == "Rice Bowl"].groupby(["meal_id", "cuisine"]).agg(
    avg_price=("checkout_price", "mean"), avg_orders=("num_orders", "mean"),
    avg_discount=("discount_pct", "mean")).reset_index()
rb = rb.merge(meal_elas[meal_elas.category == "Rice Bowl"][["meal_id", "median"]]
              .rename(columns={"median": "elasticity"}), on="meal_id")
rb.sort_values("elasticity").to_csv(OUT + "ricebowl_detail.csv", index=False)

HIGH_ELASTIC_RB = [1727, 2290]
rball = df[df.category == "Rice Bowl"].copy()
rball["tier"] = np.where(rball.meal_id.isin(HIGH_ELASTIC_RB), "high_elastic", "low_elastic(1109)")
rball.groupby(["tier", "discount_bin"], observed=True)["revenue"].mean().unstack().to_csv(OUT + "ricebowl_tier_revenue.csv")
rball.groupby("tier")["discount_pct"].mean().to_csv(OUT + "ricebowl_tier_discount.csv")

# ============ 7. control checks: time trend, seasonality ============
weekly = df.groupby("week").agg(total_orders=("num_orders", "sum"),
                                 avg_discount=("discount_pct", "mean")).reset_index()
weekly.to_csv(OUT + "weekly_trend.csv", index=False)

# ============ 8. region center counts (why region-level analysis was dropped) ============
region_counts = centers.groupby("region_code")["center_id"].nunique().sort_values(ascending=False)
region_counts.to_csv(OUT + "region_center_counts.csv")

# ============ 9. A/B test sample-size inputs: real weekly per-center Beverages revenue variance ============
bev_weekly_center = df[df.category == "Beverages"].groupby(["week", "center_id"])["revenue"].sum().reset_index()
bev_weekly_center.to_csv(OUT + "bev_weekly_center_revenue.csv", index=False)

print("All metrics computed and saved to", OUT)
print(f"  - {len(elas_df)} qualifying meal x center pairs (of {df.groupby(['meal_id','center_id']).ngroups} total)")
print(f"  - Beverages weekly per-center revenue CV: {bev_weekly_center['revenue'].std()/bev_weekly_center['revenue'].mean()*100:.1f}%")
print(f"  - Regions with only 1 center: {(region_counts==1).sum()} of {len(region_counts)}")
