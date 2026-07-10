# Methodology Appendix

Technical details behind the main README, for readers who want the full method rather than the business narrative. Every number here matches what's cited in the main report — this document explains *how*, the main report explains *what it means*.

## 1. Price elasticity estimation

**Method:** log-log OLS regression. For a given meal×center pair, we fit:

```
log(num_orders) = β₀ + β₁ · log(checkout_price) + ε
```

β₁ is the elasticity — the % change in orders associated with a 1% change in price, holding that specific meal/center's own price history as the source of variation (not a cross-sectional comparison across different products).

**Qualifying criteria:** a meal×center pair is only included if it has:
- ≥10 distinct price points (enough price variation to fit a meaningful slope)
- ≥20 total observations (enough weeks of data)

3,534 of 3,597 total meal×center pairs qualified (98.2%).

**Aggregation to category level:** the *median* (not mean) of all qualifying pairs' elasticity within a category, to reduce sensitivity to outlier pairs — e.g., a single noisy pair with a very large slope doesn't dominate the category number the way it would under a mean.

**Sanity check:** 96.9% of the 3,534 pairs returned a negative coefficient (price up → orders down), which is the behaviorally expected sign. This isn't guaranteed by the method — a pair with genuinely random or reversed price/order behavior would fail this check — so the high pass rate is evidence the estimates are picking up real price-demand relationships, not noise.

## 2. Why log-log, not a linear model

A log-log slope is directly interpretable as a % elasticity (the standard economics definition), whereas a linear regression of `num_orders` on `checkout_price` would give a slope in raw units (orders per dollar) that doesn't generalize across products at very different price and volume scales. Since this report compares elasticity across 14 categories with different absolute price levels, the log-log form is the one that makes those comparisons valid.

## 3. Promotion lift, and why it's price-controlled

Promotion (`emailer_for_promotion`, `homepage_featured`) is correlated with discounting in this dataset — rows with promotion active carry a materially deeper average discount than rows without. This means a naive comparison of "promoted vs. non-promoted" order volume would conflate the promotion effect with the discount effect.

**Control applied:** every promotion-lift number in this report (Findings 2 and 3) is computed only on rows with `discount_pct <= 5%`, i.e. price held approximately flat. This isolates the promotion channel's own effect. It's a restriction on the sample, not a statistical adjustment — the tradeoff is a smaller sample for the promoted-rows group in some categories (flagged inline wherever n < 100).

## 4. Confound checks (Finding 1)

Two alternative explanations were tested and ruled out as primary drivers of the category elasticity differences:

- **Center type / size:** elasticity means by `center_type` range from -2.22 to -2.41 (a narrow band), and the correlation between `op_area` (center size) and pair-level elasticity is -0.09 (see `sql/analysis_queries.sql`, query 02, for the underlying aggregation).
- **Time trend:** weekly total order volume correlates with week number at 0.11; weekly average discount depth correlates with week number at -0.12. Neither shows meaningful drift across the 145-week window (query 03).

Both are necessary-but-not-sufficient checks: they rule out two specific, testable alternative explanations, not every possible confound. Price was not randomly assigned in this dataset (this is observational, not experimental data), so residual confounding from factors not captured in the available fields cannot be fully excluded — this is why the report frames these results as "directionally reliable" rather than causal, and why the proposed A/B test exists.

## 5. A/B test sample-size calculation

**Formula used** (two-sample comparison of means, detecting a relative effect):

```
n per arm = 2 · (z_α/2 + z_β)² · (CV / effect_size)²
```

Where:
- `CV` = coefficient of variation (std. dev. / mean) of the outcome metric
- `z_α/2` = 1.96 (5% two-sided significance)
- `z_β` = 0.84 (80% power)
- `effect_size` = 0.15 (the minimum relative change the test is designed to detect)

**Input data:** real weekly per-center Beverages revenue from this dataset (`sql/analysis_queries.sql`, query 10) has CV = 58.9% — noisier than a naive first guess, which is why the sample-size curve (Chart 12) shows required centers-per-arm dropping sharply as test duration increases (averaging over T weeks reduces effective CV by √T).

## 6. Suggested robustness extension (not yet implemented)

The meal×center pair-level approach used here already controls for center-specific and product-specific baseline differences implicitly (each pair gets its own slope, estimated from its own price history). A complementary check worth adding in a future iteration would be a pooled panel regression with explicit fixed effects:

```
log(num_orders) ~ log(checkout_price) + emailer_for_promotion + homepage_featured
                 + C(week) + C(center_id) + C(category)
```

This would test whether the category elasticity ranking is stable when week and center effects are controlled for simultaneously in one model, rather than implicitly through the pair-level design. Not included in the current version of this analysis — noted here as a documented next step, not silently assumed to be unnecessary.
