"""Supply Chain Analytics — a Streamlit dashboard for supply chain KPIs and trends."""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_PATH = "data/supply_chain_data.csv"

# Palette — white surface, bleu canard (teal) + jaune moutarde (mustard) accents
COLOR_BG = "#FFFFFF"
COLOR_SURFACE = "#F4F8F8"
COLOR_INK = "#1A1A1A"
COLOR_MUTED = "#6B7280"

COLOR_TEAL = "#0E7C86"
COLOR_TEAL_DARK = "#0B5E66"
COLOR_TEAL_SOFT = "#DCEEF0"
COLOR_MUSTARD = "#DDA51C"
COLOR_MUSTARD_SOFT = "#FBEED2"
COLOR_CHARCOAL = "#4B5563"

# Status colors (reserved — never reused as brand/categorical colors)
COLOR_GOOD = "#0CA30C"
COLOR_WARNING = "#DDA51C"
COLOR_CRITICAL = "#D03B3B"

CHART_COLORWAY = [COLOR_TEAL, COLOR_MUSTARD, COLOR_CHARCOAL]

# KPI thresholds
AVAILABILITY_HIGH = 70
AVAILABILITY_LOW = 50
STOCK_COVERAGE_HIGH_DAYS = 7
STOCK_COVERAGE_LOW_DAYS = 3
DEFECT_RATE_HIGH_PCT = 2.5
DEFECT_RATE_LOW_PCT = 1.0
DEFECT_RATE_METER_MAX = 2 * DEFECT_RATE_HIGH_PCT  # meter scale ceiling

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


