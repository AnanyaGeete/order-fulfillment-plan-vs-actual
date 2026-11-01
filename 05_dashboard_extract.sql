-- 05_dashboard_extract.sql : small summary tables for the dashboard (exported to JSON)
-- Cube A: month x region x shipping mode x segment
COPY (
SELECT order_month, market, order_region, shipping_mode, customer_segment,
       COUNT(*) lines, SUM(on_time) on_time, SUM(within_tolerance) within_tol,
       SUM(CASE WHEN slippage_days > 1 THEN 1 ELSE 0 END) breach,
       SUM(slippage_days) slip_sum, SUM(days_real) real_sum, SUM(days_scheduled) sched_sum,
       ROUND(SUM(sales)::numeric,2) sales, ROUND(SUM(discount)::numeric,2) discount,
       ROUND(SUM(order_item_total)::numeric,2) net, ROUND(SUM(profit)::numeric,2) profit,
       ROUND(SUM(GREATEST(discount - 0.10*sales,0))::numeric,2) save10,
       ROUND(SUM(GREATEST(discount - 0.05*sales,0))::numeric,2) save5,
       ROUND(SUM(GREATEST(discount - 0.15*sales,0))::numeric,2) save15,
       SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) loss_lines,
       ROUND(COALESCE(SUM(profit) FILTER (WHERE profit < 0),0)::numeric,2) loss_amt,
       SUM(margin_breach) margin_breach
FROM v_flags   -- v_flags (03_tolerance.sql) = main window + tolerance flags
GROUP BY 1,2,3,4,5) TO STDOUT CSV HEADER;

-- Cube B: year x category x market x shipping mode x segment x discount band
COPY (
SELECT EXTRACT(YEAR FROM order_month)::int yr, department, category, market, shipping_mode, customer_segment, discount_band,
       COUNT(*) lines, SUM(on_time) on_time, ROUND(SUM(sales)::numeric,2) sales, ROUND(SUM(discount)::numeric,2) discount,
       ROUND(SUM(order_item_total)::numeric,2) net, ROUND(SUM(profit)::numeric,2) profit,
       ROUND(SUM(GREATEST(discount - 0.10*sales,0))::numeric,2) save10,
       SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) loss_lines,
       ROUND(COALESCE(SUM(profit) FILTER (WHERE profit < 0),0)::numeric,2) loss_amt,
       SUM(margin_breach) margin_breach
FROM v_flags
GROUP BY 1,2,3,4,5,6,7) TO STDOUT CSV HEADER;

-- Cube S: slippage distribution
COPY (
SELECT slippage_days, shipping_mode, EXTRACT(YEAR FROM order_month)::int yr, market, customer_segment, COUNT(*) n
FROM v_flags GROUP BY 1,2,3,4,5) TO STDOUT CSV HEADER;

-- Monthly series for the forecast
COPY (
SELECT order_month, COUNT(DISTINCT order_id) orders, COUNT(*) lines, AVG(on_time) on_time,
       SUM(profit)/SUM(order_item_total) margin
FROM v_orders GROUP BY 1 ORDER BY 1) TO STDOUT CSV HEADER;
