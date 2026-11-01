"""Small helper tables for the Power BI report (targets, sort orders, margin-bridge steps, forecast)."""
import json
import pandas as pd

out = "powerbi/data/"
pd.DataFrame([
    ("On-time delivery", ">=", 0.45, 1), ("Within 1-day tolerance", ">=", 0.80, 2),
    ("Average slippage (days)", "<=", 0.50, 3), ("Profit margin", ">=", 0.12, 4),
    ("Discount as % of gross sales", "<=", 0.10, 5), ("Loss-making order lines", "<=", 0.15, 6),
], columns=["kpi", "rule", "target", "sort_order"]).to_csv(out + "kpi_targets.csv", index=False)

pd.DataFrame({"discount_band": ["0%", "1-5%", "6-10%", "11-15%", "16-25%"], "sort_order": [1, 2, 3, 4, 5]}) \
    .to_csv(out + "dim_discount_band.csv", index=False)

pd.DataFrame({"step": ["Gross sales", "Discount", "Cost"], "sort_order": [1, 2, 3]}) \
    .to_csv(out + "bridge_steps.csv", index=False)

f = json.load(open("results/forecast.json"))
rows = []
for key, name in [("orders", "Orders"), ("late_rate", "Late-delivery rate")]:
    s = f["series"][key]
    n, nt = len(s["months"]), len(s["test_prediction"])
    for i, m in enumerate(s["months"]):
        rows.append({"series": name, "month": m + "-01", "actual": s["history"][i],
                     "test_prediction": s["test_prediction"][i - (n - nt)] if i >= n - nt else None, "forecast": None,
                     "best_model": s["best_model"]})
    for m, v in zip(s["forecast_months"], s["forecast"]):
        rows.append({"series": name, "month": m + "-01", "actual": None, "test_prediction": None, "forecast": v,
                     "best_model": s["best_model"]})
pd.DataFrame(rows).to_csv(out + "forecast.csv", index=False)

mape = [{"model": m, "orders_mape_pct": f["series"]["orders"]["mape_by_model"][m],
         "late_rate_mape_pct": f["series"]["late_rate"]["mape_by_model"][m]} for m in f["series"]["orders"]["mape_by_model"]]
pd.DataFrame(mape).to_csv(out + "forecast_error.csv", index=False)
print("done")