def status_color(value: float, high: float, low: float, invert: bool = False) -> str:
    """Good above `high`, critical below `low`, warning in between. `invert` flips the direction."""
    if invert:
        if value < low:
            return COLOR_GOOD
        if value > high:
            return COLOR_CRITICAL
        return COLOR_WARNING
    if value > high:
        return COLOR_GOOD
    if value < low:
        return COLOR_CRITICAL
    return COLOR_WARNING


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
            background-color: {COLOR_BG};
            color: {COLOR_INK};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {COLOR_SURFACE};
            border-right: 1px solid #E5E7EB;
        }}
        section[data-testid="stSidebar"] * {{
            color: {COLOR_INK};
        }}
        section[data-testid="stSidebar"] h3 {{
            color: {COLOR_TEAL_DARK};
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {COLOR_INK};
            font-weight: 700;
        }}
        .app-subtitle {{
            color: {COLOR_MUTED};
            font-size: 0.95rem;
            margin-top: -0.6rem;
        }}
        .section-title {{
            color: {COLOR_INK};
            font-weight: 600;
            font-size: 1.05rem;
            margin: 0.4rem 0 0.6rem 0;
        }}
        /* --- Stat tiles (KPI row) — no boxes, mixed visual forms --- */
        .stat-tile {{
            padding: 0.2rem 0.6rem;
            height: 100%;
        }}
        .stat-top {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .stat-icon {{
            font-size: 1.2rem;
        }}
        .stat-value {{
            font-size: 1.8rem;
            font-weight: 800;
            color: {COLOR_INK};
            line-height: 1.15;
        }}
        .stat-label {{
            color: {COLOR_MUTED};
            font-size: 0.8rem;
            font-weight: 500;
            margin-top: 0.15rem;
        }}
        .stat-accent {{
            height: 3px;
            width: 34px;
            border-radius: 2px;
            margin: 0.4rem 0 0.35rem 0;
        }}
        .meter-track {{
            background-color: {COLOR_SURFACE};
            border-radius: 999px;
            height: 8px;
            width: 100%;
            margin-top: 0.5rem;
            overflow: hidden;
        }}
        .meter-fill {{
            height: 8px;
            border-radius: 999px;
        }}
        .stat-caption {{
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 0.15rem;
        }}
        /* --- Alert pills --- */
        .alert-pills-wrap {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.6rem;
            margin-bottom: 0.6rem;
        }}
        .alert-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem 0.9rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        /* --- Scrolling stockout ticker --- */
        .ticker-wrap {{
            width: 100%;
            overflow: hidden;
            background-color: {COLOR_CRITICAL}14;
            border-radius: 999px;
            padding: 0.55rem 0;
            margin-bottom: 1rem;
        }}
        .ticker-track {{
            display: inline-block;
            white-space: nowrap;
            padding-left: 100%;
            animation: ticker-scroll 15s linear infinite;
        }}
        .ticker-item {{
            display: inline-block;
            padding-right: 3rem;
            color: {COLOR_CRITICAL};
            font-weight: 600;
            font-size: 0.85rem;
        }}
        @keyframes ticker-scroll {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(-100%); }}
        }}
        /* --- Chart cards — kept as boxes, restyled to the light theme --- */
        div[data-testid="stPlotlyChart"] {{
            background-color: {COLOR_SURFACE};
            border-radius: 12px;
            padding: 0.6rem;
            border: 1px solid #E5E7EB;
            box-sizing: border-box;
            overflow: hidden;
        }}
        div[data-testid="stPlotlyChart"] > div {{
            max-width: 100%;
        }}
        div[data-testid="stExpander"] {{
            background-color: {COLOR_SURFACE};
            border-radius: 16px;
            border: 1px solid #E5E7EB;
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
        title=dict(text=title, font=dict(color=COLOR_INK, size=15, family="Inter")),
        paper_bgcolor=COLOR_SURFACE,
        plot_bgcolor=COLOR_SURFACE,
        font=dict(color=COLOR_INK, family="Inter"),
        colorway=CHART_COLORWAY,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    fig.update_yaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    return fig


# ---------------------------------------------------------------------------
# UI: header, sidebar
# ---------------------------------------------------------------------------


def render_header() -> None:
    st.markdown("# Supply Chain Analytics")
    st.markdown(
        '<div class="app-subtitle">Inventory, supplier, and logistics performance at a glance</div>',
        unsafe_allow_html=True,
    )
    st.write("")


def render_sidebar(df: pd.DataFrame) -> tuple:
    st.sidebar.markdown("### Filters")

    st.sidebar.markdown("**Product type**")
    product_types = [
        pt
        for pt in sorted(df["Product type"].unique())
        if st.sidebar.checkbox(pt, value=True, key=f"filter_pt_{pt}")
    ]

    st.sidebar.markdown("**Supplier**")
    suppliers = [
        sup
        for sup in sorted(df["Supplier name"].unique())
        if st.sidebar.checkbox(sup, value=True, key=f"filter_sup_{sup}")
    ]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Dataset stats")
    st.sidebar.metric("Total SKUs", df["SKU"].nunique())
    st.sidebar.metric("Suppliers", df["Supplier name"].nunique())
    st.sidebar.metric("Product types", df["Product type"].nunique())

    return product_types or list(df["Product type"].unique()), suppliers or list(
        df["Supplier name"].unique()
    )


# ---------------------------------------------------------------------------
# UI: KPI stat tiles (mixed visual forms — meters, a badge, plain stats)
# ---------------------------------------------------------------------------


def render_meter_tile(col, icon: str, display_value: str, label: str, fill_pct: float, color: str) -> None:
    fill_pct = max(0, min(100, fill_pct))
    with col:
        st.markdown(
            f"""
            <div class="stat-tile">
                <div class="stat-top"><span class="stat-icon">{icon}</span></div>
                <div class="stat-value">{display_value}</div>
                <div class="stat-label">{label}</div>
                <div class="meter-track">
                    <div class="meter-fill" style="width:{fill_pct}%; background-color:{color};"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_plain_tile(
    col, icon: str, display_value: str, label: str, accent_color: str, caption: Optional[str] = None
) -> None:
    caption_html = (
        f'<div class="stat-caption" style="color:{accent_color};">{caption}</div>'
        if caption
        else ""
    )
    with col:
        st.markdown(
            f"""
            <div class="stat-tile">
                <div class="stat-top"><span class="stat-icon">{icon}</span></div>
                <div class="stat-value">{display_value}</div>
                <div class="stat-accent" style="background-color:{accent_color};"></div>
                <div class="stat-label">{label}</div>
                {caption_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_kpi_row(kpis: dict) -> None:
    cols = st.columns(5)

    availability_color = status_color(kpis["availability_rate"], AVAILABILITY_HIGH, AVAILABILITY_LOW)
    render_meter_tile(
        cols[0],
        "📦",
        f'{kpis["availability_rate"]:.1f}%',
        "Availability Rate",
        kpis["availability_rate"],
        availability_color,
    )

    coverage_color = status_color(
        kpis["stock_coverage_days"], STOCK_COVERAGE_HIGH_DAYS, STOCK_COVERAGE_LOW_DAYS
    )
    render_plain_tile(
        cols[1],
        "🗓️",
        f'{kpis["stock_coverage_days"]:.1f}d',
        "Stock Coverage (median)",
        coverage_color,
    )

    stockouts = kpis["stockouts"]
    stockout_color = COLOR_CRITICAL if stockouts > 0 else COLOR_GOOD
    render_plain_tile(
        cols[2],
        "🚨",
        f"{stockouts}",
        "Stockouts",
        stockout_color,
        caption="Action needed" if stockouts > 0 else "All clear",
    )

    render_plain_tile(
        cols[3],
        "🚚",
        f'{kpis["avg_lead_time"]:.1f}d',
        "Avg Lead Time",
        COLOR_TEAL,
    )

    defect_color = status_color(
        kpis["avg_defect_rate"], DEFECT_RATE_HIGH_PCT, DEFECT_RATE_LOW_PCT, invert=True
    )
    render_meter_tile(
        cols[4],
        "🛠️",
        f'{kpis["avg_defect_rate"]:.2f}%',
        "Avg Defect Rate",
        (kpis["avg_defect_rate"] / DEFECT_RATE_METER_MAX) * 100,
        defect_color,
    )
    st.write("")


def render_alert_banner(df: pd.DataFrame) -> None:
    stockout_rows = df[df["Stock levels"] <= STOCKOUT_STOCK_LEVEL]
    low_stock_rows = df[
        (df["Stock levels"] > STOCKOUT_STOCK_LEVEL) & (df["Stock levels"] < LOW_STOCK_THRESHOLD)
    ]

    if stockout_rows.empty and low_stock_rows.empty:
        return

    pills = []
    if not stockout_rows.empty:
        pills.append(
            f'<span class="alert-pill" style="background-color:{COLOR_CRITICAL}22; color:{COLOR_CRITICAL};">'
            f"🚨 {len(stockout_rows)} SKU(s) out of stock</span>"
        )
    if not low_stock_rows.empty:
        pills.append(
            f'<span class="alert-pill" style="background-color:{COLOR_WARNING}22; color:{COLOR_WARNING};">'
            f"⚠️ {len(low_stock_rows)} SKU(s) low stock (&lt; {LOW_STOCK_THRESHOLD} units)</span>"
        )

    st.markdown(f'<div class="alert-pills-wrap">{"".join(pills)}</div>', unsafe_allow_html=True)
    with st.expander("View affected SKUs"):
        affected = pd.concat([stockout_rows, low_stock_rows])[
            ["SKU", "Product type", "Supplier name", "Stock levels", "Availability"]
        ].sort_values("Stock levels")
        st.dataframe(affected, width="stretch", hide_index=True)


def render_stockout_ticker(df: pd.DataFrame) -> None:
    stockout_rows = df[df["Stock levels"] <= STOCKOUT_STOCK_LEVEL]
    if stockout_rows.empty:
        return

    items = [
        f"🚨 {row['SKU']} — {row['Product type']} ({row['Supplier name']}) out of stock"
        for _, row in stockout_rows.iterrows()
    ]
    ticker_text = "".join(f'<span class="ticker-item">{item}</span>' for item in items)

    st.markdown(
        f"""
        <div class="ticker-wrap">
            <div class="ticker-track">{ticker_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def chart_stock_levels_by_sku(df: pd.DataFrame) -> go.Figure:
    top = df.sort_values("Stock levels", ascending=False).head(TOP_N_SKUS_CHART)
    fig = px.bar(top, x="SKU", y="Stock levels", color_discrete_sequence=[COLOR_TEAL])
    fig.update_xaxes(categoryorder="total descending")
    return plotly_theme(fig, f"Stock Levels by SKU (Top {TOP_N_SKUS_CHART})")


def chart_lead_time_by_supplier(df: pd.DataFrame) -> go.Figure:
    fig = px.box(df, x="Supplier name", y="Lead times", color_discrete_sequence=[COLOR_TEAL])
    fig.update_layout(showlegend=False)
    return plotly_theme(fig, "Lead Time by Supplier")


def chart_defect_rate_by_supplier(df: pd.DataFrame) -> go.Figure:
    grouped = df.groupby("Supplier name", as_index=False)["Defect rates"].mean()
    grouped = grouped.sort_values("Defect rates", ascending=False)
    fig = px.bar(
        grouped, x="Supplier name", y="Defect rates", color_discrete_sequence=[COLOR_TEAL]
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
        marker_color=COLOR_TEAL,
    )
    fig.add_bar(
        x=grouped["Product type"], y=grouped["Number of products sold"], name="Sold",
        marker_color=COLOR_MUSTARD,
    )
    fig.update_layout(barmode="group")
    return plotly_theme(fig, "Production vs Sold")


def chart_shipping_cost_by_carrier(df: pd.DataFrame) -> go.Figure:
    grouped = df.groupby("Shipping carriers", as_index=False)["Shipping costs"].mean()
    fig = px.bar(
        grouped,
        x="Shipping carriers",
        y="Shipping costs",
        color_discrete_sequence=[COLOR_TEAL],
    )
    return plotly_theme(fig, "Avg Shipping Cost by Carrier")


# ---------------------------------------------------------------------------
# Raw data explorer
# ---------------------------------------------------------------------------


def render_raw_data_explorer(df: pd.DataFrame) -> None:
    with st.expander("Raw data explorer"):
        st.dataframe(df, width="stretch", hide_index=True)
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
    product_types, suppliers = render_sidebar(raw_df)
    df = filter_data(raw_df, product_types, suppliers)

    if df.empty:
        render_header()
        st.warning("No data matches the selected filters.")
        return

    render_stockout_ticker(df)
    render_header()

    kpis = compute_kpis(df)
    render_kpi_row(kpis)
    render_alert_banner(df)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(chart_stock_levels_by_sku(df), use_container_width=True)
    with col2:
        st.plotly_chart(chart_lead_time_by_supplier(df), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(chart_defect_rate_by_supplier(df), use_container_width=True)
    with col4:
        st.plotly_chart(chart_revenue_by_category(df), use_container_width=True)

    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(chart_production_vs_sold(df), use_container_width=True)
    with col6:
        st.plotly_chart(chart_shipping_cost_by_carrier(df), use_container_width=True)

    render_raw_data_explorer(df)


if __name__ == "__main__":
    main()
