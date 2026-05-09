"""
PetroDCA – Production Analytics
================================
A professional Streamlit web application for petroleum decline curve analysis.
Features:
  • Multi-well production data ingestion (Excel / CSV, any structure)
  • Automatic unit conversion  (Sm³/day → STB/day, Sm³/day → Mscf/day)
  • Arps decline curve fitting : Exponential, Harmonic, Hyperbolic
  • Estimated Ultimate Recovery (EUR) calculation with economic limit
  • Interactive Plotly visualisations with light / dark theme
  • Field-level insights, top-well comparisons, scatter analytics
  • Data export – Excel, CSV, PNG charts

External Libraries Used:
  streamlit   ≥ 1.28   – Web UI framework
  pandas      ≥ 2.0    – Data manipulation and tabular analysis
  numpy       ≥ 1.24   – Numerical computing
  scipy       ≥ 1.11   – Non-linear curve fitting & numerical integration
  plotly      ≥ 5.17   – Interactive charts
  openpyxl    ≥ 3.1    – Reading .xlsx workbooks
  xlsxwriter  ≥ 3.1    – Writing formatted Excel export files

Usage:
    streamlit run app.py
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st

def _html(s: str) -> None:
    if hasattr(st, "html"):
        try:
            st.html(s)
        except Exception:
            st.markdown(s, unsafe_allow_html=True)
    else:
        st.markdown(s, unsafe_allow_html=True)

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import io
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# 2. PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PetroDCA – Production Analytics",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. UNIT CONVERSION CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
SM3_TO_BBL  = 6.28981
SM3_TO_MSCF = 0.035315
BBL_TO_BOE  = 1.0
MSCF_TO_BOE = 1 / 6.0

# ─────────────────────────────────────────────────────────────────────────────
# 4. THEME PALETTES  (Light & Dark)
# ─────────────────────────────────────────────────────────────────────────────

C_LIGHT = {
    "bg":           "#f4f7fb",
    "sidebar":      "#e9eef7",
    "sidebar_text": "#10203c",
    "sidebar_muted":"#55647e",
    "card":         "#ffffff",
    "card2":        "#eef4fb",
    "border":       "#d5dee8",
    "text":         "#0f172a",
    "heading":      "#0b1225",
    "muted":        "#4b5668",
    "input_bg":     "#ffffff",
    "green":        "#16a34a",
    "red":          "#dc2626",
    "blue":         "#2563eb",
    "orange":       "#d97706",
    "purple":       "#7c3aed",
    "teal":         "#0891b2",
    "yellow":       "#ca8a04",
    "pink":         "#db2777",
    "kpi_value":    "#0b1225",
    "result_value": "#0b1225",
    "btn_bg":       "#2563eb",
    "btn_hover":    "#1d4ed8",
    "chart_bg":     "#ffffff",
    "chart_paper":  "#ffffff",
    "chart_grid":   "#d5dee8",
    "chart_tick":   "#475569",
    "chart_text":   "#0f172a",
    "tag_bg":       "#dbeafe",
    "tag_text":     "#1e40af",
}

C_DARK = {
    "bg":           "#0d1929",
    "sidebar":      "#060e1a",
    "sidebar_text": "#e8f0fe",
    "sidebar_muted":"#7a99be",
    "card":         "#162338",
    "card2":        "#0f1d30",
    "border":       "#1e3a56",
    "text":         "#e2eaf8",
    "heading":      "#ffffff",
    "muted":        "#7a99be",
    "input_bg":     "#0f1d30",
    "green":        "#10b981",
    "red":          "#f87171",
    "blue":         "#60a5fa",
    "orange":       "#fbbf24",
    "purple":       "#a78bfa",
    "teal":         "#22d3ee",
    "yellow":       "#facc15",
    "pink":         "#f472b6",
    "kpi_value":    "#ffffff",
    "result_value": "#e2eaf8",
    "btn_bg":       "#1d4ed8",
    "btn_hover":    "#2563eb",
    "chart_bg":     "#0f1d30",
    "chart_paper":  "#0f1d30",
    "chart_grid":   "#1e3a56",
    "chart_tick":   "#7a99be",
    "chart_text":   "#e2eaf8",
    "tag_bg":       "#1e3a56",
    "tag_text":     "#93c5fd",
}

def get_C() -> dict:
    """Return active colour palette based on current theme setting."""
    return C_DARK if st.session_state.get("theme", "Dark") == "Dark" else C_LIGHT

WELL_COLOURS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444",
                "#8b5cf6", "#14b8a6", "#ec4899", "#eab308"]

# ─────────────────────────────────────────────────────────────────────────────
# 5. DYNAMIC PLOTLY THEME
# ─────────────────────────────────────────────────────────────────────────────

def get_plotly_bg() -> dict:
    C = get_C()
    return dict(
        plot_bgcolor  = C["chart_bg"],
        paper_bgcolor = C["chart_paper"],
        font          = dict(color=C["chart_text"], family="Inter, sans-serif"),
        xaxis = dict(
            gridcolor=C["chart_grid"], linecolor=C["chart_grid"],
            tickfont=dict(color=C["chart_tick"]),
        ),
        yaxis = dict(
            gridcolor=C["chart_grid"], linecolor=C["chart_grid"],
            tickfont=dict(color=C["chart_tick"]),
        ),
        legend = dict(bgcolor=C["card"], bordercolor=C["border"],
                      font=dict(color=C["text"])),
        margin = dict(l=50, r=20, t=40, b=40),
    )

# ─────────────────────────────────────────────────────────────────────────────
# 6. CSS INJECTION  (called on every render to apply active theme)
# ─────────────────────────────────────────────────────────────────────────────

def inject_css():
    C = get_C()
    _html(f"""
<style>
/* ── Google Font ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global ──────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    color: {C['text']};
}}
.stApp {{
    background-color: {C['bg']};
}}

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background-color: {C['sidebar']} !important;
    border-right: 1px solid {C['border']};
}}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label {{
    color: {C['sidebar_muted']} !important;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span:not([data-testid]),
[data-testid="stSidebar"] .stCaption {{
    color: {C['sidebar_text']} !important;
}}

/* ── Sidebar nav buttons ─────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {{
    background-color: {C['card2']} !important;
    color: {C['sidebar_text']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 500;
    display: flex;
    justify-content: flex-start;
    align-items: center;
    text-align: left !important;
    gap: 10px;
    padding: 8px 16px;
    margin-bottom: 6px;
    transition: all 0.18s;
    width: 100%;
}}
[data-testid="stSidebar"] .stButton > button > div,
[data-testid="stSidebar"] .stButton > button > span {{
    justify-content: flex-start;
    text-align: left !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: {C['blue']} !important;
    border-color: {C['blue']} !important;
    color: #ffffff !important;
    transform: none;
}}

/* ── Theme toggle area ───────────────────────────────────── */
.theme-toggle-wrap {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
}}
.theme-label {{
    color: {C['sidebar_muted']};
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    flex: 1;
}}

/* ── Radio nav (legacy – keep for safety) ────────────────── */
[data-testid="stSidebar"] div[role="radiogroup"] label {{
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-size: 0.9rem !important;
    padding: 8px 12px;
    border-radius: 8px;
    margin-bottom: 2px;
    color: {C['sidebar_muted']} !important;
    cursor: pointer;
    display: block !important;
    width: 100% !important;
}}

/* ── Main content text ───────────────────────────────────── */
.stMarkdown, .stText, p, li, span, div {{
    color: {C['text']};
}}
h1, h2, h3, h4, h5, h6 {{
    color: {C['heading']} !important;
}}
.stMarkdown strong {{
    color: {C['heading']};
}}

/* ── Input fields ────────────────────────────────────────── */
.stSelectbox > div > div,
.stMultiSelect > div > div {{
    background-color: {C['input_bg']} !important;
    border: 1px solid {C['border']} !important;
    color: {C['text']} !important;
    border-radius: 8px;
}}
.stSelectbox label, .stMultiSelect label,
.stNumberInput label, .stSlider label,
.stToggle label, .stCheckbox label,
.stTextInput label, .stTextArea label,
.stDateInput label, .stRadio label {{
    color: {C['muted']} !important;
    font-size: 0.82rem;
}}
.stTextInput > div > input,
.stTextArea > div > textarea,
.stNumberInput > div > input {{
    background-color: {C['input_bg']} !important;
    border: 1px solid {C['border']} !important;
    color: {C['text']} !important;
    border-radius: 8px;
}}
.stDateInput input {{
    background-color: {C['input_bg']} !important;
    border: 1px solid {C['border']} !important;
    color: {C['text']} !important;
    border-radius: 6px;
}}
/* Dropdown menu items */
[data-baseweb="popover"] li,
[data-baseweb="menu"] li {{
    background-color: {C['card']} !important;
    color: {C['text']} !important;
}}
[data-baseweb="popover"],
[data-baseweb="menu"] {{
    background-color: {C['card']} !important;
    border: 1px solid {C['border']} !important;
}}
/* Multiselect tags */
[data-baseweb="tag"] {{
    background-color: {C['tag_bg']} !important;
    color: {C['tag_text']} !important;
}}

/* ── Main action buttons ─────────────────────────────────── */
.stButton > button {{
    background-color: {C['btn_bg']};
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 8px 16px;
    transition: all 0.2s;
}}
.stButton > button:hover {{
    background-color: {C['btn_hover']};
    transform: translateY(-1px);
}}

/* ── File uploader ───────────────────────────────────────── */
[data-testid="stFileUploader"] {{
    background-color: {C['card2']};
    border: 1px dashed {C['border']};
    border-radius: 10px;
    padding: 10px;
}}
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span {{
    color: {C['text']} !important;
}}

/* ── DataFrames / tables ─────────────────────────────────── */
.stDataFrame, [data-testid="stDataFrame"] {{
    background-color: {C['card']} !important;
}}
[data-testid="stDataFrame"] th {{
    background-color: {C['card2']} !important;
    color: {C['heading']} !important;
    border-bottom: 1px solid {C['border']} !important;
}}
[data-testid="stDataFrame"] td {{
    color: {C['text']} !important;
    border-bottom: 1px solid {C['border']} !important;
}}
.stTable table {{
    background-color: {C['card']} !important;
    color: {C['text']} !important;
}}
.stTable th {{
    background-color: {C['card2']} !important;
    color: {C['heading']} !important;
    border-bottom: 1px solid {C['border']} !important;
}}
.stTable td {{
    color: {C['text']} !important;
    border-bottom: 1px solid {C['border']} !important;
}}

/* ── Tabs ────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background-color: {C['card2']};
    border-radius: 8px;
    padding: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    background-color: transparent;
    color: {C['muted']};
    border-radius: 6px;
    font-size: 0.85rem;
}}
.stTabs [aria-selected="true"] {{
    background-color: {C['blue']} !important;
    color: #ffffff !important;
}}

/* ── Sliders ─────────────────────────────────────────────── */
.stSlider > div > div > div {{
    background-color: {C['blue']} !important;
}}
.stSlider p {{ color: {C['muted']} !important; }}

/* ── Toggle / Checkbox ───────────────────────────────────── */
.stCheckbox > label, .stToggle > label {{
    color: {C['muted']};
}}

