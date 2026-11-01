"""Forecast monthly orders and the late-delivery rate, and measure forecast error.

Method
1. Use the stable window Jan 2015 - Sep 2017 (33 months). From Oct 2017 the data changes shape
   (about 1 line per order instead of 3, and fewer categories), so those months are left out.
2. Train on Jan 2015 - Mar 2017 (27 months), hold back Apr - Sep 2017 (6 months) to test.
3. Compare four simple, explainable models and keep the one with the lowest error (MAPE).
4. Refit the best model on all 33 months and forecast Oct - Dec 2017.

Input : results/monthly.csv  (exported from the SQL view, one row per month)
Output: results/forecast.json, images/forecast.png
Only needs pandas, numpy and matplotlib.
"""
import json
from itertools import product

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.ticker
import numpy as np
import pandas as pd

m = pd.read_csv("results/monthly.csv", parse_dates=["order_month"])
m = m[m.order_month < "2017-10-01"].reset_index(drop=True)
m["late_rate"] = 1 - m["on_time"]
TEST = 6
HORIZON = 3


def mape(actual, pred):
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return float(np.mean(np.abs((actual - pred) / actual)) * 100)


# ---------- the four models ----------
def moving_average(y, h, k=3):
    return np.repeat(np.mean(y[-k:]), h)


def seasonal_naive(y, h):
    # same month last year
    return np.array([y[len(y) - 12 + (i % 12)] for i in range(h)])


def linear_trend(y, h):
    x = np.arange(len(y))
    b, a = np.polyfit(x, y, 1)
    return a + b * np.arange(len(y), len(y) + h)


def holt_winters(y, h, season=12):
    """Additive Holt-Winters, parameters chosen by grid search on one-step-ahead error."""
    y = np.asarray(y, float)
    best = None
    grid = [0.05, 0.1, 0.2, 0.3, 0.5, 0.7]
    for a, b, g in product(grid, [0.0, 0.05, 0.1], grid):
        level = y[:season].mean()
        trend = (y[season:2 * season].mean() - y[:season].mean()) / season if len(y) >= 2 * season else 0.0
        seas = list(y[:season] - level)
        sse = 0.0
        for t in range(len(y)):
            s = seas[t % season]
            fc = level + trend + s
            if t >= season:
                sse += (y[t] - fc) ** 2
            new_level = a * (y[t] - s) + (1 - a) * (level + trend)
            trend = b * (new_level - level) + (1 - b) * trend
            seas[t % season] = g * (y[t] - new_level) + (1 - g) * s
            level = new_level
        if best is None or sse < best[0]:
            best = (sse, level, trend, seas[:], (a, b, g))
    _, level, trend, seas, params = best
    n = len(y)
    return np.array([level + (i + 1) * trend + seas[(n + i) % season] for i in range(h)])


MODELS = {"3-month average": moving_average, "Same month last year": seasonal_naive,
          "Linear trend": linear_trend, "Holt-Winters": holt_winters}

out = {"train_months": [d.strftime("%Y-%m") for d in m.order_month[:-TEST]],
       "test_months": [d.strftime("%Y-%m") for d in m.order_month[-TEST:]],
       "series": {}}

fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
for ax, (col, label) in zip(axes, [("orders", "Orders per month"), ("late_rate", "Late-delivery rate")]):
    y = m[col].to_numpy(float)
    train, test = y[:-TEST], y[-TEST:]
    scores = {name: mape(test, f(train, TEST)) for name, f in MODELS.items()}
    best = min(scores, key=scores.get)
    fit_test = MODELS[best](train, TEST)
    future = MODELS[best](y, HORIZON)
    future_months = pd.date_range(m.order_month.iloc[-1] + pd.offsets.MonthBegin(1), periods=HORIZON, freq="MS")
    out["series"][col] = {
        "label": label,
        "history": [round(v, 4) for v in y],
        "months": [d.strftime("%Y-%m") for d in m.order_month],
        "mape_by_model": {k: round(v, 2) for k, v in scores.items()},
        "best_model": best,
        "test_prediction": [round(v, 4) for v in fit_test],
        "forecast_months": [d.strftime("%Y-%m") for d in future_months],
        "forecast": [round(v, 4) for v in future],
    }
    ax.plot(m.order_month, y, color="#1f3a5f", lw=2, label="Actual")
    ax.plot(m.order_month[-TEST:], fit_test, color="#c77800", lw=2, ls="--", label=f"{best} on held-back months")
    ax.plot(future_months, future, color="#1d8a52", lw=2.5, marker="o", label="Forecast Oct-Dec 2017")
    ax.axvspan(m.order_month.iloc[-TEST], m.order_month.iloc[-1], color="#c77800", alpha=0.08)
    ax.set_title(f"{label}  (best: {best}, MAPE {scores[best]:.1f}%)", fontsize=11)
    if col == "late_rate":
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %Y"))
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig("images/forecast.png", dpi=150)
json.dump(out, open("results/forecast.json", "w"), indent=1)
for k, v in out["series"].items():
    print(k, v["mape_by_model"], "best:", v["best_model"], "forecast:", v["forecast"])
