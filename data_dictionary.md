# Data Dictionary

Three raw tables, joined on `meal_id` and `center_id`. All fields below are as provided by the source dataset — no field was renamed or transformed except where noted (`discount_pct`, `revenue`, `discount_bin` are derived columns computed in `scripts/01_compute_metrics.py`, not part of the raw data).

## `train.csv` (456,548 rows — the core transaction table)

| Field | Type | Description |
|---|---|---|
| `id` | int | Unique row identifier |
| `week` | int | Week number, 1–145 (no calendar date is provided — this is relative time, not tied to a specific year) |
| `center_id` | int | Fulfilment center identifier, joins to `fulfilment_center_info.csv` |
| `meal_id` | int | Product identifier, joins to `meal_info.csv` |
| `checkout_price` | float | Actual price charged to the customer that week, at that center, for that meal |
| `base_price` | float | List/undiscounted price for the same meal, center, and week |
| `emailer_for_promotion` | int (0/1) | Whether an email marketing campaign promoted this meal that week |
| `homepage_featured` | int (0/1) | Whether this meal was featured on the homepage that week |
| `num_orders` | int | Number of orders placed for this meal, at this center, that week — the demand variable used throughout the analysis |

**Derived fields added during analysis (not in the raw file):**

| Field | Formula | Used in |
|---|---|---|
| `discount_pct` | `(base_price - checkout_price) / base_price * 100` | All revenue/discount charts |
| `revenue` | `checkout_price * num_orders` | Finding 1, Finding 4 |
| `discount_bin` | `discount_pct` bucketed into `no_disc / 0-5% / 5-15% / 15-30% / 30%+` | Finding 1, Finding 4 |

## `meal_info.csv` (51 rows — one per product)

| Field | Type | Description |
|---|---|---|
| `meal_id` | int | Product identifier |
| `category` | string | Product category (14 distinct values: Seafood, Pizza, Beverages, Rice Bowl, etc.) |
| `cuisine` | string | Cuisine type (4 distinct values: Continental, Italian, Indian, Thai) |

## `fulfilment_center_info.csv` (77 rows — one per center)

| Field | Type | Description |
|---|---|---|
| `center_id` | int | Fulfilment center identifier |
| `city_code` | int | City the center operates in |
| `region_code` | int | Broader region grouping (8 distinct values — see Limitations for why region-level analysis was dropped) |
| `center_type` | string | TYPE_A / TYPE_B / TYPE_C — an operational classification, meaning not further specified by the data source |
| `op_area` | float | Operational area / size metric for the center, range 0.9–7.0 (unit not specified by the data source — treated as a relative size proxy, not an absolute measurement) |

## Notes on data quality

- No missing values in any of the three tables (verified during initial data validation).
- `checkout_price` and `base_price` are both present and populated for every row — no row has an undefined discount.
- All fields are used as provided; no imputation was needed or performed.
