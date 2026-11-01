"""Generate a Power BI Project (.pbip) for the Plan vs Actual report.

Output: powerbi/pbip/Order_Fulfilment.pbip + .SemanticModel (model.bim) + .Report (report.json).
Open the .pbip in Power BI Desktop, set the DataFolder parameter to the full path of powerbi/data/,
and click Refresh. Everything (tables, relationships, measures, 7 pages) is defined here as text,
so it can be reviewed and versioned on GitHub.
"""
import json
import pathlib
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi" / "pbip"
NAME = "Order_Fulfilment"
DEFAULT_FOLDER = r"C:\projects\order-fulfilment-plan-vs-actual\powerbi\data" + "\\"

# ---------------------------------------------------------------- semantic model
TYPES = {"int": ("int64", "Int64.Type"), "dbl": ("double", "type number"), "str": ("string", "type text"),
         "date": ("dateTime", "type date")}


def csv_table(name, file, cols, measures=None, extra=None):
    """cols: list of (column, kind, format or None, summarize)"""
    typed = ", ".join(f'{{"{c}", {TYPES[k][1]}}}' for c, k, *_ in cols)
    m = [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "{file}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'    Typed = Table.TransformColumnTypes(Promoted, {{{typed}}}, "en-US")',
        "in",
        "    Typed",
    ]
    t = {"name": name,
         "columns": [dict({"name": c, "dataType": TYPES[k][0], "sourceColumn": c,
                           "summarizeBy": (s if s else ("none" if k in ("str", "date") or c.endswith("_id") or c == "sort_order" else "sum"))},
                          **({"formatString": f} if f else {})) for c, k, f, s in [(*x, None)[:4] if len(x) == 3 else x for x in cols]],
         "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": m}}]}
    if measures:
        t["measures"] = measures
    if extra:
        t.update(extra)
    return t


def meas(name, expr, fmt=None, folder=None):
    d = {"name": name, "expression": expr}
    if fmt:
        d["formatString"] = fmt
    if folder:
        d["displayFolder"] = folder
    return d