/* ── Info / warning / success boxes ─────────────────────── */
.stAlert {{
    background-color: {C['card2']} !important;
    border: 1px solid {C['border']} !important;
    color: {C['text']} !important;
    border-radius: 10px;
}}
.stInfo  {{ border-left: 3px solid {C['blue']}   !important; }}
.stSuccess {{ border-left: 3px solid {C['green']} !important; }}
.stWarning {{ border-left: 3px solid {C['orange']} !important; }}
.stError {{ border-left: 3px solid {C['red']}    !important; }}

/* ── Metric widget ───────────────────────────────────────── */
[data-testid="stMetricValue"] {{
    color: {C['heading']} !important;
}}
[data-testid="stMetricLabel"] {{
    color: {C['muted']} !important;
}}

/* ── Expander ────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    background-color: {C['card2']} !important;
    border: 1px solid {C['border']} !important;
    border-radius: 10px;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {{
    color: {C['muted']} !important;
}}

/* ── Caption ─────────────────────────────────────────────── */
.stCaption, .stCaption p {{
    color: {C['muted']} !important;
}}

/* ── KPI card ────────────────────────────────────────────── */
.kpi-card {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 14px;
    padding: 18px 16px;
    display: flex; flex-direction: column;
    gap: 6px;
    min-height: 120px;
    height: auto;
}}
.kpi-icon {{
    font-size: 1.4rem;
    margin-bottom: 2px;
}}
.kpi-label {{
    font-size: 0.78rem;
    color: {C['muted']};
    font-weight: 500;
}}
.kpi-value-row {{
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
}}
.kpi-unit {{
    font-size: 0.68rem;
    color: {C['muted']};
    white-space: normal;
    flex-shrink: 1;
    min-width: 0;
    overflow-wrap: anywhere;
}}
.kpi-value {{
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.1;
    color: {C['kpi_value']};
    min-width: 0;
    overflow-wrap: anywhere;
}}
.kpi-delta {{
    font-size: 0.75rem;
    font-weight: 500;
}}
@media (max-width: 1200px) {{
    .kpi-value {{ font-size: 1.6rem; }}
    .kpi-unit  {{ font-size: 0.62rem; }}
}}
.kpi-delta.pos {{ color: {C['green']}; }}
.kpi-delta.neg {{ color: {C['red']};   }}

/* ── Section header ──────────────────────────────────────── */
.section-header {{
    font-size: 1.3rem;
    font-weight: 700;
    color: {C['heading']};
    margin: 0 0 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid {C['border']};
}}

/* ── Panel card ──────────────────────────────────────────── */
.panel-card {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 14px;
    padding: 20px;
}}

/* ── Insight alert ───────────────────────────────────────── */
.insight-item {{
    display: flex; align-items: flex-start; gap: 10px;
    background: {C['card2']};
    border: 1px solid {C['border']};
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
    font-size: 0.84rem;
}}
.insight-item span:last-child {{
    color: {C['text']} !important;
}}

/* ── Page title ──────────────────────────────────────────── */
.page-title {{
    font-size: 1.6rem;
    font-weight: 700;
    color: {C['heading']};
    margin-bottom: 20px;
}}

/* ── Top bar ─────────────────────────────────────────────── */
.top-bar {{
    background: {C['card']};
    border: 1px solid {C['border']};
    padding: 10px 24px;
    display: flex; align-items: center;
    justify-content: space-between;
    border-radius: 12px;
    margin-bottom: 20px;
}}
.top-bar-title  {{ font-weight: 700; font-size: 1.05rem; color: {C['heading']}; }}
.top-bar-sub    {{ color: {C['muted']}; font-size: 0.85rem; margin-left: 8px; }}
.top-bar-label  {{ color: {C['muted']}; font-size: 0.82rem; }}
.top-bar-value  {{ color: {C['heading']}; font-weight: 700; }}

/* ── Result row ──────────────────────────────────────────── */
.result-row {{
    display: flex; justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid {C['border']};
    font-size: 0.87rem;
}}
.result-label {{ color: {C['muted']}; }}
.result-value {{ color: {C['result_value']}; font-weight: 600; }}

/* ── Status bar ──────────────────────────────────────────── */
.status-bar {{
    background: {C['card2']};
    border: 1px solid {C['border']};
    border-radius: 8px;
    padding: 8px 10px;
    margin-top: 8px;
    font-size: 0.8rem;
    color: {C['muted']};
}}

