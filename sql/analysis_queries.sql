-- ============================================================================
-- analysis_queries.sql
--
-- SQL equivalents of the core pandas aggregations behind the README findings.
-- Written against three tables (train, meal_info, fulfilment_center_info),
-- standard ANSI SQL — tested logic against PostgreSQL/SQLite syntax.
--
-- Note: the elasticity coefficients themselves (log-log regression slopes)
-- are NOT reproducible in pure SQL — that step needs a stats/regression
-- library (see scripts/01_compute_metrics.py). The queries below cover every
-- aggregation, join, and business-logic step that SQL is well suited for:
-- the revenue/discount/promo tables that sit underneath each chart.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 00. Base view: adds discount_pct, revenue, and discount_bin to every row.
--     Every query below builds on this view instead of repeating the CASE
--     statement and derived columns each time.
-- ----------------------------------------------------------------------------
CREATE VIEW v_orders AS
SELECT
    t.id,
    t.week,
    t.center_id,
    t.meal_id,
    t.checkout_price,
    t.base_price,
    t.emailer_for_promotion,
    t.homepage_featured,
    t.num_orders,
    m.category,
    m.cuisine,
    c.center_type,
    c.region_code,
    c.op_area,
    (t.base_price - t.checkout_price) / t.base_price * 100.0            AS discount_pct,
    t.checkout_price * t.num_orders                                    AS revenue,
    CASE
        WHEN (t.base_price - t.checkout_price) / t.base_price * 100.0 <= 0  THEN 'no_disc'
        WHEN (t.base_price - t.checkout_price) / t.base_price * 100.0 <= 5  THEN '0-5%'
        WHEN (t.base_price - t.checkout_price) / t.base_price * 100.0 <= 15 THEN '5-15%'
        WHEN (t.base_price - t.checkout_price) / t.base_price * 100.0 <= 30 THEN '15-30%'
        ELSE '30%+'
    END                                                                  AS discount_bin
FROM train t
JOIN meal_info m               ON t.meal_id = m.meal_id
JOIN fulfilment_center_info c  ON t.center_id = c.center_id;


-- ----------------------------------------------------------------------------
-- 01. Finding 1 (Chart 02): avg revenue per row by category x discount bin
--     — the core revenue-validation table for Seafood/Pizza/Extras/Biryani.
-- ----------------------------------------------------------------------------
SELECT
    category,
    discount_bin,
    ROUND(AVG(revenue), 0)   AS avg_revenue,
    ROUND(AVG(num_orders), 1) AS avg_orders,
    COUNT(*)                 AS n
FROM v_orders
WHERE category IN ('Seafood', 'Pizza', 'Extras', 'Biryani')
GROUP BY category, discount_bin
ORDER BY category,
    CASE discount_bin
        WHEN 'no_disc' THEN 1 WHEN '0-5%' THEN 2 WHEN '5-15%' THEN 3
        WHEN '15-30%' THEN 4 ELSE 5
    END;


-- ----------------------------------------------------------------------------
-- 02. Finding 1 (Chart 10, Panel A): mean elasticity input check — orders
--     and price variability by center_type, used to sanity-check that
--     elasticity isn't secretly a center-type effect.
--     (elasticity itself is computed in Python; this is the descriptive
--     precursor showing order/price variation by center type)
-- ----------------------------------------------------------------------------
SELECT
    center_type,
    COUNT(DISTINCT center_id)          AS n_centers,
    COUNT(*)                            AS n_rows,
    ROUND(AVG(checkout_price), 2)       AS avg_price,
    ROUND(AVG(num_orders), 1)           AS avg_orders
FROM v_orders
GROUP BY center_type
ORDER BY center_type;


-- ----------------------------------------------------------------------------
-- 03. Finding 1 (Chart 11): weekly order volume and discount trend
--     — the control check confirming no seasonal/time drift.
-- ----------------------------------------------------------------------------
SELECT
    week,
    SUM(num_orders)          AS total_orders,
    ROUND(AVG(discount_pct), 2) AS avg_discount_pct
FROM v_orders
GROUP BY week
ORDER BY week;


-- ----------------------------------------------------------------------------
-- 04. Finding 2 (Chart 03): promotion channel lift, price held ~constant
--     (discount <= 5%) — the four-way combo table (none/email/homepage/both).
-- ----------------------------------------------------------------------------
SELECT
    emailer_for_promotion,
    homepage_featured,
    ROUND(AVG(num_orders), 1) AS avg_orders,
    COUNT(*)                  AS n
FROM v_orders
WHERE discount_pct <= 5
GROUP BY emailer_for_promotion, homepage_featured
ORDER BY emailer_for_promotion, homepage_featured;


