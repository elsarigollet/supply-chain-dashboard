"""Supply Chain Analytics — a Streamlit dashboard for supply chain KPIs and trends."""

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_PATH = "data/supply_chain_data.csv"

# Palette
COLOR_BLACK = "#0A0A0A"
COLOR_WHITE = "#FFFFFF"
COLOR_VIOLET = "#7C3AED"
COLOR_VIOLET_SOFT = "#EDE9FE"
COLOR_CARD = "#141414"
COLOR_GREEN = "#22C55E"
COLOR_RED = "#EF4444"
COLOR_GRAY_TEXT = "#A1A1AA"

CHART_COLORWAY = ["#7C3AED", "#A78BFA", "#C4B5FD", "#EDE9FE", "#5B21B6", "#DDD6FE"]

# KPI thresholds
AVAILABILITY_HIGH = 70
AVAILABILITY_LOW = 50
STOCK_COVERAGE_HIGH_DAYS = 7
STOCK_COVERAGE_LOW_DAYS = 3
DEFECT_RATE_HIGH_PCT = 2.5
DEFECT_RATE_LOW_PCT = 1.0

# Business assumptions
DAYS_IN_PERIOD = 365  # "Number of products sold" is treated as annual demand for stock-coverage math
STOCKOUT_STOCK_LEVEL = 0
LOW_STOCK_THRESHOLD = 10
TOP_N_SKUS_CHART = 20

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Stock coverage days"] = df["Stock levels"] / (
        df["Number of products sold"] / DAYS_IN_PERIOD
    ).replace(0, pd.NA)
    return df


def filter_data(df: pd.DataFrame, product_types: list, suppliers: list) -> pd.DataFrame:
    filtered = df[df["Product type"].isin(product_types)]
    filtered = filtered[filtered["Supplier name"].isin(suppliers)]
    return filtered


# ---------------------------------------------------------------------------
# KPI computation
# ---------------------------------------------------------------------------


def compute_kpis(df: pd.DataFrame) -> dict:
    return {
        "availability_rate": df["Availability"].mean(),
        "stock_coverage_days": df["Stock coverage days"].median(),
        "stockouts": int((df["Stock levels"] <= STOCKOUT_STOCK_LEVEL).sum()),
        "avg_lead_time": df["Lead times"].mean(),
        "avg_defect_rate": df["Defect rates"].mean(),
    }


def kpi_color(value: float, high: float, low: float, invert: bool = False) -> str:
    """Green above `high`, red below `low`, violet in between. `invert` flips the direction."""
    if invert:
        if value < low:
            return COLOR_GREEN
        if value > high:
            return COLOR_RED
        return COLOR_VIOLET
    if value > high:
        return COLOR_GREEN
    if value < low:
        return COLOR_RED
    return COLOR_VIOLET


# ---------------------------------------------------------------------------
# UI: styling
# ---------------------------------------------------------------------------