/* ── Footer ──────────────────────────────────────────────── */
.app-footer {{
    margin-top: 40px;
    padding-top: 12px;
    border-top: 1px solid {C['border']};
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: {C['muted']};
}}
</style>
""")


# ─────────────────────────────────────────────────────────────────────────────
# 7. DATA LOADING & CLEANING
# ─────────────────────────────────────────────────────────────────────────────

def _format_well_name(raw: str) -> str:
    name  = raw.replace("_", " ")
    parts = name.split("-")
    if len(parts) >= 2:
        name = parts[0] + "/" + parts[1] + "-" + "-".join(parts[2:])
    return name.strip()

def load_excel_production(file) -> dict:
    xl    = pd.ExcelFile(file)
    wells = {}
    for sheet in xl.sheet_names:
        if "index" in sheet.lower() or "summary" in sheet.lower():
            continue
        raw = None
        for header_row in [0, 1, 2]:
            try:
                raw = xl.parse(sheet, header=header_row)
                if len(raw.columns) > 1:
                    break
            except Exception:
                continue
        if raw is None or len(raw.columns) < 2:
            continue
        raw.columns = raw.columns.astype(str).str.strip().str.lower()
        col_map = {}
        for col in raw.columns:
            if any(x in col for x in ["date", "time", "periode", "start date"]):
                col_map[col] = "Date"
            elif any(x in col for x in ["oil rate", "oil prod", "crude oil", "daily oil"]):
                col_map[col] = "Oil_Sm3"
            elif any(x in col for x in ["gas rate", "gas prod", "dry gas", "daily gas"]):
                col_map[col] = "Gas_Sm3"
            elif any(x in col for x in ["water rate", "water prod", "produced water", "daily water"]):
                col_map[col] = "Water_Sm3"
            elif any(x in col for x in ["on-stream", "onstream", "on stream", "hrs", "hours", "uptime", "operating"]):
                col_map[col] = "OnStreamHrs"
        raw = raw.rename(columns=col_map)
        available = [c for c in ["Date", "Oil_Sm3", "Gas_Sm3", "Water_Sm3", "OnStreamHrs"]
                     if c in raw.columns]
        if "Date" not in available or "Oil_Sm3" not in available:
            st.warning(f"⚠️ Sheet '{sheet}': Missing Date or Oil columns. Skipping.")
            continue
        df = raw[available].copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"].notna()].copy()
        if len(df) < 10:
            st.warning(f"⚠️ Sheet '{sheet}': Only {len(df)} valid date rows. Skipping.")
            continue
        for col in ["Oil_Sm3", "Gas_Sm3", "Water_Sm3", "OnStreamHrs"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        df = df[df["Oil_Sm3"] > 0].copy()
        if "OnStreamHrs" in df.columns:
            df = df[(df["OnStreamHrs"] > 0) & (df["OnStreamHrs"] <= 24)].copy()
        if len(df) < 10:
            st.warning(f"⚠️ Sheet '{sheet}': Insufficient valid production data ({len(df)} rows). Skipping.")
            continue
        df["Oil_bbl"]   = df["Oil_Sm3"]  * SM3_TO_BBL
        df["Gas_mscf"]  = df.get("Gas_Sm3",  pd.Series(0.0, index=df.index)) * SM3_TO_MSCF
        df["Water_bbl"] = df.get("Water_Sm3", pd.Series(0.0, index=df.index)) * SM3_TO_BBL
        df = df.sort_values("Date").reset_index(drop=True)
        well_name = _format_well_name(sheet)
        wells[well_name] = df
    return wells

def load_csv_production(file) -> dict:
    try:
        df = pd.read_csv(file)
    except Exception as e:
        st.error(f"CSV read error: {e}")
        return {}
    if df.empty:
        st.error("CSV file is empty.")
        return {}
    df.columns = df.columns.astype(str).str.strip().str.lower()
    col_map = {}
    for col in df.columns:
        if any(x in col for x in ["date", "time", "periode", "start date"]):
            col_map[col] = "Date"
        elif col in ("well", "wellname", "well_name", "wellid"):
            col_map[col] = "Well"
        elif any(x in col for x in ["oil rate", "oil prod", "crude oil", "daily oil", "oil"]):
            col_map[col] = "Oil_Sm3"
        elif any(x in col for x in ["gas rate", "gas prod", "dry gas", "daily gas", "gas"]):
            col_map[col] = "Gas_Sm3"
        elif any(x in col for x in ["water rate", "water prod", "produced water", "daily water", "water", "wtr"]):
            col_map[col] = "Water_Sm3"
        elif any(x in col for x in ["on-stream", "onstream", "on stream", "hrs", "hours", "uptime", "operating"]):
            col_map[col] = "OnStreamHrs"
    df = df.rename(columns=col_map)
    if "Date" not in df.columns or "Oil_Sm3" not in df.columns:
        st.error("CSV must contain 'date' and 'oil' columns.")
        return {}
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    initial_rows = len(df)
    df = df[df["Date"].notna()].copy()
    for col in ["Oil_Sm3", "Gas_Sm3", "Water_Sm3", "OnStreamHrs"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    max_oil = df["Oil_Sm3"].max()
    if max_oil > 2000:
        df["Oil_bbl"]   = df["Oil_Sm3"]  * SM3_TO_BBL
        df["Gas_mscf"]  = df.get("Gas_Sm3",  pd.Series(0.0, index=df.index)) * SM3_TO_MSCF
        df["Water_bbl"] = df.get("Water_Sm3", pd.Series(0.0, index=df.index)) * SM3_TO_BBL
    else:
        df["Oil_bbl"]   = df["Oil_Sm3"]
        df["Gas_mscf"]  = df.get("Gas_Sm3", pd.Series(0.0, index=df.index))
        df["Water_bbl"] = df.get("Water_Sm3", pd.Series(0.0, index=df.index))
    wells = {}
    if "Well" in df.columns:
        for well, grp in df.groupby("Well"):
            well_name = str(well).strip()
            well_df   = grp[grp["Oil_bbl"] > 0].sort_values("Date").reset_index(drop=True)
            if len(well_df) >= 10:
                wells[well_name] = well_df
    else:
        df_clean = df[df["Oil_bbl"] > 0].sort_values("Date").reset_index(drop=True)
        if len(df_clean) >= 10:
            wells["Well-01"] = df_clean
    if not wells:
        st.warning(f"No valid production data found. Processed {initial_rows} rows, but none met quality criteria.")
    return wells

# ─────────────────────────────────────────────────────────────────────────────
# 8. DCA ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def exp_decline(t, qi, Di):
    return qi * np.exp(-Di * t)

def harm_decline(t, qi, Di):
    return qi / (1.0 + Di * t)

def hyp_decline(t, qi, Di, b):
    return qi / (1.0 + b * Di * t) ** (1.0 / b)

def _r2_rmse(q_actual, q_pred):
    ss_res = float(np.sum((q_actual - q_pred) ** 2))
    ss_tot = float(np.sum((q_actual - q_actual.mean()) ** 2))
    r2   = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(ss_res / len(q_actual)))
    return round(r2, 4), round(rmse, 2)

def fit_arps_models(df, phase="Oil_bbl", resample="ME") -> dict:
    if phase not in df.columns or len(df) < 20:
        return {}
    monthly = (df.set_index("Date")[phase]
               .resample(resample).mean()
               .dropna()
               .reset_index())
    monthly.columns = ["Date", "q"]
    monthly = monthly[monthly["q"] > 10].copy()
    if len(monthly) < 8:
        return {}
    peak_i = monthly["q"].idxmax()
    fit_df = monthly.iloc[peak_i:].copy()
    t0     = fit_df["Date"].iloc[0]
    t      = (fit_df["Date"] - t0).dt.days.values.astype(float)
    q      = fit_df["q"].values.astype(float)
    qi0    = float(q[0])
    Di0    = 0.001
    results = {}
    n = len(q)
    try:
        popt, _ = curve_fit(exp_decline, t, q,
                            p0=[qi0, Di0],
                            bounds=([qi0*0.3, 1e-7], [qi0*3, 10/365]),
                            maxfev=20000)
        qi_e, Di_e = popt
        q_fit = exp_decline(t, *popt)
        r2, rmse = _r2_rmse(q, q_fit)
        k = 2
        aic = n * np.log(np.sum((q - q_fit) ** 2) / n) + 2 * k
        results["Exponential"] = dict(
            qi=qi_e, Di_day=Di_e, Di_year=Di_e*365, b=0.0,
            r2=r2, rmse=rmse, AIC=round(aic, 1),
            t=t, q_actual=q, q_fitted=q_fit,
            dates=fit_df["Date"].values, peak_date=t0,
        )
    except Exception:
        pass
    try:
        popt, _ = curve_fit(harm_decline, t, q,
                            p0=[qi0, Di0],
                            bounds=([qi0*0.3, 1e-7], [qi0*3, 10/365]),
                            maxfev=20000)
        qi_h, Di_h = popt
        q_fit = harm_decline(t, *popt)
        r2, rmse = _r2_rmse(q, q_fit)
        k = 2
        aic = n * np.log(np.sum((q - q_fit) ** 2) / n) + 2 * k
        results["Harmonic"] = dict(
            qi=qi_h, Di_day=Di_h, Di_year=Di_h*365, b=1.0,
            r2=r2, rmse=rmse, AIC=round(aic, 1),
            t=t, q_actual=q, q_fitted=q_fit,
            dates=fit_df["Date"].values, peak_date=t0,
        )
    except Exception:
        pass
    try:
        popt, _ = curve_fit(hyp_decline, t, q,
                            p0=[qi0, Di0, 0.8],
                            bounds=([qi0*0.3, 1e-7, 0.01], [qi0*3, 10/365, 1.99]),
                            maxfev=50000)
        qi_y, Di_y, b_y = popt
        q_fit = hyp_decline(t, *popt)
        r2, rmse = _r2_rmse(q, q_fit)
        k = 3
        aic = n * np.log(np.sum((q - q_fit) ** 2) / n) + 2 * k
        results["Hyperbolic"] = dict(
            qi=qi_y, Di_day=Di_y, Di_year=Di_y*365, b=b_y,
            r2=r2, rmse=rmse, AIC=round(aic, 1),
            t=t, q_actual=q, q_fitted=q_fit,
            dates=fit_df["Date"].values, peak_date=t0,
        )
    except Exception:
        pass
    return results

def best_model(results: dict) -> str:
    if not results:
        return "Hyperbolic"
    return max(results, key=lambda k: results[k]["r2"])

# ─────────────────────────────────────────────────────────────────────────────
# 9. EUR CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

def calculate_eur(qi, Di_day, b, model, econ_limit_bbl,
                  horizon_years=30, peak_date=None, cum_to_date_bbl=0.0) -> dict:
    t_max = horizon_years * 365
    t_f   = np.arange(0.0, float(t_max), 1.0)
    if model == "Exponential" or b < 0.01:
        q_f = exp_decline(t_f, qi, Di_day)
    elif model == "Harmonic" or abs(b - 1.0) < 0.01:
        q_f = harm_decline(t_f, qi, Di_day)
    else:
        q_f = hyp_decline(t_f, qi, Di_day, b)
    econ_idx = np.where(q_f <= econ_limit_bbl)[0]
    if len(econ_idx):
        cut    = econ_idx[0]
        t_econ = float(t_f[cut])
        q_f[cut:] = econ_limit_bbl
    else:
        t_econ = float(t_max)
    cum_f          = np.cumsum(q_f)
    eur_from_peak  = float(cum_f[-1])
    eur_total      = eur_from_peak + cum_to_date_bbl
    remaining      = max(0.0, eur_from_peak)
    if peak_date is not None:
        peak_dt    = pd.Timestamp(peak_date)
        dates_fore = [peak_dt + pd.Timedelta(days=int(tt)) for tt in t_f]
    else:
        dates_fore = list(t_f)
    return dict(
        eur_bbl=eur_total, eur_mmbbl=eur_total/1e6,
        remaining_bbl=remaining, remaining_mmbbl=remaining/1e6,
        cum_to_date_mmbbl=cum_to_date_bbl/1e6,
        t_econ_days=t_econ, t_econ_years=round(t_econ/365, 1),
        peak_rate=qi, t_forecast=t_f, q_forecast=q_f,
        cum_forecast=cum_f, dates_forecast=dates_fore,
        econ_limit=econ_limit_bbl,
    )

# ─────────────────────────────────────────────────────────────────────────────
# 10. SESSION STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _init_state():
    defaults = dict(
        wells        = {},
        selected     = [],
        dca_results  = {},
        eur_results  = {},
        data_uploaded= False,
        theme        = "Dark",          # ← NEW: default theme
        settings     = dict(
            econ_limit       = 50.0,
            horizon          = 30,
            phase            = "Oil_bbl",
            smooth           = True,
            auto_model       = True,
            model            = "Hyperbolic",
            available_models = {"Exponential": True, "Harmonic": True, "Hyperbolic": True},
        ),
        ai_log       = [],
        page         = "Dashboard Overview",
        field_name   = "Field",
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _run_dca_all():
    available_models = st.session_state.settings.get(
        "available_models", {"Exponential": True, "Harmonic": True, "Hyperbolic": True})
    for well in st.session_state.selected:
        df  = st.session_state.wells.get(well)
        if df is None:
            continue
        phase = st.session_state.settings["phase"]
        res   = fit_arps_models(df, phase=phase)
        if available_models:
            res = {m: r for m, r in res.items() if available_models.get(m, True)}
        st.session_state.dca_results[well] = res
        if not res:
            continue
        bm = best_model(res)
        r  = res[bm]
        eu = calculate_eur(
            qi=r["qi"], Di_day=r["Di_day"], b=r["b"], model=bm,
            econ_limit_bbl=st.session_state.settings["econ_limit"] * SM3_TO_BBL,
            horizon_years=st.session_state.settings["horizon"],
            peak_date=r["peak_date"],
            cum_to_date_bbl=float(df[phase].sum()),
        )
        st.session_state.eur_results[well] = dict(
            model=bm, **eu,
            **{k: r[k] for k in ("qi", "Di_year", "b", "r2", "rmse", "AIC")}
        )

# ─────────────────────────────────────────────────────────────────────────────
# 11. PLOTTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _themed_fig(**kwargs) -> go.Figure:
    """Return a Plotly figure pre-configured with the active theme."""
    fig = go.Figure(**kwargs)
    fig.update_layout(**get_plotly_bg())
    return fig

def _phase_label(phase: str) -> tuple:
    return {
        "Oil_bbl":   ("Oil Rate",   "STB/day"),
        "Gas_mscf":  ("Gas Rate",   "Mscf/day"),
        "Water_bbl": ("Water Rate", "STB/day"),
    }.get(phase, (phase, ""))

# ─────────────────────────────────────────────────────────────────────────────
# 12. CHART BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def chart_production_rates(wells_data, selected, phases, smooth=True) -> go.Figure:
    phase_cfg = {
        "Oil_bbl":   ("#10b981", "solid",   "Oil (STB/day)"),
        "Gas_mscf":  ("#ef4444", "dot",     "Gas (Mscf/day)"),
        "Water_bbl": ("#3b82f6", "dashdot", "Water (STB/day)"),
    }
    PBG = get_plotly_bg()
    fig = _themed_fig()
    for i, well in enumerate(selected):
        df  = wells_data.get(well)
        if df is None:
            continue
        col = WELL_COLOURS[i % len(WELL_COLOURS)]
        for phase, (ph_col, dash, lbl) in phase_cfg.items():
            if phase not in phases or phase not in df.columns:
                continue
            y  = df[phase].rolling(30, min_periods=1).mean() if smooth else df[phase]
            nm = f"{lbl}" if len(selected) == 1 else f"{well} – {lbl}"
            fig.add_trace(go.Scatter(
                x=df["Date"], y=y, name=nm, mode="lines",
                line=dict(color=ph_col if len(selected) == 1 else col,
                          dash=dash, width=1.8),
            ))
    fig.update_layout(
        showlegend=True, height=280,
        legend=dict(orientation="v", font=dict(size=11, color=PBG["font"]["color"])),
        **{k: v for k, v in PBG.items() if k not in ["margin", "legend"]},
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig

def chart_decline_curve(res, model, actual_dates, actual_q,
                        log_scale=False, forecast_years=10, eur_dict=None) -> go.Figure:
    C   = get_C()
    PBG = get_plotly_bg()
    r   = res[model]
    dates_fit = pd.to_datetime(r["dates"])
    fig = _themed_fig()
    fig.add_trace(go.Scatter(
        x=actual_dates, y=actual_q,
        name="Actual", mode="markers",
        marker=dict(color=C["muted"], size=4, opacity=0.7),
    ))
    fig.add_trace(go.Scatter(
        x=dates_fit, y=r["q_fitted"],
        name=f"Fitted ({model})", mode="lines",
        line=dict(color=C["green"], width=2.5),
    ))
    if eur_dict:
        fore_dates = eur_dict["dates_forecast"][:forecast_years*365]
        fore_q     = eur_dict["q_forecast"][:forecast_years*365]
        fig.add_trace(go.Scatter(
            x=fore_dates, y=fore_q,
            name="Forecast", mode="lines",
            line=dict(color=C["orange"], width=2, dash="dash"),
        ))
        fig.add_hline(
            y=eur_dict["econ_limit"], line_dash="dot",
            line_color=C["red"], line_width=1,
            annotation_text=f"Econ. Limit {eur_dict['econ_limit']:.0f} STB/d",
            annotation_font_color=C["red"],
        )
    fig.update_layout(
        title=dict(text=f"Decline Curve ({model})", font=dict(size=14, color=C["heading"])),
        xaxis_title="Date", yaxis_title="Oil Rate (STB/day)",
        yaxis_type="log" if log_scale else "linear",
        hovermode="x unified", height=380,
        **{k: v for k, v in PBG.items() if k != "margin"},
        margin=dict(l=50, r=20, t=60, b=40),
    )
    return fig

def chart_residuals(res, model) -> go.Figure:
    C   = get_C()
    PBG = get_plotly_bg()
    r     = res[model]
    resid = r["q_actual"] - r["q_fitted"]
    dates = pd.to_datetime(r["dates"])
    fig = _themed_fig()
    fig.add_hline(y=0, line_color=C["border"], line_width=1)
    fig.add_trace(go.Scatter(
        x=dates, y=resid, mode="markers",
        marker=dict(color=np.where(resid >= 0, C["green"], C["red"]),
                    size=5, opacity=0.8),
        name="Residual",
    ))
    fig.update_layout(
        title=dict(text="Residuals (Actual − Fitted)", font=dict(size=12, color=C["heading"])),
        xaxis_title="Date", yaxis_title="Residual (STB/day)",
        height=200,
        **{k: v for k, v in PBG.items() if k != "margin"},
        margin=dict(l=50, r=20, t=40, b=30),
    )
    return fig

def chart_cumulative_forecast(df_actual, eur_dict, well_name, phase="Oil_bbl") -> go.Figure:
    C   = get_C()
    PBG = get_plotly_bg()
    cum_actual = df_actual[phase].cumsum()
    dates_a    = df_actual["Date"]
    fore_dates = eur_dict["dates_forecast"]
    fore_cum   = eur_dict["cum_forecast"] + float(cum_actual.iloc[-1])
    fig = _themed_fig()
    fig.add_trace(go.Scatter(
        x=dates_a, y=cum_actual/1e6,
        name="Actual", mode="lines",
        line=dict(color=C["green"], width=2.5),
    ))
    fig.add_trace(go.Scatter(
        x=fore_dates, y=fore_cum/1e6,
        name="Forecast (P50)", mode="lines",
        line=dict(color=C["green"], width=2, dash="dash"),
        fill="tonexty", fillcolor=f"rgba(16,185,129,0.08)",
    ))
    fig.add_annotation(
        x=0.98, y=0.92, xref="paper", yref="paper",
        text=f"EUR (P50)<br><b>{eur_dict['eur_mmbbl']:.2f} MM STB</b>",
        showarrow=False, align="right",
        font=dict(color=C["green"], size=12),
        bgcolor=C["card"], bordercolor=C["border"],
    )
    fig.update_layout(
        title=dict(text="Cumulative Oil Production", font=dict(size=14, color=C["heading"])),
        xaxis_title="Date", yaxis_title="Cumulative Oil (MM STB)",
        hovermode="x unified", height=320,
        **{k: v for k, v in PBG.items() if k != "margin"},
        margin=dict(l=55, r=20, t=60, b=40),
    )
    return fig

def chart_production_split_by_phase(wells_data, selected) -> dict:
    C   = get_C()
    PBG = get_plotly_bg()
    phase_config = {
        "Oil":   ("Oil_bbl",   "#10b981", "STB/day"),
        "Gas":   ("Gas_mscf",  "#ef4444", "Mscf/day"),
        "Water": ("Water_bbl", "#3b82f6", "STB/day"),
    }
    figures = {}
    for phase_name, (col_name, colour, unit) in phase_config.items():
        well_data = []
        total = 0.0
        for well in selected:
            df = wells_data.get(well)
            if df is None or len(df) == 0:
                continue
            last  = df.iloc[-1]
            value = float(last.get(col_name, 0))
            if col_name == "Gas_mscf":
                value = value * 6
            well_data.append({"well": well, "value": value})
            total += value
        fig = _themed_fig()
        if well_data:
            well_names = [w["well"] for w in well_data]
            values     = [w["value"] for w in well_data]
            colours    = [WELL_COLOURS[i % len(WELL_COLOURS)] for i in range(len(well_names))]
            fig.add_trace(go.Pie(
                labels=well_names, values=values, hole=0.55,
                marker=dict(colors=colours),
                textinfo="percent+label",
                textfont=dict(size=10, color=C["text"]),
                hovertemplate="<b>%{label}</b><br>%{value:,.0f} "+unit+"<br>%{percent}<extra></extra>",
            ))
            total_display = f"{total:,.0f}" if col_name != "Gas_mscf" else f"{total/6:,.1f}"
            total_unit    = unit if col_name != "Gas_mscf" else "Mscf/day"
            fig.add_annotation(
                text=f"<b>{total_display}</b><br>{total_unit}",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=12, color=C["text"]),
            )
        fig.update_layout(
            title=dict(text=f"{phase_name} Production (Latest Day)",
                       font=dict(size=12, color=C["heading"])),
            showlegend=True, height=250,
            legend=dict(orientation="v", font=dict(size=9, color=C["text"]), x=1.0, y=1.0),
            **{k: v for k, v in PBG.items() if k not in ["margin", "legend"]},
            margin=dict(l=10, r=10, t=40, b=10),
        )
        figures[phase_name] = fig
    return figures

def chart_eur_vs_decline(eur_results) -> go.Figure:
    C   = get_C()
    PBG = get_plotly_bg()
    wells = [w for w in eur_results if eur_results[w].get("eur_mmbbl")]
    eurs  = [eur_results[w]["eur_mmbbl"] for w in wells]
    dis   = [eur_results[w]["Di_year"]   for w in wells]
    qis   = [eur_results[w]["qi"]        for w in wells]
    clrs  = [WELL_COLOURS[i % len(WELL_COLOURS)] for i in range(len(wells))]
    fig   = _themed_fig()
    fig.add_trace(go.Scatter(
        x=dis, y=eurs, mode="markers+text",
        text=[w.split("/")[-1] for w in wells],
        textposition="top center",
        textfont=dict(color=C["text"]),
        marker=dict(size=[max(10, q/500) for q in qis],
                    color=clrs, opacity=0.85,
                    line=dict(width=1, color=C["border"])),
        customdata=list(zip(wells, qis)),
        hovertemplate="<b>%{customdata[0]}</b><br>EUR: %{y:.2f} MM STB<br>"
                      "Di: %{x:.3f}/yr<br>qi: %{customdata[1]:,.0f} STB/d<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="EUR vs Decline Rate", font=dict(size=13, color=C["heading"])),
        xaxis_title="Decline Rate (1/yr)",
        yaxis_title="EUR (MM STB)",
        height=320,
        **{k: v for k, v in PBG.items() if k != "margin"},
        margin=dict(l=55, r=20, t=50, b=50),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# 13. HTML COMPONENT HELPERS  (all use get_C())
# ─────────────────────────────────────────────────────────────────────────────

def kpi_card(icon, label, value, unit, delta="", delta_pos=True) -> str:
    C = get_C()
    delta_cls  = "pos" if delta_pos else "neg"
    delta_html = f'<div class="kpi-delta {delta_cls}">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value-row">
        <div class="kpi-value">{value}</div>
        <div class="kpi-unit">{unit}</div>
      </div>
      {delta_html}
    </div>"""