P1, P0, USD, DAYS, INT = "0.0%", "0%", "\\$#,0", "0.00", "#,0"
MEASURES = [
    meas("Order Lines", "COUNTROWS ( fact_order_lines )", INT, "Volume"),
    meas("Orders", "DISTINCTCOUNT ( fact_order_lines[order_id] )", INT, "Volume"),
    meas("Avg Promised Days", "AVERAGE ( fact_order_lines[days_scheduled] )", DAYS, "Delivery"),
    meas("Avg Actual Days", "AVERAGE ( fact_order_lines[days_real] )", DAYS, "Delivery"),
    meas("Avg Slippage", "AVERAGE ( fact_order_lines[slippage_days] )", DAYS, "Delivery"),
    meas("On-time %", "DIVIDE ( SUM ( fact_order_lines[on_time] ), [Order Lines] )", P1, "Delivery"),
    meas("Within Tolerance %", "DIVIDE ( SUM ( fact_order_lines[within_tolerance] ), [Order Lines] )", P1, "Delivery"),
    meas("One Day Late %", "[Within Tolerance %] - [On-time %]", P1, "Delivery"),
    meas("Breach %", "DIVIDE ( SUM ( fact_order_lines[delivery_breach] ), [Order Lines] )", P1, "Delivery"),
    meas("Gross Sales", "SUM ( fact_order_lines[sales] )", USD, "Money"),
    meas("Discount", "SUM ( fact_order_lines[discount] )", USD, "Money"),
    meas("Amount Paid", "SUM ( fact_order_lines[amount_paid] )", USD, "Money"),
    meas("Cost", "SUM ( fact_order_lines[cost] )", USD, "Money"),
    meas("Profit", "SUM ( fact_order_lines[profit] )", USD, "Money"),
    meas("Margin %", "DIVIDE ( [Profit], [Amount Paid] )", P1, "Money"),
    meas("Discount % of Sales", "DIVIDE ( [Discount], [Gross Sales] )", P1, "Money"),
    meas("Discount vs Profit", "DIVIDE ( [Discount], [Profit] )", P0, "Money"),
    meas("Expected Margin %", "AVERAGE ( fact_order_lines[expected_margin] )", P1, "Margin"),
    meas("Margin Gap (pts)", "( [Margin %] - [Expected Margin %] ) * 100", "0.0", "Margin"),
    meas("Margin Breach %", "DIVIDE ( SUM ( fact_order_lines[margin_breach] ), [Order Lines] )", P1, "Margin"),
    meas("Loss Lines %", "DIVIDE ( CALCULATE ( [Order Lines], fact_order_lines[profit] < 0 ), [Order Lines] )", P1, "Margin"),
    meas("Loss Amount", "CALCULATE ( [Profit], fact_order_lines[profit] < 0 )", USD, "Margin"),
    meas("Profit on Profitable Lines", "CALCULATE ( [Profit], fact_order_lines[profit] >= 0 )", USD, "Margin"),
    meas("Bridge Value", 'SWITCH ( SELECTEDVALUE ( bridge_steps[step] ), "Gross sales", [Gross Sales], "Discount", - [Discount], "Cost", - [Cost] )', USD, "Margin"),
    meas("Discount Cap Value", "SELECTEDVALUE ( 'Discount Cap'[Discount Cap], 0.10 )", P0, "Discount cap"),
    meas("Cap Saving", "SUMX ( fact_order_lines, MAX ( 0, fact_order_lines[discount] - [Discount Cap Value] * fact_order_lines[sales] ) )", USD, "Discount cap"),
    meas("Profit Uplift %", "DIVIDE ( [Cap Saving], [Profit] )", P0, "Discount cap"),
    meas("Lines Affected %", "VAR cap = [Discount Cap Value] RETURN DIVIDE ( CALCULATE ( [Order Lines], fact_order_lines[discount_pct] > cap ), [Order Lines] )", P0, "Discount cap"),
    meas("KPI Actual", 'SWITCH ( SELECTEDVALUE ( kpi_targets[kpi] ), "On-time delivery", [On-time %], "Within 1-day tolerance", [Within Tolerance %], "Average slippage (days)", [Avg Slippage], "Profit margin", [Margin %], "Discount as % of gross sales", [Discount % of Sales], "Loss-making order lines", [Loss Lines %] )', "0.000", "KPI check"),
    meas("KPI Target", "SELECTEDVALUE ( kpi_targets[target] )", "0.000", "KPI check"),
    meas("KPI Pass", 'VAR a = ROUND ( [KPI Actual], 3 ) VAR t = [KPI Target] RETURN IF ( ISBLANK ( a ), BLANK (), IF ( SELECTEDVALUE ( kpi_targets[rule] ) = ">=", IF ( a >= t, 1, 0 ), IF ( a <= t, 1, 0 ) ) )', "0", "KPI check"),
    meas("KPI Status", 'SWITCH ( [KPI Pass], 1, "PASS", 0, "FAIL", BLANK () )', None, "KPI check"),
    meas("KPIs Passed", "SUMX ( VALUES ( kpi_targets[kpi] ), [KPI Pass] )", "0", "KPI check"),
    meas("Orders Actual", 'CALCULATE ( SUM ( forecast[actual] ), forecast[series] = "Orders" )', INT, "Forecast"),
    meas("Orders Test", 'CALCULATE ( SUM ( forecast[test_prediction] ), forecast[series] = "Orders" )', INT, "Forecast"),
    meas("Orders Forecast", 'CALCULATE ( SUM ( forecast[forecast] ), forecast[series] = "Orders" )', INT, "Forecast"),
    meas("Late Rate Actual", 'CALCULATE ( SUM ( forecast[actual] ), forecast[series] = "Late-delivery rate" )', P1, "Forecast"),
    meas("Late Rate Test", 'CALCULATE ( SUM ( forecast[test_prediction] ), forecast[series] = "Late-delivery rate" )', P1, "Forecast"),
    meas("Late Rate Forecast", 'CALCULATE ( SUM ( forecast[forecast] ), forecast[series] = "Late-delivery rate" )', P1, "Forecast"),
    meas("Title Delivery", '"Only " & FORMAT ( [On-time %], "0.0%" ) & " of order lines arrive within the promised days"', None, "Titles"),
    meas("Title Profit", '"Discounts of $" & FORMAT ( [Discount] / 1000000, "0.00" ) & "M against profit of $" & FORMAT ( [Profit] / 1000000, "0.00" ) & "M"', None, "Titles"),
]

