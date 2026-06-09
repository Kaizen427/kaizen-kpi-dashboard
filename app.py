import streamlit as st
import requests
from collections import defaultdict

st.set_page_config(page_title="Kaizen KPI Dashboard", layout="wide", page_icon="📊")

st.markdown("""
<style>
  .main { background-color: #F8FAFC; }
  .metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    border-left: 4px solid #6366F1;
    margin-bottom: 12px;
  }
  .metric-label { font-size: 13px; color: #64748B; font-weight: 500; margin-bottom: 4px; }
  .metric-value { font-size: 26px; font-weight: 700; color: #1E293B; }
  .metric-sub   { font-size: 12px; color: #94A3B8; margin-top: 2px; }
  .section-title {
    font-size: 15px; font-weight: 700; color: #1E293B;
    text-transform: uppercase; letter-spacing: 0.05em;
    margin: 24px 0 12px 0;
  }
  .funnel-bar {
    background: #EEF2FF; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 8px;
    display: flex; justify-content: space-between; align-items: center;
  }
</style>
""", unsafe_allow_html=True)

def get_lark_token():
    app_id     = st.secrets["LARK_APP_ID"]
    app_secret = st.secrets["LARK_APP_SECRET"]
    resp = requests.post(
        "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10
    )
    data = resp.json()
    if "tenant_access_token" not in data:
        st.error(f"Auth error: {data}")
        st.stop()
    return data["tenant_access_token"]

@st.cache_data(ttl=300, show_spinner="Loading data from Lark...")
def load_data():
    token = get_lark_token()
    headers = {"Authorization": f"Bearer {token}"}
    range_str = "J1VBBO!A1:U300"
    url = f"https://open.larksuite.com/open-apis/sheets/v2/spreadsheets/HxMwsatsKhpmcxtO9Hqlhsh4gFb/values/{requests.utils.quote(range_str, safe='')}"
    resp = requests.get(url, headers=headers, params={"valueRenderOption": "FormattedValue"}, timeout=15)
    data = resp.json()
    if data.get("code", 0) != 0 or "data" not in data:
        st.error(f"Lark API error: {data.get('msg', data)}")
        st.stop()
    rows = data["data"]["valueRange"]["values"]

    records = []
    for row in rows[1:]:
        month_raw = row[4]
        month = "June" if month_raw in ("Jun", "June") else month_raw
        if len(row) < 6 or not month_raw or month not in ("March", "April", "May", "June"):
            continue
        def g(i):
            try: return float(str(row[i]).replace(",","")) if i < len(row) and row[i] not in (None,"") else 0
            except: return 0
        records.append({
            "bd":      row[0] or "",
            "region":  row[1] or "",
            "month":   month,
            "reg":     g(5),  "ftd": g(6),  "ftt": g(7),  "efttc": g(8),
            "dep":     g(9),  "net_dep": g(10),
            "contract_tv": g(13), "spot_tv": g(17), "net_fees": g(20),
        })
    return records

def fmt_num(v, prefix="", suffix=""):
    if v >= 1_000_000: return f"{prefix}{v/1_000_000:.2f}M{suffix}"
    if v >= 1_000:     return f"{prefix}{v/1_000:.1f}K{suffix}"
    return f"{prefix}{v:,.0f}{suffix}"