def inject_css() -> None:
    st.markdown(
        f"""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}
        .stApp {{
            background-color: {COLOR_BLACK};
            color: {COLOR_WHITE};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {COLOR_BLACK};
            border-right: 1px solid #262626;
        }}
        section[data-testid="stSidebar"] * {{
            color: {COLOR_WHITE};
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {COLOR_WHITE};
            font-weight: 700;
        }}
        .app-subtitle {{
            color: {COLOR_GRAY_TEXT};
            font-size: 0.95rem;
            margin-top: -0.6rem;
        }}
        .app-updated {{
            color: {COLOR_GRAY_TEXT};
            font-size: 0.8rem;
        }}
        .kpi-card {{
            background-color: {COLOR_CARD};
            border-radius: 16px;
            padding: 1.1rem 1.3rem;
            box-shadow: 0 0 24px rgba(124, 58, 237, 0.18);
            border: 1px solid rgba(124, 58, 237, 0.25);
            height: 100%;
        }}
        .kpi-icon {{
            font-size: 1.4rem;
        }}
        .kpi-value {{
            font-size: 1.7rem;
            font-weight: 800;
            color: {COLOR_WHITE};
            margin: 0.2rem 0 0.1rem 0;
        }}
        .kpi-label {{
            color: {COLOR_GRAY_TEXT};
            font-size: 0.82rem;
            font-weight: 500;
        }}
        .kpi-dot {{
            display: inline-block;
            width: 9px;
            height: 9px;
            border-radius: 50%;
            margin-right: 6px;
        }}
        .alert-banner {{
            background-color: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.35);
            border-radius: 16px;
            padding: 0.9rem 1.3rem;
            margin-bottom: 0.6rem;
            color: {COLOR_WHITE};
        }}
        .section-title {{
            color: {COLOR_WHITE};
            font-weight: 600;
            font-size: 1.05rem;
            margin: 0.4rem 0 0.6rem 0;
        }}
        div[data-testid="stPlotlyChart"] {{
            background-color: {COLOR_CARD};
            border-radius: 12px;
            padding: 0.6rem;
            border: 1px solid rgba(124, 58, 237, 0.15);
        }}
        div[data-testid="stExpander"] {{
            background-color: {COLOR_CARD};
            border-radius: 16px;
            border: 1px solid rgba(124, 58, 237, 0.2);
        }}
        div[data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plotly_theme(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(color=COLOR_WHITE, size=15, family="Inter")),
        paper_bgcolor=COLOR_CARD,
        plot_bgcolor=COLOR_CARD,
        font=dict(color=COLOR_WHITE, family="Inter"),
        colorway=CHART_COLORWAY,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="#262626", zerolinecolor="#262626")
    fig.update_yaxes(gridcolor="#262626", zerolinecolor="#262626")
    return fig


# ---------------------------------------------------------------------------
# UI: header, sidebar, KPIs, alerts
# ---------------------------------------------------------------------------


def render_header() -> None:
    st.markdown("# Supply Chain Analytics")
    st.markdown(
        '<div class="app-subtitle">Inventory, supplier, and logistics performance at a glance</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="app-updated">Last updated: {date.today().strftime("%B %d, %Y")}</div>',
        unsafe_allow_html=True,
    )
    st.write("")


def render_sidebar(df: pd.DataFrame) -> tuple:
    st.sidebar.markdown("### Filters")
    product_types = st.sidebar.multiselect(
        "Product type",
        options=sorted(df["Product type"].unique()),
        default=sorted(df["Product type"].unique()),
    )
    suppliers = st.sidebar.multiselect(
        "Supplier",
        options=sorted(df["Supplier name"].unique()),
        default=sorted(df["Supplier name"].unique()),
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Dataset stats")
    st.sidebar.metric("Total SKUs", df["SKU"].nunique())
    st.sidebar.metric("Suppliers", df["Supplier name"].nunique())
    st.sidebar.metric("Product types", df["Product type"].nunique())

    return product_types or list(df["Product type"].unique()), suppliers or list(
        df["Supplier name"].unique()
    )


def render_kpi_card(col, icon: str, value: str, label: str, color: str) -> None:
    with col:
        st.markdown(
            f"""
            <div class="kpi-card">
                <span class="kpi-icon">{icon}</span>
                <div class="kpi-value">{value}</div>
                <div class="kpi-label"><span class="kpi-dot" style="background-color:{color};"></span>{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_kpi_row(kpis: dict) -> None:
    cols = st.columns(5)

    render_kpi_card(
        cols[0],
        "📦",
        f'{kpis["availability_rate"]:.1f}%',
        "Availability Rate",
        kpi_color(kpis["availability_rate"], AVAILABILITY_HIGH, AVAILABILITY_LOW),
    )
    render_kpi_card(
        cols[1],
        "🗓️",
        f'{kpis["stock_coverage_days"]:.1f}d',
        "Stock Coverage",
        kpi_color(
            kpis["stock_coverage_days"], STOCK_COVERAGE_HIGH_DAYS, STOCK_COVERAGE_LOW_DAYS
        ),
    )
    render_kpi_card(
        cols[2],
        "🚨",
        f'{kpis["stockouts"]}',
        "Stockouts",
        COLOR_RED if kpis["stockouts"] > 0 else COLOR_GREEN,
    )
    render_kpi_card(
        cols[3],
        "🚚",
        f'{kpis["avg_lead_time"]:.1f}d',
        "Avg Lead Time",
        COLOR_VIOLET,
    )
    render_kpi_card(
        cols[4],
        "🛠️",
        f'{kpis["avg_defect_rate"]:.2f}%',
        "Avg Defect Rate",
        kpi_color(
            kpis["avg_defect_rate"],
            DEFECT_RATE_HIGH_PCT,
            DEFECT_RATE_LOW_PCT,
            invert=True,
        ),
    )
    st.write("")


def render_alert_banner(df: pd.DataFrame, kpis: dict) -> None:
    stockout_rows = df[df["Stock levels"] <= STOCKOUT_STOCK_LEVEL]
    low_stock_rows = df[
        (df["Stock levels"] > STOCKOUT_STOCK_LEVEL) & (df["Stock levels"] < LOW_STOCK_THRESHOLD)
    ]

    if stockout_rows.empty and low_stock_rows.empty:
        return

    message_parts = []
    if not stockout_rows.empty:
        message_parts.append(f"{len(stockout_rows)} SKU(s) out of stock")
    if not low_stock_rows.empty:
        message_parts.append(f"{len(low_stock_rows)} SKU(s) at low stock (< {LOW_STOCK_THRESHOLD} units)")

    st.markdown(
        f'<div class="alert-banner">⚠️ <b>Inventory alert:</b> {" · ".join(message_parts)}</div>',
        unsafe_allow_html=True,
    )
    with st.expander("View affected SKUs"):
        affected = pd.concat([stockout_rows, low_stock_rows])[
            ["SKU", "Product type", "Supplier name", "Stock levels", "Availability"]
        ].sort_values("Stock levels")
        st.dataframe(affected, width='stretch', hide_index=True)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def chart_stock_levels_by_sku(df: pd.DataFrame) -> go.Figure:
    top = df.sort_values("Stock levels", ascending=False).head(TOP_N_SKUS_CHART)
    fig = px.bar(top, x="SKU", y="Stock levels", color_discrete_sequence=[COLOR_VIOLET])
    fig.update_xaxes(categoryorder="total descending")
    return plotly_theme(fig, f"Stock Levels by SKU (Top {TOP_N_SKUS_CHART})")


def chart_lead_time_by_supplier(df: pd.DataFrame) -> go.Figure:
    fig = px.box(df, x="Supplier name", y="Lead times", color="Supplier name")
    fig.update_layout(showlegend=False)
    return plotly_theme(fig, "Lead Time by Supplier")


def chart_defect_rate_by_supplier(df: pd.DataFrame) -> go.Figure:
    grouped = df.groupby("Supplier name", as_index=False)["Defect rates"].mean()
    grouped = grouped.sort_values("Defect rates", ascending=False)
    fig = px.bar(
        grouped, x="Supplier name", y="Defect rates", color_discrete_sequence=[COLOR_VIOLET]
    )
    return plotly_theme(fig, "Defect Rate by Supplier (%)")


def chart_revenue_by_category(df: pd.DataFrame) -> go.Figure:
    grouped = df.groupby("Product type", as_index=False)["Revenue generated"].sum()
    fig = px.pie(
        grouped,
        names="Product type",
        values="Revenue generated",
        hole=0.55,
        color_discrete_sequence=CHART_COLORWAY,
    )
    return plotly_theme(fig, "Revenue by Category")


def chart_production_vs_sold(df: pd.DataFrame) -> go.Figure:
    grouped = df.groupby("Product type", as_index=False)[
        ["Production volumes", "Number of products sold"]
    ].sum()
    fig = go.Figure()
    fig.add_bar(
        x=grouped["Product type"], y=grouped["Production volumes"], name="Produced",
        marker_color=COLOR_VIOLET,
    )
    fig.add_bar(
        x=grouped["Product type"], y=grouped["Number of products sold"], name="Sold",
        marker_color=COLOR_VIOLET_SOFT,
    )
    fig.update_layout(barmode="group")
    return plotly_theme(fig, "Production vs Sold")


def chart_shipping_cost_by_carrier(df: pd.DataFrame) -> go.Figure:
    grouped = df.groupby("Shipping carriers", as_index=False)["Shipping costs"].mean()
    fig = px.bar(
        grouped,
        x="Shipping carriers",
        y="Shipping costs",
        color_discrete_sequence=[COLOR_VIOLET],
    )
    return plotly_theme(fig, "Avg Shipping Cost by Carrier")


# ---------------------------------------------------------------------------
# Raw data explorer
# ---------------------------------------------------------------------------


def render_raw_data_explorer(df: pd.DataFrame) -> None:
    with st.expander("Raw data explorer"):
        st.dataframe(df, width='stretch', hide_index=True)
        st.download_button(
            "Download filtered data as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="supply_chain_data_filtered.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Supply Chain Analytics", page_icon="📦", layout="wide")
    inject_css()

    raw_df = load_data(DATA_PATH)
    render_header()

    product_types, suppliers = render_sidebar(raw_df)
    df = filter_data(raw_df, product_types, suppliers)

    if df.empty:
        st.warning("No data matches the selected filters.")
        return

    kpis = compute_kpis(df)
    render_kpi_row(kpis)
    render_alert_banner(df, kpis)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(chart_stock_levels_by_sku(df), width='stretch')
    with col2:
        st.plotly_chart(chart_lead_time_by_supplier(df), width='stretch')

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(chart_defect_rate_by_supplier(df), width='stretch')
    with col4:
        st.plotly_chart(chart_revenue_by_category(df), width='stretch')

    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(chart_production_vs_sold(df), width='stretch')
    with col6:
        st.plotly_chart(chart_shipping_cost_by_carrier(df), width='stretch')

    render_raw_data_explorer(df)


if __name__ == "__main__":
    main()