FACT_COLS = [("order_item_id", "int", None), ("order_id", "int", None), ("order_date", "date", None),
             ("order_month", "date", None), ("country", "str", None), ("region", "str", None), ("market", "str", None),
             ("shipping_mode", "str", None), ("customer_segment", "str", None), ("department", "str", None),
             ("category", "str", None), ("days_real", "int", None), ("days_scheduled", "int", None),
             ("slippage_days", "int", None, "none"), ("on_time", "int", None), ("within_tolerance", "int", None),
             ("delivery_breach", "int", None), ("sales", "dbl", USD), ("discount", "dbl", USD),
             ("discount_pct", "dbl", P0, "none"), ("discount_band", "str", None), ("amount_paid", "dbl", USD),
             ("cost", "dbl", USD), ("profit", "dbl", USD), ("expected_margin", "dbl", P1, "none"),
             ("margin_breach", "int", None)]

date_m = [
    "let",
    "    Dates = List.Dates(#date(2015, 1, 1), Duration.Days(#date(2017, 12, 31) - #date(2015, 1, 1)) + 1, #duration(1, 0, 0, 0)),",
    '    T = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),',
    '    Typed = Table.TransformColumnTypes(T, {{"Date", type date}}),',
    '    AddYear = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),',
    '    AddMonthNo = Table.AddColumn(AddYear, "MonthNo", each Date.Year([Date]) * 100 + Date.Month([Date]), Int64.Type),',
    '    AddMonth = Table.AddColumn(AddMonthNo, "Month", each Date.ToText([Date], "MMM yyyy", "en-US"), type text)',
    "in",
    "    AddMonth",
]
cap_m = [
    "let",
    '    Values = List.Transform({0..25}, each _ / 100),',
    '    T = Table.FromList(Values, Splitter.SplitByNothing(), {"Discount Cap"}),',
    '    Typed = Table.TransformColumnTypes(T, {{"Discount Cap", type number}})',
    "in",
    "    Typed",
]

tables = [
    csv_table("fact_order_lines", "fact_order_lines.csv", FACT_COLS, MEASURES),
    {"name": "Date", "dataCategory": "Time",
     "columns": [{"name": "Date", "dataType": "dateTime", "sourceColumn": "Date", "isKey": True, "formatString": "dd mmm yyyy", "summarizeBy": "none"},
                 {"name": "Year", "dataType": "int64", "sourceColumn": "Year", "summarizeBy": "none"},
                 {"name": "MonthNo", "dataType": "int64", "sourceColumn": "MonthNo", "summarizeBy": "none", "isHidden": True},
                 {"name": "Month", "dataType": "string", "sourceColumn": "Month", "sortByColumn": "MonthNo", "summarizeBy": "none"}],
     "partitions": [{"name": "Date", "mode": "import", "source": {"type": "m", "expression": date_m}}]},
    csv_table("dim_shipping_mode", "dim_shipping_mode.csv", [("shipping_mode", "str", None), ("promised_days", "int", None, "none"), ("sort_order", "int", None)]),
    csv_table("dim_discount_band", "dim_discount_band.csv", [("discount_band", "str", None), ("sort_order", "int", None)]),
    csv_table("kpi_targets", "kpi_targets.csv", [("kpi", "str", None), ("rule", "str", None), ("target", "dbl", None, "none"), ("sort_order", "int", None)]),
    csv_table("bridge_steps", "bridge_steps.csv", [("step", "str", None), ("sort_order", "int", None)]),
    csv_table("forecast", "forecast.csv", [("series", "str", None), ("month", "date", None), ("actual", "dbl", None),
                                           ("test_prediction", "dbl", None), ("forecast", "dbl", None), ("best_model", "str", None)]),
    csv_table("forecast_error", "forecast_error.csv", [("model", "str", None), ("orders_mape_pct", "dbl", "0.00", "none"), ("late_rate_mape_pct", "dbl", "0.00", "none")]),
    {"name": "Discount Cap",
     "columns": [{"name": "Discount Cap", "dataType": "double", "sourceColumn": "Discount Cap", "formatString": "0%", "summarizeBy": "none"}],
     "partitions": [{"name": "Discount Cap", "mode": "import", "source": {"type": "m", "expression": cap_m}}]},
]
# sort text columns by their sort_order
for t in tables:
    names = {c["name"] for c in t["columns"]}
    if "sort_order" in names:
        t["columns"][0]["sortByColumn"] = "sort_order"
        for c in t["columns"]:
            if c["name"] == "sort_order":
                c["isHidden"] = True
