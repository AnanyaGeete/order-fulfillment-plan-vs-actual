-- 06_monthly_extract.sql : export one month of order lines for the Excel report
-- Run in psql (change both dates), then open excel/KPI_Report.xlsm and click Generate Report.
\copy (SELECT order_id, order_date, market, shipping_mode, customer_segment, category, days_real, days_scheduled, sales, discount, order_item_total, profit FROM v_orders WHERE order_date >= '2017-09-01' AND order_date < '2017-10-01' ORDER BY order_date) TO 'data/monthly_extract_2017-09.csv' CSV HEADER
