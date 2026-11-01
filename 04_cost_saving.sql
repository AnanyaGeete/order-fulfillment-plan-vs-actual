-- 04_cost_saving.sql : business case for a discount cap
-- Assumption: the same orders would still be placed with a lower discount, and costs stay the same,
-- so every unit of discount not given becomes profit. This is an upper-bound estimate.

-- C1. Discount given vs profit earned
SELECT ROUND(SUM(sales)::numeric, 0)                    AS gross_sales,
       ROUND(SUM(discount)::numeric, 0)                 AS discount_given,
       ROUND(SUM(profit)::numeric, 0)                   AS profit,
       ROUND((100.0 * SUM(discount) / SUM(profit))::numeric, 1) AS discount_as_pct_of_profit
FROM v_orders WHERE in_main_window;

-- C2. Saving from capping discounts at 5%, 10% and 15%
SELECT cap,
       ROUND(SUM(GREATEST(discount - cap * sales, 0))::numeric, 0)              AS discount_saved,
       ROUND((100.0 * SUM(GREATEST(discount - cap * sales, 0)) / SUM(profit))::numeric, 1) AS profit_uplift_pct,
       ROUND(100.0 * AVG(CASE WHEN discount_pct > cap THEN 1 ELSE 0 END), 1)    AS lines_affected_pct
FROM v_orders CROSS JOIN (VALUES (0.05), (0.10), (0.15)) AS c(cap)
WHERE in_main_window
GROUP BY cap ORDER BY cap;

-- C3. Same 10% cap by category: where would it matter most?
SELECT category,
       ROUND(SUM(GREATEST(discount - 0.10 * sales, 0))::numeric, 0) AS saving_at_10pct_cap,
       ROUND((100.0 * SUM(profit) / SUM(order_item_total))::numeric, 1) AS margin_pct
FROM v_orders WHERE in_main_window
GROUP BY category ORDER BY saving_at_10pct_cap DESC LIMIT 10;
