import matplotlib.pyplot as plt
import pandas as pd

def plot_top_products(
    monthly_product_trends, top_product_transactions, figures_dir,
    country_name, country_filename,
):

    fig, ax = plt.subplots(figsize=(11, 5))
    month_labels = monthly_product_trends.index.astype(str)

    product_names = top_product_transactions.groupby("StockCode")["Description"].first()

    partial_month = month_labels == "2011-12"

    for stock_code in monthly_product_trends.columns:
        name = product_names.get(stock_code)
        sales = monthly_product_trends[stock_code].to_numpy()

        line, = ax.plot(
            month_labels[~partial_month],
            sales[~partial_month],
            marker="o",
            label=name if pd.notna(name) else str(stock_code),
        )

        ax.plot(
            month_labels[-2:],
            sales[-2:],
            linestyle="--",
            color=line.get_color(),
        )
        ax.plot(
            month_labels[partial_month],
            sales[partial_month],
            marker="o",
            linestyle="none",
            markerfacecolor="none",
            color=line.get_color(),
        )

    ax.set_title(f"Monthly Net Sales of Top 3 Products - {country_name}")
    ax.set_xlabel("Month (December 2011 includes only Dec 1–9)")
    ax.set_ylabel("Net product sales (£)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(title="Product")
    fig.tight_layout()
    fig.savefig(figures_dir / f"monthly_top_products_{country_filename}.png", dpi=200)
    plt.close(fig)

def monthly_product_sales(product_transactions):
    months = product_transactions["InvoiceDate"].dt.to_period("M")
    return product_transactions["Revenue"].groupby(months).sum()

def run_sales_trends(transactions, country_transactions, figures_dir, l1_net_sales):
    product_transactions = transactions[
        transactions["TransactionType"].isin(["Product sale", "Cancellation"])
    ]

    monthly_net_sales = monthly_product_sales(product_transactions)

    monthly_total = monthly_net_sales.sum()
    difference = monthly_total - l1_net_sales

    assert abs(difference) < 0.01, f"Reconciliation failed: £{difference:,.2f}"

    country_product_transactions = country_transactions[
        country_transactions["TransactionType"].isin(["Product sale", "Cancellation"])
    ].copy()

    country_product_transactions["StockCode"] = (
        country_product_transactions["StockCode"].astype(str)
    )
    country_monthly_sales = monthly_product_sales(country_product_transactions)

    weeks = product_transactions["InvoiceDate"].dt.to_period("W-SUN")
    weekly_net_sales = product_transactions["Revenue"].groupby(weeks).sum()
    assert abs(weekly_net_sales.sum() - l1_net_sales) < 0.01, (
        "Weekly reconciliation failed"
    )

    country_weeks = country_product_transactions["InvoiceDate"].dt.to_period("W-SUN")
    country_weekly_sales = country_product_transactions["Revenue"].groupby(country_weeks).sum()

    country_total = country_monthly_sales.sum()
    assert abs(country_weekly_sales.sum() - country_total) < 0.01
    print("\nL2-A | Monthly and weekly net sales reconcile")
    print(f"Overall: £{monthly_total:,.2f} | Selected country: £{country_total:,.2f}")

    top_products = (
        country_product_transactions.groupby("StockCode")["Revenue"]
        .sum()
        .nlargest(3)
    )

    top_product_transactions = country_product_transactions[
        country_product_transactions["StockCode"].isin(top_products.index)
    ]
    product_months = top_product_transactions["InvoiceDate"].dt.to_period("M")

    monthly_product_trends = (
        top_product_transactions.groupby([product_months, "StockCode"])["Revenue"]
        .sum()
        .unstack(fill_value=0)
        .reindex(index=monthly_net_sales.index, columns=top_products.index, fill_value=0)
    )

    all_weeks = pd.period_range(
        weekly_net_sales.index.min(), weekly_net_sales.index.max(), freq="W-SUN"
    )

    weekly_plot_sales = weekly_net_sales.reindex(all_weeks)
    country_weekly_plot_sales = (
        country_weekly_sales
        .reindex(weekly_net_sales.index, fill_value=0)
        .reindex(all_weeks)
    )

    plot_weekly_sales(
        weekly_plot_sales,
        figures_dir,
        "Weekly Net Product Sales - Overall",
        "weekly_net_product_sales.png",
    )

    country_name = country_transactions["Country"].iloc[0]
    country_filename = country_name.lower().replace(" ", "_")
    if not top_products.empty:
        plot_top_products(
            monthly_product_trends, top_product_transactions, figures_dir,
            country_name, country_filename,
        )

    plot_weekly_sales(
        country_weekly_plot_sales,
        figures_dir,
        f"Weekly Net Product Sales - {country_name}",
        f"weekly_net_product_sales_{country_filename}.png",
    )

    plot_monthly_sales(
        monthly_net_sales,
        figures_dir,
        "Monthly Net Product Sales",
        "monthly_net_product_sales.png",
    )

    plot_monthly_sales(
        country_monthly_sales,
        figures_dir,
        f"Monthly Net Product Sales - {country_name}",
        f"monthly_net_product_sales_{country_filename}.png",
    )

def plot_monthly_sales(monthly_net_sales, figures_dir, title, filename):
    fig, ax = plt.subplots(figsize=(11, 5))
    month_labels = monthly_net_sales.index.astype(str)
    bar_colors = [
        "tab:orange" if month == "2011-12" else "tab:blue"
        for month in month_labels
    ]
    ax.bar(month_labels, monthly_net_sales.values, color=bar_colors)
    ax.set_title(title)
    ax.set_ylabel("Net product sales (£)")
    ax.set_xlabel("Month (December 2011 includes only Dec 1–9)")
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:,.0f}")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(figures_dir / filename, dpi=200)
    plt.close(fig)

def plot_weekly_sales(weekly_sales, figures_dir, title, filename):
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(weekly_sales.index.start_time, weekly_sales)
    ax.set_title(title)
    ax.set_xlabel("Week starting Monday (first and last weeks are partial)")
    ax.set_ylabel("Net product sales (£)")
    fig.tight_layout()
    fig.savefig(figures_dir / filename, dpi=200)
    plt.close(fig)