def result_row(label, value) -> str:
    return f"""<div class="result-row">
      <span class="result-label">{label}</span>
      <span class="result-value">{value}</span>
    </div>"""

def insight_item(icon, text, color="#f59e0b") -> str:
    C = get_C()
    return f"""<div class="insight-item">
      <span style="color:{color};font-size:1.1rem">{icon}</span>
      <span style="color:{C['text']}">{text}</span>
    </div>"""

# ─────────────────────────────────────────────────────────────────────────────
# 14. PAGE RENDERS
# ─────────────────────────────────────────────────────────────────────────────

def page_dashboard():
    C = get_C()
    _html(f'<div class="page-title">Dashboard Overview</div>')
    wells_data = st.session_state.wells
    selected   = st.session_state.selected
    eur_res    = st.session_state.eur_results
    smooth     = st.session_state.settings["smooth"]
    if not selected:
        st.info("⬅️  Select wells in the sidebar to begin analysis.")
        return
    if any(w not in st.session_state.eur_results or not st.session_state.eur_results[w]
           for w in selected):
        with st.spinner("⚙️ Calculating EUR and decline metrics for selected wells…"):
            _run_dca_all()
        eur_res = st.session_state.eur_results
    latest_oil = latest_gas = latest_water = cum_oil = 0.0
    all_dis = []
    all_eurs = []
    for well in selected:
        df = wells_data.get(well)
        if df is None or len(df) == 0:
            continue
        last = df.iloc[-1]
        latest_oil   += float(last.get("Oil_bbl",   0))
        latest_gas   += float(last.get("Gas_mscf",  0))
        latest_water += float(last.get("Water_bbl", 0))
        cum_oil      += float(df["Oil_bbl"].sum())
        er = eur_res.get(well, {})
        if er.get("Di_year"):
            all_dis.append(er["Di_year"])
        if er.get("eur_mmbbl"):
            all_eurs.append(er["eur_mmbbl"])
    avg_di  = float(np.mean(all_dis))  if all_dis  else 0.0
    est_eur = float(np.sum(all_eurs))  if all_eurs else 0.0
    cols = st.columns(6, gap="small")
    kpis = [
        ("🛢️",  "Current Oil Rate",   f"{latest_oil:,.0f}",  "STB/day",  ""),
        ("🔥",  "Current Gas Rate",   f"{latest_gas:,.0f}",  "Mscf/day", ""),
        ("💧",  "Current Water Rate", f"{latest_water:,.0f}","STB/day",  ""),
        ("⚖️",  "Cumulative Oil",     f"{cum_oil/1e6:.2f}",  "MM STB",   ""),
        ("📊",  "Estimated EUR",      f"{est_eur:.2f}",      "MM STB",   ""),
        ("📉",  "Avg Decline Rate",   f"{avg_di:.3f}",       "1/yr",     ""),
    ]
    for col, (icon, label, val, unit, delta) in zip(cols, kpis):
        with col:
            _html(kpi_card(icon, label, val, unit, delta))
    _html("<br>")
    phases = ["Oil_bbl", "Gas_mscf", "Water_bbl"]
    for i, well in enumerate(selected):
        fig = chart_production_rates(wells_data, [well], phases, smooth)
        fig.update_layout(title=dict(text=well, font=dict(size=13, color=C["heading"])),
                          height=360)
        st.plotly_chart(fig, use_container_width=True)
        if i < len(selected) - 1:
            st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    w0  = selected[0]
    df0 = wells_data[w0]
    er0 = eur_res.get(w0)
    if er0:
        st.plotly_chart(chart_cumulative_forecast(df0, er0, w0), use_container_width=True)
    else:
        cum = df0["Oil_bbl"].cumsum()
        fig = _themed_fig()
        fig.add_trace(go.Scatter(x=df0["Date"], y=cum/1e6, name="Cumulative Oil",
                                 mode="lines", line=dict(color=C["green"], width=2.5)))
        fig.update_layout(title="Cumulative Oil Production", yaxis_title="MM STB",
                          height=520, **get_plotly_bg())
        st.plotly_chart(fig, use_container_width=True)
    _html(f'<p style="font-weight:600;color:{C["heading"]};margin-bottom:8px">'
          'Latest Day Production by Phase</p>')
    phase_figs = chart_production_split_by_phase(wells_data, selected)
    for phase_name, fig in phase_figs.items():
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
    _html(f'<p style="font-weight:600;color:{C["heading"]};margin-bottom:8px">'
          'Well Performance Summary</p>')
    rows = []
    for well in selected:
        df = wells_data.get(well, pd.DataFrame())
        er = eur_res.get(well, {})
        rows.append({
            "Well":              well,
            "Curr. Oil (STB/d)": f"{df['Oil_bbl'].iloc[-1]:,.0f}" if len(df) else "—",
            "Cum. Oil (MM STB)": f"{df['Oil_bbl'].sum()/1e6:.3f}" if len(df) else "—",
            "Di (1/yr)":         f"{er.get('Di_year', 0):.3f}"    if er else "—",
            "EUR P50 (MM STB)":  f"{er.get('eur_mmbbl', 0):.2f}"  if er else "—",
            "R²":                f"{er.get('r2', 0):.3f}"          if er else "—",
        })
    tbl = pd.DataFrame(rows)
    st.dataframe(tbl, use_container_width=True, hide_index=True,
                 height=min(200, 36 * len(rows) + 38))
    _html("<br>")
    _html(f'<p style="font-weight:600;color:{C["heading"]};margin-bottom:8px">Insights & Alerts</p>')
    insights_html = ""
    for well in selected[:3]:
        er = eur_res.get(well, {})
        di = er.get("Di_year", 0)
        if di > 0.4:
            insights_html += insight_item("⚠️", f"{well}: Decline rate {di:.3f}/yr is above field average.", "#f59e0b")
        else:
            insights_html += insight_item("✅", f"{well}: Performing within expected decline range.", C["green"])
    if latest_water > latest_oil * 0.5:
        insights_html += insight_item("ℹ️", "High water cut detected. Review water injection operations.", C["blue"])
    _html(insights_html)