for c in tables[0]["columns"]:
    if c["name"] in ("order_item_id", "order_month", "expected_margin"):
        c["isHidden"] = True

relationships = [
    {"name": "fact_date", "fromTable": "fact_order_lines", "fromColumn": "order_date", "toTable": "Date", "toColumn": "Date"},
    {"name": "fact_mode", "fromTable": "fact_order_lines", "fromColumn": "shipping_mode", "toTable": "dim_shipping_mode", "toColumn": "shipping_mode"},
    {"name": "fact_band", "fromTable": "fact_order_lines", "fromColumn": "discount_band", "toTable": "dim_discount_band", "toColumn": "discount_band"},
]
model = {
    "compatibilityLevel": 1567,
    "model": {
        "culture": "en-US",
        "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
        "defaultPowerBIDataSourceVersion": "powerBI_V3",
        "sourceQueryCulture": "en-US",
        "tables": tables,
        "relationships": relationships,
        "expressions": [{"name": "DataFolder", "kind": "m",
                         "expression": f'"{DEFAULT_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]'}],
        "annotations": [{"name": "PBI_QueryOrder", "value": json.dumps(["DataFolder"] + [t["name"] for t in tables])}],
    },
}

# ---------------------------------------------------------------- report
ALIAS = {}


def ref(table, field, kind="Column"):
    a = ALIAS.setdefault(table, "t" + str(len(ALIAS)))
    return {"kind": kind, "table": table, "field": field, "alias": a, "name": f"{table}.{field}"}


def C(table, field):
    return ref(table, field, "Column")


def M(field):
    return ref("fact_order_lines", field, "Measure")


def visual(vtype, x, y, w, h, roles=None, title=None, objects=None, extra=None):
    roles = roles or {}
    froms, selects, seen = [], [], set()
    for items in roles.values():
        for r in items:
            if r["table"] not in [f["Entity"] for f in froms]:
                froms.append({"Name": r["alias"], "Entity": r["table"], "Type": 0})
            if r["name"] not in seen:
                seen.add(r["name"])
                selects.append({r["kind"]: {"Expression": {"SourceRef": {"Source": r["alias"]}}, "Property": r["field"]}, "Name": r["name"]})
    sv = {"visualType": vtype, "drillFilterOtherVisuals": True}
    if roles:
        sv["projections"] = {role: [{"queryRef": r["name"]} for r in items] for role, items in roles.items()}
        sv["prototypeQuery"] = {"Version": 2, "From": froms, "Select": selects}
    vc_objects = {}
    if title:
        vc_objects["title"] = [{"properties": {"show": lit("true"), "text": lit(f"'{title}'")}}]
    if vc_objects:
        sv["vcObjects"] = vc_objects
    if objects:
        sv["objects"] = objects
    if extra:
        sv.update(extra)
    name = uuid.uuid4().hex[:20]
    cfg = {"name": name, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}], "singleVisual": sv}
    return {"x": x, "y": y, "z": 0, "width": w, "height": h, "config": json.dumps(cfg), "filters": "[]"}


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def textbox(x, y, w, h, paragraphs):
    paras = []
    for p in paragraphs:
        runs = p if isinstance(p, list) else [p]
        paras.append({"textRuns": [{"value": r[0], "textStyle": {"fontSize": f"{r[1]}pt", **({"fontWeight": "bold"} if r[2] else {})}}
                                   if isinstance(r, tuple) else {"value": r} for r in runs]})
    return visual("textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paras}}]})


def card(x, y, w, h, measure, title):
    return visual("card", x, y, w, h, {"Values": [M(measure)]}, title)


def slicers(y=8):
    return [visual("slicer", 8 + i * 210, y, 200, 56, {"Values": [c]}, None,
                   objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]})
            for i, c in enumerate([C("Date", "Year"), C("fact_order_lines", "market"), C("dim_shipping_mode", "shipping_mode"),
                                   C("fact_order_lines", "customer_segment")])]


