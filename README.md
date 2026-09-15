# Supply Chain Analytics

A Streamlit dashboard for monitoring inventory health, supplier reliability, and logistics
performance from a supply chain dataset.

## Running locally

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

The app reads data from `data/supply_chain_data.csv`. That file is not tracked in git (see
`.gitignore`) — place your own copy at that path before running the dashboard.

## KPIs

The dashboard surfaces five headline metrics as a mix of meters, a status badge, and plain
stat tiles (rather than uniform boxes), each colored green/mustard/red against a threshold so
issues are visible at a glance:

- **Availability Rate** — average of the `Availability` column across all SKUs. Green above
  70%, red below 50%.
- **Stock Coverage** — median number of days current stock would last, estimated as
  `Stock levels / (Number of products sold / 365)`, treating `Number of products sold` as
  annual demand. Green above 7 days, red below 3 days.
- **Stockouts** — count of SKUs with zero stock on hand. Red if any exist, green if none.
- **Avg Lead Time** — average of the `Lead times` column, in days. Shown as a neutral metric
  with no pass/fail threshold.
- **Avg Defect Rate** — average of the `Defect rates` column. Green below 1%, red above 2.5%.

An inventory alert banner appears above the charts whenever stockouts or low-stock SKUs
(under 10 units) are detected, with a collapsible list of the affected items.

## Charts

- **Stock Levels by SKU** — bar chart of the top SKUs by current stock, to spot overstocked
  items.
- **Lead Time by Supplier** — box plot of lead times per supplier, showing both typical
  performance and variability.
- **Defect Rate by Supplier** — bar chart of average defect rate per supplier, to flag
  quality risk.
- **Revenue by Category** — donut chart of total revenue generated per product type.
- **Production vs Sold** — grouped bar chart comparing units produced against units sold per
  product type, to spot over- or under-production.
- **Shipping Cost by Carrier** — bar chart of average shipping cost per carrier.

A collapsible **raw data explorer** at the bottom shows the filtered dataset in full, with a
CSV download button.

## Filters

The sidebar lets you filter the entire dashboard by **product type** and **supplier** via
checkboxes (all selected by default), and shows quick dataset stats (total SKUs, suppliers,
product types).

## Tech

- **Streamlit** for the app shell and layout
- **Pandas** for data loading and aggregation
- **Plotly** for interactive charts
