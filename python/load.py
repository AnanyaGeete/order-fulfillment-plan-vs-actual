"""Step 1: load the DataCo CSV into PostgreSQL (keeps 24 columns, drops all customer personal data).
Run:  python scripts/load.py
Needs: pip install pandas sqlalchemy psycopg2-binary
Set your PostgreSQL password first (Windows):  set PGPASSWORD=yourpassword
"""
import os
import pandas as pd
from sqlalchemy import create_engine

RAW = "data/DataCoSupplyChainDataset.csv"   # the big file you downloaded (do NOT commit it)

df = pd.read_csv(RAW, encoding="latin-1")
print(df.shape)            # expect about 180,519 rows and 53 columns
print(list(df.columns))    # if a name below is different, fix it here

cols = {
    "Order Id": "order_id",
    "Order Item Id": "order_item_id",
    "order date (DateOrders)": "order_date",
    "shipping date (DateOrders)": "shipping_date",
    "Days for shipping (real)": "days_real",
    "Days for shipment (scheduled)": "days_scheduled",
    "Delivery Status": "delivery_status",
    "Late_delivery_risk": "late_risk",
    "Shipping Mode": "shipping_mode",
    "Order Status": "order_status",
    "Market": "market",
    "Order Region": "order_region",
    "Order Country": "order_country",
    "Customer Segment": "customer_segment",
    "Department Name": "department",
    "Category Name": "category",
    "Product Name": "product",
    "Order Item Product Price": "unit_price",
    "Order Item Quantity": "quantity",
    "Sales": "sales",                       # list price x quantity
    "Order Item Discount": "discount",
    "Order Item Discount Rate": "discount_rate",
    "Order Item Total": "order_item_total", # sales - discount
    "Order Profit Per Order": "profit",
}
df = df[list(cols)].rename(columns=cols)   # drops names, emails, passwords, addresses
for c in ["order_date", "shipping_date"]:
    df[c] = pd.to_datetime(df[c], format="%m/%d/%Y %H:%M")

# quick sanity checks: both should print a number close to 0
print("sales check:", (df.sales - df.unit_price * df.quantity).abs().max())
print("total check:", (df.order_item_total - (df.sales - df.discount)).abs().max())

engine = create_engine(
    f"postgresql+psycopg2://postgres:{os.environ['PGPASSWORD']}@localhost:5432/dataco")
df.to_sql("orders", engine, if_exists="replace", index=False, chunksize=10000)
print("loaded into PostgreSQL table: orders")