def page_production_data():
    C = get_C()
    _html('<div class="page-title">Production Data</div>')
    wells_data = st.session_state.wells
    selected   = st.session_state.selected
    smooth     = st.session_state.settings["smooth"]
    if not selected:
        st.info("⬅️  Select wells in the sidebar.")
        return
    tabs = st.tabs(["📋 Data Table", "📈 Charts", "🔍 Data Quality"])
    with tabs[0]:
        well_sel = st.selectbox("Select Well", selected, key="prod_table_well")
        df = wells_data[well_sel].copy()
        df_disp = df[["Date", "OnStreamHrs", "Oil_bbl", "Gas_mscf", "Water_bbl"]].copy()
        df_disp.columns = ["Date", "On-Stream Hrs", "Oil (STB/d)", "Gas (Mscf/d)", "Water (STB/d)"]
        df_disp["Date"] = df_disp["Date"].dt.strftime("%Y-%m-%d")
        for c in ["Oil (STB/d)", "Gas (Mscf/d)", "Water (STB/d)"]:
            df_disp[c] = df_disp[c].map("{:,.1f}".format)
        c1, c2 = st.columns([3, 1])
        with c1:
            st.dataframe(df_disp, use_container_width=True, height=420, hide_index=True)
        with c2:
            df_raw = wells_data[well_sel]
            st.markdown("**Summary Statistics**")
            stats = {
                "Total Days":        len(df_raw),
                "Start Date":        df_raw["Date"].min().strftime("%Y-%m-%d"),
                "End Date":          df_raw["Date"].max().strftime("%Y-%m-%d"),
                "Peak Oil (STB/d)":  f"{df_raw['Oil_bbl'].max():,.0f}",
                "Avg Oil (STB/d)":   f"{df_raw['Oil_bbl'].mean():,.0f}",
                "Cum Oil (MM STB)":  f"{df_raw['Oil_bbl'].sum()/1e6:.3f}",
                "Avg GOR":           f"{(df_raw['Gas_mscf']/df_raw['Oil_bbl'].replace(0,np.nan)).mean():.2f}",
                "Peak Water (STB/d)":f"{df_raw['Water_bbl'].max():,.0f}",
            }
            html = "".join(result_row(k, str(v)) for k, v in stats.items())
            _html(f'<div class="panel-card">{html}</div>')
    with tabs[1]:
        st.markdown("**Production Rates Overview**")
        phases = ["Oil_bbl", "Gas_mscf", "Water_bbl"]
        fig    = chart_production_rates(wells_data, selected, phases, smooth)
        st.plotly_chart(fig, use_container_width=True)
        well_sel2 = st.selectbox("Well (monthly bar)", selected, key="prod_bar_well")
        df2 = wells_data[well_sel2].copy()
        monthly = (df2.set_index("Date")[["Oil_bbl", "Gas_mscf", "Water_bbl"]]
                   .resample("ME").mean().reset_index())
        PBG = get_plotly_bg()
        fig2 = go.Figure()
        fig2.add_bar(x=monthly["Date"], y=monthly["Oil_bbl"],
                     name="Oil (STB/d)", marker_color=C["green"])
        fig2.add_bar(x=monthly["Date"], y=monthly["Water_bbl"],
                     name="Water (STB/d)", marker_color=C["blue"])
        fig2.update_layout(title="Monthly Average Rates", barmode="group",
                           height=300, **PBG)
        st.plotly_chart(fig2, use_container_width=True)
    with tabs[2]:
        well_sel3 = st.selectbox("Well (quality check)", selected, key="qual_well")
        df3 = wells_data[well_sel3]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Rows",  f"{len(df3):,}")
        c2.metric("Missing Oil", f"{(df3['Oil_bbl']==0).sum():,}")
        c3.metric("Missing Gas", f"{(df3['Gas_mscf']==0).sum():,}")
        PBG = get_plotly_bg()
        fig3 = px.histogram(df3, x="OnStreamHrs", nbins=25,
                            title="On-Stream Hours Distribution",
                            color_discrete_sequence=[C["blue"]])
        fig3.update_layout(height=250, **PBG)
        st.plotly_chart(fig3, use_container_width=True)
        zero_mask = df3["Oil_bbl"] == 0
        if zero_mask.any():
            fig4 = _themed_fig()
            fig4.add_trace(go.Scatter(
                x=df3.loc[zero_mask, "Date"],
                y=np.ones(zero_mask.sum()),
                mode="markers",
                marker=dict(color=C["red"], size=5, symbol="x"),
                name="Shut-in / Zero Oil",
            ))
            fig4.update_layout(title="Shut-in / Zero-Rate Days", yaxis_visible=False,
                               height=150,
                               **{k:v for k,v in PBG.items() if k!="margin"},
                               margin=dict(l=20,r=20,t=40,b=20))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.success("✅ No zero-oil-rate days detected in selected well.")


def page_dca():
    C = get_C()
    _html('<div class="page-title">Decline Curve Analysis (DCA)</div>')
    wells_data = st.session_state.wells
    selected   = st.session_state.selected
    if not selected:
        st.info("⬅️  Select wells in the sidebar.")
        return
    well = st.selectbox("Select Well", selected, key="dca_well")
    if well not in st.session_state.dca_results or not st.session_state.dca_results.get(well):
        with st.spinner(f"⚙️ Fitting models for {well}…"):
            _run_dca_all()
    dca_res = st.session_state.dca_results
    eur_res = st.session_state.eur_results

    _html('<div class="panel-card">')
    st.markdown("**Input Parameters**")
    model_sel = st.selectbox("View Model", ["Hyperbolic","Exponential","Harmonic"], key="dca_model")
    st.caption("All three DCA models are fitted automatically on well selection.")
    log_scale = st.toggle("Log Scale Y-axis", value=True, key="dca_log")
    fore_yrs  = st.slider("Forecast Horizon (Years)", 5, 50, 15, key="dca_fore")
    econ_lim  = st.number_input("Economic Limit (STB/day)", 1.0, 500.0,
                                value=st.session_state.settings["econ_limit"]*SM3_TO_BBL,
                                step=5.0, key="dca_econ")
    if st.button("🔄 Re-fit All Models", key="dca_run", use_container_width=True):
        with st.spinner("⚙️ Re-fitting all three decline models…"):
            _run_dca_all()
        dca_res = st.session_state.dca_results
        eur_res = st.session_state.eur_results
        st.success("✅ Models re-fitted successfully!")
    _html("</div>")

    er   = eur_res.get(well, {})
    dr   = dca_res.get(well, {}).get(model_sel, {})
    res_w = dca_res.get(well, {})

    if res_w:
        _html("<br>")
        _html('<div class="panel-card">')
        _html(f'<div class="section-header" style="margin-bottom:12px;padding-bottom:0;border-bottom:none;font-size:1rem">All Model Fits (DCA Results)</div>')
        model_rows = []
        for model_name, model_res in res_w.items():
            model_rows.append({
                "Model": model_name,
                "qi (STB/d)": f"{model_res['qi']:,.0f}",
                "Di (1/yr)":  f"{model_res['Di_year']:.4f}",
                "b":          f"{model_res['b']:.3f}",
                "R²":         f"{model_res['r2']:.4f}",
                "RMSE":       f"{model_res['rmse']:.1f}",
                "AIC":        f"{model_res['AIC']:.1f}",
            })
        model_df = pd.DataFrame(model_rows)
        st.dataframe(model_df, use_container_width=True, hide_index=True, height=160)
        _html("</div>")

    if dr:
        _html("<br>")
        _html('<div class="panel-card">')
        _html(f'<div class="section-header" style="margin-bottom:12px;padding-bottom:0;border-bottom:none;font-size:1rem">Selected Model Summary</div>')
        rows_html = "".join([
            result_row("Model",         model_sel),
            result_row("qi (STB/day)",  f"{dr['qi']:,.0f}"),
            result_row("Di (1/yr)",     f"{dr['Di_year']:.4f}"),
            result_row("b",             f"{dr['b']:.3f}"),
            result_row("R²",            f"{dr['r2']:.4f}"),
            result_row("RMSE (STB/d)",  f"{dr['rmse']:.1f}"),
            result_row("AIC",           f"{dr['AIC']:.1f}"),
            result_row("Forecast (yrs)",f"{fore_yrs}"),
        ])
        _html(rows_html)
        _html("</div>")
        df_w = wells_data[well]
        _html("<br>")
        _html('<div class="panel-card">')
        _html(f'<div class="section-header" style="margin-bottom:12px;padding-bottom:0;border-bottom:none;font-size:1rem">Well Information</div>')
        info_html = "".join([
            result_row("Well",        well),
            result_row("Field",       st.session_state.field_name),
            result_row("Start Date",  df_w["Date"].min().strftime("%Y-%m-%d")),
            result_row("End Date",    df_w["Date"].max().strftime("%Y-%m-%d")),
            result_row("Econ. Limit", f"{econ_lim:.0f} STB/d"),
        ])
        _html(info_html)
        _html("</div>")

    df_w  = wells_data.get(well, pd.DataFrame())
    res_w = dca_res.get(well, {})
    eur_w = eur_res.get(well)
    if not res_w:
        st.warning("⚠️ Decline models could not be fitted. Need ≥ 20 days and ≥ 8 months of positive oil production.")
    else:
        if dr:
            eur_fore = calculate_eur(
                qi=dr["qi"], Di_day=dr["Di_day"], b=dr["b"], model=model_sel,
                econ_limit_bbl=econ_lim, horizon_years=fore_yrs,
                peak_date=dr["peak_date"], cum_to_date_bbl=float(df_w["Oil_bbl"].sum()),
            )
        else:
            eur_fore = eur_w
        st.session_state.eur_results[well] = dict(
            model=model_sel,
            **(eur_fore or {}),
            **{k: dr[k] for k in ("qi","Di_year","b","r2","rmse","AIC")}
        )
        monthly = (df_w.set_index("Date")["Oil_bbl"]
                   .resample("ME").mean().dropna().reset_index())
        monthly.columns = ["Date", "Oil_bbl"]
        if model_sel in res_w:
            fig_dc = chart_decline_curve(
                res_w, model_sel,
                actual_dates=monthly["Date"],
                actual_q=monthly["Oil_bbl"],
                log_scale=log_scale,
                forecast_years=fore_yrs,
                eur_dict=eur_fore,
            )
            st.plotly_chart(fig_dc, use_container_width=True)
            PBG         = get_plotly_bg()
            model_names = list(res_w.keys())
            r2_vals     = [res_w[m]["r2"]   for m in model_names]
            rmse_vals   = [res_w[m]["rmse"]  for m in model_names]
            col_bars    = [C["green"] if m == model_sel else C["muted"] for m in model_names]
            fig_cmp     = make_subplots(rows=1, cols=2, subplot_titles=["R² Comparison","RMSE Comparison"])
            fig_cmp.add_trace(go.Bar(x=model_names, y=r2_vals,   marker_color=col_bars, name="R²"),   row=1, col=1)
            fig_cmp.add_trace(go.Bar(x=model_names, y=rmse_vals, marker_color=col_bars, name="RMSE"), row=1, col=2)
            fig_cmp.update_layout(height=200, showlegend=False,
                                  **{k:v for k,v in PBG.items() if k!="margin"},
                                  margin=dict(l=40,r=20,t=30,b=30))
            st.plotly_chart(fig_cmp, use_container_width=True)
            st.plotly_chart(chart_residuals(res_w, model_sel), use_container_width=True)
        else:
            st.warning(f"Model '{model_sel}' could not be fitted for this well.")


