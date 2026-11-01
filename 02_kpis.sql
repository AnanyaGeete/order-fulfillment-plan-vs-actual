-- 02_kpis.sql : the business questions (main window Jan 2015 - Sep 2017)

-- Q1. Headline KPIs
SELECT COUNT(DISTINCT order_id)                                    AS orders,
       COUNT(*)                                                    AS order_lines,
       ROUND(100.0 * AVG(on_time), 1)                              AS on_time_pct,
       ROUND(100.0 * AVG(within_tolerance), 1)                     AS within_tolerance_pct,
       ROUND(AVG(slippage_days), 2)                                AS avg_slippage_days,
       ROUND((100.0 * SUM(profit) / SUM(order_item_total))::numeric, 1) AS margin_pct
FROM v_orders WHERE in_main_window;

-- Q2. Plan vs actual delivery by shipping mode
SELECT shipping_mode,
       days_scheduled                                              AS promised_days,
       ROUND(AVG(days_real), 2)                                    AS avg_actual_days,
       ROUND(100.0 * AVG(on_time), 1)                              AS on_time_pct,
       ROUND(100.0 * AVG(within_tolerance), 1)                     AS within_tolerance_pct,
       COUNT(*)                                                    AS order_lines
FROM v_orders WHERE in_main_window
GROUP BY shipping_mode, days_scheduled
ORDER BY on_time_pct;

-- Q3. Delivery by market (is it a regional or a process problem?)
SELECT market,
       ROUND(100.0 * AVG(on_time), 1)                              AS on_time_pct,
       ROUND(AVG(slippage_days), 2)                                AS avg_slippage_days
FROM v_orders WHERE in_main_window
GROUP BY market ORDER BY on_time_pct;

-- Q4. Does a bigger discount mean a smaller margin?
SELECT discount_band,
       COUNT(*)                                                    AS order_lines,
       ROUND((100.0 * SUM(discount) / SUM(sales))::numeric, 1)          AS avg_discount_pct,
       ROUND((100.0 * SUM(profit) / SUM(order_item_total))::numeric, 1) AS margin_pct
FROM v_orders WHERE in_main_window
GROUP BY discount_band ORDER BY MIN(discount_pct);

-- Q5. Monthly trend
SELECT order_month,
       COUNT(DISTINCT order_id)                                    AS orders,
       ROUND(100.0 * AVG(on_time), 1)                              AS on_time_pct,
       ROUND((100.0 * SUM(profit) / SUM(order_item_total))::numeric, 1) AS margin_pct
FROM v_orders
GROUP BY order_month ORDER BY order_month;

-- Q6. Loss-making lines by category
SELECT category,
       COUNT(*) FILTER (WHERE profit < 0)                          AS loss_lines,
       ROUND(100.0 * COUNT(*) FILTER (WHERE profit < 0) / COUNT(*), 1) AS loss_line_pct,
       ROUND((SUM(profit) FILTER (WHERE profit < 0))::numeric, 0)  AS loss_amount
FROM v_orders WHERE in_main_window
GROUP BY category ORDER BY loss_amount LIMIT 10;
