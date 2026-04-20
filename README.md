# Project Ignite — Starbucks India Pilot Dashboard

An interactive dashboard that measures 5 pilot pricing strategies across ~53 Starbucks India outlets, mirroring the structure of the `Project_Ignite_KPI.xlsx` template.

## What's in this folder

```
sbux_dashboard/
├── dashboard.py                   # Main Streamlit app (matches Project Ignite tabs)
├── requirements.txt               # Python packages
├── data/
│   └── sbux_pilot_sample.csv      # Dummy data (replace with real CSV tomorrow)
└── README.md                      # This file
```

## Dashboard tabs

The dashboard has 7 tabs that mirror the Excel template, with added charts:

| Tab | What it shows |
|---|---|
| **1A. Overall summary** | Heatmap of incremental lift for every pilot × metric combination. Color-coded green (pilot winning) to red (pilot losing). Plus headline KPIs and a bar chart of ADT lift by pilot. |
| **1B. Pilot summary** | One tab per pilot. Full Pilot vs Control comparison (Baseline, Current, %Δ, Incremental) across Overall/Channel/Menu Mix dimensions. Side-by-side charts for channel and menu mix. |
| **1C. Deep dive** | Category-level breakdown of ADT and USD splits — filterable by pilot. |
| **2A. Monthly summary** | Same structure as 1A but on latest-month window. Includes weekly ADS trend chart with pilot launch marker. |
| **2B. Monthly pilot summary** | Monthly deep dive per pilot — adds loyalty metrics (new/existing, frequency) and GM %. |
| **3A. Pricing objective** | Per-pilot pricing deep dive: ADT% split by category, absolute ADT by category, APR (Average Price Realization). Bar chart comparing pilot vs control APR. |
| **3B. Loyalty objective** | New registrations, purchase frequency, loyalty trend chart. |

All tabs respect the sidebar filters: Market (Metro A/B, Metro C, T1, T2), Micro-market, Channel, Product (Beverage/Food), and time period.

## Setup (10 minutes, one-time)

### 1. Python (you've already installed it)

Verify from Command Prompt (Windows) or Terminal (Mac):

```
python --version
```

If you see `Python 3.11` or newer, you're good. If `python` doesn't work, try `py` on Windows.

### 2. Install packages

Navigate to this folder:

```
cd path\to\sbux_dashboard
```

Then:

```
pip install -r requirements.txt
```

If that fails with a package version error (e.g. on Python 3.14), try:

```
pip install streamlit pandas numpy plotly --break-system-packages
```

### 3. Run the dashboard

```
streamlit run dashboard.py
```

Browser opens to `http://localhost:8501`. The sample data loads automatically.

## Daily refresh workflow

1. Get the day's transaction CSV
2. Drop it into the `data/` folder (any filename — `sbux_2026_04_20.csv`, `pilot_data_latest.csv`, whatever)
3. Press `R` in the browser (or hamburger menu → Rerun)
4. New data appears

The app reads every CSV in `data/`, stacks them, and deduplicates by transaction ID. So you can keep all historical files if you want, or replace the one file daily.

## Required CSV columns

| Column | Type | Example |
|---|---|---|
| transaction_id | string | TXN20260420SBUX10030001 |
| transaction_datetime | datetime | 2026-04-20 09:15:00 |
| store_id | string | SBUX1003 |
| store_name | string | Mumbai North #1 |
| micro_market | string | Mumbai North |
| market_tier | string | Metro A/B, Metro C, T1, T2 |
| pilot | string | Pilot 1 through Pilot 5 |
| pilot_strategy | string | Only EPP, Aggressive Core Recruiter, etc. |
| store_type | string | Pilot or Control |
| item_name | string | Cafe Latte |
| category | string | EPP, Tasty Recruiter, Everyday Core, Expert Brew, Food |
| quantity | int | 1 |
| unit_price | float | 295.00 |
| line_total | float | 295.00 |
| channel | string | Offline - Non-SR, Offline - SR, Delivery |
| payment_method | string | Card, UPI, Cash, Wallet, Starbucks Rewards |
| loyalty_member | bool | True/False |
| is_new_registration | bool | True/False |

If the real CSV uses different column names, the dashboard will error on load — just tell Claude and it'll add a mapping step.

## Sharing with your partner

### Option A — same Wi-Fi (fastest, live demo)

```
streamlit run dashboard.py --server.address 0.0.0.0
```

Find your IP (`ipconfig` on Windows, `ifconfig` on Mac) — something like `192.168.1.47`. Share `http://192.168.1.47:8501` with your partner. They open it in their browser. No install on their side.

Caveat: your laptop has to stay on with the dashboard running.

### Option B — send the zip

Send `sbux_dashboard.zip` to your partner (email, WhatsApp, Google Drive). They follow the same setup steps on their machine. Each of you has an independent copy.

### Option C — Streamlit Community Cloud (best for permanent use, free)

1. Create a private GitHub repo
2. Upload this folder to it
3. Go to share.streamlit.io → connect repo → deploy
4. Get a permanent URL like `project-ignite.streamlit.app`
5. Share that URL with your partner (and anyone else who needs access)

Updates: push new CSVs to the GitHub repo, the dashboard auto-refreshes.

## Troubleshooting

**"No data found"** → CSV isn't in `data/`. Drop one there.

**Column error** → real CSV has different column names. Send Claude a sample row.

**Slow on large files** → ask Claude to swap pandas for DuckDB (a 20-min change).

**Numbers look wrong** → check the baseline/current date pickers in the sidebar.
