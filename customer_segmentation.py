from datetime import timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def customer_purchases(transactions):
    return transactions.loc[
        transactions["TransactionType"].eq("Product sale")
        & transactions["CustomerID"].notna()
    ]


def run_customer_segmentation(transactions, figures_dir):
    purchases = customer_purchases(transactions)
    if purchases.empty:
        print("\nNo product purchases with a customer ID.")
        return pd.DataFrame(
            columns=["Recency", "Frequency", "Monetary", "R_Score", "F_Score", "M_Score", "Segment"],
            index=pd.Index([], dtype=int, name="CustomerID"),
        )

    customer_count = purchases["CustomerID"].nunique()
    product_sales = purchases["Revenue"].sum()

    snapshot_date = transactions["InvoiceDate"].max().normalize() + timedelta(days=1)

    rfm = purchases.groupby("CustomerID").agg(
        last_purchase=("InvoiceDate", "max"),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("Revenue", "sum"),
    )

    rfm["Recency"] = (snapshot_date - rfm["last_purchase"].dt.normalize()).dt.days
    rfm = rfm[["Recency", "Frequency", "Monetary"]]
    rfm.index = rfm.index.astype(int)

    assert len(rfm) == customer_count, "RFM customer count does not match"
    assert abs(rfm["Monetary"].sum() - product_sales) < 0.01, (
        "RFM monetary total does not match"
    )

    print(f"\nRFM snapshot: {snapshot_date:%Y-%m-%d}")
    print(f"{len(purchases):,} purchase rows | {len(rfm):,} customers | £{product_sales:,.2f}")

    # Average percentile ranks keep customers with the same value in the same band.
    for metric in ("Recency", "Frequency", "Monetary"):
        percentiles = rfm[metric].rank(pct=True, ascending=metric != "Recency")
        rfm[f"{metric[0]}_Score"] = np.ceil(percentiles * 5).astype(int)

    # Assign the broadest group first so more specific rules take precedence.
    rfm["Segment"] = "Other active"
    rfm.loc[rfm["R_Score"].ge(4) & rfm["Frequency"].eq(1), "Segment"] = (
        "Recent one-time buyers"
    )
    rfm.loc[rfm["R_Score"].le(2), "Segment"] = "Less recent"
    rfm.loc[rfm["R_Score"].le(2) & rfm["F_Score"].ge(4), "Segment"] = (
        "At-risk repeat buyers"
    )
    rfm.loc[rfm[["R_Score", "F_Score", "M_Score"]].ge(4).all(axis=1), "Segment"] = (
        "Champions"
    )

    summary = rfm.groupby("Segment").agg(
        Customers=("Monetary", "size"),
        Purchase_Sales=("Monetary", "sum"),
    ).sort_values("Customers", ascending=False)
    summary["Customer_Share_Pct"] = 100 * summary["Customers"] / len(rfm)
    summary["Sales_Share_Pct"] = 100 * summary["Purchase_Sales"] / product_sales

    assert summary["Customers"].sum() == customer_count
    assert abs(summary["Purchase_Sales"].sum() - product_sales) < 0.01

    print("\nCustomer segment summary (all countries):")
    print(summary.round(2).to_string())

    fig, (customers_ax, sales_ax) = plt.subplots(1, 2, figsize=(11, 4), sharex=True, sharey=True)
    customers_ax.barh(summary.index, summary["Customer_Share_Pct"], color="tab:blue")
    sales_ax.barh(summary.index, summary["Sales_Share_Pct"], color="tab:orange")
    customers_ax.invert_yaxis()
    customers_ax.set_xlabel("Share of customers (%)")
    sales_ax.set_xlabel("Share of product sales (%)")
    fig.suptitle("RFM customer segments (all countries)")
    fig.tight_layout()
    fig.savefig(figures_dir / "customer_segments.png", dpi=200)
    plt.close(fig)
    return rfm
