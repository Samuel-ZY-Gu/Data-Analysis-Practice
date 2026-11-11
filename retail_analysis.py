from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "Online_Retail_Practice.xlsx"

df = pd.read_excel(DATA_PATH, sheet_name="Online Retail")

required_columns = [
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country"
]

df = df[required_columns].copy()
df["Description"] = df["Description"].str.strip()

print("Missing values by column:")
print(df.isna().sum())

print(f"Total rows for analysis: {len(df):,}")

print(f"Rows involved in duplicates: {df.duplicated(keep=False).sum():,}")
print(f"Extra duplicate rows: {df.duplicated().sum():,}")

REMOVE_DUPLICATES = False

df_all = df.drop_duplicates().copy() if REMOVE_DUPLICATES else df.copy()

print(f"Rows after duplicate handling: {len(df_all):,}")

df_all["Revenue"] = df_all["Quantity"] * df_all["UnitPrice"]

df_all["TransactionType"] = "Unclassified"

bad_debt_mask = (
        df_all["Description"].eq("Adjust bad debt") &
        (df_all["UnitPrice"] < 0)
)

df_all.loc[bad_debt_mask, "TransactionType"] = "Bad debt"

df_all.loc[df_all["UnitPrice"] == 0, "TransactionType"] = "Zero-price"

non_product_codes = [
    "DOT", "POST", "M", "D", "BANK CHARGES",
    "AMAZONFEE", "CRUK", "C2", "B"
]

df_all.loc[
    df_all["StockCode"].isin(non_product_codes) &
    df_all["TransactionType"].eq("Unclassified"),
    "TransactionType"
] = "Non-product"

cancellation_mask = (
    df_all["InvoiceNo"].astype(str).str.startswith("C") &
    (df_all["UnitPrice"] > 0) &
    df_all["TransactionType"].eq("Unclassified")
)

df_all.loc[cancellation_mask, "TransactionType"] = "Cancellation"

product_sales_mask = (
        df_all["TransactionType"].eq("Unclassified") &
        (df_all["Quantity"] > 0) &
        (df_all["UnitPrice"] > 0)
)

df_all.loc[product_sales_mask, "TransactionType"] = "Product sale"

print("\nTransaction type counts:")
print(df_all["TransactionType"].value_counts())

def calculate_metrics(data):
    by_type = data.groupby("TransactionType")["Revenue"].sum()

    return {
        "Product sales": by_type.get("Product sale", 0),
        "Cancellation": -by_type.get("Cancellation", 0),
        "Non-product (net)": by_type.get("Non-product", 0),
        "Bad debt": by_type.get("Bad debt", 0),
        "Transaction total": data["Revenue"].sum()
    }

while True:
    country = input("Which country do you want to analyze? ").strip()

    df_country = df_all[
        df_all["Country"].str.strip().str.lower() == country.lower()
    ]

    if not df_country.empty:
        break

    print("Country not found. Please try again.")

print(f"Total rows for selected country: {len(df_country):,}")

country_name = df_country["Country"].iloc[0]

metrics = pd.DataFrame({
    "Overall": calculate_metrics(df_all),
    country_name: calculate_metrics(df_country)
}).T

metrics["Net product sales"] = (
    metrics["Product sales"] - metrics["Cancellation"]
)

metrics["Check"] = (
    metrics["Net product sales"]
    + metrics["Non-product (net)"]
    + metrics["Bad debt"]
    - metrics["Transaction total"]
)

metrics["Cancellation amount ratio (%)"] = (
    metrics["Cancellation"] / metrics["Product sales"] * 100
)

metrics["Share of overall product sales (%)"] = (
    metrics["Product sales"] /
    metrics.loc["Overall", "Product sales"] * 100
)

assert metrics["Check"].abs().lt(0.01).all(), "Revenue reconciliation failed"

print(metrics.T.round(2))

FIGURES_DIR = BASE_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

def save_top10(data, title, xlabel, filename):
    top10 = data.nlargest(10).sort_values()
    ax = top10.plot.barh(figsize=(10, 6))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / filename, dpi=200)
    plt.close()

products = df_all[
    df_all["TransactionType"].isin(["Product sale", "Cancellation"])
]

country_sales = products.groupby("Country")["Revenue"].sum()
country_share = country_sales / country_sales.sum() * 100

non_uk = country_sales.drop("United Kingdom", errors="ignore")
non_uk_share = non_uk / non_uk.sum() * 100

overall_products = products.groupby("Description")["Revenue"].sum()

selected_products = df_country[
    df_country["TransactionType"].isin(["Product sale", "Cancellation"])
].groupby("Description")["Revenue"].sum()

save_top10(
    country_share, "Country Sales Share",
    "Share (%)", "country_share.png"
)

save_top10(
    non_uk_share, "Sales Share Excluding UK",
    "Share among non-UK countries (%)", "country_share_ex_uk.png"
)

save_top10(
    overall_products, "Top Products - Overall",
    "Gross Product Sales (£)", "products_overall.png"
)

save_top10(
    selected_products, f"Top Products - {country_name}",
    "Gross Product Sales (£)",
    f"products_{country_name.lower().replace(' ', '_')}.png"
)

print("Analysis complete.")
print("Charts saved to figures/")
