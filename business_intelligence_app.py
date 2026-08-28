"""
Interactive Business Intelligence Dashboard

"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Business Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------
st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fb;
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 15px 15px 8px 15px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
    }
    .block-container {
        padding-top: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    return df


DATA_PATH = "data/business_data.csv"
df = load_data(DATA_PATH)

# ----------------------------------------------------------------------
# SIDEBAR — FILTERS
# ----------------------------------------------------------------------
st.sidebar.title("🔎 Filters")

min_date, max_date = df["date"].min().date(), df["date"].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

regions = sorted(df["region"].unique())
selected_regions = st.sidebar.multiselect("Region", regions, default=regions)

categories = sorted(df["category"].unique())
selected_categories = st.sidebar.multiselect("Category", categories, default=categories)

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Dataset: {len(df):,} rows | {min_date} → {max_date}"
)

# ----------------------------------------------------------------------
# APPLY FILTERS
# ----------------------------------------------------------------------
mask = (
    (df["date"].dt.date >= start_date)
    & (df["date"].dt.date <= end_date)
    & (df["region"].isin(selected_regions))
    & (df["category"].isin(selected_categories))
)
fdf = df.loc[mask].copy()

if fdf.empty:
    st.warning("No data matches the selected filters. Adjust the filters in the sidebar.")
    st.stop()

# previous equal-length period, for delta comparisons on the KPI cards
period_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days + 1
prev_start = pd.Timestamp(start_date) - pd.Timedelta(days=period_days)
prev_end = pd.Timestamp(start_date) - pd.Timedelta(days=1)
pmask = (
    (df["date"] >= prev_start)
    & (df["date"] <= prev_end)
    & (df["region"].isin(selected_regions))
    & (df["category"].isin(selected_categories))
)
pdf = df.loc[pmask].copy()


def pct_delta(current, previous):
    if previous == 0 or pd.isna(previous):
        return None
    return (current - previous) / previous * 100


# ----------------------------------------------------------------------
# KPI CALCULATIONS
# ----------------------------------------------------------------------
total_revenue = fdf["revenue"].sum()
active_users = fdf["active_users"].sum()
churned_users = fdf["churned_users"].sum()
churn_rate = (churned_users / active_users * 100) if active_users else 0
total_orders = fdf["orders"].sum()
avg_ticket_size = total_revenue / total_orders if total_orders else 0

prev_revenue = pdf["revenue"].sum()
prev_active_users = pdf["active_users"].sum()
prev_churned = pdf["churned_users"].sum()
prev_churn_rate = (prev_churned / prev_active_users * 100) if prev_active_users else 0
prev_orders = pdf["orders"].sum()
prev_avg_ticket = prev_revenue / prev_orders if prev_orders else 0

d_revenue = pct_delta(total_revenue, prev_revenue)
d_users = pct_delta(active_users, prev_active_users)
d_churn = pct_delta(churn_rate, prev_churn_rate)
d_ticket = pct_delta(avg_ticket_size, prev_avg_ticket)

# ----------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------
st.title("📊 Business Intelligence Dashboard")
st.caption(
    f"Showing **{start_date} → {end_date}** | "
    f"Regions: {', '.join(selected_regions) if len(selected_regions) < len(regions) else 'All'} | "
    f"Categories: {', '.join(selected_categories) if len(selected_categories) < len(categories) else 'All'}"
)

# ----------------------------------------------------------------------
# KPI CARDS
# ----------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"₹{total_revenue:,.0f}",
          f"{d_revenue:+.1f}%" if d_revenue is not None else None)
k2.metric("Active Users", f"{active_users:,}",
          f"{d_users:+.1f}%" if d_users is not None else None)
k3.metric("Churn %", f"{churn_rate:.2f}%",
          f"{d_churn:+.1f}%" if d_churn is not None else None,
          delta_color="inverse")
k4.metric("Avg Ticket Size", f"₹{avg_ticket_size:,.0f}",
          f"{d_ticket:+.1f}%" if d_ticket is not None else None)

st.markdown("---")

# ----------------------------------------------------------------------
# ROW 1: Revenue trend + Region split
# ----------------------------------------------------------------------
c1, c2 = st.columns((2, 1))

with c1:
    st.subheader("Revenue Trend")
    trend = fdf.groupby(pd.Grouper(key="date", freq="W"))["revenue"].sum().reset_index()
    fig_trend = px.area(trend, x="date", y="revenue", labels={"revenue": "Revenue (₹)", "date": ""})
    fig_trend.update_traces(line_color="#6366f1", fillcolor="rgba(99,102,241,0.15)")
    fig_trend.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=340)
    st.plotly_chart(fig_trend, use_container_width=True)

with c2:
    st.subheader("Revenue by Region")
    by_region = fdf.groupby("region")["revenue"].sum().reset_index().sort_values("revenue")
    fig_region = px.bar(by_region, x="revenue", y="region", orientation="h",
                         labels={"revenue": "Revenue (₹)", "region": ""},
                         color="revenue", color_continuous_scale="Purples")
    fig_region.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=340,
                              coloraxis_showscale=False)
    st.plotly_chart(fig_region, use_container_width=True)

# ----------------------------------------------------------------------
# ROW 2: Category breakdown + Churn trend
# ----------------------------------------------------------------------
c3, c4 = st.columns(2)

with c3:
    st.subheader("Revenue Share by Category")
    by_cat = fdf.groupby("category")["revenue"].sum().reset_index()
    fig_cat = px.pie(by_cat, names="category", values="revenue", hole=0.5,
                      color_discrete_sequence=px.colors.sequential.Purples_r)
    fig_cat.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=340)
    st.plotly_chart(fig_cat, use_container_width=True)

with c4:
    st.subheader("Churn Rate Trend")
    churn_trend = fdf.groupby(pd.Grouper(key="date", freq="W")).agg(
        active_users=("active_users", "sum"), churned_users=("churned_users", "sum")
    ).reset_index()
    churn_trend["churn_rate"] = (churn_trend["churned_users"] / churn_trend["active_users"] * 100).fillna(0)
    fig_churn = go.Figure()
    fig_churn.add_trace(go.Scatter(x=churn_trend["date"], y=churn_trend["churn_rate"],
                                    mode="lines+markers", line=dict(color="#ef4444")))
    fig_churn.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=340,
                             yaxis_title="Churn %", xaxis_title="")
    st.plotly_chart(fig_churn, use_container_width=True)

# ----------------------------------------------------------------------
# ROW 3: Orders vs Ticket Size by category (table + bar)
# ----------------------------------------------------------------------
st.subheader("Category Performance")
cat_perf = fdf.groupby("category").agg(
    orders=("orders", "sum"),
    revenue=("revenue", "sum"),
).reset_index()
cat_perf["avg_ticket"] = cat_perf["revenue"] / cat_perf["orders"]
cat_perf = cat_perf.sort_values("revenue", ascending=False)

c5, c6 = st.columns((1.3, 1))
with c5:
    fig_cat_perf = px.bar(cat_perf, x="category", y="revenue",
                           labels={"revenue": "Revenue (₹)", "category": ""},
                           color="category", color_discrete_sequence=px.colors.qualitative.Set2)
    fig_cat_perf.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, showlegend=False)
    st.plotly_chart(fig_cat_perf, use_container_width=True)

with c6:
    st.dataframe(
        cat_perf.rename(columns={
            "category": "Category", "orders": "Orders",
            "revenue": "Revenue (₹)", "avg_ticket": "Avg Ticket (₹)"
        }).style.format({"Revenue (₹)": "{:,.0f}", "Avg Ticket (₹)": "{:,.0f}"}),
        use_container_width=True, height=320, hide_index=True
    )

st.markdown("---")
st.caption("Built with Streamlit + Plotly · Data is synthetic sample data for demonstration purposes.")