def page_eur():
    C = get_C()
    _html('<div class="page-title">EUR Prediction</div>')
    wells_data = st.session_state.wells
    selected   = st.session_state.selected
    if not selected:
        st.info("⬅️  Select wells in the sidebar.")
        return
    if any(w not in st.session_state.dca_results or not st.session_state.dca_results.get(w)
           for w in selected):
        with st.spinner("⚙️ Fitting decline curves…"):
            _run_dca_all()
    dca_res = st.session_state.dca_results
    eur_res = st.session_state.eur_results
    analyzed_wells = [w for w in selected if w in dca_res and dca_res[w]]
    if not analyzed_wells:
        st.warning("⚠️ Decline models could not be fitted for any selected well.")
        return
    default_well = st.session_state.get("eur_well")
    if default_well not in analyzed_wells:
        default_well = analyzed_wells[0]
    well   = st.selectbox("Select Well", analyzed_wells,
                          index=analyzed_wells.index(default_well), key="eur_well")
    dr_all = dca_res.get(well, {})
    df_w   = wells_data.get(well, pd.DataFrame())
    if not dr_all:
        st.warning("⚠️ No DCA results for this well.")
        return
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        model_sel = st.selectbox("Model", list(dr_all.keys()), key="eur_model_sel",
                                 index=list(dr_all.keys()).index(best_model(dr_all)))
    with ic2:
        econ_lim  = st.number_input("Economic Limit (STB/day)", 1.0, 500.0,
                                    value=50.0*SM3_TO_BBL, step=5.0, key="eur_econ2")
    with ic3:
        horizon   = st.slider("Forecast Horizon (Years)", 5, 50, 30, key="eur_horizon2")
    dr = dr_all.get(model_sel, {})
    if not dr:
        st.error("Selected model unavailable.")
        return
    eur = calculate_eur(
        qi=dr["qi"], Di_day=dr["Di_day"], b=dr["b"], model=model_sel,
        econ_limit_bbl=econ_lim, horizon_years=horizon,
        peak_date=dr["peak_date"], cum_to_date_bbl=float(df_w["Oil_bbl"].sum()),
    )
    st.session_state.eur_results[well] = dict(
        model=model_sel, **eur,
        **{k: dr[k] for k in ("qi","Di_year","b","r2","rmse","AIC")}
    )
    k1, k2, k3, k4, k5 = st.columns(5)
    kpi_data = [
        (k1, "📊", "EUR (P50)",           f"{eur['eur_mmbbl']:.2f}",        "MM STB"),
        (k2, "📦", "Cum. Production",     f"{eur['cum_to_date_mmbbl']:.2f}","MM STB"),
        (k3, "🔋", "Remaining Recovery",  f"{eur['remaining_mmbbl']:.2f}",  "MM STB"),
        (k4, "⏱️", "Time to Econ. Limit", f"{eur['t_econ_years']:.1f}",    "yrs"),
        (k5, "⛽", "Peak Rate",           f"{eur['peak_rate']:,.0f}",       "STB/d"),
    ]
    for col, icon, label, val, unit in kpi_data:
        with col:
            _html(kpi_card(icon, label, val, unit))
    _html("<br>")
    st.plotly_chart(chart_cumulative_forecast(df_w, eur, well), use_container_width=True)
    _html("<br>")
    PBG = get_plotly_bg()
    fig_rate = _themed_fig()
    monthly  = (df_w.set_index("Date")["Oil_bbl"].resample("ME").mean()
                .dropna().reset_index())
    monthly.columns = ["Date", "Oil_bbl"]
    fig_rate.add_trace(go.Scatter(x=monthly["Date"], y=monthly["Oil_bbl"],
                                  name="Actual", mode="lines",
                                  line=dict(color=C["green"], width=2)))
    fig_rate.add_trace(go.Scatter(
        x=eur["dates_forecast"][:horizon*365:30],
        y=eur["q_forecast"][:horizon*365:30],
        name="Forecast (P50)", mode="lines",
        line=dict(color=C["orange"], width=2, dash="dash"),
    ))
    fig_rate.add_hline(y=econ_lim, line_dash="dot", line_color=C["red"],
                       annotation_text="Economic Limit",
                       annotation_font_color=C["red"])
    fig_rate.update_layout(
        title="Production Rate Forecast",
        xaxis_title="Date", yaxis_title="Oil Rate (STB/day)",
        height=320, hovermode="x unified",
        **{k:v for k,v in PBG.items() if k!="margin"},
        margin=dict(l=55,r=20,t=50,b=40),
    )
    st.plotly_chart(fig_rate, use_container_width=True)
    _html(f'<p style="font-weight:600;color:{C["heading"]}">EUR Results (Base Case)</p>')
    res_cols = st.columns(2)
    res_data = {
        "Estimated Ultimate Recovery (EUR)": f"{eur['eur_mmbbl']:.3f} MM STB",
        "Cumulative Production to Date":     f"{eur['cum_to_date_mmbbl']:.3f} MM STB",
        "Remaining Recovery":                f"{eur['remaining_mmbbl']:.3f} MM STB",
        "Time to Economic Limit":            f"{eur['t_econ_years']:.1f} years",
        "Peak Rate (qi)":                    f"{eur['peak_rate']:,.0f} STB/day",
        "Economic Limit":                    f"{econ_lim:.0f} STB/day",
        "Decline Rate (Di)":                 f"{dr['Di_year']:.4f} /yr",
        "Arps Exponent (b)":                 f"{dr['b']:.3f}",
        "Model R²":                          f"{dr['r2']:.4f}",
        "Forecast Model":                    model_sel,
    }
    items = list(res_data.items())
    half  = len(items) // 2
    with res_cols[0]:
        _html('<div class="panel-card">' +
              "".join(result_row(k,v) for k,v in items[:half]) + "</div>")
    with res_cols[1]:
        _html('<div class="panel-card">' +
              "".join(result_row(k,v) for k,v in items[half:]) + "</div>")


def page_model_settings():
    C = get_C()
    _html('<div class="page-title">Model Settings</div>')
    s  = st.session_state.settings
    t1, t2, t3 = st.tabs(["Decline Model", "Advanced Settings", "Units & Display"])
    with t1:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("**Decline Model Options**")
            s["model"] = st.selectbox(
                "Default Decline Model", ["Hyperbolic","Exponential","Harmonic"],
                index=["Hyperbolic","Exponential","Harmonic"].index(s.get("model","Hyperbolic")),
            )
            s["auto_model"] = st.toggle("Automatic Model Selection (best R²)",
                                        value=s.get("auto_model", True))
            st.markdown("**Available Models**")
            available_models = s.get("available_models",
                                     {"Exponential": True, "Harmonic": True, "Hyperbolic": True})
            for m in ["Exponential","Harmonic","Hyperbolic"]:
                available_models[m] = st.checkbox(m, value=available_models.get(m, True),
                                                   key=f"model_chk_{m}")
            s["available_models"] = available_models
        with c2:
            st.markdown("**Curve Fitting Method**")
            st.selectbox("Method", ["Nonlinear Least Squares (scipy)",
                                    "Differential Evolution"], key="fit_method")
            st.toggle("Robust Fitting (Huber loss)", value=False, key="robust_fit")
            st.toggle("Outlier Detection", value=True, key="outlier_det")
            st.slider("Outlier Threshold (Std Dev)", 1.0, 5.0, 3.0, key="outlier_std")
    with t2:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("**Forecast Settings**")
            st.radio("Economic Limit Type", ["Fixed Rate","Economic Value"], horizontal=True)
            s["econ_limit"] = st.number_input(
                "Economic Limit (Sm³/day)", 1.0, 500.0,
                value=float(s.get("econ_limit", 50.0)), step=5.0,
            )
            s["horizon"] = st.slider("Forecast Horizon (Years)", 5, 50,
                                     int(s.get("horizon", 30)))
        with c2:
            st.markdown("**Data Smoothing**")
            s["smooth"] = st.toggle("Apply Smoothing", value=bool(s.get("smooth", True)))
            smooth_method = st.selectbox("Smoothing Method",
                                         ["Moving Average","Exponential Weighted","Savitzky-Golay"])
            if smooth_method == "Moving Average":
                st.slider("Window Size (Days)", 7, 90, 30, key="smooth_window")
    with t3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Unit System**")
            st.info("✅ Field Units  (STB/day, Mscf/day)  – fixed for this session")
            unit_data = pd.DataFrame([
                {"Fluid": "Oil",   "Input Unit": "Sm³/day", "Output Unit": "STB/day",  "Factor": "6.2898"},
                {"Fluid": "Gas",   "Input Unit": "Sm³/day", "Output Unit": "Mscf/day", "Factor": "0.0353"},
                {"Fluid": "Water", "Input Unit": "Sm³/day", "Output Unit": "STB/day",  "Factor": "6.2898"},
            ])
            st.table(unit_data)
        with c2:
            st.markdown("**Display Preferences**")
            st.selectbox("Time Axis Format", ["Calendar Date","Days from Peak","Years from Peak"])
            st.selectbox("Rate Scale Default", ["Linear","Logarithmic"])
            st.selectbox("Volume Unit for EUR", ["MM STB","STB","BOE"])


