-- 01_view.sql : one clean view used by every query, the dashboard and the report
DROP VIEW IF EXISTS v_orders CASCADE;
CREATE VIEW v_orders AS
SELECT
    o.*,
    o.order_date::date                                        AS order_day,
    DATE_TRUNC('month', o.order_date)::date                   AS order_month,
    o.days_real - o.days_scheduled                            AS slippage_days,
    CASE WHEN o.days_real <= o.days_scheduled THEN 1 ELSE 0 END AS on_time,          -- met the promise
    CASE WHEN o.days_real - o.days_scheduled <= 1 THEN 1 ELSE 0 END AS within_tolerance, -- at most 1 day late
    o.order_item_total - o.profit                             AS cost,
    CASE WHEN o.order_item_total = 0 THEN NULL
         ELSE o.profit / o.order_item_total END               AS margin_ratio,
    CASE                                                      -- rates are stored as floats (0.100000001), so round first
        WHEN ROUND(o.discount_rate::numeric, 2) = 0     THEN '0%'
        WHEN ROUND(o.discount_rate::numeric, 2) <= 0.05 THEN '1-5%'
        WHEN ROUND(o.discount_rate::numeric, 2) <= 0.10 THEN '6-10%'
        WHEN ROUND(o.discount_rate::numeric, 2) <= 0.15 THEN '11-15%'
        ELSE '16-25%'
    END                                                       AS discount_band,
    ROUND(o.discount_rate::numeric, 2)                        AS discount_pct,
    o.order_date < DATE '2017-10-01'                          AS in_main_window       -- see data check D3
FROM orders o
WHERE o.delivery_status <> 'Shipping canceled'
  AND o.order_status NOT IN ('CANCELED', 'SUSPECTED_FRAUD');