-- ----------------------------------------------------------------------------
-- 05. Finding 3 (Chart 14): worked example — promo lift for Seafood and
--     Beverages specifically (the two axis-extreme categories).
-- ----------------------------------------------------------------------------
SELECT
    category,
    CASE WHEN emailer_for_promotion = 1 OR homepage_featured = 1
         THEN 1 ELSE 0 END      AS any_promo,
    ROUND(AVG(num_orders), 1)   AS avg_orders,
    COUNT(*)                    AS n
FROM v_orders
WHERE discount_pct <= 5
  AND category IN ('Seafood', 'Beverages')
GROUP BY category, any_promo
ORDER BY category, any_promo;


-- ----------------------------------------------------------------------------
-- 06. Finding 3 (Chart 05 input): promo lift by category, price-controlled
--     — feeds the elasticity-vs-promo-lift scatter (elasticity itself is
--     joined in from the Python-computed table, category_elasticity.csv).
-- ----------------------------------------------------------------------------
SELECT
    category,
    CASE WHEN emailer_for_promotion = 1 OR homepage_featured = 1
         THEN 1 ELSE 0 END      AS any_promo,
    ROUND(AVG(num_orders), 1)   AS avg_orders,
    COUNT(*)                    AS n
FROM v_orders
WHERE discount_pct <= 5
GROUP BY category, any_promo
ORDER BY category, any_promo;


-- ----------------------------------------------------------------------------
-- 07. Finding 4 (Chart 08): Beverages — current discount policy by
--     elasticity tier (Continental high-elastic vs. the rest).
-- ----------------------------------------------------------------------------
SELECT
    CASE WHEN meal_id IN (1207, 2322, 1230)
         THEN 'high_elastic_continental' ELSE 'low_elastic_rest' END AS tier,
    ROUND(AVG(discount_pct), 2)  AS avg_discount_pct,
    ROUND(AVG(checkout_price),2) AS avg_price,
    COUNT(*)                     AS n
FROM v_orders
WHERE category = 'Beverages'
GROUP BY tier;


-- ----------------------------------------------------------------------------
-- 08. Finding 4 (Chart 09): Rice Bowl — revenue by discount bin, split by
--     elasticity tier (meal 1109 vs. the other two).
-- ----------------------------------------------------------------------------
SELECT
    CASE WHEN meal_id IN (1727, 2290) THEN 'high_elastic' ELSE 'low_elastic_1109' END AS tier,
    discount_bin,
    ROUND(AVG(revenue), 0) AS avg_revenue,
    COUNT(*)               AS n
FROM v_orders
WHERE category = 'Rice Bowl'
GROUP BY tier, discount_bin
ORDER BY tier,
    CASE discount_bin
        WHEN 'no_disc' THEN 1 WHEN '0-5%' THEN 2 WHEN '5-15%' THEN 3
        WHEN '15-30%' THEN 4 ELSE 5
    END;


-- ----------------------------------------------------------------------------
-- 09. Limitations (Chart 13): centers per region — why region-level
--     analysis was dropped (4 of 8 regions have only 1 center).
-- ----------------------------------------------------------------------------
SELECT
    region_code,
    COUNT(DISTINCT center_id) AS n_centers
FROM fulfilment_center_info
GROUP BY region_code
ORDER BY n_centers DESC;


-- ----------------------------------------------------------------------------
-- 10. Proposed A/B Test: real weekly per-center Beverages revenue —
--     the input used to compute test-duration feasibility (Chart 12).
-- ----------------------------------------------------------------------------
SELECT
    week,
    center_id,
    SUM(revenue) AS weekly_center_revenue
FROM v_orders
WHERE category = 'Beverages'
GROUP BY week, center_id
ORDER BY week, center_id;


-- ----------------------------------------------------------------------------
-- 11. Top-level sanity check: overall dataset shape, referenced in the
--     README's Business Context section.
-- ----------------------------------------------------------------------------
SELECT
    COUNT(*)                                    AS total_rows,
    COUNT(DISTINCT week)                        AS n_weeks,
    COUNT(DISTINCT center_id)                   AS n_centers,
    COUNT(DISTINCT meal_id)                     AS n_meals,
    COUNT(DISTINCT category)                    AS n_categories,
    ROUND(AVG(CASE WHEN discount_pct > 0  THEN 1.0 ELSE 0 END) * 100, 1) AS pct_rows_discounted,
    ROUND(AVG(CASE WHEN discount_pct < 0  THEN 1.0 ELSE 0 END) * 100, 1) AS pct_rows_price_increase,
    ROUND(AVG(CASE WHEN emailer_for_promotion = 1 OR homepage_featured = 1
               THEN 1.0 ELSE 0 END) * 100, 1)   AS pct_rows_any_promo
FROM v_orders;