def page_insights():
    C = get_C()
    _html('<div class="page-title">Field Insights</div>')
    wells_data = st.session_state.wells
    selected   = st.session_state.selected
    eur_res    = st.session_state.eur_results
    if not selected:
        st.info("⬅️  Select wells and run DCA first.")
        return
    if any(w not in eur_res or not eur_res[w] for w in selected):
        with st.spinner("⚙️ Calculating field-level EUR and decline metrics…"):
            _run_dca_all()
        eur_res = st.session_state.eur_results
    eur_wells = [w for w in selected if w in eur_res]
    total_eur = sum(eur_res.get(w, {}).get("eur_mmbbl", 0) for w in eur_wells)
    avg_di    = float(np.mean([eur_res[w].get("Di_year", 0) for w in eur_wells])) if eur_wells else 0.0
    avg_eur   = total_eur / max(1, len(eur_wells)) if eur_wells else 0.0
    k1, k2, k3, k4 = st.columns(4)
    with k1: _html(kpi_card("🏭","Total Wells",      f"{len(selected)}","",""))
    with k2: _html(kpi_card("📊","Total Oil EUR",    f"{total_eur:.2f}","MM STB",""))
    with k3: _html(kpi_card("📉","Avg Decline Rate", f"{avg_di:.3f}","1/yr",""))
    with k4: _html(kpi_card("⛽","Avg EUR per Well", f"{avg_eur:.2f}","MM STB",""))
    _html("<br>")
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        if len(eur_res) >= 2:
            st.plotly_chart(chart_eur_vs_decline(eur_res), use_container_width=True)
        else:
            st.info("Run DCA on 2+ wells to see EUR vs Decline Rate scatter.")
    with c2:
        _html(f'<p style="font-weight:600;color:{C["heading"]};margin-bottom:8px">Top Performing Wells</p>')
        rows = []
        for well in selected:
            er = eur_res.get(well, {})
            rows.append({
                "Well":         well,
                "EUR (MM STB)": round(er.get("eur_mmbbl", 0), 2),
                "Di (1/yr)":    round(er.get("Di_year",   0), 3),
                "R²":           round(er.get("r2",         0), 3),
            })
        rows_df = pd.DataFrame(rows).sort_values("EUR (MM STB)", ascending=False)
        st.dataframe(rows_df, use_container_width=True, hide_index=True)
    _html(f'<p style="font-weight:600;color:{C["heading"]};margin:16px 0 8px">Cumulative Oil Comparison</p>')
    PBG = get_plotly_bg()
    fig_cum = _themed_fig()
    for i, well in enumerate(selected):
        df = wells_data.get(well)
        if df is None:
            continue
        cum = df["Oil_bbl"].cumsum() / 1e6
        fig_cum.add_trace(go.Scatter(
            x=df["Date"], y=cum, name=well, mode="lines",
            line=dict(color=WELL_COLOURS[i % len(WELL_COLOURS)], width=2),
        ))
    fig_cum.update_layout(
        xaxis_title="Date", yaxis_title="Cumulative Oil (MM STB)",
        height=300, hovermode="x unified",
        **{k:v for k,v in PBG.items() if k!="margin"},
        margin=dict(l=55,r=20,t=10,b=40),
    )
    st.plotly_chart(fig_cum, use_container_width=True)
    _html(f'<p style="font-weight:600;color:{C["heading"]};margin:16px 0 8px">Insights & Recommendations</p>')
    if eur_res:
        best_w  = max(eur_res, key=lambda w: eur_res[w].get("eur_mmbbl", 0))
        worst_w = min(eur_res, key=lambda w: eur_res[w].get("Di_year",   0))
        hi_di   = [w for w in eur_res if eur_res[w].get("Di_year", 0) > avg_di * 1.3]
        _html(
            insight_item("🏆", f"{best_w} has the highest EUR at "
                               f"{eur_res[best_w].get('eur_mmbbl',0):.2f} MM STB.", C["green"]) +
            insight_item("📉", f"Average field decline rate: {avg_di:.3f}/yr.", C["orange"]) +
            ("".join(insight_item("⚠️",
                f"{w}: Decline rate {eur_res[w]['Di_year']:.3f}/yr is 30% above field average.",
                C["red"]) for w in hi_di[:2]) if hi_di else ""),
        )


