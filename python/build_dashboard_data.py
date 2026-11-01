"""Pack the SQL extracts (results/*.csv) and the forecast into one compact JSON for the dashboard."""
import json
import pandas as pd

A = pd.read_csv("results/cube_a.csv")
B = pd.read_csv("results/cube_b.csv")
S = pd.read_csv("results/cube_slip.csv")
F = json.load(open("results/forecast.json"))


def encode(df, dims, measures):
    """Store each dimension once as a list and each row as numbers (keeps the file small)."""
    out = {"dims": {}, "cols": dims + measures, "rows": []}
    codes = {}
    for d in dims:
        vals = sorted(df[d].astype(str).unique())
        out["dims"][d] = vals
        codes[d] = {v: i for i, v in enumerate(vals)}
    for r in df.to_dict("records"):
        row = [codes[d][str(r[d])] for d in dims]
        row += [round(float(r[m]), 2) if isinstance(r[m], float) else int(r[m]) for m in measures]
        out["rows"].append(row)
    return out


A["month"] = A["order_month"].str[:7]
data = {
    "A": encode(A, ["month", "market", "order_region", "shipping_mode", "customer_segment"],
                ["lines", "on_time", "within_tol", "breach", "slip_sum", "real_sum", "sched_sum", "sales", "discount",
                 "net", "profit", "save5", "save10", "save15", "loss_lines", "loss_amt", "margin_breach"]),
    "B": encode(B, ["yr", "department", "category", "market", "shipping_mode", "customer_segment", "discount_band"],
                ["lines", "on_time", "sales", "discount", "net", "profit", "save10", "loss_lines", "loss_amt",
                 "margin_breach"]),
    "S": encode(S, ["yr", "shipping_mode", "market", "customer_segment"], ["slippage_days", "n"]),
    "F": F,
    "meta": {"window": "Jan 2015 - Sep 2017", "expected_margin": 0.27, "tolerance_days": 1, "margin_tolerance_pts": 10},
}
json.dump(data, open("results/dashboard_data.json", "w"), separators=(",", ":"))
print("lines", A.lines.sum(), "on-time", round(100 * A.on_time.sum() / A.lines.sum(), 1),
      "margin breach", round(100 * A.margin_breach.sum() / A.lines.sum(), 1))