def page(name, display, visuals):
    return {"name": name, "displayName": display, "displayOption": 1, "width": 1280, "height": 720,
            "config": "{}", "filters": "[]", "visualContainers": visuals}


pages = []
pages.append(page("p1", "1 Project objectives", [
    textbox(24, 16, 1232, 96, [("Plan vs Actual: where orders run late and profit leaks", 24, True),
                               ("Orders are promised a delivery date and a price. How often does the business keep those promises, and what does missing them cost? DataCo public data, 164,572 order lines, Jan 2015 to Sep 2017.", 12, False)]),
    textbox(24, 124, 604, 280, [("Objective 1 · Plan vs actual", 14, True),
                                ("Compare promised vs actual delivery days and expected vs actual margin by market, category and shipping mode, and flag order lines outside tolerance limits.", 11, False),
                                ("Result: 42.7% on time · 23.7% of lines more than 1 day late · 38.5% below the margin tolerance.", 11, True),
                                ("Objective 2 · Dashboard and cost-saving case", 14, True),
                                ("Drill-downs and a margin bridge (list price, discount, cost, profit) showing where delays and discounting reduce profit; business case for capping discounts.", 11, False),
                                ("Result: discounts $3.32M vs profit $3.53M · a 10% cap keeps up to $1.02M (+29% profit).", 11, True)]),
    textbox(652, 124, 604, 280, [("Objective 3 · Forecast", 14, True),
                                 ("Forecast monthly orders and the late-delivery rate and test accuracy on held-back months.", 11, False),
                                 ("Result: orders within 0.9% error, late rate within 1.3% · next quarter about 57.8% late.", 11, True),
                                 ("Objective 4 · One-click monthly report", 14, True),
                                 ("Excel VBA report that checks each KPI against its target and produces a pass/fail summary.", 11, False),
                                 ("Result: 6 KPIs checked every month · Sep 2017 passed 1 of 6.", 11, True)]),
    card(24, 420, 300, 120, "Order Lines", "Order lines"), card(340, 420, 300, 120, "On-time %", "On-time delivery"),
    card(656, 420, 300, 120, "Margin %", "Profit margin"), card(972, 420, 284, 120, "Discount vs Profit", "Discount given vs profit"),
    textbox(24, 560, 1232, 140, [("Pages: 2 Overview · 3 Delivery · 4 Profit and discount case · 5 Forecast · 6 Monthly KPI report · 7 Method", 11, False),
                                 ("Tools: PostgreSQL (SQL), Power BI (DAX), Python, Excel VBA. Data: Constante, Silva and Pereira (2019), DataCo Smart Supply Chain, Mendeley Data V5.", 10, False)]),
]))
pages.append(page("p2", "2 Overview", slicers() + [
    card(8, 76, 205, 100, "Order Lines", "Order lines"), card(221, 76, 205, 100, "On-time %", "On-time delivery (target 45%)"),
    card(434, 76, 205, 100, "Within Tolerance %", "Within 1-day tolerance (target 80%)"), card(647, 76, 205, 100, "Avg Slippage", "Avg slippage, days (target 0.50)"),
    card(860, 76, 205, 100, "Margin %", "Profit margin (target 12%)"), card(1073, 76, 199, 100, "Discount vs Profit", "Discount vs profit"),
    visual("lineChart", 8, 188, 628, 250, {"Category": [C("Date", "Month")], "Y": [M("On-time %")]}, "On-time delivery by month"),
    visual("lineChart", 644, 188, 628, 250, {"Category": [C("Date", "Month")], "Y": [M("Margin %")]}, "Profit margin by month"),
    visual("hundredPercentStackedBarChart", 8, 448, 1264, 264,
           {"Category": [C("dim_shipping_mode", "shipping_mode")], "Y": [M("On-time %"), M("One Day Late %"), M("Breach %")]},
           "Delivery against the promise by shipping mode: on time, 1 day late, 2+ days late"),
]))
pages.append(page("p3", "3 Delivery", slicers() + [
    card(860, 8, 412, 56, "Title Delivery", None),
    visual("clusteredBarChart", 8, 76, 628, 300, {"Category": [C("dim_shipping_mode", "shipping_mode")], "Y": [M("Avg Promised Days"), M("Avg Actual Days")]},
           "Promised vs actual delivery days"),
    visual("clusteredColumnChart", 644, 76, 628, 300, {"Category": [C("fact_order_lines", "slippage_days")], "Y": [M("Order Lines")]},
           "How late? Order lines by slippage (actual minus promised days)"),
    visual("pivotTable", 8, 388, 1264, 324,
           {"Rows": [C("fact_order_lines", "market"), C("fact_order_lines", "region"), C("fact_order_lines", "country")],
            "Columns": [C("dim_shipping_mode", "shipping_mode")], "Values": [M("Breach %")]},
           "Tolerance breaches (% more than 1 day late): expand market > region > country"),
]))
pages.append(page("p4", "4 Profit", slicers() + [
    card(860, 8, 412, 56, "Title Profit", None),
    visual("waterfallChart", 8, 76, 628, 330, {"Category": [C("bridge_steps", "step")], "Y": [M("Bridge Value")]}, "Margin bridge: gross sales to profit"),
    visual("slicer", 644, 76, 300, 80, {"Values": [C("Discount Cap", "Discount Cap")]}, "Discount cap"),
    card(952, 76, 320, 80, "Cap Saving", "Discount kept at this cap"),
    card(644, 166, 300, 80, "Profit Uplift %", "Profit uplift (upper bound)"),
    card(952, 166, 320, 80, "Lines Affected %", "Order lines affected"),
    visual("clusteredColumnChart", 644, 256, 628, 150, {"Category": [C("dim_discount_band", "discount_band")], "Y": [M("Margin %")]}, "Margin % by discount band"),
    visual("tableEx", 8, 416, 1264, 296,
           {"Values": [C("fact_order_lines", "category"), M("Amount Paid"), M("Expected Margin %"), M("Margin %"), M("Margin Gap (pts)"),
                       M("Margin Breach %"), M("Loss Amount"), M("Cap Saving")]},
           "Expected vs actual margin by category"),
]))
pages.append(page("p5", "5 Forecast", [
    visual("lineChart", 8, 8, 628, 420, {"Category": [C("forecast", "month")], "Y": [M("Orders Actual"), M("Orders Test"), M("Orders Forecast")]},
           "Orders per month: actual, Holt-Winters on held-back months, forecast"),
    visual("lineChart", 644, 8, 628, 420, {"Category": [C("forecast", "month")], "Y": [M("Late Rate Actual"), M("Late Rate Test"), M("Late Rate Forecast")]},
           "Late-delivery rate: actual, 3-month average on held-back months, forecast"),
    visual("tableEx", 8, 440, 628, 200, {"Values": [C("forecast_error", "model"), C("forecast_error", "orders_mape_pct"), C("forecast_error", "late_rate_mape_pct")]},
           "Forecast error (MAPE %) on Apr to Sep 2017"),
    textbox(644, 440, 628, 200, [("Trained on Jan 2015 to Mar 2017 and tested on 6 held-back months. Best models: Holt-Winters for orders (0.9% error) and a 3-month average for the late rate (1.3%).", 11, False),
                                 ("Without a process change, about 57.8% of lines will keep arriving later than promised in Oct to Dec 2017.", 11, True)]),
]))
pages.append(page("p6", "6 Monthly KPI report", [
    visual("slicer", 8, 8, 300, 56, {"Values": [C("Date", "Month")]}, "Month", objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]}),
    card(320, 8, 300, 56, "KPIs Passed", "KPIs passed (of 6)"),
    visual("tableEx", 8, 76, 1264, 240, {"Values": [C("kpi_targets", "kpi"), C("kpi_targets", "rule"), M("KPI Target"), M("KPI Actual"), M("KPI Status")]},
           "KPI vs target for the selected month"),
    visual("pivotTable", 8, 328, 1264, 384, {"Rows": [C("kpi_targets", "kpi")], "Columns": [C("Date", "Month")], "Values": [M("KPI Pass")]},
           "Pass (1) / fail (0) by month: add icons in conditional formatting"),
]))
pages.append(page("p7", "7 Method", [
    textbox(24, 16, 1232, 680, [("Method", 18, True),
        ("1 Load: Python keeps 24 business columns of the public CSV and drops all customer personal data. 2 Clean: a PostgreSQL view removes 7,754 cancelled and suspected-fraud lines and adds slippage, on-time and tolerance flags. 3 Compare: promised vs actual days (tolerance 1 day) and actual vs category median margin (tolerance 10 points). 4 Business case: discount kept under 5%, 10% and 15% caps. 5 Forecast: four models tested on 6 held-back months. 6 Report: Excel VBA macro checks 6 KPIs against targets.", 11, False),
        ("Data checks", 14, True),
        ("Sales = unit price × quantity and amount paid = sales − discount on every line. No missing values or duplicate line ids. From Oct 2017 the data changes shape (about 1 line per order instead of 3), so 8,193 lines are excluded.", 11, False),
        ("Limitations", 14, True),
        ("Patterns are nearly identical across markets, which suggests the public dataset is partly simulated. The discount-cap saving is an upper bound. Expected margin is a historical median, not a budget; KPI targets were set for this study.", 11, False),
        ("Source: Constante, F., Silva, F. and Pereira, A. (2019). DataCo Smart Supply Chain for Big Data Analysis. Mendeley Data, V5. doi:10.17632/8gx2fvg2k6.5", 10, False)]),
]))

for i, p in enumerate(pages):
    p["ordinal"] = i
report = {"config": json.dumps({"version": "5.43", "activeSectionIndex": 0, "defaultDrillFilterOtherVisuals": True}),
          "layoutOptimization": 0, "resourcePackages": [], "sections": pages, "filters": "[]"}

# ---------------------------------------------------------------- write files
sm, rp = OUT / f"{NAME}.SemanticModel", OUT / f"{NAME}.Report"
sm.mkdir(parents=True, exist_ok=True)
rp.mkdir(parents=True, exist_ok=True)
(OUT / f"{NAME}.pbip").write_text(json.dumps({"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                              "settings": {"enableAutoRecovery": True}}, indent=2))
(sm / "definition.pbism").write_text(json.dumps({"version": "1.0", "settings": {}}, indent=2))
(sm / "model.bim").write_text(json.dumps(model, indent=2, ensure_ascii=False))
(rp / "definition.pbir").write_text(json.dumps({"version": "1.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}, "byConnection": None}}, indent=2))
(rp / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
(OUT / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
print("pages:", len(pages), "visuals:", sum(len(p["visualContainers"]) for p in pages), "measures:", len(MEASURES))
