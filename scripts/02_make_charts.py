"""
02_make_charts.py

Generates all 14 charts used in the README from the processed metrics
(data/processed/, produced by 01_compute_metrics.py) plus the raw data
where a chart needs the full row-level dataset (control checks, A/B
sample-size curve).

Run 01_compute_metrics.py first.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

D = "data/processed/"
RAW = "data/raw/"
OUT = "assets/"
os.makedirs(OUT, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.edgecolor"] = "#444444"
plt.rcParams["axes.labelcolor"] = "#222222"
plt.rcParams["text.color"] = "#222222"
plt.rcParams["xtick.color"] = "#444444"
plt.rcParams["ytick.color"] = "#444444"

BLUE, ORANGE, GRAY, RED, GREEN, LIGHTGRAY = (
    "#2E5C8A", "#D97B29", "#9AA0A6", "#C0392B", "#1F8A5F", "#DADCE0"
)
BINS = ["no_disc", "0-5%", "5-15%", "15-30%", "30%+"]


# ---------- 01: category elasticity, ranked ----------
def chart_01():
    cat_elas = pd.read_csv(D + "category_elasticity.csv").sort_values("median")
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = [RED if v <= -3 else (ORANGE if v <= -1.5 else GRAY) for v in cat_elas["median"]]
    bars = ax.barh(cat_elas["category"], cat_elas["median"], color=colors)
    for bar, val in zip(bars, cat_elas["median"]):
        ax.text(val - 0.08, bar.get_y() + bar.get_height() / 2, f"{val:.2f}",
                 va="center", ha="right", fontsize=9, color="#222222", fontweight="bold")
    ax.set_xlabel("Price Elasticity of Demand (median, log-log slope)")
    ax.set_title("Finding 1: Price Elasticity Varies Sharply by Category\n"
                  "(more negative = demand more sensitive to price)", fontsize=13, fontweight="bold", loc="left")
    ax.axvline(-1, color="black", linestyle="--", linewidth=1, alpha=0.6)
    ax.text(-1, -0.9, "unit elastic (-1.0)", fontsize=8, ha="center", color="black", alpha=0.7)
    ax.set_xlim(-4.5, 0.3)
    plt.figtext(0.12, 0.01, "n = 3,534 meal×center pairs with ≥10 distinct price points; "
                             "red = highly elastic, gray = inelastic", fontsize=8, color=GRAY)
    plt.tight_layout()
    plt.savefig(OUT + "01_category_elasticity.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 02: revenue by discount bin, 4 categories, elasticity labeled ----------
def chart_02():
    rev4 = pd.read_csv(D + "revenue_by_discount_4cats.csv")
    cat_elas = pd.read_csv(D + "category_elasticity.csv").set_index("category")["median"]
    cats4 = ["Seafood", "Pizza", "Extras", "Biryani"]
    colors4 = {"Seafood": RED, "Pizza": ORANGE, "Extras": BLUE, "Biryani": GRAY}
    fig, axes = plt.subplots(1, 4, figsize=(16, 5.5))
    for ax, cat in zip(axes, cats4):
        sub = rev4[rev4.category == cat].set_index("discount_bin").reindex(BINS)
        bars = ax.bar(BINS, sub["avg_revenue"] / 1000, color=colors4[cat])
        max_h = (sub["avg_revenue"] / 1000).max()
        for bar, val in zip(bars, sub["avg_revenue"]):
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h - max_h * 0.06, f"{val/1000:.0f}k",
                     ha="center", va="top", fontsize=8, color="white", fontweight="bold")
        ax.set_title(f"{cat}\n(elasticity = {cat_elas[cat]:.2f})", fontsize=11, fontweight="bold")
        ax.set_xticks(range(len(BINS)))
        ax.set_xticklabels(BINS, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Avg Revenue per Meal-Center-Week (thousands, dataset units)" if cat == "Seafood" else "")
    fig.suptitle("Finding 1 (validated): Revenue vs Discount Depth by Category\n"
                  "High-elasticity categories gain revenue from deep discounts; low-elasticity categories lose it",
                  fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    plt.savefig(OUT + "02_revenue_by_discount_4cats.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 03: promo combo lift ----------
def chart_03():
    combo = pd.read_csv(D + "promo_combo_lift.csv")
    combo.columns = ["emailer", "homepage", "mean_orders", "count"]
    labels = ["No Promo", "Homepage Only", "Emailer Only", "Both"]
    combo_sorted = combo.set_index(["emailer", "homepage"]).loc[[(0, 0), (0, 1), (1, 0), (1, 1)]].reset_index()
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(labels, combo_sorted["mean_orders"], color=[GRAY, ORANGE, BLUE, RED])
    baseline = combo_sorted["mean_orders"].iloc[0]
    for bar, val in zip(bars, combo_sorted["mean_orders"]):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 8, f"{val:.0f} orders\n({val/baseline:.2f}x)",
                 ha="center", fontsize=9, fontweight="bold")
    ax.set_ylabel("Avg Orders per Meal-Center-Week (price held ≈ constant, discount ≤5%)")
    ax.set_title("Finding 2: Promotion Channels Lift Orders\n"
                  "(price controlled — this isolates the promo effect from the discount effect)",
                  fontsize=12, fontweight="bold", loc="left")
    ax.set_ylim(0, combo_sorted["mean_orders"].max() * 1.25)
    plt.tight_layout()
    plt.savefig(OUT + "03_promo_combo_lift.png", dpi=150, bbox_inches="tight")
    plt.close()
    return combo_sorted, baseline


# ---------- 04: diminishing returns ----------
def chart_04(combo_sorted, baseline):
    lift_email = combo_sorted.loc[2, "mean_orders"] / baseline
    lift_home = combo_sorted.loc[1, "mean_orders"] / baseline
    lift_both_actual = combo_sorted.loc[3, "mean_orders"] / baseline
    lift_both_expected = lift_email * lift_home
    fig, ax = plt.subplots(figsize=(7, 6))
    bars = ax.bar(["Expected if channels\nwere fully independent\n(multiplicative)",
                    "Actual observed\nlift (both channels)"],
                   [lift_both_expected, lift_both_actual], color=[LIGHTGRAY, RED])
    for bar, val in zip(bars, [lift_both_expected, lift_both_actual]):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.05, f"{val:.2f}x", ha="center",
                 fontsize=12, fontweight="bold")
    shortfall = (1 - lift_both_actual / lift_both_expected) * 100
    ax.annotate(f"-{shortfall:.0f}% shortfall", xy=(1, lift_both_actual), xytext=(0.5, 3.2),
                fontsize=11, color=RED, fontweight="bold", ha="center",
                arrowprops=dict(arrowstyle="->", color=RED))
    ax.set_ylabel("Order Lift vs No-Promo Baseline (x)")
    ax.set_title("Finding 2: Stacking Both Promo Channels Shows\nClear Diminishing Returns",
                  fontsize=12, fontweight="bold", loc="left")
    ax.set_ylim(0, 4.3)
    plt.tight_layout()
    plt.savefig(OUT + "04_promo_diminishing_returns.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 05: elasticity vs promo lift, colored by category ----------
def chart_05():
    epl = pd.read_csv(D + "elasticity_vs_promolift.csv")
    cats = epl["category"].tolist()
    colors = plt.cm.tab20(np.linspace(0, 1, len(cats)))
    color_map = dict(zip(cats, colors))
    offsets = {
        "Starters": (8, -12), "Desert": (8, 10), "Soup": (-35, 8), "Other Snacks": (10, -14),
        "Salad": (8, 6), "Sandwich": (8, 6), "Pizza": (10, 4), "Seafood": (10, 4),
        "Fish": (10, -10), "Rice Bowl": (10, 4), "Extras": (10, 4), "Biryani": (10, 4),
        "Pasta": (10, 6), "Beverages": (10, 6),
    }
    fig, ax = plt.subplots(figsize=(10, 8))
    for _, row in epl.iterrows():
        ax.scatter(row["median_elasticity"], row["lift"], s=row["n_promo"] / 8,
                    color=color_map[row["category"]], alpha=0.85, edgecolor="white", linewidth=1, zorder=3)
    for _, row in epl.iterrows():
        dx, dy = offsets.get(row["category"], (8, 3))
        ax.annotate(row["category"], (row["median_elasticity"], row["lift"]), fontsize=8.5,
                     xytext=(dx, dy), textcoords="offset points", color=color_map[row["category"]],
                     fontweight="bold")
    corr = epl["median_elasticity"].corr(epl["lift"])
    ax.set_xlabel("Price Elasticity (median, more negative = more price-sensitive)")
    ax.set_ylabel("Promotion Lift (x, price-controlled)")
    ax.set_title(f"Finding 3: Price Sensitivity and Promo Responsiveness Are Independent\n"
                  f"correlation = {corr:.2f} (essentially no relationship)", fontsize=12, fontweight="bold", loc="left")
    ax.invert_xaxis()
    plt.figtext(0.12, 0.01, "bubble size = sample size of promoted rows for that category; "
                             "color = category (no ordering implied)", fontsize=8, color="#888888")
    plt.tight_layout()
    plt.savefig(OUT + "05_elasticity_vs_promolift.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 06: within-category spread (dumbbell) ----------
def chart_06():
    spread = pd.read_csv(D + "category_spread.csv").sort_values("range", ascending=True)
    meal_elas = pd.read_csv(D + "meal_elasticity.csv")
    fig, ax = plt.subplots(figsize=(10, 8))
    for i, cat in enumerate(spread["category"]):
        vals = meal_elas[meal_elas.category == cat]["median"].values
        ax.plot([vals.min(), vals.max()], [i, i], color=LIGHTGRAY, linewidth=3, zorder=1)
        ax.scatter(vals, [i] * len(vals), color=BLUE, s=60, zorder=2, edgecolor="white")
    ax.set_yticks(range(len(spread)))
    ax.set_yticklabels(spread["category"])
    for i, cat in enumerate(spread["category"]):
        if cat in ["Beverages", "Rice Bowl"]:
            ax.get_yticklabels()[i].set_color(RED)
            ax.get_yticklabels()[i].set_fontweight("bold")
    ax.set_xlabel("Elasticity of Individual Products within Category (each dot = 1 product)")
    ax.set_title("Finding 4: Category Averages Hide Product-Level Divergence\n"
                  "(Beverages & Rice Bowl in red — internal spread too wide to trust the category average)",
                  fontsize=12, fontweight="bold", loc="left")
    plt.tight_layout()
    plt.savefig(OUT + "06_within_category_spread.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 07: beverages price vs elasticity ----------
def chart_07():
    bev = pd.read_csv(D + "beverages_detail.csv")
    fig, ax = plt.subplots(figsize=(9, 7))
    colors_bev = [RED if c == "Continental" else BLUE for c in bev["cuisine"]]
    ax.scatter(bev["avg_price"], bev["elasticity"], s=bev["avg_orders"] / 3, c=colors_bev,
                alpha=0.75, edgecolor="white", linewidth=1)
    z = np.polyfit(bev["avg_price"], bev["elasticity"], 1)
    xline = np.linspace(bev["avg_price"].min(), bev["avg_price"].max(), 50)
    ax.plot(xline, np.polyval(z, xline), "--", color="black", alpha=0.5, linewidth=1)
    corr = bev["elasticity"].corr(bev["avg_price"])
    ax.set_xlabel("Average Checkout Price (dataset units)")
    ax.set_ylabel("Elasticity (product-level)")
    ax.set_title(f"Beverages: Elasticity Splits by Price Tier\ncorrelation with price = {corr:.2f} — "
                  f"red = Continental (premium), blue = other cuisines", fontsize=12, fontweight="bold", loc="left")
    plt.figtext(0.12, 0.01, "bubble size = average weekly orders (popularity)", fontsize=8, color=GRAY)
    plt.tight_layout()
    plt.savefig(OUT + "07_beverages_price_elasticity.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 08: beverages discount mismatch ----------
def chart_08():
    bev_disc = pd.read_csv(D + "beverages_tier_discount.csv")
    bev_disc.columns = ["tier", "avg_discount"]
    fig, ax = plt.subplots(figsize=(7, 6))
    bars = ax.bar(["High-Elastic\n(Continental)", "Low-Elastic\n(Rest)"], bev_disc["avg_discount"], color=[RED, BLUE])
    for bar, val in zip(bars, bev_disc["avg_discount"]):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.1, f"{val:.2f}%", ha="center",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Current Average Discount (%)")
    ax.set_title("Finding 4: Current Discount Policy Is Backwards for Beverages\n"
                  "(the price-sensitive tier is discounted LESS, not more)", fontsize=12, fontweight="bold", loc="left")
    plt.tight_layout()
    plt.savefig(OUT + "08_beverages_discount_mismatch.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 09: rice bowl revenue by discount ----------
def chart_09():
    rb_rev = pd.read_csv(D + "ricebowl_tier_revenue.csv").set_index("tier").T.reindex(BINS)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(BINS, rb_rev["high_elastic"] / 1000, marker="o", color=RED, linewidth=2, label="High-Elastic (1727, 2290)")
    ax.plot(BINS, rb_rev["low_elastic(1109)"] / 1000, marker="o", color=BLUE, linewidth=2, label="Low-Elastic (1109)")
    for x, y in zip(BINS, rb_rev["high_elastic"] / 1000):
        ax.text(x, y + 8, f"{y:.0f}k", ha="center", fontsize=8, color=RED)
    for x, y in zip(BINS, rb_rev["low_elastic(1109)"] / 1000):
        ax.text(x, y - 18, f"{y:.0f}k", ha="center", fontsize=8, color=BLUE)
    ax.set_ylabel("Avg Revenue per Meal-Center-Week (thousands, dataset units)")
    ax.set_xlabel("Discount Depth")
    ax.set_title("Rice Bowl: Same Mispricing Pattern as Beverages\n"
                  "(cause unexplained by available fields — but the revenue effect is real)",
                  fontsize=12, fontweight="bold", loc="left")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT + "09_ricebowl_revenue.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 10: control check — center type & size ----------
def chart_10():
    elas_df = pd.read_csv(D + "pair_elasticity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    ct = elas_df.groupby("center_type")["elasticity"].agg(["mean", "count"])
    bars = axes[0].bar(ct.index, ct["mean"], color=[BLUE, ORANGE, GRAY])
    for bar, val, n in zip(bars, ct["mean"], ct["count"]):
        axes[0].text(bar.get_x() + bar.get_width() / 2, val - 0.1, f"{val:.2f} (n={n})",
                      ha="center", va="top", fontsize=9, color="#222222", fontweight="bold")
    axes[0].set_ylabel("Mean Elasticity")
    axes[0].set_ylim(-2.8, 0.2)
    axes[0].axhline(0, color="#444444", linewidth=0.8)
    lo, hi = ct["mean"].min(), ct["mean"].max()
    axes[0].set_title(f"A. Elasticity by Center Type\n(range: {lo:.2f} to {hi:.2f} — no meaningful difference)",
                        fontsize=10, fontweight="bold")

    axes[1].scatter(elas_df["op_area"], elas_df["elasticity"], s=10, alpha=0.3, color=BLUE)
    z = np.polyfit(elas_df["op_area"], elas_df["elasticity"], 1)
    xline = np.linspace(elas_df["op_area"].min(), elas_df["op_area"].max(), 50)
    axes[1].plot(xline, np.polyval(z, xline), "--", color=RED, linewidth=2)
    corr = elas_df["op_area"].corr(elas_df["elasticity"])
    axes[1].set_xlabel("Center Size (op_area)")
    axes[1].set_ylabel("Elasticity (per meal×center pair)")
    axes[1].set_title(f"B. Center Size vs Elasticity\n(correlation = {corr:.2f} — essentially flat)",
                        fontsize=10, fontweight="bold")

    fig.suptitle("Control Check 1: Elasticity Differences Are Not Explained by Which Centers Sell the Product",
                  fontsize=12, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    plt.savefig(OUT + "10_control_center.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 11: control check — time trend ----------
def chart_11():
    weekly = pd.read_csv(D + "weekly_trend.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].scatter(weekly["week"], weekly["total_orders"] / 1000, s=12, alpha=0.5, color=BLUE)
    z1 = np.polyfit(weekly["week"], weekly["total_orders"] / 1000, 1)
    axes[0].plot(weekly["week"], np.polyval(z1, weekly["week"]), "--", color=RED, linewidth=2)
    corr1 = weekly["week"].corr(weekly["total_orders"])
    axes[0].set_xlabel("Week Number (1-145)")
    axes[0].set_ylabel("Total Weekly Orders (thousands)")
    axes[0].set_title(f"A. Order Volume Over Time\n(correlation with week = {corr1:.2f} — no trend)",
                        fontsize=10, fontweight="bold")

    axes[1].scatter(weekly["week"], weekly["avg_discount"], s=12, alpha=0.5, color=ORANGE)
    z2 = np.polyfit(weekly["week"], weekly["avg_discount"], 1)
    axes[1].plot(weekly["week"], np.polyval(z2, weekly["week"]), "--", color=RED, linewidth=2)
    corr2 = weekly["week"].corr(weekly["avg_discount"])
    axes[1].set_xlabel("Week Number (1-145)")
    axes[1].set_ylabel("Average Discount (%)")
    axes[1].set_title(f"B. Discount Depth Over Time\n(correlation with week = {corr2:.2f} — no clustering)",
                        fontsize=10, fontweight="bold")

    fig.suptitle("Control Check 2: No Seasonal/Time Trend That Could Bias the Discount-Revenue Relationship",
                  fontsize=12, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    plt.savefig(OUT + "11_control_time.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 12: A/B test sample-size feasibility ----------
def chart_12():
    bev_wc = pd.read_csv(D + "bev_weekly_center_revenue.csv")
    cv_weekly = bev_wc["revenue"].std() / bev_wc["revenue"].mean()
    z_alpha, z_beta, effect = 1.96, 0.84, 0.15  # 5% two-sided sig, 80% power, detect 15% change

    weeks = np.arange(1, 21)
    cv_eff = cv_weekly / np.sqrt(weeks)
    n_per_arm = 2 * (z_alpha + z_beta) ** 2 * (cv_eff / effect) ** 2

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(weeks, n_per_arm, color=BLUE, linewidth=2, marker="o", markersize=4)
    ax.axhline(38, color=RED, linestyle="--", linewidth=1.5, label="Max available per arm (38 of 77 centers)")
    ax.set_xlabel("Test Duration (weeks)")
    ax.set_ylabel("Required Sample Size per Arm")
    ax.set_title("A/B Test Feasibility: Required Centers per Arm vs. Test Duration\n"
                  "(to detect a 15% Beverages revenue change, 80% power, 5% significance)",
                  fontsize=11, fontweight="bold")
    ax.set_ylim(0, 150)
    for w in [8, 12]:
        idx = w - 1
        ax.annotate(f"{w}wk: {n_per_arm[idx]:.0f}/arm", xy=(w, n_per_arm[idx]), xytext=(w + 1, n_per_arm[idx] + 15),
                    fontsize=9, fontweight="bold", color=GREEN, arrowprops=dict(arrowstyle="->", color=GREEN))
    ax.legend()
    plt.figtext(0.12, 0.01, f"Based on real weekly per-center Beverages revenue variance in this dataset: "
                             f"CV = {cv_weekly*100:.1f}%", fontsize=8, color="#888888")
    plt.tight_layout()
    plt.savefig(OUT + "12_ab_sample_size.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 13: why region-level analysis was dropped ----------
def chart_13():
    rc = pd.read_csv(D + "region_center_counts.csv")
    rc.columns = ["region_code", "n_centers"]
    rc = rc.sort_values("n_centers", ascending=True)
    colors = [RED if n == 1 else BLUE for n in rc["n_centers"]]
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.barh(rc["region_code"].astype(str), rc["n_centers"], color=colors)
    for bar, val in zip(bars, rc["n_centers"]):
        ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2, str(val), va="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("Number of Fulfilment Centers")
    ax.set_ylabel("Region Code")
    n_single = (rc["n_centers"] == 1).sum()
    ax.set_title(f'Why Region-Level Analysis Was Dropped\n{n_single} of {len(rc)} regions (red) have only 1 '
                  f'center — "region effect" would just be "center effect"', fontsize=11, fontweight="bold")
    ax.set_xlim(0, rc["n_centers"].max() + 3)
    plt.tight_layout()
    plt.savefig(OUT + "13_region_dropped.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 14: how promotion lift is calculated (worked example) ----------
def chart_14():
    ex = pd.read_csv(D + "promolift_worked_example.csv")
    elas = {"Seafood": -3.84, "Beverages": -1.53}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
    for ax, cat in zip(axes, ["Seafood", "Beverages"]):
        sub = ex[ex.category == cat].set_index("any_promo")
        vals = [sub.loc[0, "mean"], sub.loc[1, "mean"]]
        counts = [sub.loc[0, "count"], sub.loc[1, "count"]]
        bars = ax.bar(["No Promotion", "Any Promotion"], vals, color=[GRAY, RED if cat == "Seafood" else BLUE])
        max_h = max(vals)
        for bar, val, n in zip(bars, vals, counts):
            ax.text(bar.get_x() + bar.get_width() / 2, val - max_h * 0.07, f"{val:.1f} (n={n})",
                     ha="center", va="top", fontsize=9, fontweight="bold", color="white")
        lift = vals[1] / vals[0]
        ax.annotate("", xy=(1, vals[1] * 0.55), xytext=(0, vals[0] * 0.55),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.5, linestyle="--"))
        ax.text(0.5, max_h * 0.35, f"÷ = {lift:.2f}x", ha="center", fontsize=11, fontweight="bold",
                 color="black", bbox=dict(boxstyle="round", facecolor="white", edgecolor="black"))
        note = "most sensitive" if cat == "Seafood" else "mid"
        ax.set_title(f"{cat}\n(elasticity {elas[cat]}, {note})", fontsize=10, fontweight="bold")
        ax.set_ylim(0, max_h * 1.15)
        ax.set_ylabel("Avg Orders per Meal-Center-Week" if cat == "Seafood" else "")
    fig.suptitle('How "Promotion Lift" Is Calculated: Avg Orders, Promoted ÷ Non-Promoted\n'
                  "(price held ≈ constant — discount ≤5% only)", fontsize=12, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    plt.savefig(OUT + "14_promolift_calc_example.png", dpi=150, bbox_inches="tight")
    plt.close()


# ---------- 15: recommendation matrix ----------
def chart_15():
    import matplotlib.patches as patches
    quadrants = [
        {"xy": (0, 0.5), "color": "#E8F0E8", "title": "Discount deeply for volume",
         "sub": "Price is the main lever;\npromotion adds little", "examples": "e.g. Seafood, Pizza"},
        {"xy": (0.5, 0.5), "color": "#FFF3E0", "title": "Deep discount + promote",
         "sub": "Both levers work — split\nBeverages/Rice Bowl by product", "examples": "e.g. Rice Bowl, Beverages*"},
        {"xy": (0, 0), "color": "#F5F5F5", "title": "Leave alone",
         "sub": "Neither lever moves\nthis category", "examples": "e.g. Biryani, Extras"},
        {"xy": (0.5, 0), "color": "#E3EDF5", "title": "Promote without discounting",
         "sub": "The traffic lever works,\nprice doesn't", "examples": "e.g. Sandwich, Salad"},
    ]
    fig, ax = plt.subplots(figsize=(10, 8))
    for q in quadrants:
        rect = patches.Rectangle(q["xy"], 0.5, 0.5, facecolor=q["color"], edgecolor="#888888", linewidth=1.5)
        ax.add_patch(rect)
        cx, cy = q["xy"][0] + 0.25, q["xy"][1] + 0.25
        ax.text(cx, cy + 0.12, q["title"], ha="center", va="center", fontsize=13, fontweight="bold", color="#222222")
        ax.text(cx, cy - 0.01, q["sub"], ha="center", va="center", fontsize=9.5, color="#444444")
        ax.text(cx, cy - 0.14, q["examples"], ha="center", va="center", fontsize=9, style="italic", color="#666666")
    ax.text(0.5, -0.06, "Price Sensitivity (Elasticity) →", ha="center", fontsize=11, fontweight="bold")
    ax.text(0.25, -0.03, "Low", ha="center", fontsize=9, color="#666666")
    ax.text(0.75, -0.03, "High", ha="center", fontsize=9, color="#666666")
    ax.text(-0.08, 0.5, "Promotion Responsiveness →", ha="center", va="center", rotation=90, fontsize=11, fontweight="bold")
    ax.text(-0.04, 0.25, "Low", ha="center", va="center", rotation=90, fontsize=9, color="#666666")
    ax.text(-0.04, 0.75, "High", ha="center", va="center", rotation=90, fontsize=9, color="#666666")
    ax.set_xlim(-0.15, 1.02)
    ax.set_ylim(-0.12, 1.05)
    ax.axis("off")
    ax.set_title("Recommendation Matrix: Pricing & Promotion Strategy by Category\n"
                 "*Beverages and Rice Bowl need product-level splits per Finding 4, not single-cell treatment",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT + "15_recommendation_matrix.png", dpi=150, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    chart_01()
    chart_02()
    combo_sorted, baseline = chart_03()
    chart_04(combo_sorted, baseline)
    chart_05()
    chart_06()
    chart_07()
    chart_08()
    chart_09()
    chart_10()
    chart_11()
    chart_12()
    chart_13()
    chart_14()
    chart_15()
    print(f"All 15 charts saved to {OUT}")
