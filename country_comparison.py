import pandas as pd
from customer_segmentation import customer_purchases

def compare_country_segments(rfm, country_transactions, country_name):
    purchases = customer_purchases(country_transactions)
    print(f"\n{country_name} vs Overall (including {country_name})")
    if purchases.empty:
        print("No product purchases with a customer ID in the selected country.")
        return

    country_sales = purchases.groupby("CustomerID")["Revenue"].sum()
    country_sales.index = country_sales.index.astype(int)
    country_customers = rfm.loc[country_sales.index, ["Segment"]].copy()
    country_customers["Monetary"] = country_sales
    assert abs(country_customers["Monetary"].sum() - purchases["Revenue"].sum()) < 0.01

    overall = rfm.groupby("Segment")["Monetary"].agg(["size", "sum"])
    country = country_customers.groupby("Segment")["Monetary"].agg(["size", "sum"])
    country = country.reindex(overall.index, fill_value=0)

    comparison = pd.DataFrame({
        "Country customers": country["size"],
        "Country customer %": 100 * country["size"] / len(country_customers),
        "Overall customer %": 100 * overall["size"] / len(rfm),
        "Country purchase %": 100 * country["sum"] / country_sales.sum(),
        "Overall purchase %": 100 * overall["sum"] / rfm["Monetary"].sum(),
    }).sort_values("Overall customer %", ascending=False)
    print(f"{len(country_customers):,} customers | £{country_sales.sum():,.2f} in gross product sales")
    if len(country_customers) < 30:
        print("Small sample: percentages are unstable, read the counts.")
    print(comparison.round(2).to_string())
    return comparison
