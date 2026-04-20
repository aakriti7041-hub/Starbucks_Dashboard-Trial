"""
Starbucks India — Project Ignite Pilot Dashboard (v2)
======================================================
Matches the Project_Ignite_KPI.xlsx template structure with added visualizations.

Tabs:
  1A. Overall Summary      — heatmap of incremental lift across pilots & metrics
  1B. Pilot Summary        — per-pilot Pilot vs Control comparison (weekly)
  1C. Deep Dive            — channel-level mix, filterable
  2A. Monthly Summary      — aggregated monthly view
  2B. Monthly Pilot Summary — per-pilot monthly deep dive
  3A. Pricing Objective    — ADT%, ADT abs, USD, APR splits by category
  3B. Loyalty Objective    — new vs existing, frequency

Run:
  pip install streamlit pandas numpy plotly
  streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from pathlib import Path
import glob

import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Project Ignite — Pilot Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Starbucks theme
st.markdown("""
<style>
    :root { --sbux-green: #00704A; --sbux-dark: #1e3932; }
    .main .block-container { padding-top: 1.5rem; max-width: 1700px; }
    h1, h2, h3 { color: #1e3932; }
    .stMetric { background: #F1F8F6; padding: 12px 16px; border-radius: 8px;
                border-left: 4px solid #00704A; }
    .positive { color: #00704A; font-weight: 600; }
    .negative { color: #c0392b; font-weight: 600; }
    .stDataFrame { font-size: 13px; }
    [data-testid="stSidebar"] { background-color: #F8FAF9; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATA LOADING
# ============================================================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

@st.cache_data(ttl=3600)
def load_data():
    files = sorted(glob.glob(str(DATA_DIR / "*.csv")))
    if not files:
        return None
    dfs = [pd.read_csv(f, parse_dates=['transaction_datetime']) for f in files]
    all_df = pd.concat(dfs, ignore_index=True)
    all_df = all_df.drop_duplicates(subset=['transaction_id', 'item_name', 'store_id'])
    all_df['date'] = all_df['transaction_datetime'].dt.date
    all_df['week_start'] = pd.to_datetime(all_df['date']).dt.to_period('W').dt.start_time
    all_df['month_start'] = pd.to_datetime(all_df['date']).dt.to_period('M').dt.start_time
    # Category remapping to template buckets
    all_df['category_bucket'] = all_df['category'].map({
        'EPP': 'EPP',
        'Tasty Recruiter': 'Recruiter',
        'Everyday Core': 'Core',
        'Expert Brew': 'Expert Brew ++',
        'Food - Beverages': 'Food',
        'Food': 'Food',
    }).fillna('Other')
    return all_df

df = load_data()

if df is None or df.empty:
    st.error("⚠️ No data found in `data/` folder. Drop a CSV file there and refresh (press R).")
    st.info("Expected columns: transaction_id, transaction_datetime, store_id, store_name, "
            "micro_market, market_tier, pilot, pilot_strategy, store_type, item_name, "
            "category, quantity, unit_price, line_total, channel, payment_method, "
            "loyalty_member, is_new_registration")
    st.stop()

# ============================================================
# SIDEBAR — GLOBAL FILTERS (match template filters)
# ============================================================
with st.sidebar:
    st.markdown("### ☕ Project Ignite")
    st.caption("Pilot measurement dashboard")
    st.markdown("---")
    st.markdown("### 🔍 Filters")

    # Market tier — matches template: Metro A/B, Metro C, T1, T2
    tiers = ['All'] + sorted(df['market_tier'].unique().tolist())
    sel_tier = st.selectbox("**Market**", tiers, key='tier')

    # Micro-market
    if sel_tier != 'All':
        markets = ['All'] + sorted(df[df['market_tier']==sel_tier]['micro_market'].unique().tolist())
    else:
        markets = ['All'] + sorted(df['micro_market'].unique().tolist())
    sel_market = st.selectbox("**Micro-market**", markets, key='market')

    # Channel filter
    channels = ['All'] + sorted(df['channel'].unique().tolist())
    sel_channel = st.selectbox("**Channel**", channels, key='channel')

    # Product filter
    sel_product = st.radio("**Product**", ['All', 'Beverage', 'Food'], horizontal=True, key='product')

    st.markdown("---")
    st.markdown("### 📅 Time period")

    min_date = df['date'].min()
    max_date = df['date'].max()

    st.caption("**Baseline** (FY'26 Jan YTD)")
    b_col1, b_col2 = st.columns(2)
    base_start = b_col1.date_input("From", min_date, key='bs', label_visibility='collapsed')
    base_end = b_col2.date_input("To", min(min_date + timedelta(days=30), max_date), key='be', label_visibility='collapsed')

    st.caption("**Current period**")
    cur_preset = st.radio(" ", ["Latest week", "Latest 2 weeks", "Latest month", "Custom"],
                         horizontal=False, key='preset', label_visibility='collapsed')
    if cur_preset == "Latest week":
        cur_end = max_date; cur_start = cur_end - timedelta(days=6)
    elif cur_preset == "Latest 2 weeks":
        cur_end = max_date; cur_start = cur_end - timedelta(days=13)
    elif cur_preset == "Latest month":
        cur_end = max_date; cur_start = cur_end - timedelta(days=29)
    else:
        c_col1, c_col2 = st.columns(2)
        cur_start = c_col1.date_input("From", max_date - timedelta(days=6), key='cs', label_visibility='collapsed')
        cur_end = c_col2.date_input("To", max_date, key='ce', label_visibility='collapsed')

    st.markdown("---")
    st.caption(f"📊 **Data range:** {min_date} → {max_date}")
    st.caption(f"📈 **Rows loaded:** {len(df):,}")
    st.caption(f"🔄 **Last refresh:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============================================================
# APPLY FILTERS
# ============================================================
fdf = df.copy()
if sel_tier != 'All':
    fdf = fdf[fdf['market_tier']==sel_tier]
if sel_market != 'All':
    fdf = fdf[fdf['micro_market']==sel_market]
if sel_channel != 'All':
    fdf = fdf[fdf['channel']==sel_channel]
if sel_product == 'Beverage':
    fdf = fdf[fdf['category_bucket'].isin(['EPP','Recruiter','Core','Expert Brew ++'])]
elif sel_product == 'Food':
    fdf = fdf[fdf['category_bucket']=='Food']

# ============================================================
# METRIC HELPERS
# ============================================================
def compute_metrics(subset_df, n_stores):
    """Compute all dashboard metrics for a subset."""
    default = dict.fromkeys([
        'adt','ads','usd','at','ipt','ipt_bev','ipt_food','revenue_week','revenue_month','gm_pct',
        'adt_nonsr','adt_sr','adt_delivery',
        'usd_epp','usd_recruiter','usd_core','usd_expert','usd_food',
        'adt_epp','adt_recruiter','adt_core','adt_expert','adt_food',
        'apr_epp','apr_recruiter','apr_core','apr_expert','apr_food','apr_total',
        'new_reg','adt_new','adt_existing','freq',
    ], 0)
    if subset_df.empty or n_stores == 0:
        return default

    txns = subset_df.groupby('transaction_id').agg(
        dt=('transaction_datetime','first'),
        revenue=('line_total','sum'),
        units=('quantity','sum'),
        channel=('channel','first'),
        loyalty=('loyalty_member','first'),
        new_reg=('is_new_registration','first'),
    ).reset_index()

    n_days = max(1, (subset_df['date'].max() - subset_df['date'].min()).days + 1)

    default['adt'] = len(txns) / n_days / n_stores
    default['ads'] = txns['revenue'].sum() / n_days / n_stores
    default['usd'] = txns['units'].sum() / n_days / n_stores
    default['at'] = txns['revenue'].mean() if len(txns) else 0  # Average Ticket
    default['ipt'] = txns['units'].mean() if len(txns) else 0

    bev_cats = ['EPP','Recruiter','Core','Expert Brew ++']
    bev = subset_df[subset_df['category_bucket'].isin(bev_cats)]
    food = subset_df[subset_df['category_bucket']=='Food']
    default['ipt_bev'] = bev['quantity'].sum() / max(1, len(txns))
    default['ipt_food'] = food['quantity'].sum() / max(1, len(txns))
    default['revenue_week'] = txns['revenue'].sum() / max(1, n_days/7) / 1e7
    default['revenue_month'] = txns['revenue'].sum() / max(1, n_days/30) / 1e7
    default['gm_pct'] = 0.793  # placeholder - would come from COGS data

    # Channel (ADT per channel per store)
    ch = txns.groupby('channel').size()
    default['adt_nonsr'] = ch.get('Offline - Non-SR',0) / n_days / n_stores
    default['adt_sr'] = ch.get('Offline - SR',0) / n_days / n_stores
    default['adt_delivery'] = ch.get('Delivery',0) / n_days / n_stores

    # Menu mix: USD (units sold daily per category) and ADT (txns containing category)
    tu = subset_df['quantity'].sum()
    for cat, key in [('EPP','epp'),('Recruiter','recruiter'),('Core','core'),
                     ('Expert Brew ++','expert'),('Food','food')]:
        cat_df = subset_df[subset_df['category_bucket']==cat]
        default[f'usd_{key}'] = cat_df['quantity'].sum() / max(1,tu) * 100  # % of units
        # ADT for category = unique txns with this category / days / stores
        cat_txns = cat_df['transaction_id'].nunique()
        default[f'adt_{key}'] = cat_txns / n_days / n_stores
        # APR = revenue / units for this category (average price realization)
        if cat_df['quantity'].sum() > 0:
            default[f'apr_{key}'] = cat_df['line_total'].sum() / cat_df['quantity'].sum()

    if subset_df['quantity'].sum() > 0:
        default['apr_total'] = subset_df['line_total'].sum() / subset_df['quantity'].sum()

    # Loyalty
    default['new_reg'] = int(txns['new_reg'].sum())
    default['adt_new'] = txns['new_reg'].sum() / n_days / n_stores
    default['adt_existing'] = txns['loyalty'].sum() / n_days / n_stores
    n_loyal = txns['loyalty'].sum()
    default['freq'] = len(txns) / n_loyal if n_loyal > 0 else 0

    return default

def pct_change(c, b):
    return 0 if b == 0 else (c - b) / b * 100

# Precompute once per pilot × store_type × period
@st.cache_data(ttl=600)
def build_pilot_metrics(fdf_hash, base_start, base_end, cur_start, cur_end):
    # Note: fdf_hash is just for cache invalidation; real data comes from global `fdf`
    results = {}
    for pilot in sorted(fdf['pilot'].unique()):
        results[pilot] = {'strategy': fdf[fdf['pilot']==pilot]['pilot_strategy'].iloc[0]}
        for st_type in ['Pilot','Control']:
            n = fdf[(fdf['pilot']==pilot) & (fdf['store_type']==st_type)]['store_id'].nunique()
            results[pilot][f'{st_type}_n'] = n
            base = fdf[(fdf['pilot']==pilot) & (fdf['store_type']==st_type) &
                       (fdf['date']>=base_start) & (fdf['date']<=base_end)]
            cur = fdf[(fdf['pilot']==pilot) & (fdf['store_type']==st_type) &
                      (fdf['date']>=cur_start) & (fdf['date']<=cur_end)]
            results[pilot][f'{st_type}_base'] = compute_metrics(base, n)
            results[pilot][f'{st_type}_cur'] = compute_metrics(cur, n)
    return results

metrics = build_pilot_metrics(len(fdf), base_start, base_end, cur_start, cur_end)

# ============================================================
# HEADER
# ============================================================
st.markdown("# ☕ Project Ignite — Pilot Measurement Dashboard")
st.caption(f"**Baseline:** {base_start} → {base_end}  |  **Current:** {cur_start} → {cur_end}  "
           f"|  **Filters:** {sel_tier} · {sel_market} · {sel_channel} · {sel_product}")

# ============================================================
# TABS — match template structure
# ============================================================
tab_1a, tab_1b, tab_1c, tab_2a, tab_2b, tab_3a, tab_3b = st.tabs([
    "**1A. Overall summary**",
    "**1B. Pilot summary**",
    "**1C. Deep dive**",
    "**2A. Monthly summary**",
    "**2B. Monthly pilot summary**",
    "**3A. Pricing objective**",
    "**3B. Loyalty objective**",
])

# ============================================================
# TAB 1A — OVERALL SUMMARY (heatmap of incremental lift per pilot × metric)
# ============================================================
with tab_1a:
    st.markdown("### Incremental lift — all pilots at a glance")
    st.caption("Each cell = (Pilot store % change) − (Control store % change), expressed in percentage points. "
               "Green = pilot beating control, red = pilot underperforming.")

    METRIC_ROWS = [
        ('Overall business', 'ADT', 'adt', 'number'),
        ('Overall business', 'ADS', 'ads', 'number'),
        ('Overall business', 'USD', 'usd', 'number'),
        ('Overall business', 'AT', 'at', 'number'),
        ('Overall business', 'IPT', 'ipt', 'number'),
        ('Overall business', 'Revenue/week (Cr)', 'revenue_week', 'number'),
        ('Channel mix', 'ADT: Offline — Non-SR', 'adt_nonsr', 'number'),
        ('Channel mix', 'ADT: Offline — SR', 'adt_sr', 'number'),
        ('Channel mix', 'ADT: Delivery', 'adt_delivery', 'number'),
        ('Menu mix', 'USD: EPP', 'usd_epp', 'pct'),
        ('Menu mix', 'USD: Tasty Recruiter', 'usd_recruiter', 'pct'),
        ('Menu mix', 'USD: Everyday Core', 'usd_core', 'pct'),
        ('Menu mix', 'USD: Expert Brew', 'usd_expert', 'pct'),
    ]
    pilots = sorted(metrics.keys())

    # Build incremental matrix
    heatmap_rows = []
    for dim, label, key, _ in METRIC_ROWS:
        row = {'Dimension': dim, 'Metric': label}
        for p in pilots:
            pb = metrics[p]['Pilot_base'][key]
            pc = metrics[p]['Pilot_cur'][key]
            cb = metrics[p]['Control_base'][key]
            cc = metrics[p]['Control_cur'][key]
            incr = pct_change(pc, pb) - pct_change(cc, cb)
            row[p] = incr
        heatmap_rows.append(row)

    heat_df = pd.DataFrame(heatmap_rows)
    display_df = heat_df.copy()
    for p in pilots:
        display_df[p] = display_df[p].apply(lambda x: f"{x:+.1f}pp")

    # Color scale using pandas Styler
    def color_cell(val):
        try:
            n = float(str(val).replace('pp','').replace('+',''))
            if n > 3: return 'background-color: #0F6E56; color: white; font-weight: 600;'
            if n > 1: return 'background-color: #9FE1CB; color: #04342C; font-weight: 600;'
            if n > -1: return 'color: #888;'
            if n > -3: return 'background-color: #F7C1C1; color: #501313; font-weight: 600;'
            return 'background-color: #A32D2D; color: white; font-weight: 600;'
        except: return ''

    styled = display_df.style.map(color_cell, subset=pilots)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500)

    st.markdown("---")
    # Summary KPIs
    st.markdown("### Headline — current week across all pilots")
    c1, c2, c3, c4, c5 = st.columns(5)
    total_pilot_base = sum(metrics[p]['Pilot_base']['ads'] * metrics[p]['Pilot_n'] for p in pilots)
    total_pilot_cur = sum(metrics[p]['Pilot_cur']['ads'] * metrics[p]['Pilot_n'] for p in pilots)
    total_ctrl_base = sum(metrics[p]['Control_base']['ads'] * metrics[p]['Control_n'] for p in pilots)
    total_ctrl_cur = sum(metrics[p]['Control_cur']['ads'] * metrics[p]['Control_n'] for p in pilots)
    p_ads_pct = pct_change(total_pilot_cur, total_pilot_base)
    c_ads_pct = pct_change(total_ctrl_cur, total_ctrl_base)

    c1.metric("Pilots active", f"{len(pilots)}")
    c2.metric("Pilot stores", f"{sum(metrics[p]['Pilot_n'] for p in pilots)}")
    c3.metric("Control stores", f"{sum(metrics[p]['Control_n'] for p in pilots)}")
    c4.metric("Pilot ADS %Δ", f"{p_ads_pct:+.1f}%", f"vs control: {p_ads_pct-c_ads_pct:+.1f}pp")
    c5.metric("Best pilot", max(pilots, key=lambda p: pct_change(metrics[p]['Pilot_cur']['adt'], metrics[p]['Pilot_base']['adt']) - pct_change(metrics[p]['Control_cur']['adt'], metrics[p]['Control_base']['adt'])))

    # Bar chart — incremental ADT lift by pilot
    st.markdown("### Incremental ADT lift by pilot")
    fig = go.Figure()
    adt_incrs = []
    for p in pilots:
        inc = pct_change(metrics[p]['Pilot_cur']['adt'], metrics[p]['Pilot_base']['adt']) - \
              pct_change(metrics[p]['Control_cur']['adt'], metrics[p]['Control_base']['adt'])
        adt_incrs.append(inc)
    colors = ['#0F6E56' if v > 0 else '#A32D2D' for v in adt_incrs]
    fig.add_trace(go.Bar(x=pilots, y=adt_incrs, marker_color=colors,
                          text=[f"{v:+.1f}pp" for v in adt_incrs], textposition='outside'))
    fig.update_layout(height=320, showlegend=False, margin=dict(l=20,r=20,t=30,b=20),
                      yaxis_title="Incremental ADT lift (pp)", xaxis_title="",
                      plot_bgcolor='white', paper_bgcolor='white')
    fig.update_yaxes(gridcolor='#eee', zerolinecolor='#888')
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 1B — PILOT SUMMARY (per-pilot comparison, matches template 1B)
# ============================================================
with tab_1b:
    st.markdown("### Pilot Store vs Control Store — weekly comparison")

    pilot_tabs = st.tabs([f"**{p}**" for p in pilots])

    PILOT_1B_ROWS = [
        ('Overall Business Metrics', 'ADT (Avg Daily Transactions)', 'adt', '{:,.0f}'),
        ('Overall Business Metrics', 'ADS (Avg Daily Sales, ₹)', 'ads', '₹{:,.0f}'),
        ('Overall Business Metrics', 'USD (Units Sold Daily)', 'usd', '{:,.0f}'),
        ('Overall Business Metrics', 'AT (Average Ticket, ₹)', 'at', '₹{:,.0f}'),
        ('Overall Business Metrics', 'IPT', 'ipt', '{:.2f}'),
        ('Overall Business Metrics', '  — Beverages', 'ipt_bev', '{:.2f}'),
        ('Overall Business Metrics', '  — Food', 'ipt_food', '{:.2f}'),
        ('Overall Business Metrics', 'Revenue per week (Cr)', 'revenue_week', '₹{:.2f}'),
        ('Channel Mix', 'ADT: Offline — Non-SR', 'adt_nonsr', '{:,.0f}'),
        ('Channel Mix', 'ADT: Offline — SR', 'adt_sr', '{:,.0f}'),
        ('Channel Mix', 'ADT: Delivery', 'adt_delivery', '{:,.0f}'),
        ('Menu Mix', 'USD: EPP (%)', 'usd_epp', '{:.1f}%'),
        ('Menu Mix', 'USD: Tasty Recruiter (%)', 'usd_recruiter', '{:.1f}%'),
        ('Menu Mix', 'USD: Everyday Core (%)', 'usd_core', '{:.1f}%'),
        ('Menu Mix', 'USD: Expert Brew (%)', 'usd_expert', '{:.1f}%'),
    ]

    for tab_idx, pilot in enumerate(pilots):
        with pilot_tabs[tab_idx]:
            pd_data = metrics[pilot]
            st.markdown(f"#### {pilot} — _{pd_data['strategy']}_")
            st.caption(f"Pilot: {pd_data['Pilot_n']} stores  ·  Control: {pd_data['Control_n']} stores")

            # Build comparison rows
            rows = []
            prev_dim = None
            for dim, label, key, fmt in PILOT_1B_ROWS:
                pb = pd_data['Pilot_base'][key]
                pc = pd_data['Pilot_cur'][key]
                cb = pd_data['Control_base'][key]
                cc = pd_data['Control_cur'][key]
                p_pct = pct_change(pc, pb)
                c_pct = pct_change(cc, cb)
                incr = p_pct - c_pct
                rows.append({
                    'Dimension': dim if dim != prev_dim else '',
                    'Metric': label,
                    "Pilot FY'26 Jan YTD": fmt.format(pb),
                    'Pilot current': fmt.format(pc),
                    'Pilot %Δ': f"{p_pct:+.1f}%",
                    "Control FY'26 Jan YTD": fmt.format(cb),
                    'Control current': fmt.format(cc),
                    'Control %Δ': f"{c_pct:+.1f}%",
                    'Incremental': f"{incr:+.1f}pp",
                })
                prev_dim = dim

            df_display = pd.DataFrame(rows)

            def color_pct(val):
                try:
                    n = float(str(val).replace('%','').replace('+',''))
                    return 'color: #0F6E56; font-weight: 600;' if n > 0.5 else ('color: #A32D2D; font-weight: 600;' if n < -0.5 else 'color: #888;')
                except: return ''

            def color_incr(val):
                try:
                    n = float(str(val).replace('pp','').replace('+',''))
                    if n > 1: return 'background-color: #EAF3DE; color: #27500A; font-weight: 700;'
                    if n < -1: return 'background-color: #FCEBEB; color: #791F1F; font-weight: 700;'
                    return 'color: #666;'
                except: return ''

            styled = df_display.style.map(color_pct, subset=['Pilot %Δ','Control %Δ']).map(color_incr, subset=['Incremental'])
            st.dataframe(styled, use_container_width=True, hide_index=True, height=580)

            # Visualization: side-by-side channel mix
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Channel mix — pilot stores (current)**")
                ch_data = pd.DataFrame({
                    'Channel': ['Offline Non-SR','Offline SR','Delivery'],
                    'ADT': [pd_data['Pilot_cur']['adt_nonsr'], pd_data['Pilot_cur']['adt_sr'], pd_data['Pilot_cur']['adt_delivery']],
                })
                fig = px.bar(ch_data, x='Channel', y='ADT', color='Channel',
                             color_discrete_sequence=['#00704A','#1D9E75','#9FE1CB'])
                fig.update_layout(height=280, showlegend=False, margin=dict(l=10,r=10,t=20,b=10),
                                  plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("**Menu mix — units sold %**")
                mm_data = pd.DataFrame({
                    'Category': ['EPP','Recruiter','Core','Expert Brew','Food'],
                    'Pilot (current)': [pd_data['Pilot_cur'][f'usd_{k}'] for k in ['epp','recruiter','core','expert','food']],
                    'Control (current)': [pd_data['Control_cur'][f'usd_{k}'] for k in ['epp','recruiter','core','expert','food']],
                })
                mm_long = mm_data.melt(id_vars='Category', var_name='Store type', value_name='USD %')
                fig = px.bar(mm_long, x='Category', y='USD %', color='Store type', barmode='group',
                             color_discrete_sequence=['#00704A','#B4B2A9'])
                fig.update_layout(height=280, margin=dict(l=10,r=10,t=20,b=10),
                                  plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 1C — DEEP DIVE (channel-level, filterable)
# ============================================================
with tab_1c:
    st.markdown("### Deep dive — transaction mix by category & channel")
    st.caption("Filter panel (left) applies. Each pilot shown separately. Values are current period averages for pilot stores.")

    dd_pilots = st.multiselect("Select pilots", pilots, default=pilots[:2])
    if not dd_pilots:
        st.info("Select at least one pilot.")
    else:
        for p in dd_pilots:
            st.markdown(f"#### {p} — _{metrics[p]['strategy']}_")
            pb = metrics[p]['Pilot_base']
            pc = metrics[p]['Pilot_cur']
            cb = metrics[p]['Control_base']
            cc = metrics[p]['Control_cur']

            # ADT % split table (from template 1C)
            categories = ['EPP','Recruiter','Core','Expert Brew ++','Food']
            cat_keys = ['epp','recruiter','core','expert','food']

            # Build the USD% and ADT% table
            rows_dd = []
            for metric_label, suffix in [('% split of USD', 'usd_'), ('ADT by category', 'adt_')]:
                for i, cat in enumerate(categories):
                    k = cat_keys[i]
                    pb_v, pc_v = pb[suffix+k], pc[suffix+k]
                    cb_v, cc_v = cb[suffix+k], cc[suffix+k]
                    p_pct = pct_change(pc_v, pb_v)
                    c_pct = pct_change(cc_v, cb_v)
                    fmt = '{:.1f}%' if suffix == 'usd_' else '{:,.1f}'
                    rows_dd.append({
                        'Metric': metric_label if i == 0 else '',
                        'Category': cat,
                        "Pilot FY'26 Jan": fmt.format(pb_v),
                        'Pilot current': fmt.format(pc_v),
                        'Pilot %Δ': f"{p_pct:+.1f}%",
                        "Control FY'26 Jan": fmt.format(cb_v),
                        'Control current': fmt.format(cc_v),
                        'Control %Δ': f"{c_pct:+.1f}%",
                        'Incremental': f"{p_pct-c_pct:+.1f}pp",
                    })

            dd_df = pd.DataFrame(rows_dd)
            st.dataframe(dd_df, use_container_width=True, hide_index=True, height=450)

# ============================================================
# TAB 2A — MONTHLY SUMMARY
# ============================================================
with tab_2a:
    st.markdown("### Monthly summary — incremental by pilot and metric")
    st.caption("Same structure as 1A but computed on latest-month data. Use for monthly executive reviews.")

    # Recompute metrics on latest month
    latest_month_end = max_date
    latest_month_start = latest_month_end - timedelta(days=29)
    st.caption(f"Latest month window: {latest_month_start} → {latest_month_end}")

    monthly_rows = []
    for dim, label, key, _ in METRIC_ROWS:
        row = {'Dimension': dim, 'Metric': label}
        for p in pilots:
            n_p = fdf[(fdf['pilot']==p) & (fdf['store_type']=='Pilot')]['store_id'].nunique()
            n_c = fdf[(fdf['pilot']==p) & (fdf['store_type']=='Control')]['store_id'].nunique()
            p_base = compute_metrics(
                fdf[(fdf['pilot']==p) & (fdf['store_type']=='Pilot') &
                    (fdf['date']>=base_start) & (fdf['date']<=base_end)], n_p)
            p_cur = compute_metrics(
                fdf[(fdf['pilot']==p) & (fdf['store_type']=='Pilot') &
                    (fdf['date']>=latest_month_start) & (fdf['date']<=latest_month_end)], n_p)
            c_base = compute_metrics(
                fdf[(fdf['pilot']==p) & (fdf['store_type']=='Control') &
                    (fdf['date']>=base_start) & (fdf['date']<=base_end)], n_c)
            c_cur = compute_metrics(
                fdf[(fdf['pilot']==p) & (fdf['store_type']=='Control') &
                    (fdf['date']>=latest_month_start) & (fdf['date']<=latest_month_end)], n_c)
            incr = pct_change(p_cur[key], p_base[key]) - pct_change(c_cur[key], c_base[key])
            row[p] = incr
        monthly_rows.append(row)

    m_df = pd.DataFrame(monthly_rows)
    m_display = m_df.copy()
    for p in pilots:
        m_display[p] = m_display[p].apply(lambda x: f"{x:+.1f}pp")

    def color_cell_m(val):
        try:
            n = float(str(val).replace('pp','').replace('+',''))
            if n > 3: return 'background-color: #0F6E56; color: white; font-weight: 600;'
            if n > 1: return 'background-color: #9FE1CB; color: #04342C; font-weight: 600;'
            if n > -1: return 'color: #888;'
            if n > -3: return 'background-color: #F7C1C1; color: #501313; font-weight: 600;'
            return 'background-color: #A32D2D; color: white; font-weight: 600;'
        except: return ''

    st.dataframe(m_display.style.map(color_cell_m, subset=pilots),
                 use_container_width=True, hide_index=True, height=500)

    # Weekly trend line showing pilot go-live
    st.markdown("### Weekly ADS trend — pilot stores only")
    pilot_only = fdf[fdf['store_type']=='Pilot']
    weekly = (pilot_only.groupby(['week_start','pilot'])
              .agg(revenue=('line_total','sum'),
                   stores=('store_id','nunique'))
              .reset_index())
    weekly['ads'] = weekly['revenue'] / 7 / weekly['stores']
    fig = px.line(weekly, x='week_start', y='ads', color='pilot',
                  labels={'week_start':'Week','ads':'ADS (₹)'},
                  color_discrete_sequence=['#00704A','#1D9E75','#BA7517','#7F77DD','#D85A30'])
    fig.add_vline(x=date(2026,3,1), line_dash='dash', line_color='gray',
                  annotation_text='Pilot launch', annotation_position='top right')
    fig.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white',
                      hovermode='x unified', margin=dict(l=20,r=20,t=30,b=20))
    fig.update_yaxes(gridcolor='#eee', tickformat=',.0f')
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 2B — MONTHLY PILOT SUMMARY
# ============================================================
with tab_2b:
    st.markdown("### Monthly deep dive per pilot")
    st.caption("Detailed per-pilot view for the latest month, including loyalty metrics.")

    sel_pilot_2b = st.selectbox("Select pilot", pilots, key='p2b')
    pd_data = metrics[sel_pilot_2b]

    # Monthly metrics
    n_p = pd_data['Pilot_n']; n_c = pd_data['Control_n']
    pm_base = compute_metrics(
        fdf[(fdf['pilot']==sel_pilot_2b) & (fdf['store_type']=='Pilot') &
            (fdf['date']>=base_start) & (fdf['date']<=base_end)], n_p)
    pm_cur = compute_metrics(
        fdf[(fdf['pilot']==sel_pilot_2b) & (fdf['store_type']=='Pilot') &
            (fdf['date']>=latest_month_start) & (fdf['date']<=latest_month_end)], n_p)
    cm_base = compute_metrics(
        fdf[(fdf['pilot']==sel_pilot_2b) & (fdf['store_type']=='Control') &
            (fdf['date']>=base_start) & (fdf['date']<=base_end)], n_c)
    cm_cur = compute_metrics(
        fdf[(fdf['pilot']==sel_pilot_2b) & (fdf['store_type']=='Control') &
            (fdf['date']>=latest_month_start) & (fdf['date']<=latest_month_end)], n_c)

    ROWS_2B = [
        ('Overall Business Metrics', 'ADT', 'adt', '{:,.0f}'),
        ('Overall Business Metrics', 'ADS (₹)', 'ads', '₹{:,.0f}'),
        ('Overall Business Metrics', 'USD', 'usd', '{:,.0f}'),
        ('Overall Business Metrics', 'IPT', 'ipt', '{:.2f}'),
        ('Overall Business Metrics', '  — Beverages', 'ipt_bev', '{:.2f}'),
        ('Overall Business Metrics', '  — Food', 'ipt_food', '{:.2f}'),
        ('Overall Business Metrics', 'Revenue/month (Cr)', 'revenue_month', '₹{:.2f}'),
        ('Overall Business Metrics', 'GM %', 'gm_pct', '{:.1%}'),
        ('Channel Mix', 'ADT: Offline — Non-SR', 'adt_nonsr', '{:,.0f}'),
        ('Channel Mix', 'ADT: Offline — SR', 'adt_sr', '{:,.0f}'),
        ('Channel Mix', 'ADT: Delivery', 'adt_delivery', '{:,.0f}'),
        ('Menu Mix', 'USD: EPP (%)', 'usd_epp', '{:.1f}%'),
        ('Menu Mix', 'USD: Tasty Recruiter (%)', 'usd_recruiter', '{:.1f}%'),
        ('Menu Mix', 'USD: Everyday Core (%)', 'usd_core', '{:.1f}%'),
        ('Loyalty', 'ADT - New (per day)', 'adt_new', '{:.2f}'),
        ('Loyalty', 'ADT - Existing (per day)', 'adt_existing', '{:,.1f}'),
        ('Loyalty', 'Purchase frequency', 'freq', '{:.2f}'),
    ]

    rows2b = []
    prev_dim = None
    for dim, label, key, fmt in ROWS_2B:
        pb = pm_base[key]; pc = pm_cur[key]
        cb = cm_base[key]; cc = cm_cur[key]
        p_pct = pct_change(pc, pb); c_pct = pct_change(cc, cb)
        rows2b.append({
            'Dimension': dim if dim != prev_dim else '',
            'Metric': label,
            "Pilot FY'26 Jan": fmt.format(pb),
            'Pilot (month)': fmt.format(pc),
            'Pilot %Δ': f"{p_pct:+.1f}%",
            "Control FY'26 Jan": fmt.format(cb),
            'Control (month)': fmt.format(cc),
            'Control %Δ': f"{c_pct:+.1f}%",
            'Incremental': f"{p_pct-c_pct:+.1f}pp",
        })
        prev_dim = dim

    st.dataframe(pd.DataFrame(rows2b), use_container_width=True, hide_index=True, height=650)

# ============================================================
# TAB 3A — PRICING OBJECTIVE (ADT split, USD split, APR)
# ============================================================
with tab_3a:
    st.markdown("### Pricing objective — category-level deep dive")
    st.caption("Tracks ADT split by category, USD split, Hot vs Cold mix, and APR (average price realization) per category.")

    sel_pilot_3a = st.selectbox("Select pilot", pilots, key='p3a')
    pd_data = metrics[sel_pilot_3a]
    pb, pc = pd_data['Pilot_base'], pd_data['Pilot_cur']
    cb, cc = pd_data['Control_base'], pd_data['Control_cur']

    # Build three sub-tables matching template 3A
    ROWS_3A = [
        # (section, label, key, fmt)
        ('% split of ADT (category mix)', '% EPP', 'usd_epp', '{:.1f}%'),  # reusing USD% as proxy
        ('% split of ADT (category mix)', '% Recruiter', 'usd_recruiter', '{:.1f}%'),
        ('% split of ADT (category mix)', '% Core', 'usd_core', '{:.1f}%'),
        ('% split of ADT (category mix)', '% Expert Brew ++', 'usd_expert', '{:.1f}%'),
        ('% split of ADT (category mix)', '% Food', 'usd_food', '{:.1f}%'),
        ('ADT (absolute, by category)', 'EPP', 'adt_epp', '{:,.1f}'),
        ('ADT (absolute, by category)', 'Recruiter', 'adt_recruiter', '{:,.1f}'),
        ('ADT (absolute, by category)', 'Core', 'adt_core', '{:,.1f}'),
        ('ADT (absolute, by category)', 'Expert Brew ++', 'adt_expert', '{:,.1f}'),
        ('ADT (absolute, by category)', 'Food', 'adt_food', '{:,.1f}'),
        ('APR (Avg Price Realization, ₹)', 'EPP', 'apr_epp', '₹{:,.0f}'),
        ('APR (Avg Price Realization, ₹)', 'Recruiter', 'apr_recruiter', '₹{:,.0f}'),
        ('APR (Avg Price Realization, ₹)', 'Core', 'apr_core', '₹{:,.0f}'),
        ('APR (Avg Price Realization, ₹)', 'Expert Brew ++', 'apr_expert', '₹{:,.0f}'),
        ('APR (Avg Price Realization, ₹)', 'Food', 'apr_food', '₹{:,.0f}'),
        ('APR (Avg Price Realization, ₹)', 'Total', 'apr_total', '₹{:,.0f}'),
    ]

    rows3a = []
    prev_s = None
    for section, label, key, fmt in ROWS_3A:
        pb_v, pc_v = pb[key], pc[key]
        cb_v, cc_v = cb[key], cc[key]
        p_pct = pct_change(pc_v, pb_v); c_pct = pct_change(cc_v, cb_v)
        rows3a.append({
            'Section': section if section != prev_s else '',
            'Metric': label,
            "Pilot FY'26 Jan": fmt.format(pb_v),
            'Pilot current': fmt.format(pc_v),
            'Pilot %Δ': f"{p_pct:+.1f}%",
            "Control FY'26 Jan": fmt.format(cb_v),
            'Control current': fmt.format(cc_v),
            'Control %Δ': f"{c_pct:+.1f}%",
            'Incremental': f"{p_pct-c_pct:+.1f}pp",
        })
        prev_s = section

    st.dataframe(pd.DataFrame(rows3a), use_container_width=True, hide_index=True, height=620)

    # APR visualization
    st.markdown("### APR — pilot vs control (current period)")
    apr_data = pd.DataFrame({
        'Category': ['EPP','Recruiter','Core','Expert Brew','Food'],
        'Pilot current': [pc[k] for k in ['apr_epp','apr_recruiter','apr_core','apr_expert','apr_food']],
        'Control current': [cc[k] for k in ['apr_epp','apr_recruiter','apr_core','apr_expert','apr_food']],
    })
    apr_long = apr_data.melt(id_vars='Category', var_name='Store type', value_name='APR (₹)')
    fig = px.bar(apr_long, x='Category', y='APR (₹)', color='Store type', barmode='group',
                 color_discrete_sequence=['#00704A','#B4B2A9'])
    fig.update_layout(height=350, plot_bgcolor='white', paper_bgcolor='white',
                      margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 3B — LOYALTY OBJECTIVE
# ============================================================
with tab_3b:
    st.markdown("### Loyalty objective")
    st.caption("New vs existing customer trends, purchase frequency, retention proxies.")

    sel_pilot_3b = st.selectbox("Select pilot", pilots, key='p3b')
    pd_data = metrics[sel_pilot_3b]

    col_l1, col_l2, col_l3 = st.columns(3)
    pc_ = pd_data['Pilot_cur']; pb_ = pd_data['Pilot_base']
    cc_ = pd_data['Control_cur']; cb_ = pd_data['Control_base']

    col_l1.metric("New registrations (pilot, current)", f"{pc_['new_reg']:,}",
                   f"{pct_change(pc_['new_reg'], pb_['new_reg']):+.1f}% vs baseline")
    col_l2.metric("Purchase frequency (pilot)", f"{pc_['freq']:.2f}",
                   f"{pc_['freq']-pb_['freq']:+.2f} vs baseline")
    col_l3.metric("Incremental freq vs control", f"{pc_['freq']-cc_['freq']:+.2f}",
                   f"Baseline gap was {pb_['freq']-cb_['freq']:+.2f}")

    # Table of loyalty metrics
    LOYALTY_ROWS = [
        ('New registrations (count)', 'new_reg', '{:,}'),
        ('ADT - New (per day)', 'adt_new', '{:.2f}'),
        ('ADT - Existing (per day)', 'adt_existing', '{:,.1f}'),
        ('Purchase frequency (existing)', 'freq', '{:.2f}'),
    ]
    rowsl = []
    for label, key, fmt in LOYALTY_ROWS:
        pb_v, pc_v = pb_[key], pc_[key]
        cb_v, cc_v = cb_[key], cc_[key]
        p_pct = pct_change(pc_v, pb_v); c_pct = pct_change(cc_v, cb_v)
        rowsl.append({
            'Metric': label,
            "Pilot FY'26 Jan": fmt.format(pb_v),
            'Pilot current': fmt.format(pc_v),
            'Pilot %Δ': f"{p_pct:+.1f}%",
            "Control FY'26 Jan": fmt.format(cb_v),
            'Control current': fmt.format(cc_v),
            'Control %Δ': f"{c_pct:+.1f}%",
            'Incremental': f"{p_pct-c_pct:+.1f}pp",
        })

    st.dataframe(pd.DataFrame(rowsl), use_container_width=True, hide_index=True, height=220)

    # Weekly new registrations trend
    st.markdown("### Weekly new registrations — pilot vs control")
    wk_loyalty = (fdf[fdf['pilot']==sel_pilot_3b]
                  .groupby(['week_start','store_type'])
                  .agg(new_reg=('is_new_registration','sum'),
                       stores=('store_id','nunique'))
                  .reset_index())
    wk_loyalty['new_reg_per_store'] = wk_loyalty['new_reg'] / wk_loyalty['stores']
    fig = px.line(wk_loyalty, x='week_start', y='new_reg_per_store', color='store_type',
                  color_discrete_sequence=['#00704A','#B4B2A9'],
                  labels={'week_start':'Week','new_reg_per_store':'New regs / store'})
    fig.add_vline(x=date(2026,3,1), line_dash='dash', line_color='gray',
                  annotation_text='Pilot launch')
    fig.update_layout(height=350, plot_bgcolor='white', paper_bgcolor='white',
                      margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# DATA HEALTH (always visible at bottom)
# ============================================================
st.markdown("---")
with st.expander("🔧 Data health & refresh status"):
    files = sorted(glob.glob(str(DATA_DIR / "*.csv")))
    c1, c2 = st.columns(2)
    c1.markdown(f"**Files loaded:** {len(files)}")
    for f in files[-5:]:
        c1.code(Path(f).name)
    daily = df.groupby('date').size().reset_index(name='rows')
    c2.markdown("**Rows per day (last 30 days):**")
    c2.bar_chart(daily.tail(30).set_index('date'), height=200)