def metric_card(label, value, sub=""):
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      {'<div class="metric-sub">'+sub+'</div>' if sub else ''}
    </div>""", unsafe_allow_html=True)

# ── Load ────────────────────────────────────────────────────────────────────
records  = load_data()
all_bds  = sorted(set(r["bd"] for r in records if r["bd"]))
all_months = ["March + April + May + June (Total)", "March", "April", "May", "June"]

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Kaizen")
    st.title("KPI Filters")
    st.markdown("---")
    sel_bd    = st.selectbox("BD Agent", ["All BDs"] + all_bds)
    sel_month = st.selectbox("Period", all_months)
    st.markdown("---")
    st.caption("Data source: Kaizen KPI Sheet\nRefreshes every 5 min")
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

# ── Filter ───────────────────────────────────────────────────────────────────
filtered = records
if sel_bd != "All BDs":
    filtered = [r for r in filtered if r["bd"] == sel_bd]
if sel_month != "March + April + May + June (Total)":
    filtered = [r for r in filtered if r["month"] == sel_month]

def total(key): return sum(r[key] for r in filtered)

reg    = total("reg");    ftd   = total("ftd")
ftt    = total("ftt");    efttc = total("efttc")
ctr_tv = total("contract_tv"); spt_tv = total("spot_tv")
tot_tv = ctr_tv + spt_tv;     fees  = total("net_fees")

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("## 📊 Kaizen Team — KPI Dashboard")
label = f"{sel_bd}  ·  {sel_month}" if sel_bd != "All BDs" else f"All BDs  ·  {sel_month}"
st.markdown(f"**{label}**")
st.markdown("---")

# ── KPI Cards ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Cumulative Results</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1: metric_card("Registered Users",          f"{int(reg):,}")
with c2: metric_card("First Time Deposit (FTD)",  f"{int(ftd):,}")
with c3: metric_card("First Time Trade (FTT)",    f"{int(ftt):,}")
with c4: metric_card("EFTTC — Converted Traders", f"{int(efttc):,}")

c5, c6, c7, c8 = st.columns(4)
with c5: metric_card("Contract Trading Vol.",  fmt_num(ctr_tv, "$"))
with c6: metric_card("Spot Trading Vol.",      fmt_num(spt_tv, "$"))
with c7: metric_card("Total Trading Vol.",     fmt_num(tot_tv, "$"))
with c8: metric_card("Net Fees (USD)",         fmt_num(fees,   "$"))

# ── Funnel ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Conversion Funnel</div>', unsafe_allow_html=True)
f1, f2 = st.columns([1, 2])
with f1:
    reg2ftd   = ftd/reg*100   if reg else 0
    reg2ftt   = ftt/reg*100   if reg else 0
    reg2efttc = efttc/reg*100 if reg else 0
    for lbl, val in [("Reg → FTD", reg2ftd), ("Reg → FTT", reg2ftt), ("Reg → EFTTC", reg2efttc)]:
        st.markdown(f"""
        <div class="funnel-bar">
          <span style="color:#1E293B;font-weight:600">{lbl}</span>
          <span style="color:#6366F1;font-weight:700;font-size:18px">{val:.1f}%</span>
        </div>""", unsafe_allow_html=True)
with f2:
    if filtered:
        import pandas as pd
        bd_summary = defaultdict(lambda: defaultdict(float))
        for r in records:
            if sel_month != "March + April + May + June (Total)" and r["month"] != sel_month: continue
            bd_summary[r["bd"]]["reg"]    += r["reg"]
            bd_summary[r["bd"]]["efttc"]  += r["efttc"]
            bd_summary[r["bd"]]["tot_tv"] += r["contract_tv"] + r["spot_tv"]
            bd_summary[r["bd"]]["fees"]   += r["net_fees"]
        rows_df = []
        for bd, m in sorted(bd_summary.items(), key=lambda x: -x[1]["tot_tv"]):
            if bd and (sel_bd == "All BDs" or bd == sel_bd):
                rows_df.append({"BD Agent": bd,
                    "Reg": int(m["reg"]), "EFTTC": int(m["efttc"]),
                    "Total TV": fmt_num(m["tot_tv"], "$"),
                    "Net Fees": fmt_num(m["fees"], "$")})
        if rows_df:
            st.dataframe(pd.DataFrame(rows_df), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("📁 [Open KPI Dashboard in Lark](https://up3mczep5h.sg.larksuite.com/wiki/GCDzwr6OpiYqcNkMhonlr9oHgpe?sheet=XmOhq)  ·  Q2 2025 (Mar–Jun)  ·  Kaizen Team")