def page_reports():
    C = get_C()
    _html('<div class="page-title">Reports & Export</div>')
    wells_data = st.session_state.wells
    selected   = st.session_state.selected
    eur_res    = st.session_state.eur_results
    c1, c2 = st.columns([2, 1], gap="medium")
    with c1:
        st.markdown("**Generate Report**")
        report_type       = st.selectbox("Report Type",
            ["DCA Summary Report","EUR Forecast Report",
             "Well Performance Report","Executive Summary"])
        wells_for_report  = st.multiselect("Select Wells", selected, default=selected[:3])
        inc_col1, inc_col2 = st.columns(2)
        with inc_col1:
            inc_prod = st.checkbox("Production Data & Charts", True)
            inc_dca  = st.checkbox("DCA Results", True)
        with inc_col2:
            inc_eur  = st.checkbox("EUR Forecast", True)
            inc_fi   = st.checkbox("Field Insights", True)
        if st.button("📄 Generate Excel Report", use_container_width=True):
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                if wells_data and selected:
                    all_rows = []
                    for well in wells_for_report:
                        df = wells_data.get(well, pd.DataFrame())
                        if len(df):
                            monthly = (df.set_index("Date")[["Oil_bbl","Gas_mscf","Water_bbl"]]
                                       .resample("ME").mean().reset_index())
                            monthly.insert(0, "Well", well)
                            all_rows.append(monthly)
                    if all_rows:
                        pd.concat(all_rows).to_excel(writer, sheet_name="Production", index=False)
                if eur_res:
                    eur_rows = []
                    for well in wells_for_report:
                        er = eur_res.get(well, {})
                        if er:
                            eur_rows.append({
                                "Well":                well,
                                "Model":               er.get("model",""),
                                "qi (STB/d)":          round(er.get("qi",0), 1),
                                "Di (1/yr)":           round(er.get("Di_year",0), 4),
                                "b":                   round(er.get("b",0), 3),
                                "R2":                  round(er.get("r2",0), 4),
                                "EUR (MM STB)":        round(er.get("eur_mmbbl",0), 3),
                                "Remaining (MM STB)":  round(er.get("remaining_mmbbl",0), 3),
                                "Econ Limit (yrs)":    er.get("t_econ_years",""),
                            })
                    if eur_rows:
                        pd.DataFrame(eur_rows).to_excel(writer, sheet_name="DCA_EUR", index=False)
            buf.seek(0)
            st.download_button(
                label="⬇️ Download Excel Report",
                data=buf.getvalue(),
                file_name=f"PetroDCA_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    with c2:
        st.markdown("**Export Data**")
        if selected and wells_data:
            all_dfs = []
            for w in selected:
                df = wells_data.get(w, pd.DataFrame())
                if len(df):
                    d = df[["Date","Oil_bbl","Gas_mscf","Water_bbl"]].copy()
                    d.insert(0, "Well", w)
                    all_dfs.append(d)
            if all_dfs:
                csv_str = pd.concat(all_dfs).to_csv(index=False)
                st.download_button("📥 Export to CSV", csv_str,
                                   file_name="production_data.csv",
                                   mime="text/csv", use_container_width=True)
        if eur_res:
            eur_rows = [{
                "Well":         w,
                "EUR (MM STB)": round(eur_res[w].get("eur_mmbbl",0), 3),
                "Di (1/yr)":    round(eur_res[w].get("Di_year",0),   4),
                "R2":           round(eur_res[w].get("r2",0),         4),
            } for w in selected if eur_res.get(w)]
            if eur_rows:
                st.download_button("📥 Export EUR Results",
                                   pd.DataFrame(eur_rows).to_csv(index=False),
                                   file_name="eur_results.csv",
                                   mime="text/csv", use_container_width=True)
        st.markdown("**Field Summary**")
        if eur_res and selected:
            total_eur = sum(eur_res.get(w, {}).get("eur_mmbbl", 0) for w in selected)
            avg_r2    = np.mean([eur_res.get(w, {}).get("r2", 0) for w in selected
                                  if eur_res.get(w, {}).get("r2")])
            html = (result_row("Wells Analysed", str(len(selected))) +
                    result_row("Total EUR",       f"{total_eur:.2f} MM STB") +
                    result_row("Avg Model R²",    f"{avg_r2:.4f}"))
            _html(f'<div class="panel-card">{html}</div>')


def page_ai_log():
    C = get_C()
    _html('<div class="page-title">AI Interaction Log</div>')
    tab1, tab2 = st.tabs(["💬 Prompts & Responses", "📋 Summary"])
    with tab1:
        _html(f"""
        <div class="panel-card" style="margin-bottom:12px">
          <p style="color:{C['muted']};font-size:0.85rem">
          AI is used for code generation, debugging, optimisation, documentation,
          and idea generation. All DCA fitting is performed using rigorous
          scipy non-linear least squares — AI suggestions are advisory only.
          </p>
        </div>""")
        prompt = st.text_area("Ask a question about your production data or DCA results…",
                              placeholder="e.g. Why is my decline rate unusually high for well 15/9-F-11?",
                              height=80, key="ai_prompt")
        if st.button("Send", key="ai_send") and prompt.strip():
            eur_res = st.session_state.eur_results
            well    = st.session_state.selected[0] if st.session_state.selected else None
            er      = eur_res.get(well, {}) if well else {}
            resp    = _ai_advisor(prompt, er, well)
            st.session_state.ai_log.append({"role":"user", "text": prompt})
            st.session_state.ai_log.append({"role":"ai",   "text": resp})
        for entry in reversed(st.session_state.ai_log[-20:]):
            if entry["role"] == "user":
                _html(f"""
                <div style="background:{C['card2']};border:1px solid {C['border']};border-radius:10px;
                            padding:10px 14px;margin-bottom:8px;font-size:0.87rem">
                  <span style="color:{C['muted']};font-size:0.75rem">You</span><br>
                  <span style="color:{C['text']}">{entry['text']}</span>
                </div>""")
            else:
                _html(f"""
                <div style="background:{C['card']};border:1px solid {C['border']};border-radius:10px;
                            padding:10px 14px;margin-bottom:8px;font-size:0.87rem">
                  <span style="color:{C['green']};font-size:0.75rem">AI Response</span><br>
                  <span style="color:{C['text']}">{entry['text']}</span>
                </div>""")
        if st.session_state.ai_log:
            st.caption(f"Total Interactions: {len(st.session_state.ai_log)//2}")
    with tab2:
        st.markdown("**How AI is Used in PetroDCA**")
        st.info("""
        **PetroDCA** uses data-driven analysis powered by:

        • **scipy curve_fit** – non-linear least squares for Arps model fitting  
        • **Automatic model selection** – best R² across Exponential / Harmonic / Hyperbolic  
        • **AIC scoring** – penalises over-parameterised models  
        • **AI advisor** – interprets results and flags anomalies  

        All computations are deterministic and reproducible.
        """)

def _ai_advisor(prompt, er, well) -> str:
    prompt_l = prompt.lower()
    if any(w in prompt_l for w in ["decline rate", "high decline", "di"]):
        di = er.get("Di_year", 0)
        if di > 0.5:
            return (f"The decline rate for <b>{well}</b> is <b>{di:.3f}/yr</b>, "
                    "which is relatively high (>0.5/yr). Consider reviewing reservoir "
                    "pressure data and evaluating artificial lift or infill drilling options.")
        elif di > 0.2:
            return (f"The decline rate for <b>{well}</b> is <b>{di:.3f}/yr</b> — "
                    "moderate. Continue monitoring monthly trends.")
        else:
            return f"Decline rate {di:.3f}/yr is relatively low — typical for high-permeability reservoirs."
    if "eur" in prompt_l or "ultimate recovery" in prompt_l:
        eur = er.get("eur_mmbbl", 0)
        return (f"Estimated Ultimate Recovery for <b>{well}</b> is <b>{eur:.2f} MM STB</b>. "
                "This is calculated by integrating the fitted Arps decline curve to the economic limit.")
    if "hyperbolic" in prompt_l or "model" in prompt_l:
        r2 = er.get("r2", 0)
        return (f"The Hyperbolic Arps model achieved R²={r2:.4f} for <b>{well}</b>. "
                "Hyperbolic decline is the most general Arps form.")
    if "water" in prompt_l or "wor" in prompt_l:
        return "Rising WOR suggests water influx or coning. Check aquifer material balance."
    if "r2" in prompt_l or "fit" in prompt_l or "accuracy" in prompt_l:
        r2   = er.get("r2", 0)
        rmse = er.get("rmse", 0)
        return (f"Model fit for <b>{well}</b>: R²={r2:.4f}, RMSE={rmse:,.0f} STB/d. "
                "R² > 0.90 indicates a reliable fit.")
    return ("I can help analyse your decline curve results. Ask me about: "
            "decline rates, EUR estimates, model selection, water cut trends, "
            "R² fit quality, or forecast sensitivity.")

# ─────────────────────────────────────────────────────────────────────────────
# 15. SIDEBAR  (with theme toggle)
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar():
    C = get_C()
    is_dark = st.session_state.get("theme", "Dark") == "Dark"

    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────
        _html(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:8px 0 12px">
          <div style="background:{C['blue']};border-radius:10px;width:40px;height:40px;
                      display:flex;align-items:center;justify-content:center;
                      font-size:1.3rem">🛢️</div>
          <div>
            <div style="font-weight:700;font-size:1.05rem;color:{C['sidebar_text']}">PetroDCA</div>
            <div style="color:{C['sidebar_muted']};font-size:0.75rem">Production Analytics</div>
          </div>
        </div>
        <hr style="border-color:{C['border']};margin:0 0 10px">
        """)

        # ── Theme toggle ────────────────────────────────────────────
        _html(f'<div style="color:{C["sidebar_muted"]};font-size:0.72rem;'
              f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">'
              f'🎨 Theme</div>')
        col_tog1, col_tog2 = st.columns([1, 1])
        with col_tog1:
            if st.button("☀️ Light" if is_dark else "☀️ Light ✓",
                         key="sidebar_theme_light", use_container_width=True):
                st.session_state.theme = "Light"
                st.rerun()
        with col_tog2:
            if st.button("🌙 Dark ✓" if is_dark else "🌙 Dark",
                         key="sidebar_theme_dark", use_container_width=True):
                st.session_state.theme = "Dark"
                st.rerun()

        _html(f'<hr style="border-color:{C["border"]};margin:10px 0">')

        # ── Upload ─────────────────────────────────────────────────
        _html(f'<div style="color:{C["sidebar_muted"]};font-size:0.72rem;'
              f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">'
              f'📂 Project / Selection</div>')
        with st.expander("📋 Data Format Guide", expanded=False):
            st.markdown("""
            **Expected Excel Structure:**
            - One sheet per well (well name as sheet tab)
            - Headers: `Date`, `Oil Rate`, `Gas Rate`, `Water Rate`, `On-Stream Hrs`
            - Units: Sm³/day → auto-converts to STB/day / Mscf/day

            **CSV Alternative:**
            - Columns: `date`, `oil`, `gas`, `water`, `well`
            """)
        uploaded = st.file_uploader(
            "Upload Data (Excel / CSV)",
            type=["xlsx","xls","csv"],
            label_visibility="collapsed",
        )
        if uploaded:
            with st.spinner("⏳ Loading and validating data…"):
                try:
                    if uploaded.name.endswith(".csv"):
                        st.session_state.wells = load_csv_production(uploaded)
                    else:
                        st.session_state.wells = load_excel_production(uploaded)
                    st.session_state.selected     = list(st.session_state.wells.keys())[:3]
                    st.session_state.dca_results  = {}
                    st.session_state.eur_results  = {}
                    if st.session_state.wells:
                        st.session_state.data_uploaded = True
                        st.success(f"✅ {len(st.session_state.wells)} well(s) loaded!")
                    else:
                        st.session_state.data_uploaded = False
                        st.error("❌ No valid wells found. Check data format.")
                except Exception as e:
                    st.session_state.data_uploaded = False
                    st.error(f"❌ Error loading file: {e}")

        # ── Field & Wells ──────────────────────────────────────────
        st.session_state.field_name = st.text_input(
            "Field", value=st.session_state.field_name,
        )
        all_wells = list(st.session_state.wells.keys())
        if all_wells:
            st.session_state.selected = st.multiselect(
                "Wells", options=all_wells,
                default=st.session_state.selected or all_wells[:3],
            )

        if st.session_state.wells:
            with st.expander("📦 Loaded Wells", expanded=False):
                st.markdown(f"**{len(st.session_state.wells)} well(s) loaded**")
                for well, df in st.session_state.wells.items():
                    if "Date" in df.columns and not df["Date"].empty:
                        date_range = f"({df['Date'].min().date()} → {df['Date'].max().date()})"
                    else:
                        date_range = ""
                    st.caption(f"✓ {well}: {len(df)} records {date_range}")

        _html(f'<hr style="border-color:{C["border"]};margin:8px 0">')

        # ── Navigation ─────────────────────────────────────────────
        _html(f'<div style="color:{C["sidebar_muted"]};font-size:0.72rem;'
              f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px">'
              f'Navigation</div>')
        pages = [
            ("🏠", "Dashboard Overview"),
            ("📋", "Production Data"),
            ("📉", "Decline Curve Analysis (DCA)"),
            ("🔮", "EUR Prediction"),
            ("⚙️", "Model Settings"),
            ("💡", "Field Insights"),
            ("📤", "Reports & Export"),
            ("🤖", "AI Interaction Log"),
        ]
        if "page" not in st.session_state or \
           st.session_state.page not in [p[1] for p in pages]:
            st.session_state.page = pages[0][1]

        for i, (icon, label) in enumerate(pages):
            is_active = st.session_state.page == label
            if st.button(f"{icon}  {label}", key=f"nav_{i}", use_container_width=True):
                st.session_state.page = label

        _html(f'<hr style="border-color:{C["border"]};margin:8px 0">')

        # ── Filters ────────────────────────────────────────────────
        with st.expander("FILTERS", expanded=True):
            st.markdown("**Date Range**")
            all_dfs = list(st.session_state.wells.values())
            if all_dfs:
                min_d = min(df["Date"].min() for df in all_dfs).to_pydatetime()
                max_d = max(df["Date"].max() for df in all_dfs).to_pydatetime()
                st.slider("", min_value=min_d, max_value=max_d,
                          value=(min_d, max_d), format="YYYY-MM", key="date_filter")
            st.markdown("**Production Phase**")
            fc1, fc2, fc3 = st.columns(3)
            with fc1: st.checkbox("Oil",   True, key="f_oil")
            with fc2: st.checkbox("Gas",   True, key="f_gas")
            with fc3: st.checkbox("Water", True, key="f_water")
            st.selectbox("Rate Type", ["Daily Rates","Monthly Avg","Yearly Avg"],
                         key="rate_type")
            st.session_state.settings["smooth"] = st.toggle(
                "Smoothing", value=st.session_state.settings.get("smooth", True),
                key="smooth_tog",
            )

        # ── Status bar ────────────────────────────────────────────
        n_analyzed = len(st.session_state.dca_results)
        if n_analyzed:
            _html(f"""
            <div class="status-bar">
              ✅ {n_analyzed} well(s) analysed &nbsp;|&nbsp;
              {len(st.session_state.eur_results)} EUR calc(s)
            </div>""")

# ─────────────────────────────────────────────────────────────────────────────
# 16. TOP BAR
# ─────────────────────────────────────────────────────────────────────────────

def render_top_bar():
    C      = get_C()
    n_sel  = len(st.session_state.selected)
    field  = st.session_state.field_name
    dot_c  = C["green"] if st.session_state.data_uploaded else C["red"]
    status = "Data Loaded" if st.session_state.data_uploaded else "Data Not Loaded"
    theme  = st.session_state.get("theme", "Dark")
    _html(f"""
    <div class="top-bar">
      <div style="display:flex;align-items:center;gap:16px">
        <div>
          <span class="top-bar-title">Decline Curve Analysis Estimator</span>
          <span class="top-bar-sub">Field: {field} · {n_sel} Well{'s' if n_sel!=1 else ''} Selected</span>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:20px">
        <div style="display:flex;align-items:center;gap:6px">
          <div style="width:8px;height:8px;border-radius:50%;background:{dot_c}"></div>
          <span class="top-bar-label">{status}</span>
        </div>
        <span class="top-bar-label">Unit System: <b class="top-bar-value">Field Units</b></span>
        <span class="top-bar-label">Theme: <b class="top-bar-value">{theme}</b></span>
        <span class="top-bar-label">{datetime.now().strftime('%d %b %Y  %H:%M')}</span>
      </div>
    </div>
    """)

# ─────────────────────────────────────────────────────────────────────────────
# 17. MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _init_state()

    # ── Inject theme CSS on every render ──────────────────────────
    inject_css()

    # ── Auto-load sample data on first run ───────────────────────
    if not st.session_state.wells:
        try:
            import os
            sample_path = os.path.join(os.path.dirname(__file__), "sample_data.xlsx")
            if os.path.exists(sample_path):
                st.session_state.wells    = load_excel_production(sample_path)
                st.session_state.selected = list(st.session_state.wells.keys())[:3]
        except Exception:
            pass

    render_sidebar()

    # ── Main content ──────────────────────────────────────────────
    render_top_bar()

    page = st.session_state.page
    if page == "Dashboard Overview":
        page_dashboard()
    elif page == "Production Data":
        page_production_data()
    elif page == "Decline Curve Analysis (DCA)":
        page_dca()
    elif page == "EUR Prediction":
        page_eur()
    elif page == "Model Settings":
        page_model_settings()
    elif page == "Field Insights":
        page_insights()
    elif page == "Reports & Export":
        page_reports()
    elif page == "AI Interaction Log":
        page_ai_log()

    # ── Footer ────────────────────────────────────────────────────
    C = get_C()
    _html(f"""
    <div class="app-footer">
      <span>PetroDCA – Production Analytics &nbsp;|&nbsp; Sample Field Dataset</span>
      <span>Unit System: Field Units &nbsp;|&nbsp;
            Sm³→STB ×6.2898 &nbsp;|&nbsp; Sm³→Mscf ×0.0353</span>
    </div>
    """)

if __name__ == "__main__":
    main()