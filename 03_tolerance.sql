-- 03_tolerance.sql : expected vs actual, with tolerance limits
-- Delivery: on time = actual <= promised; within tolerance = at most 1 day late; breach = more than 1 day late.
-- Margin:   expected margin = the category's median line margin; breach = more than 10 points below it.

DROP VIEW IF EXISTS v_expected_margin CASCADE;
CREATE VIEW v_expected_margin AS
SELECT category,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY margin_ratio)   AS expected_margin
FROM v_orders WHERE in_main_window
GROUP BY category;

DROP VIEW IF EXISTS v_flags;
CREATE VIEW v_flags AS
SELECT v.*,
       e.expected_margin,
       CASE WHEN v.slippage_days > 1 THEN 1 ELSE 0 END             AS delivery_breach,
       CASE WHEN v.margin_ratio < e.expected_margin - 0.10 THEN 1 ELSE 0 END AS margin_breach
FROM v_orders v JOIN v_expected_margin e USING (category)
WHERE v.in_main_window;

-- T1. How many lines break each tolerance?
SELECT COUNT(*)                                        AS order_lines,
       ROUND(100.0 * AVG(delivery_breach), 1)          AS delivery_breach_pct,
       ROUND(100.0 * AVG(margin_breach), 1)            AS margin_breach_pct,
       ROUND(100.0 * AVG(delivery_breach * margin_breach), 1) AS both_pct
FROM v_flags;

-- T2. Where do delivery breaches concentrate? (market x shipping mode)
SELECT market, shipping_mode,
       ROUND(100.0 * AVG(delivery_breach), 1)          AS delivery_breach_pct,
       COUNT(*)                                        AS order_lines
FROM v_flags GROUP BY market, shipping_mode ORDER BY delivery_breach_pct DESC;

-- T3. Expected vs actual margin by category (largest shortfall first, categories with real volume)
SELECT category,
       ROUND((100 * MAX(expected_margin))::numeric, 1)                  AS expected_margin_pct,
       ROUND((100.0 * SUM(profit) / SUM(order_item_total))::numeric, 1) AS actual_margin_pct,
       ROUND((100.0 * SUM(profit) / SUM(order_item_total) - 100 * MAX(expected_margin))::numeric, 1) AS gap_pts,
       ROUND(100.0 * AVG(margin_breach), 1)                             AS margin_breach_pct,
       ROUND(SUM(order_item_total)::numeric, 0)                         AS net_sales
FROM v_flags GROUP BY category HAVING SUM(order_item_total) > 100000
ORDER BY gap_pts LIMIT 15;
