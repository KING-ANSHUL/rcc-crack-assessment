"""
RCC Crack Risk Assessment System — Final Year Project
IS 456:2000 · IS 13920:2016 · IS 1893:2016 · ACI 318-19
Delhi Technological University | B.Tech Civil Engineering | 2025–26
"""

import streamlit as st
import os
import sys
import json
import shutil
from PIL import Image
import io

# Portable path resolution — works as PyInstaller EXE, in dev, and on Streamlit Cloud
_FROZEN = getattr(sys, 'frozen', False)
# _SRC: read-only bundled / repo assets (samples, kaggle_data, batch_test_results)
_SRC    = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
# _DATA: writable folder — next to .exe when frozen, /tmp/rcc_data on cloud/Linux, project dir on Windows dev
if _FROZEN:
    _DATA = os.path.dirname(sys.executable)
elif os.name != 'nt':          # Linux / macOS (Streamlit Cloud runs on Linux)
    _DATA = "/tmp/rcc_data"
else:                           # Windows dev machine
    _DATA = os.path.dirname(os.path.abspath(__file__))

from image_processor import process_image
from risk_engine import (
    full_assessment, compute_fri, probable_mechanism,
    MEMBER_TYPES, ORIENTATIONS, DISTANCES, ACTIVITIES,
    IMPORTANCES, EXPOSURE_CLASSES, CONCRETE_GRADES_LIST,
    SEISMIC_ZONES, JOINT_TYPES, WEIGHTS,
    IS456_CRACK_WIDTH_LIMIT,
    member_multiplier,
)
from datetime import datetime
import pandas as pd
from pdf_report import build_pdf


# ── Theme CSS builder ─────────────────────────────────────────────────────────
def _build_css(dark: bool) -> str:
    """Return the full <style> block for dark or light mode."""
    if dark:
        bg   = "#0e1117"; surf  = "#0d1525"; surf2 = "#141c25"
        deep = "#0a1628"; inp   = "#0f172a"; tab_a = "#0f1f3d"
        brd  = "#1e293b"; brd2  = "#1e2a3a"
        txt  = "#cbd5e1"; txt2  = "#94a3b8"; txt3  = "#64748b"; txt4 = "#475569"
        hdg  = "#f1f5f9"; acc   = "#4A7FA5"; acc_b = "#7aafc7"
        sbbg = "#0d1117"; sc_t  = "#0d1117"; sc_th = "#2d3f50"
        bpb  = "#1d4ed8"; bsb   = "#0d1525"; bsbr  = "#2d3748"; bst  = "#94a3b8"
        bdb  = "#0d2960"; bdbr  = "#1d4ed8"; bdt   = "#93c5fd"
        upbg = "#0d1525"; upbr  = "#2d3748"
        albg = "#0a1628"; albr  = "#1d4ed8"
        tbg  = "#0d1525"; thbg  = "#0f1f3d"; tht   = "#7aafc7"
        ttd  = "#94a3b8"; ttdb  = "#111827"; ttr   = "#0f1f3d"
        gbg  = "#1e293b"; ebg   = "#0d1525"; ebr   = "#1e3a5f"; et = "#334155"
        cbg  = "#0a1628"; wbg   = "#1a0e00"; xbg   = "#1a0000"
        tact = "#4A7FA5"; tcol  = "#64748b"
    else:
        bg   = "#FFFFFF"; surf  = "#F8FAFC"; surf2 = "#EFF6FF"
        deep = "#EFF6FF"; inp   = "#FFFFFF"; tab_a = "#EFF6FF"
        brd  = "#E2E8F0"; brd2  = "#E2E8F0"
        txt  = "#334155"; txt2  = "#475569"; txt3  = "#64748B"; txt4 = "#94A3B8"
        hdg  = "#0F172A"; acc   = "#2563EB"; acc_b = "#2563EB"
        sbbg = "#F1F5F9"; sc_t  = "#F1F5F9"; sc_th = "#CBD5E1"
        bpb  = "#2563EB"; bsb   = "#F8FAFC"; bsbr  = "#E2E8F0"; bst  = "#475569"
        bdb  = "#EFF6FF"; bdbr  = "#3B82F6"; bdt   = "#1D4ED8"
        upbg = "#F8FAFC"; upbr  = "#CBD5E1"
        albg = "#EFF6FF"; albr  = "#3B82F6"
        tbg  = "#F8FAFC"; thbg  = "#EFF6FF"; tht   = "#2563EB"
        ttd  = "#475569"; ttdb  = "#F1F5F9"; ttr   = "#EFF6FF"
        gbg  = "#E2E8F0"; ebg   = "#F8FAFC"; ebr   = "#BFDBFE"; et = "#94A3B8"
        cbg  = "#EFF6FF"; wbg   = "#FFF7ED"; xbg   = "#FFF1F2"
        tact = "#2563EB"; tcol  = "#64748B"

    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  html, body, [data-testid="stAppViewContainer"],
  [data-testid="stMain"], .main, .block-container {{
    background: {bg} !important;
    font-family: 'Inter', sans-serif !important;
  }}
  .block-container {{ padding-top: 1.5rem !important; }}

  [data-testid="stMain"] p, [data-testid="stMain"] span,
  [data-testid="stMain"] label, [data-testid="stMain"] div,
  [data-testid="stMain"] li, [data-testid="stMain"] td,
  [data-testid="stMain"] th,
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] li {{ color: {txt} !important; }}

  [data-testid="stMain"] h1, [data-testid="stMain"] h2,
  [data-testid="stMain"] h3 {{ color: {hdg} !important; }}

  [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ background: {sbbg} !important; }}
  [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] small,
  [data-testid="stSidebar"] .stMarkdown {{ color: {txt2} !important; }}
  [data-testid="stSidebar"] h3 {{ color: {hdg} !important; font-size: 0.88rem; letter-spacing: .06em; text-transform: uppercase; }}
  [data-testid="stSidebar"] [data-baseweb="select"] > div {{ background: {inp} !important; border-color: {brd} !important; color: {hdg} !important; }}
  [data-testid="stSidebar"] hr {{ border-color: {brd2} !important; }}
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ color: {txt3} !important; }}

  [data-testid="stRadio"] label, [data-testid="stRadio"] p, [data-testid="stRadio"] span,
  [data-testid="stFileUploader"] label, [data-testid="stNumberInput"] label,
  [data-testid="stSlider"] label, [data-testid="stSelectbox"] label,
  [data-testid="stTextArea"] label, [data-testid="stWidgetLabel"],
  [data-testid="stWidgetLabel"] p {{ color: {txt2} !important; font-size: 0.82rem !important; }}

  [data-baseweb="input"] input, [data-baseweb="select"] input,
  [data-baseweb="textarea"] textarea {{ background: {inp} !important; color: {hdg} !important; border-color: {brd} !important; }}
  [data-baseweb="select"] > div {{ background: {inp} !important; border-color: {brd} !important; color: {hdg} !important; }}
  [data-baseweb="popover"] ul {{ background: {inp} !important; }}
  [data-baseweb="popover"] li {{ color: {txt} !important; }}
  [data-baseweb="popover"] li:hover {{ background: {surf} !important; }}
  [data-testid="stNumberInput"] input {{ background: {inp} !important; color: {hdg} !important; }}

  [data-testid="stSlider"] [data-baseweb="slider"] div {{ background: {brd} !important; }}
  [data-testid="stCaptionContainer"] p {{ color: {txt3} !important; font-size: 0.78rem !important; }}

  [data-testid="stTabs"] {{ border-bottom: 1px solid {brd} !important; }}
  [data-testid="stTabs"] button {{
    background: transparent !important; color: {tcol} !important;
    font-weight: 600 !important; font-size: 0.82rem !important; letter-spacing: .03em !important;
  }}
  [data-testid="stTabs"] button p {{ color: {tcol} !important; }}
  [data-testid="stTabs"] button[aria-selected="true"] {{ background: {tab_a} !important; border-bottom: 2px solid {tact} !important; }}
  [data-testid="stTabs"] button[aria-selected="true"] p {{ color: {acc_b} !important; font-weight: 700 !important; }}

  [data-testid="stExpander"] {{ background: {surf} !important; border: 1px solid {brd} !important; border-radius: 4px !important; }}
  [data-testid="stExpander"] summary {{ color: {txt2} !important; }}
  [data-testid="stExpander"] summary p {{ color: {txt2} !important; }}

  [data-testid="stDataFrame"] {{ background: {tbg} !important; border-radius: 4px !important; }}
  [data-testid="stDataFrame"] th {{ background: {thbg} !important; color: {tht} !important; }}
  [data-testid="stDataFrame"] td {{ color: {txt} !important; background: {tbg} !important; }}

  div[data-testid="stImage"] img {{ border-radius: 4px; border: 1px solid {brd}; }}

  .card {{
    background: {surf}; border: 1px solid {brd};
    border-radius: 4px; padding: 16px 18px; margin-bottom: 12px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
  }}
  .card * {{ color: {txt} !important; }}
  .card-title {{
    font-size: 0.78rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: {acc} !important;
    margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
  }}

  .risk-banner {{ border-radius: 4px; padding: 18px 24px; text-align: center; margin-bottom: 14px; }}
  .risk-Low      {{ background: #052e16; border: 1px solid #16a34a; }}
  .risk-Moderate {{ background: #1c1400; border: 1px solid #ca8a04; }}
  .risk-High     {{ background: #1c0a00; border: 1px solid #ea580c; }}
  .risk-Critical {{ background: #1a0000; border: 1px solid #dc2626; }}

  .badge {{ display: inline-block; padding: 5px 20px; border-radius: 2px; font-weight: 800; font-size: 0.9rem; letter-spacing: 1px; }}
  .badge-Low      {{ background: #14532d; color: #4ade80 !important; border: 1px solid #16a34a; }}
  .badge-Moderate {{ background: #422006; color: #fbbf24 !important; border: 1px solid #ca8a04; }}
  .badge-High     {{ background: #431407; color: #fb923c !important; border: 1px solid #ea580c; }}
  .badge-Critical {{ background: #450a0a; color: #f87171 !important; border: 1px solid #dc2626; }}

  .code-ref {{ background: {cbg}; border-left: 3px solid {acc}; padding: 9px 13px; border-radius: 0 4px 4px 0; font-size: 0.79rem; margin: 6px 0; }}
  .code-ref * {{ color: {acc_b} !important; }}
  .warn-box {{ background: {wbg}; border-left: 3px solid #f97316; padding: 9px 13px; border-radius: 0 8px 8px 0; font-size: 0.79rem; margin: 6px 0; }}
  .warn-box * {{ color: #fdba74 !important; }}
  .crit-box {{ background: {xbg}; border-left: 3px solid #ef4444; padding: 9px 13px; border-radius: 0 4px 4px 0; font-size: 0.79rem; margin: 6px 0; }}
  .crit-box * {{ color: #fca5a5 !important; }}

  .gauge-wrap {{ margin-bottom: 11px; }}
  .gauge-label {{ display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 4px; }}
  .gauge-label * {{ color: {txt} !important; }}
  .gauge-bar-bg {{ background: {gbg}; border-radius: 6px; height: 10px; overflow: hidden; }}
  .gauge-note {{ font-size: 0.71rem; color: {txt4} !important; margin-top: 3px; }}

  .metric-card {{ background: {surf}; border: 1px solid {brd}; border-radius: 4px; padding: 16px 18px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
  .metric-card .m-label {{ font-size: 0.70rem; text-transform: uppercase; letter-spacing: .08em; color: {txt4} !important; margin-bottom: 6px; }}
  .metric-card .m-value {{ font-size: 1.8rem; font-weight: 800; color: {acc_b} !important; line-height: 1; }}
  .metric-card .m-sub   {{ font-size: 0.72rem; color: {txt4} !important; margin-top: 4px; }}

  .empty-state {{ background: {ebg}; border: 1px dashed {ebr}; border-radius: 4px; padding: 48px 20px; text-align: center; }}
  .empty-state .icon {{ font-size: 2.8rem; }}
  .empty-state p {{ color: {et} !important; font-size: 0.88rem; margin-top: 10px; }}

  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: {sc_t}; }}
  ::-webkit-scrollbar-thumb {{ background: {sc_th}; border-radius: 3px; }}

  [data-testid="stButton"] button[kind="primary"] {{
    background: {bpb} !important; border: none !important; color: white !important;
    font-weight: 700 !important; border-radius: 4px !important; letter-spacing: .03em !important; transition: all 0.2s ease !important;
  }}
  [data-testid="stButton"] button[kind="primary"]:hover {{ background: #2563eb !important; transform: translateY(-1px) !important; }}
  [data-testid="stButton"] button[kind="secondary"] {{
    background: {bsb} !important; border: 1px solid {bsbr} !important; color: {bst} !important; border-radius: 4px !important;
  }}
  [data-testid="stDownloadButton"] button {{
    background: {bdb} !important; border: 1px solid {bdbr} !important; color: {bdt} !important; border-radius: 4px !important; font-weight: 600 !important;
  }}
  [data-testid="stFileUploader"] section {{
    background: {upbg} !important; border: 1px dashed {upbr} !important; border-radius: 4px !important;
  }}
  [data-testid="stAlert"] {{ border-radius: 4px !important; }}
  div[data-testid="stAlert"][data-baseweb="notification"] {{ background: {albg} !important; border-color: {albr} !important; }}

  table {{ background: {tbg} !important; border-collapse: collapse; width: 100%; }}
  th {{ background: {thbg} !important; color: {tht} !important; font-size: 0.78rem !important; padding: 8px 12px !important; border-bottom: 1px solid {brd} !important; }}
  td {{ color: {ttd} !important; font-size: 0.78rem !important; padding: 7px 12px !important; border-bottom: 1px solid {ttdb} !important; }}
  tr:hover td {{ background: {ttr} !important; }}
</style>
"""


# ── Persistent history helpers ────────────────────────────────────────────────
HISTORY_DIR  = os.path.join(_DATA, "history")
HISTORY_JSON = os.path.join(HISTORY_DIR, "history.json")
os.makedirs(HISTORY_DIR, exist_ok=True)


def _load_history_from_disk() -> list:
    if not os.path.exists(HISTORY_JSON):
        return []
    try:
        with open(HISTORY_JSON, "r", encoding="utf-8") as f:
            records = json.load(f)
        # Re-attach image bytes from saved files
        for rec in records:
            for key in ("original_bytes", "overlay_bytes"):
                path = rec.get(f"{key}_path")
                if path and os.path.exists(path):
                    with open(path, "rb") as fimg:
                        rec[key] = fimg.read()
                else:
                    rec[key] = None
        return records
    except Exception:
        return []


def _save_history_to_disk(history: list):
    serialisable = []
    for rec in history:
        row = {k: v for k, v in rec.items()
               if k not in ("original_bytes", "overlay_bytes", "result")}
        serialisable.append(row)
    with open(HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(serialisable, f, indent=2)


def _save_assessment(rec: dict):
    """Write one new assessment record to disk (images + updated JSON)."""
    uid = rec["uid"]
    img_dir = os.path.join(HISTORY_DIR, uid)
    os.makedirs(img_dir, exist_ok=True)

    for key in ("original_bytes", "overlay_bytes"):
        data = rec.get(key)
        if data:
            path = os.path.join(img_dir, f"{key}.jpg")
            with open(path, "wb") as f:
                f.write(data)
            rec[f"{key}_path"] = path

    # Re-save full JSON
    history = st.session_state.get("history", [])
    _save_history_to_disk(history)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RCC Crack Risk Assessor — DTU",
    page_icon="🏗️",
    layout="wide",
)

# ── Session state init (must come before CSS so dark_mode is available) ───────
if "history" not in st.session_state:
    st.session_state["history"] = _load_history_from_disk()
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = True

# ── CSS — theme-aware ─────────────────────────────────────────────────────────
st.markdown(_build_css(st.session_state["dark_mode"]), unsafe_allow_html=True)

# ── (CSS content moved to _build_css() function above) ────────────────────────
_DEAD_CSS_PLACEHOLDER = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  /* ── Global dark background ── */
  html, body, [data-testid="stAppViewContainer"],
  [data-testid="stMain"], .main, .block-container {
    background: #0e1117 !important;
    font-family: 'Inter', sans-serif !important;
  }
  .block-container { padding-top: 1.5rem !important; }

  /* ── All text light by default ── */
  [data-testid="stMain"] p,
  [data-testid="stMain"] span,
  [data-testid="stMain"] label,
  [data-testid="stMain"] div,
  [data-testid="stMain"] li,
  [data-testid="stMain"] td,
  [data-testid="stMain"] th,
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] li { color: #cbd5e1 !important; }

  /* headings */
  [data-testid="stMain"] h1,
  [data-testid="stMain"] h2,
  [data-testid="stMain"] h3 { color: #f1f5f9 !important; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"],
  [data-testid="stSidebar"] > div { background: #0d1117 !important; }
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] small,
  [data-testid="stSidebar"] .stMarkdown { color: #94a3b8 !important; }
  [data-testid="stSidebar"] h3 { color: #e2e8f0 !important; font-size: 0.88rem; letter-spacing: .06em; text-transform: uppercase; }
  [data-testid="stSidebar"] [data-baseweb="select"] > div { background: #161b27 !important; border-color: #2d3748 !important; color: #e2e8f0 !important; }
  [data-testid="stSidebar"] hr { border-color: #1e2a3a !important; }
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #64748b !important; }

  /* ── Streamlit widget labels in main area ── */
  [data-testid="stRadio"] label,
  [data-testid="stRadio"] p,
  [data-testid="stRadio"] span,
  [data-testid="stFileUploader"] label,
  [data-testid="stNumberInput"] label,
  [data-testid="stSlider"] label,
  [data-testid="stSelectbox"] label,
  [data-testid="stTextArea"] label,
  [data-testid="stWidgetLabel"],
  [data-testid="stWidgetLabel"] p { color: #94a3b8 !important; font-size: 0.82rem !important; }

  /* Input boxes */
  [data-baseweb="input"] input,
  [data-baseweb="select"] input,
  [data-baseweb="textarea"] textarea { background: #0f172a !important; color: #e2e8f0 !important; border-color: #2d3748 !important; }
  [data-baseweb="select"] > div { background: #0f172a !important; border-color: #2d3748 !important; color: #e2e8f0 !important; }
  [data-baseweb="popover"] ul { background: #0f172a !important; }
  [data-baseweb="popover"] li { color: #cbd5e1 !important; }
  [data-baseweb="popover"] li:hover { background: #1e293b !important; }
  [data-testid="stNumberInput"] input { background: #0f172a !important; color: #e2e8f0 !important; }

  /* Slider */
  [data-testid="stSlider"] [data-baseweb="slider"] div { background: #1e293b !important; }

  /* Caption */
  [data-testid="stCaptionContainer"] p { color: #64748b !important; font-size: 0.78rem !important; }

  /* ── Tabs ── */
  [data-testid="stTabs"] { border-bottom: 1px solid #1e293b !important; }
  [data-testid="stTabs"] button {
    background: transparent !important;
    color: #64748b !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: .03em !important;
  }
  [data-testid="stTabs"] button p { color: #64748b !important; }
  [data-testid="stTabs"] button[aria-selected="true"] { background: #0f1f3d !important; border-bottom: 2px solid #4A7FA5 !important; }
  [data-testid="stTabs"] button[aria-selected="true"] p { color: #7aafc7 !important; font-weight: 700 !important; }

  /* ── Expanders ── */
  [data-testid="stExpander"] { background: #0d1525 !important; border: 1px solid #1e293b !important; border-radius: 4px !important; }
  [data-testid="stExpander"] summary { color: #94a3b8 !important; }
  [data-testid="stExpander"] summary p { color: #94a3b8 !important; }

  /* ── Dataframe / table ── */
  [data-testid="stDataFrame"] { background: #0d1525 !important; border-radius: 4px !important; }
  [data-testid="stDataFrame"] th { background: #0f1f3d !important; color: #7aafc7 !important; }
  [data-testid="stDataFrame"] td { color: #cbd5e1 !important; background: #0d1525 !important; }

  /* ── Images ── */
  div[data-testid="stImage"] img { border-radius: 4px; border: 1px solid #1e293b; }

  /* ═══════════════════════════════════════════════════
     CUSTOM COMPONENTS
  ═══════════════════════════════════════════════════ */

  /* Glass card */
  .card {
    background: #0d1525;
    border: 1px solid #1e293b;
    border-radius: 4px; padding: 16px 18px; margin-bottom: 12px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  }
  .card * { color: #cbd5e1 !important; }
  .card-title {
    font-size: 0.78rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: #4A7FA5 !important;
    margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
  }

  /* Risk banners */
  .risk-banner {
    border-radius: 4px; padding: 18px 24px;
    text-align: center; margin-bottom: 14px;
  }
  .risk-Low {
    background: #052e16;
    border: 1px solid #16a34a;
  }
  .risk-Moderate {
    background: #1c1400;
    border: 1px solid #ca8a04;
  }
  .risk-High {
    background: #1c0a00;
    border: 1px solid #ea580c;
  }
  .risk-Critical {
    background: #1a0000;
    border: 1px solid #dc2626;
  }

  /* Badges */
  .badge {
    display: inline-block; padding: 5px 20px; border-radius: 2px;
    font-weight: 800; font-size: 0.9rem; letter-spacing: 1px;
  }
  .badge-Low      { background: #14532d; color: #4ade80 !important; border: 1px solid #16a34a; }
  .badge-Moderate { background: #422006; color: #fbbf24 !important; border: 1px solid #ca8a04; }
  .badge-High     { background: #431407; color: #fb923c !important; border: 1px solid #ea580c; }
  .badge-Critical { background: #450a0a; color: #f87171 !important; border: 1px solid #dc2626; }

  /* Code / IS ref box */
  .code-ref {
    background: #0a1628; border-left: 3px solid #4A7FA5;
    padding: 9px 13px; border-radius: 0 4px 4px 0;
    font-size: 0.79rem; margin: 6px 0;
  }
  .code-ref * { color: #93c5fd !important; }

  /* Warning box */
  .warn-box {
    background: #1a0e00; border-left: 3px solid #f97316;
    padding: 9px 13px; border-radius: 0 8px 8px 0; font-size: 0.79rem; margin: 6px 0;
  }
  .warn-box * { color: #fdba74 !important; }

  /* Critical box */
  .crit-box {
    background: #1a0000; border-left: 3px solid #ef4444;
    padding: 9px 13px; border-radius: 0 4px 4px 0; font-size: 0.79rem; margin: 6px 0;
  }
  .crit-box * { color: #fca5a5 !important; }

  /* Gauge bars */
  .gauge-wrap { margin-bottom: 11px; }
  .gauge-label { display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 4px; }
  .gauge-label * { color: #cbd5e1 !important; }
  .gauge-bar-bg { background: #1e293b; border-radius: 6px; height: 10px; overflow: hidden; }
  .gauge-note { font-size: 0.71rem; color: #475569 !important; margin-top: 3px; }

  /* Stat metric card */
  .metric-card {
    background: #0d1525; border: 1px solid #1e293b;
    border-radius: 4px; padding: 16px 18px; text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  }
  .metric-card .m-label { font-size: 0.70rem; text-transform: uppercase;
    letter-spacing: .08em; color: #475569 !important; margin-bottom: 6px; }
  .metric-card .m-value { font-size: 1.8rem; font-weight: 800; color: #7aafc7 !important; line-height: 1; }
  .metric-card .m-sub   { font-size: 0.72rem; color: #475569 !important; margin-top: 4px; }

  /* Empty state placeholder */
  .empty-state {
    background: #0d1525; border: 1px dashed #1e3a5f;
    border-radius: 4px; padding: 48px 20px; text-align: center;
  }
  .empty-state .icon { font-size: 2.8rem; }
  .empty-state p { color: #334155 !important; font-size: 0.88rem; margin-top: 10px; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0d1117; }
  ::-webkit-scrollbar-thumb { background: #2d3f50; border-radius: 3px; }

  /* Buttons */
  [data-testid="stButton"] button[kind="primary"] {
    background: #1d4ed8 !important;
    border: none !important; color: white !important; font-weight: 700 !important;
    border-radius: 4px !important; letter-spacing: .03em !important;
    transition: all 0.2s ease !important;
  }
  [data-testid="stButton"] button[kind="primary"]:hover {
    background: #2563eb !important;
    transform: translateY(-1px) !important;
  }
  [data-testid="stButton"] button[kind="secondary"] {
    background: #0d1525 !important; border: 1px solid #2d3748 !important;
    color: #94a3b8 !important; border-radius: 4px !important;
  }

  /* Download button */
  [data-testid="stDownloadButton"] button {
    background: #0d2960 !important; border: 1px solid #1d4ed8 !important;
    color: #93c5fd !important; border-radius: 4px !important;
    font-weight: 600 !important;
  }

  /* File uploader */
  [data-testid="stFileUploader"] section {
    background: #0d1525 !important; border: 1px dashed #2d3748 !important;
    border-radius: 4px !important;
  }

  /* Info / success / warning / error boxes */
  [data-testid="stAlert"] { border-radius: 4px !important; }
  div[data-testid="stAlert"][data-baseweb="notification"] {
    background: #0a1628 !important; border-color: #1d4ed8 !important;
  }

  /* Table (st.table) */
  table { background: #0d1525 !important; border-collapse: collapse; width: 100%; }
  th { background: #0f1f3d !important; color: #7aafc7 !important; font-size: 0.78rem !important;
       padding: 8px 12px !important; border-bottom: 1px solid #1e293b !important; }
  td { color: #94a3b8 !important; font-size: 0.78rem !important;
       padding: 7px 12px !important; border-bottom: 1px solid #111827 !important; }
  tr:hover td { background: #0f1f3d !important; }
</style>
"""  # end _DEAD_CSS_PLACEHOLDER (not rendered — kept for reference only)

# ── Sidebar — Theme toggle + Structural Parameters ───────────────────────────
with st.sidebar:
    # ── Theme toggle ──────────────────────────────────────────────────────────
    st.toggle("🌙  Dark Mode", value=True, key="dark_mode")
    st.markdown("---")

    st.markdown("### SITE INFORMATION")
    site_name     = st.text_input("Building / Site Name", value="DTU Civil Block")
    inspector     = st.text_input("Inspector Name", value="")
    inspection_dt = st.date_input("Inspection Date", value=datetime.today())

    st.markdown("---")
    st.markdown("### STRUCTURAL PARAMETERS")
    st.caption("Applied to all IS code calculations")

    concrete_grade = st.selectbox("Concrete Grade", CONCRETE_GRADES_LIST,
                                   index=CONCRETE_GRADES_LIST.index("M25"))
    exposure       = st.selectbox("Exposure Class (IS 456 Table 3)", EXPOSURE_CLASSES,
                                   index=EXPOSURE_CLASSES.index("Moderate"))
    seismic_zone   = st.selectbox("Seismic Zone (IS 1893:2016)", SEISMIC_ZONES,
                                   index=SEISMIC_ZONES.index("Zone IV"))
    joint_type     = st.selectbox("Joint Type (IS 13920)", JOINT_TYPES)

    perm_w = IS456_CRACK_WIDTH_LIMIT[exposure]

    st.markdown(f"""
    <div style="background:#0a1628;border:1px solid #1e3a6e;border-radius:4px;padding:14px 16px;margin-top:8px;font-size:.80rem;">
      <div style="color:#7aafc7;font-weight:700;font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px;">IS 456:2000 Cl. 35.3.2</div>
      <div style="color:#94a3b8;">Permissible crack width</div>
      <div style="font-size:1.6rem;font-weight:800;color:#34d399;line-height:1.2;">{perm_w} <span style="font-size:.85rem;color:#64748b;">mm</span></div>
      <div style="font-size:.72rem;color:#475569;margin-bottom:10px;">Exposure: {exposure}</div>
      <hr style="border:none;border-top:1px solid #1e293b;margin:8px 0;">
      <div style="color:#7aafc7;font-weight:700;font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;">IS 13920 Multipliers</div>
      <div style="display:flex;justify-content:space-between;color:#94a3b8;font-size:.78rem;">
        <span>Beam</span><span style="color:#e2e8f0;font-weight:600;">{member_multiplier('Beam', seismic_zone)}×</span>
      </div>
      <div style="display:flex;justify-content:space-between;color:#94a3b8;font-size:.78rem;">
        <span>Column</span><span style="color:#fbbf24;font-weight:600;">{member_multiplier('Column', seismic_zone)}×</span>
      </div>
      <div style="display:flex;justify-content:space-between;color:#94a3b8;font-size:.78rem;">
        <span>B-C Joint</span><span style="color:#f87171;font-weight:600;">{member_multiplier('Beam-Column Joint', seismic_zone)}×</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### FRAME RISK INDEX")
    st.caption("Paste MRI values (one per line) for a full frame assessment")
    fri_text = st.text_area("MRI values", placeholder="0.44\n0.79\n0.32", height=80,
                             label_visibility="collapsed")
    if st.button("Compute FRI", use_container_width=True):
        try:
            vals = [float(x.strip()) for x in fri_text.strip().splitlines() if x.strip()]
            if vals:
                fr = compute_fri(vals)
                lvl = fr["risk_level"]
                st.markdown(f"""
                <div style="background:#0a1628;border:1px solid #1e3a6e;border-radius:4px;padding:12px 14px;font-size:.80rem;">
                  <div style="color:#7aafc7;font-size:.70rem;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;">Frame Risk Index</div>
                  <div style="font-size:1.8rem;font-weight:800;color:#f1f5f9;line-height:1;">FRI = {fr['fri']}</div>
                  <div style="color:#64748b;font-size:.74rem;margin-top:4px;">C_cluster = {fr['c_cluster']} &nbsp;|&nbsp; High-risk: {fr['n_high']}/{len(vals)}</div>
                  <div style="margin-top:8px;"><span class="badge badge-{lvl}">{lvl.upper()}</span></div>
                </div>
                """, unsafe_allow_html=True)
        except ValueError:
            st.error("Enter numeric values only")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-left:4px solid #4A7FA5;padding:16px 20px;margin-bottom:20px;background:#141c25;border-top:1px solid #1e2d3d;border-right:1px solid #1e2d3d;border-bottom:1px solid #1e2d3d;">
  <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:.12em;color:#4A7FA5;margin-bottom:4px;">STRUCTURAL ASSESSMENT SYSTEM</div>
  <div style="font-size:1.2rem;font-weight:700;color:#e2e8f0;letter-spacing:.02em;">RCC Crack Risk Assessment</div>
  <div style="font-size:0.72rem;color:#64748b;margin-top:4px;">IS 456:2000 · IS 13920:2016 · IS 1893:2016 · ACI 318-19 &nbsp;|&nbsp; Delhi Technological University · Civil Engineering · 2025–26</div>
</div>
""", unsafe_allow_html=True)

# ── Main Tabs ─────────────────────────────────────────────────────────────────
tab_assess, tab_history, tab_batch, tab_annexa, tab_demo, tab_valid, tab_about = st.tabs([
    "ASSESS", "HISTORY", "BULK TEST",
    "ANNEXURE A", "DEMO", "VALIDATION", "ABOUT"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MAIN ASSESSMENT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_assess:

    # ── Top KPI bar ──────────────────────────────────────────────────────────
    n_sess = len(st.session_state.get("history", []))
    last_r = st.session_state.get("last_result")
    k1, k2, k3, k4, k5 = st.columns(5, gap="small")
    kpi_data = [
        (k1, "Site", site_name, "#7aafc7"),
        (k2, "Assessments", str(n_sess), "#a78bfa"),
        (k3, "IS 456 Limit", f"{IS456_CRACK_WIDTH_LIMIT[exposure]} mm", "#34d399"),
        (k4, "Last CRI", f"{last_r['cri']}" if last_r else "—", "#f59e0b"),
        (k5, "Last Risk", last_r["risk_level"] if last_r else "—",
         {"Low":"#4ade80","Moderate":"#fbbf24","High":"#fb923c","Critical":"#f87171"}.get(
             last_r["risk_level"] if last_r else "", "#64748b")),
    ]
    for col, lbl, val, clr in kpi_data:
        with col:
            st.markdown(f"""
            <div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;
                        padding:12px 14px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.3);">
              <div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:.08em;
                          color:#475569;margin-bottom:4px;">{lbl}</div>
              <div style="font-size:1.0rem;font-weight:800;color:{clr};
                          overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.05, 1.1, 1.35], gap="medium")

    # ── Column 1: Image ───────────────────────────────────────────────────────
    with c1:
        st.markdown('<div class="card-title">CRACK PHOTO</div>', unsafe_allow_html=True)
        input_mode = st.radio("Input method",
            ["📁 Upload Image", "📸 Take Photo (Camera)"],
            horizontal=True, label_visibility="collapsed")

        raw = None
        img_result = None

        if input_mode == "📁 Upload Image":
            uploaded = st.file_uploader("Upload JPG / PNG", type=["jpg","jpeg","png"],
                                         label_visibility="collapsed")
            if uploaded:
                raw = uploaded.read()
        else:
            st.caption("Point camera at the crack and click the shutter button.")
            camera_shot = st.camera_input("Take a photo", label_visibility="collapsed")
            if camera_shot:
                raw = camera_shot.read()

        if raw:
            with st.spinner("Analysing image..."):
                try:
                    img_result = process_image(raw)
                except Exception as e:
                    st.error(f"Image error: {e}")

            if img_result:
                t1, t2 = st.tabs(["Original", "Crack Overlay"])
                with t1:
                    st.image(raw, use_container_width=True)
                with t2:
                    st.image(img_result["overlay_bytes"], use_container_width=True)

                status_clr = "#4ade80" if img_result["crack_detected"] else "#f59e0b"
                status_txt = "Crack Detected" if img_result["crack_detected"] else "No crack — fill manually"
                conf_pct   = int(img_result["confidence"] * 100)
                conf_clr   = "#4ade80" if conf_pct >= 60 else "#f59e0b"

                st.markdown(f"""
                <div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;
                            padding:12px 14px;margin-top:10px;">
                  <div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:.08em;
                              color:#475569;margin-bottom:8px;">AI Detection</div>
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="width:8px;height:8px;background:{status_clr};
                                 border-radius:50%;display:inline-block;"></span>
                    <span style="color:{status_clr};font-weight:700;font-size:0.82rem;">{status_txt}</span>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.78rem;">
                    <div style="color:#475569;">Type</div>
                    <div style="color:#e2e8f0;font-weight:600;">{img_result['crack_type']}</div>
                    <div style="color:#475569;">Orientation</div>
                    <div style="color:#e2e8f0;font-weight:600;">{img_result['orientation']}</div>
                    <div style="color:#475569;">Width Class</div>
                    <div style="color:#e2e8f0;font-weight:600;">{img_result['width_class']}</div>
                    <div style="color:#475569;">Confidence</div>
                    <div style="color:{conf_clr};font-weight:700;">{conf_pct}%</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state">
              <div class="icon">📷</div>
              <p>Upload a photo or use the camera<br>
              <span style="color:#1e3a5f!important;font-size:0.75rem;">or try the Demo Images tab</span></p>
            </div>
            """, unsafe_allow_html=True)

    # ── Column 2: Context ─────────────────────────────────────────────────────
    with c2:
        st.markdown('<div class="card-title">STRUCTURAL CONTEXT</div>', unsafe_allow_html=True)
        member_type = st.selectbox("Member Type", MEMBER_TYPES, key="mt")

        perm_w  = IS456_CRACK_WIDTH_LIMIT[exposure]
        width_mm = st.number_input(
            f"Crack Width (mm) · IS 456 limit = {perm_w} mm",
            min_value=0.01, max_value=10.0, value=0.30, step=0.05, format="%.2f")
        depth_pct = st.slider("Crack Depth (% of section depth)", 0, 80, 20,
            help="ACI 318-19 Branson eq: >30% = significant stiffness loss")

        ai_ori  = img_result["orientation"] if img_result else ORIENTATIONS[0]
        ori_idx = ORIENTATIONS.index(ai_ori) if ai_ori in ORIENTATIONS else 0
        orientation = st.selectbox("Crack Orientation", ORIENTATIONS, index=ori_idx)
        distance    = st.selectbox("Distance from Support / Joint", DISTANCES)
        activity    = st.selectbox("Crack Activity Over Time", ACTIVITIES)
        importance  = st.selectbox("Member Importance", IMPORTANCES)

        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
        run = st.button("⚡ Compute Risk Assessment", type="primary", use_container_width=True)

    # ── Column 3: Dashboard Output ────────────────────────────────────────────
    with c3:
        if run:
            r = full_assessment(
                width_mm=width_mm, depth_pct=float(depth_pct),
                orientation=orientation, distance=distance,
                activity=activity, importance=importance,
                member_type=member_type, exposure=exposure,
                concrete_grade=concrete_grade, seismic_zone=seismic_zone,
                joint_type=joint_type,
            )
            inputs_snap = dict(
                width_mm=width_mm, depth_pct=depth_pct, orientation=orientation,
                distance=distance, activity=activity, importance=importance,
                member_type=member_type, exposure=exposure, concrete_grade=concrete_grade,
                seismic_zone=seismic_zone, joint_type=joint_type,
            )
            st.session_state["last_result"] = r
            st.session_state["last_inputs"] = inputs_snap

            _uid = datetime.now().strftime("%Y%m%d_%H%M%S_") + str(len(st.session_state["history"]) + 1)
            _rec = {
                "uid": _uid,
                "no": len(st.session_state["history"]) + 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "member": member_type, "width_mm": width_mm,
                "orientation": orientation, "cri": r["cri"], "mri": r["mri"],
                "risk": r["risk_level"], "mechanism": r["mechanism"]["mechanism"],
                "site": site_name, "inspector": inspector, "date": str(inspection_dt),
                "original_bytes": raw,
                "overlay_bytes": img_result["overlay_bytes"] if img_result else None,
                "crack_type": img_result["crack_type"] if img_result else "—",
                "confidence": img_result["confidence"] if img_result else None,
                "result": r,
                "inputs": inputs_snap,
            }
            st.session_state["history"].append(_rec)
            _save_assessment(_rec)

            level  = r["risk_level"]
            colour = r["colour"]
            mech   = r["mechanism"]

            RISK_COLORS = {
                "Low":      {"bg":"#052e16","border":"#16a34a","val":"#4ade80","glow":"rgba(74,222,128,0.2)"},
                "Moderate": {"bg":"#1c1400","border":"#ca8a04","val":"#fbbf24","glow":"rgba(251,191,36,0.2)"},
                "High":     {"bg":"#1c0a00","border":"#ea580c","val":"#fb923c","glow":"rgba(251,146,60,0.25)"},
                "Critical": {"bg":"#1a0000","border":"#dc2626","val":"#f87171","glow":"rgba(248,113,113,0.3)"},
            }
            rc = RISK_COLORS[level]

            if img_result and img_result.get("low_confidence"):
                conf = img_result["confidence"]
                st.warning(f"⚠️ Low Confidence ({conf:.0%}) — verify orientation manually before accepting output.")

            # ── Big risk + CRI/MRI display ────────────────────────────────────
            cri_pct = min(int(r["cri"] * 100), 100)
            mri_pct = min(int(r["mri"] * 100), 100)

            def svg_gauge(pct, color, label, value):
                r_outer = 52
                circumference = 2 * 3.14159 * r_outer
                dash = pct / 100 * circumference * 0.75
                gap  = circumference - dash
                rot  = -135
                return f"""
                <div style="text-align:center;">
                  <svg width="120" height="100" viewBox="0 0 120 100">
                    <circle cx="60" cy="68" r="{r_outer}" fill="none"
                      stroke="#1e293b" stroke-width="10"
                      stroke-dasharray="{circumference*0.75} {circumference*0.25}"
                      stroke-dashoffset="0"
                      transform="rotate({rot} 60 68)" stroke-linecap="round"/>
                    <circle cx="60" cy="68" r="{r_outer}" fill="none"
                      stroke="{color}" stroke-width="10"
                      stroke-dasharray="{dash} {circumference - dash}"
                      stroke-dashoffset="0"
                      transform="rotate({rot} 60 68)" stroke-linecap="round"
                      filter="url(#glow_{label})"/>
                    <defs>
                      <filter id="glow_{label}" x="-30%" y="-30%" width="160%" height="160%">
                        <feGaussianBlur stdDeviation="3" result="blur"/>
                        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                      </filter>
                    </defs>
                    <text x="60" y="64" text-anchor="middle" fill="{color}"
                      font-size="18" font-weight="800" font-family="Inter,sans-serif">{value}</text>
                    <text x="60" y="78" text-anchor="middle" fill="#475569"
                      font-size="9" font-family="Inter,sans-serif">{label}</text>
                  </svg>
                </div>"""

            g1, g2, g3 = st.columns([1, 1, 1])
            with g1:
                st.markdown(svg_gauge(cri_pct, colour, "CRI", r["cri"]), unsafe_allow_html=True)
            with g2:
                st.markdown(f"""
                <div style="background:{rc['bg']};border:2px solid {rc['border']};
                            border-radius:4px;padding:14px 10px;text-align:center;
                            margin-top:4px;">
                  <div style="font-size:0.58rem;text-transform:uppercase;letter-spacing:.1em;
                              color:#64748b;margin-bottom:6px;">RISK LEVEL</div>
                  <div style="font-size:1.5rem;font-weight:900;color:{rc['val']};
                              letter-spacing:1px;">
                    {level.upper()}</div>
                  <div style="font-size:0.68rem;color:#64748b;margin-top:6px;line-height:1.3;">
                    {r['urgency']}</div>
                </div>""", unsafe_allow_html=True)
            with g3:
                st.markdown(svg_gauge(mri_pct, colour, "MRI", r["mri"]), unsafe_allow_html=True)

            # ── Mechanism ─────────────────────────────────────────────────────
            mech_clr = {"critical":"#f87171","high":"#fb923c","moderate":"#fbbf24","low":"#4ade80"}
            mc = mech_clr.get(mech["severity"], "#7aafc7")
            st.markdown(f"""
            <div style="background:#0a1220;border:1px solid #1e293b;border-left:3px solid {mc};
                        border-radius:0 10px 10px 0;padding:10px 14px;margin:10px 0;">
              <div style="font-size:0.60rem;text-transform:uppercase;letter-spacing:.08em;
                          color:#475569;margin-bottom:4px;">Probable Mechanism</div>
              <div style="font-size:0.88rem;font-weight:700;color:{mc};">{mech['mechanism']}</div>
              <div style="font-size:0.75rem;color:#64748b;margin-top:3px;">{mech['detail']}</div>
              <div style="font-size:0.68rem;color:#334155;margin-top:4px;">Ref: <b style="color:#4A7FA5;">{mech['code']}</b></div>
            </div>""", unsafe_allow_html=True)

            # ── CRI variable bars ─────────────────────────────────────────────
            LABELS  = {"width":"Width","depth":"Depth","orientation":"Orientation",
                       "distance":"Distance","activity":"Activity","importance":"Importance"}
            BAR_COLORS = [("#4A7FA5","#1d4ed8"),("#8b5cf6","#6d28d9"),("#06b6d4","#0e7490"),
                          ("#f59e0b","#b45309"),("#10b981","#047857"),("#ec4899","#9d174d")]
            bars_html = '<div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;padding:14px 16px;margin-bottom:10px;">'
            bars_html += '<div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:.08em;color:#4A7FA5;margin-bottom:10px;">CRI Variable Breakdown</div>'
            for idx, (k, label) in enumerate(LABELS.items()):
                sv  = r["scores"][k]
                cv  = r["contributions"][k]
                pct = min(int(sv * 100), 100)
                c1c, c2c = BAR_COLORS[idx]
                bars_html += f"""
                <div style="margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;font-size:0.74rem;margin-bottom:3px;">
                    <span style="color:#94a3b8;">{label}
                      <span style="color:#334155;font-size:0.66rem;"> ×{WEIGHTS[k]}</span></span>
                    <span style="color:{c1c};font-weight:700;">{sv:.2f} → {cv:.4f}</span>
                  </div>
                  <div style="background:#1e293b;border-radius:4px;height:6px;overflow:hidden;">
                    <div style="width:{pct}%;height:6px;border-radius:4px;
                                background:linear-gradient(90deg,{c1c},{c2c});"></div>
                  </div>
                </div>"""
            bars_html += f'<div style="text-align:right;font-size:0.78rem;color:#7aafc7;font-weight:700;margin-top:6px;border-top:1px solid #1e293b;padding-top:6px;">Total CRI = {r["cri"]}</div>'
            bars_html += '</div>'
            st.markdown(bars_html, unsafe_allow_html=True)

            # ── IS code checks ────────────────────────────────────────────────
            w_ok = width_mm <= r["permissible_width_mm"]
            st.markdown(
                f'<div class="{"code-ref" if w_ok else "warn-box"}">'
                f'{"✅" if w_ok else "⚠️"} <b>IS 456 Cl. 35.3.2</b> — {r["width_status"]}</div>',
                unsafe_allow_html=True)
            if r.get("shear_note"):
                st.markdown(f'<div class="warn-box">⚠️ {r["shear_note"]}</div>', unsafe_allow_html=True)
            if member_type == "Beam-Column Joint" and r.get("joint_shear_limit"):
                st.markdown(f'<div class="crit-box">🔴 <b>IS 13920 Cl. 8.1.3</b> — {joint_type} joint · Limit={r["joint_shear_limit"]:.2f} MPa · BRITTLE FAILURE</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="code-ref">📐 <b>ACI 318-19 §6.6.3.1</b> — Ieff = {r["ie_modifier"]}·Ig for {member_type}</div>', unsafe_allow_html=True)

            # ── Recommended Action ────────────────────────────────────────────
            st.markdown(f"""
            <div style="background:#0a1628;border:1px solid #1e3a6e;border-radius:4px;
                        padding:12px 14px;margin:8px 0;">
              <div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:.08em;
                          color:#4A7FA5;margin-bottom:5px;">Recommended Action</div>
              <div style="font-size:0.82rem;color:#cbd5e1;">{r['action']}</div>
            </div>""", unsafe_allow_html=True)

            # ── PDF Export ────────────────────────────────────────────────────
            site_meta = dict(site=site_name, inspector=inspector, date=str(inspection_dt))
            try:
                pdf_bytes = build_pdf(r, inputs_snap, site_meta)
                st.download_button(
                    "📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"RCC_Risk_{member_type.replace(' ','')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"PDF error: {e}")

        else:
            st.markdown("""
            <div class="empty-state" style="margin-top:60px;">
              <div class="icon">🏗️</div>
              <p>Fill in the structural context and click<br>
              <b style="color:#4A7FA5!important;">⚡ Compute Risk Assessment</b></p>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB — SESSION HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_history:
    history = st.session_state.get("history", [])

    if not history:
        st.markdown("""
        <div class="empty-state" style="margin-top:40px;">
          <div class="icon">📋</div>
          <p>No assessments yet.<br>Go to <b style="color:#4A7FA5!important;">ASSESS</b> and click Compute.</p>
        </div>""", unsafe_allow_html=True)
    else:
        mri_vals = [h["mri"] for h in history]
        fri_r    = compute_fri(mri_vals)
        fri_lvl  = fri_r["risk_level"]
        from collections import Counter
        dist = Counter(h["risk"] for h in history)

        RISK_VAL = {"Low":"#4ade80","Moderate":"#fbbf24","High":"#fb923c","Critical":"#f87171"}
        fri_clr  = RISK_VAL.get(fri_lvl, "#7aafc7")

        # ── KPI row ──────────────────────────────────────────────────────────
        hk1, hk2, hk3, hk4, hk5, hk6 = st.columns(6, gap="small")
        hkpis = [
            (hk1, "Total Assessed", len(history),         "#7aafc7"),
            (hk2, "Frame Risk (FRI)", fri_r["fri"],       fri_clr),
            (hk3, "Mean MRI",  round(sum(mri_vals)/len(mri_vals),3), "#a78bfa"),
            (hk4, "High+Critical", dist.get("High",0)+dist.get("Critical",0), "#f87171"),
            (hk5, "Low Risk",  dist.get("Low",0),          "#4ade80"),
            (hk6, "Cluster C", fri_r["c_cluster"],        "#06b6d4"),
        ]
        for col, lbl, val, clr in hkpis:
            with col:
                st.markdown(f"""
                <div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;
                            padding:12px 10px;text-align:center;">
                  <div style="font-size:0.58rem;text-transform:uppercase;letter-spacing:.07em;
                              color:#475569;margin:3px 0;">{lbl}</div>
                  <div style="font-size:1.1rem;font-weight:800;color:{clr};">{val}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # ── Risk distribution bars ────────────────────────────────────────────
        st.markdown('<div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;color:#4A7FA5;margin-bottom:10px;">Risk Distribution</div>', unsafe_allow_html=True)
        dist_cols = st.columns(4, gap="small")
        for col, lvl in zip(dist_cols, ["Low","Moderate","High","Critical"]):
            cnt = dist.get(lvl, 0)
            pct = int(cnt / len(history) * 100) if history else 0
            clr = RISK_VAL.get(lvl, "#64748b")
            with col:
                st.markdown(f"""
                <div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;
                            padding:14px;text-align:center;">
                  <span class="badge badge-{lvl}" style="font-size:0.68rem;padding:3px 12px;">{lvl.upper()}</span>
                  <div style="font-size:2rem;font-weight:900;color:{clr};margin:6px 0;
                              ">{cnt}</div>
                  <div style="background:#1e293b;border-radius:4px;height:4px;overflow:hidden;margin:0 8px;">
                    <div style="width:{pct}%;height:4px;background:{clr};border-radius:4px;"></div>
                  </div>
                  <div style="font-size:0.68rem;color:#334155;margin-top:4px;">{pct}%</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # ── FRI formula ref ───────────────────────────────────────────────────
        st.markdown(f"""
        <div class="code-ref">
          FRI = Mean(MRI) × C_cluster &nbsp;|&nbsp; C_cluster = 1 + 0.25×(nH/N)
          &nbsp;|&nbsp; Members: {len(mri_vals)} &nbsp;|&nbsp; Urgency: {fri_r['urgency']}
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # ── View toggle ───────────────────────────────────────────────────────
        view_mode = st.radio("View Mode", ["🖼️ Card View", "📊 Table View"],
                             horizontal=True, label_visibility="collapsed")

        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

        RISK_VAL2 = {"Low":"#4ade80","Moderate":"#fbbf24","High":"#fb923c","Critical":"#f87171"}
        RISK_BG   = {"Low":"#052e16","Moderate":"#1c1400","High":"#1c0a00","Critical":"#1a0000"}
        RISK_BD   = {"Low":"#16a34a","Moderate":"#ca8a04","High":"#ea580c","Critical":"#dc2626"}

        if view_mode == "🖼️ Card View":
            for h in reversed(history):
                lvl    = h["risk"]
                rc_val = RISK_VAL2.get(lvl, "#7aafc7")
                rc_bg  = RISK_BG.get(lvl, "#0d1525")
                rc_bd  = RISK_BD.get(lvl, "#1e293b")
                conf_str = f"{int(h['confidence']*100)}%" if h.get("confidence") is not None else "—"

                with st.expander(
                    f"#{h['no']}  ·  {h['date']} {h['time']}  ·  {h['member']}  ·  "
                    f"CRI {h['cri']}  →  {lvl.upper()}",
                    expanded=False
                ):
                    img_col, info_col = st.columns([1, 1.6], gap="medium")

                    with img_col:
                        if h.get("original_bytes"):
                            t_orig, t_over = st.tabs(["📷 Original", "🔴 Overlay"])
                            with t_orig:
                                st.image(h["original_bytes"], use_container_width=True)
                            with t_over:
                                if h.get("overlay_bytes"):
                                    st.image(h["overlay_bytes"], use_container_width=True)
                                else:
                                    st.caption("No overlay (manual entry)")
                        else:
                            st.markdown("""
                            <div style="background:#0d1525;border:1px dashed #1e3a5f;
                                        border-radius:4px;padding:32px;text-align:center;">
                              <div style="font-size:2rem;">📷</div>
                              <div style="color:#334155;font-size:.78rem;margin-top:6px;">
                                No image saved<br>(manual entry)</div>
                            </div>""", unsafe_allow_html=True)

                    with info_col:
                        # Risk banner
                        st.markdown(f"""
                        <div style="background:{rc_bg};border:1px solid {rc_bd};
                                    border-radius:4px;padding:12px 16px;margin-bottom:10px;">
                          <div style="font-size:.60rem;text-transform:uppercase;letter-spacing:.09em;
                                      color:#64748b;margin-bottom:4px;">Assessment #{h['no']}</div>
                          <div style="display:flex;align-items:center;justify-content:space-between;">
                            <div style="font-size:1.4rem;font-weight:900;color:{rc_val};">{lvl.upper()}</div>
                            <div style="text-align:right;">
                              <div style="font-size:.70rem;color:#64748b;">CRI / MRI</div>
                              <div style="font-size:1.1rem;font-weight:800;color:#f1f5f9;">
                                {h['cri']} / {h['mri']}</div>
                            </div>
                          </div>
                        </div>""", unsafe_allow_html=True)

                        # Detail grid
                        st.markdown(f"""
                        <div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;
                                    padding:12px 14px;font-size:.78rem;">
                          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;">
                            <div style="color:#475569;">Site</div>
                            <div style="color:#e2e8f0;font-weight:600;">{h['site']}</div>
                            <div style="color:#475569;">Inspector</div>
                            <div style="color:#e2e8f0;">{h.get('inspector') or '—'}</div>
                            <div style="color:#475569;">Member</div>
                            <div style="color:#e2e8f0;font-weight:600;">{h['member']}</div>
                            <div style="color:#475569;">Width</div>
                            <div style="color:#e2e8f0;">{h['width_mm']} mm</div>
                            <div style="color:#475569;">Orientation</div>
                            <div style="color:#e2e8f0;">{h['orientation']}</div>
                            <div style="color:#475569;">Crack Type (AI)</div>
                            <div style="color:#e2e8f0;">{h.get('crack_type','—')}</div>
                            <div style="color:#475569;">AI Confidence</div>
                            <div style="color:#e2e8f0;">{conf_str}</div>
                            <div style="color:#475569;">Mechanism</div>
                            <div style="color:#e2e8f0;">{h['mechanism']}</div>
                          </div>
                        </div>""", unsafe_allow_html=True)

                        # Download buttons
                        dl1, dl2, dl3 = st.columns(3, gap="small")
                        with dl1:
                            if h.get("original_bytes"):
                                st.download_button("📷 Original",
                                    data=h["original_bytes"],
                                    file_name=f"crack_{h['no']}_original.jpg",
                                    mime="image/jpeg", use_container_width=True,
                                    key=f"dl_orig_{h['no']}")
                        with dl2:
                            if h.get("overlay_bytes"):
                                st.download_button("🔴 Overlay",
                                    data=h["overlay_bytes"],
                                    file_name=f"crack_{h['no']}_overlay.jpg",
                                    mime="image/jpeg", use_container_width=True,
                                    key=f"dl_over_{h['no']}")
                        with dl3:
                            if h.get("result") and h.get("inputs"):
                                try:
                                    site_meta_h = dict(site=h["site"],
                                                       inspector=h.get("inspector",""),
                                                       date=h["date"])
                                    pdf_h = build_pdf(h["result"], h["inputs"], site_meta_h)
                                    st.download_button("📄 PDF",
                                        data=pdf_h,
                                        file_name=f"RCC_Report_{h['no']}.pdf",
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key=f"dl_pdf_{h['no']}")
                                except Exception:
                                    pass

        else:  # Table View
            df = pd.DataFrame([
                {
                    "#": h["no"], "Time": h["time"], "Site": h["site"],
                    "Member": h["member"], "Width mm": h["width_mm"],
                    "Orientation": h["orientation"], "CRI": h["cri"],
                    "MRI": h["mri"], "Risk": h["risk"],
                    "Mechanism": h["mechanism"],
                    "AI Type": h.get("crack_type","—"),
                    "Conf%": f"{int(h['confidence']*100)}%" if h.get("confidence") is not None else "—",
                    "Image": "✅" if h.get("original_bytes") else "—",
                }
                for h in history
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        bc1, bc2 = st.columns(2, gap="small")
        with bc1:
            df_exp = pd.DataFrame([
                {
                    "#": h["no"], "Time": h["time"], "Site": h["site"],
                    "Member": h["member"], "Width mm": h["width_mm"],
                    "Orientation": h["orientation"], "CRI": h["cri"],
                    "MRI": h["mri"], "Risk": h["risk"],
                    "Mechanism": h["mechanism"],
                }
                for h in history
            ])
            csv = df_exp.to_csv(index=False)
            st.download_button("📥 Export CSV", data=csv,
                file_name=f"RCC_History_{site_name.replace(' ','_')}.csv",
                mime="text/csv", use_container_width=True)
        with bc2:
            if st.button("🗑️ Clear History", type="secondary", use_container_width=True):
                st.session_state["history"] = []
                if os.path.exists(HISTORY_DIR):
                    shutil.rmtree(HISTORY_DIR)
                os.makedirs(HISTORY_DIR, exist_ok=True)
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB — BULK REAL-IMAGE TEST
# ═══════════════════════════════════════════════════════════════════════════════
BATCH_RESULTS_JSON = os.path.join(_SRC, "batch_test_results", "batch_results.json")
BATCH_OVER_DIR     = os.path.join(_SRC, "batch_test_results", "overlays")
KAGGLE_DATA_DIR    = os.path.join(_SRC, "kaggle_data")

with tab_batch:
    st.markdown("""
    <div style="border-left:4px solid #4A7FA5;padding:16px 20px;margin-bottom:18px;background:#141c25;border-top:1px solid #1e2d3d;border-right:1px solid #1e2d3d;border-bottom:1px solid #1e2d3d;">
      <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:.12em;color:#4A7FA5;margin-bottom:4px;">BATCH VALIDATION</div>
      <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;">Bulk Real-Image Test — Kaggle SDNET Dataset</div>
      <div style="font-size:0.72rem;color:#64748b;margin-top:4px;">Pipeline validated on <b style="color:#94a3b8;">16,968 real structural images</b> (8,484 cracked + 8,484 non-cracked) &nbsp;·&nbsp; Decks · Pavements · Walls &nbsp;·&nbsp; Source: Kaggle / aniruddhsharma (Structural Defects Network)</div>
    </div>
    """, unsafe_allow_html=True)

    if not os.path.exists(BATCH_RESULTS_JSON):
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🌍</div>
          <p>No batch results yet.<br>
          Run <code style="color:#4A7FA5;">python batch_test.py</code> from the project folder.</p>
        </div>""", unsafe_allow_html=True)
    else:
        with open(BATCH_RESULTS_JSON, "r", encoding="utf-8") as _f:
            _batch = json.load(_f)

        _processed = [r for r in _batch if r.get("detected") is not None]
        _tp = sum(1 for r in _processed if r["true_label"]=="Cracked"     and r["detected"])
        _tn = sum(1 for r in _processed if r["true_label"]=="Non-cracked" and not r["detected"])
        _fp = sum(1 for r in _processed if r["true_label"]=="Non-cracked" and r["detected"])
        _fn = sum(1 for r in _processed if r["true_label"]=="Cracked"     and not r["detected"])
        _n  = len(_processed)
        _accuracy  = (_tp + _tn) / _n * 100 if _n else 0
        _precision = _tp / (_tp + _fp) if (_tp + _fp) else 0
        _recall    = _tp / (_tp + _fn) if (_tp + _fn) else 0
        _f1        = 2*_precision*_recall/(_precision+_recall) if (_precision+_recall) else 0
        _specificity = _tn / (_tn + _fp) if (_tn + _fp) else 0

        # ── Top KPI row ───────────────────────────────────────────────────────
        _kc = st.columns(5, gap="small")
        for _col, _lbl, _val, _clr in [
            (_kc[0], "Total Images",    f"{_n:,}",              "#7aafc7"),
            (_kc[1], "Accuracy",         f"{_accuracy:.1f}%",    "#34d399"),
            (_kc[2], "Precision",        f"{_precision:.1%}",    "#f59e0b"),
            (_kc[3], "Recall",           f"{_recall:.1%}",       "#a78bfa"),
            (_kc[4], "F1 Score",         f"{_f1:.1%}",           "#fb923c"),
        ]:
            with _col:
                st.markdown(f"""
                <div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;
                            padding:14px 10px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,.3);">
                  <div style="font-size:.60rem;text-transform:uppercase;letter-spacing:.08em;
                              color:#475569;margin:4px 0;">{_lbl}</div>
                  <div style="font-size:1.4rem;font-weight:800;color:{_clr};">{_val}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # ── Confusion matrix + per-surface ───────────────────────────────────
        _cm_col, _surf_col = st.columns([1, 1.4], gap="medium")

        with _cm_col:
            st.markdown(f"""
            <div style="background:#0d1525;border:1px solid #1e293b;border-radius:4px;padding:18px 20px;">
              <div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;
                          color:#4A7FA5;margin-bottom:14px;">Confusion Matrix</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;text-align:center;">
                <div style="background:#052e16;border:1px solid #16a34a;border-radius:4px;padding:14px;">
                  <div style="font-size:.62rem;color:#64748b;margin-bottom:4px;">TRUE POSITIVE</div>
                  <div style="font-size:1.8rem;font-weight:900;color:#4ade80;">{_tp:,}</div>
                  <div style="font-size:.68rem;color:#16a34a;">cracked · detected</div>
                </div>
                <div style="background:#1a0000;border:1px solid #dc2626;border-radius:4px;padding:14px;">
                  <div style="font-size:.62rem;color:#64748b;margin-bottom:4px;">FALSE NEGATIVE</div>
                  <div style="font-size:1.8rem;font-weight:900;color:#f87171;">{_fn:,}</div>
                  <div style="font-size:.68rem;color:#dc2626;">cracked · missed</div>
                </div>
                <div style="background:#1c0a00;border:1px solid #ea580c;border-radius:4px;padding:14px;">
                  <div style="font-size:.62rem;color:#64748b;margin-bottom:4px;">FALSE POSITIVE</div>
                  <div style="font-size:1.8rem;font-weight:900;color:#fb923c;">{_fp:,}</div>
                  <div style="font-size:.68rem;color:#ea580c;">no crack · flagged</div>
                </div>
                <div style="background:#0a2240;border:1px solid #4A7FA5;border-radius:4px;padding:14px;">
                  <div style="font-size:.62rem;color:#64748b;margin-bottom:4px;">TRUE NEGATIVE</div>
                  <div style="font-size:1.8rem;font-weight:900;color:#7aafc7;">{_tn:,}</div>
                  <div style="font-size:.68rem;color:#4A7FA5;">no crack · correct</div>
                </div>
              </div>
              <div style="margin-top:12px;font-size:.72rem;color:#475569;text-align:center;">
                Specificity: <b style="color:#7aafc7;">{_specificity:.1%}</b>
              </div>
            </div>""", unsafe_allow_html=True)

        with _surf_col:
            st.markdown('<div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;'
                        'color:#4A7FA5;margin-bottom:10px;">Per-Surface Breakdown</div>',
                        unsafe_allow_html=True)
            _SURF_CLRS = {"Decks":"#06b6d4","Pavements":"#a78bfa","Walls":"#f59e0b"}
            for _surf in ("Decks","Pavements","Walls"):
                _srows = [r for r in _processed if r.get("surface")==_surf]
                if not _srows: continue
                _stp = sum(1 for r in _srows if r["true_label"]=="Cracked"     and r["detected"])
                _stn = sum(1 for r in _srows if r["true_label"]=="Non-cracked" and not r["detected"])
                _sfp = sum(1 for r in _srows if r["true_label"]=="Non-cracked" and r["detected"])
                _sfn = sum(1 for r in _srows if r["true_label"]=="Cracked"     and not r["detected"])
                _sacc = (_stp+_stn)/len(_srows)*100
                _src  = sum(1 for r in _srows if r["true_label"]=="Cracked")
                _snc  = sum(1 for r in _srows if r["true_label"]=="Non-cracked")
                _sc   = _SURF_CLRS.get(_surf,"#7aafc7")
                st.markdown(f"""
                <div style="background:#0d1525;border:1px solid #1e293b;border-left:3px solid {_sc};
                            border-radius:0 10px 10px 0;padding:12px 16px;margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <div style="font-size:.80rem;font-weight:700;color:{_sc};">{_surf}</div>
                      <div style="font-size:.68rem;color:#475569;margin-top:2px;">
                        {len(_srows):,} images &nbsp;·&nbsp; {_src:,} cracked · {_snc:,} non-cracked</div>
                    </div>
                    <div style="font-size:1.5rem;font-weight:900;color:{_sc};">{_sacc:.1f}%</div>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;
                              margin-top:10px;text-align:center;font-size:.68rem;">
                    <div style="background:#052e16;border-radius:6px;padding:6px;">
                      <div style="color:#64748b;">TP</div>
                      <div style="color:#4ade80;font-weight:700;">{_stp:,}</div></div>
                    <div style="background:#0a2240;border-radius:6px;padding:6px;">
                      <div style="color:#64748b;">TN</div>
                      <div style="color:#7aafc7;font-weight:700;">{_stn:,}</div></div>
                    <div style="background:#1c0a00;border-radius:6px;padding:6px;">
                      <div style="color:#64748b;">FP</div>
                      <div style="color:#fb923c;font-weight:700;">{_sfp:,}</div></div>
                    <div style="background:#1a0000;border-radius:6px;padding:6px;">
                      <div style="color:#64748b;">FN</div>
                      <div style="color:#f87171;font-weight:700;">{_sfn:,}</div></div>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

        # ── Distribution charts ───────────────────────────────────────────────
        from collections import Counter as _Counter
        _detected_rows = [r for r in _processed if r.get("detected")]
        _type_d = _Counter(r.get("crack_type","—") for r in _detected_rows)
        _ori_d  = _Counter(r.get("orientation","—") for r in _detected_rows)
        _wid_d  = _Counter(r.get("width_class","—") for r in _detected_rows)

        _dc1, _dc2, _dc3 = st.columns(3, gap="small")
        for _col, _title, _dist in [
            (_dc1, "Detected Crack Types",    _type_d),
            (_dc2, "Detected Orientations",   _ori_d),
            (_dc3, "Detected Width Classes",  _wid_d),
        ]:
            with _col:
                _clrs = ["#4A7FA5","#8b5cf6","#06b6d4","#f59e0b","#10b981"]
                _total_det = sum(_dist.values()) or 1
                _html = (f'<div style="background:#0d1525;border:1px solid #1e293b;'
                         f'border-radius:4px;padding:14px 16px;">'
                         f'<div style="font-size:.65rem;text-transform:uppercase;'
                         f'letter-spacing:.08em;color:#4A7FA5;margin-bottom:12px;">{_title}</div>')
                for _ci, (_k, _v) in enumerate(_dist.most_common()):
                    _pct = int(_v / _total_det * 100)
                    _c   = _clrs[_ci % len(_clrs)]
                    _html += (f'<div style="margin-bottom:8px;">'
                              f'<div style="display:flex;justify-content:space-between;'
                              f'font-size:.74rem;margin-bottom:3px;">'
                              f'<span style="color:#94a3b8;">{_k}</span>'
                              f'<span style="color:{_c};font-weight:700;">{_v:,} ({_pct}%)</span></div>'
                              f'<div style="background:#1e293b;border-radius:3px;height:6px;">'
                              f'<div style="width:{_pct}%;height:6px;background:{_c};'
                              f'border-radius:3px;"></div>'
                              f'</div></div>')
                _html += '</div>'
                st.markdown(_html, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

        # ── Sample overlay gallery (TP images) ────────────────────────────────
        _tp_with_overlay = [r for r in _processed
                            if r.get("detected") and r.get("overlay")
                            and os.path.exists(os.path.join(BATCH_OVER_DIR, r["overlay"]))][:24]

        if _tp_with_overlay:
            st.markdown('<div style="font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;'
                        'color:#4A7FA5;margin-bottom:12px;">Sample Crack Overlays — True Positives '
                        f'(showing {len(_tp_with_overlay)} of {_tp:,})</div>',
                        unsafe_allow_html=True)
            _COLS = 6
            for _rs in range(0, len(_tp_with_overlay), _COLS):
                _row = _tp_with_overlay[_rs: _rs + _COLS]
                _gcols = st.columns(_COLS, gap="small")
                for _gc, _r in zip(_gcols, _row):
                    _op = os.path.join(BATCH_OVER_DIR, _r["overlay"])
                    with _gc:
                        st.image(_op, use_container_width=True)
                        _orig_path = os.path.join(KAGGLE_DATA_DIR,
                                                   _r["surface"], "Cracked", _r["file"])
                        st.markdown(f"""
                        <div style="font-size:.62rem;color:#64748b;text-align:center;
                                    margin-top:3px;line-height:1.3;">
                          {_r["surface"]}<br>
                          <span style="color:#fb923c;">{_r.get("crack_type","—")}</span>
                        </div>""", unsafe_allow_html=True)

        # ── Searchable results table ──────────────────────────────────────────
        st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
        with st.expander("📋 Full Results Table (16,968 rows)", expanded=False):
            _df_b = pd.DataFrame([{
                "#": r["id"], "Surface": r.get("surface",""),
                "File": r["file"], "True Label": r["true_label"],
                "Detected": "Yes" if r["detected"] else "No",
                "Crack Type": r.get("crack_type","—"),
                "Orientation": r.get("orientation","—"),
                "Width Class": r.get("width_class","—"),
                "Confidence": f"{int(r.get('confidence',0)*100)}%",
            } for r in _processed])
            st.dataframe(_df_b, use_container_width=True, hide_index=True)
            _csv_b = _df_b.to_csv(index=False)
            st.download_button("📥 Download CSV", data=_csv_b,
                               file_name="batch_results_kaggle.csv",
                               mime="text/csv")

        st.markdown("""
        <div class="code-ref" style="margin-top:12px;">
          <b>Dataset:</b> Structural Defects Network (aniruddhsharma, Kaggle) &nbsp;·&nbsp;
          8,484 cracked + 8,484 non-cracked (equal split) across Decks, Pavements, Walls &nbsp;·&nbsp;
          <b>Pipeline:</b> OpenCV 3rd-percentile dark-pixel threshold + minAreaRect elongation filter (≥60px, ≥3×) +
          Hough-line orientation + skeleton-width estimation
        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB — ANNEXURE A (WORKED EXAMPLE)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_annexa:
    st.markdown("### Annexure A — Worked CRI Calculation (Live)")
    st.caption(
        "Reproduces the worked example from Annexure A of the project report. "
        "All values are editable — change any input and the calculation updates instantly."
    )

    st.markdown("""
    <div class="code-ref">
      <b>Scenario (from Report):</b> A 0.4 mm diagonal crack observed in the web of a
      ground-floor primary frame beam, 280 mm from the beam-column interface.
      Beam span = 5.0 m, effective depth d = 400 mm. Single inspection — no prior history.
      Member is part of the primary lateral-load-resisting frame.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Adjust Inputs")
    ax1, ax2 = st.columns(2)
    with ax1:
        a_width    = st.number_input("Crack Width (mm)", 0.01, 5.0, 0.40, 0.05, format="%.2f", key="ax_w")
        a_depth    = st.slider("Depth Ratio (%)", 0, 80, 22, key="ax_d")
        a_ori      = st.selectbox("Orientation", ORIENTATIONS,
                                   index=ORIENTATIONS.index("Diagonal (shear/joint)"), key="ax_o")
        a_dist     = st.selectbox("Distance", DISTANCES,
                                   index=DISTANCES.index("Near support/joint (<0.5d)"), key="ax_ds")
    with ax2:
        a_act      = st.selectbox("Activity", ACTIVITIES,
                                   index=ACTIVITIES.index("Unknown (single observation)"), key="ax_ac")
        a_imp      = st.selectbox("Importance", IMPORTANCES,
                                   index=IMPORTANCES.index("Primary (lateral load frame)"), key="ax_im")
        a_member   = st.selectbox("Member Type", MEMBER_TYPES,
                                   index=MEMBER_TYPES.index("Beam"), key="ax_mt")
        a_exposure = st.selectbox("Exposure Class", EXPOSURE_CLASSES,
                                   index=EXPOSURE_CLASSES.index("Moderate"), key="ax_ex")

    ar = full_assessment(
        width_mm=a_width, depth_pct=float(a_depth), orientation=a_ori,
        distance=a_dist, activity=a_act, importance=a_imp,
        member_type=a_member, exposure=a_exposure,
        concrete_grade=concrete_grade, seismic_zone=seismic_zone,
    )

    st.markdown("#### Step-by-Step CRI Calculation Table")

    VAR_LABELS = ["Crack Width","Depth Ratio","Orientation",
                  "Distance from Support/Joint","Activity Over Time","Member Importance"]
    VAR_KEYS   = ["width","depth","orientation","distance","activity","importance"]
    CODE_REFS  = ["IS 456:2000 Cl. 35.3.2","ACI 318-19 Branson eq.",
                  "IS 456:2000 Cl. 40","IS 456:2000 Cl. 40.5","IS 456:2000 Cl. 19.2","IS 456:2000 Cl. 22"]

    rows = []
    for i, (k, label, ref) in enumerate(zip(VAR_KEYS, VAR_LABELS, CODE_REFS), 1):
        s  = ar["scores"][k]
        w  = WEIGHTS[k]
        c  = ar["contributions"][k]
        rows.append({
            "i": i, "Variable": label,
            "Score Sᵢ": s, "Weight wᵢ": w,
            "wᵢ × Sᵢ": c, "IS Code Ref": ref,
        })

    rows_df = pd.DataFrame(rows).set_index("i")
    st.dataframe(rows_df, use_container_width=True)

    # Summary
    lvl = ar["risk_level"]
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""<div class="card" style="text-align:center;">
          <div class="card-title">CRI = &Sigma;(wᵢ &times; Sᵢ)</div>
          <div style="font-size:2rem;font-weight:800;color:{ar['colour']};">{ar['cri']}</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="card" style="text-align:center;">
          <div class="card-title">MRI = CRI &times; {ar['member_multiplier']}</div>
          <div style="font-size:2rem;font-weight:800;color:{ar['colour']};">{ar['mri']}</div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown(f"""<div class="card" style="text-align:center;">
          <div class="card-title">Risk Level</div>
          <span class="badge badge-{lvl}">{lvl.upper()}</span>
        </div>""", unsafe_allow_html=True)

    # Report comparison
    st.markdown("#### Comparison with Report Annexure A")
    cmp_data = {
        "": ["Report (Annexure A)", "This App (live)"],
        "CRI":  ["0.744", str(ar["cri"])],
        "MRI":  ["0.744", str(ar["mri"])],
        "Risk": ["Critical", ar["risk_level"]],
    }
    st.table(pd.DataFrame(cmp_data).set_index(""))

    st.markdown(f"""
    <div class="code-ref">
      <b>Key insight from this case:</b> Even if crack width is halved to 0.20 mm (Fine class),
      the CRI remains High/Critical — because the <b>Near-joint location (0.190)</b> and
      <b>diagonal orientation (0.119)</b> still dominate. Width alone cannot determine risk.
      This is the central argument of the project (IS 456 Cl. 35.3.2 vs IS 13920 Cl. 8.3.1).
    </div>
    """, unsafe_allow_html=True)

    # Download Annexure A as PDF
    try:
        annex_inputs = dict(
            width_mm=a_width, depth_pct=a_depth, orientation=a_ori, distance=a_dist,
            activity=a_act, importance=a_imp, member_type=a_member, exposure=a_exposure,
            concrete_grade=concrete_grade, seismic_zone=seismic_zone, joint_type="Interior",
        )
        site_meta = dict(site=site_name, inspector=inspector, date=str(inspection_dt))
        annex_pdf = build_pdf(ar, annex_inputs, site_meta)
        st.download_button(
            "📄 Download Annexure A Report (PDF)",
            data=annex_pdf,
            file_name="AnnexureA_Worked_Example.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.error(f"PDF error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB — DEMO IMAGES
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
with tab_demo:
    st.markdown("### Pre-loaded Crack Images — Five Validation Cases")
    st.caption("These are the five test cases from Chapter 10 of the project report. "
               "Download any image and upload it in the Assess tab.")

    SAMPLES = [
        ("V01_flexural_midspan.jpg",  "V-01: Flexural Crack — Beam Midspan",
         "Vertical crack at soffit. Expected: **Moderate**"),
        ("V02_shear_near_support.jpg","V-02: Shear Crack — Near Support",
         "Diagonal ~45°, near column face. Expected: **High / Critical**"),
        ("V03_joint_diagonal.jpg",    "V-03: Joint Diagonal — B-C Joint Panel",
         "<0.2 mm diagonal. Expected: **Critical** (IS 13920 Cl. 8.3.1)"),
        ("V04_hairline_secondary.jpg","V-04: Hairline — Secondary Beam",
         "Very fine vertical crack. Expected: **Low**"),
        ("V05_horizontal_column.jpg", "V-05: Horizontal Bond Crack — Column",
         "Horizontal at column face. Expected: **High**"),
    ]
    PRESET_INPUTS = [
        dict(width_mm=0.30, depth_pct=25, orientation="Vertical (flexural)",
             distance="Far from support/joint", activity="Unknown (single observation)",
             importance="Secondary member", member_type="Beam"),
        dict(width_mm=0.70, depth_pct=30, orientation="Diagonal (shear/joint)",
             distance="Near support/joint (<0.5d)", activity="Unknown (single observation)",
             importance="Primary (lateral load frame)", member_type="Beam"),
        dict(width_mm=0.15, depth_pct=20, orientation="Diagonal (shear/joint)",
             distance="Near support/joint (<0.5d)", activity="Unknown (single observation)",
             importance="Primary (lateral load frame)", member_type="Beam-Column Joint"),
        dict(width_mm=0.05, depth_pct=10, orientation="Vertical (flexural)",
             distance="Far from support/joint", activity="Stable (no change)",
             importance="Secondary member", member_type="Beam"),
        dict(width_mm=0.50, depth_pct=25, orientation="Horizontal",
             distance="Near support/joint (<0.5d)", activity="Unknown (single observation)",
             importance="Primary (lateral load frame)", member_type="Column"),
    ]

    cols = st.columns(5, gap="small")
    for col, (fname, title, desc), pinputs in zip(cols, SAMPLES, PRESET_INPUTS):
        path = os.path.join(_SRC, "samples", fname)
        with col:
            if os.path.exists(path):
                st.image(path, use_container_width=True)
            st.markdown(f"<div style='font-size:.78rem;font-weight:700;margin-top:4px;'>{title}</div>",
                        unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.73rem;color:#555;'>{desc}</div>",
                        unsafe_allow_html=True)

            r = full_assessment(**pinputs, exposure=exposure,
                                concrete_grade=concrete_grade, seismic_zone=seismic_zone)
            lvl = r["risk_level"]
            st.markdown(f"""
            <div style="margin-top:6px;text-align:center;">
              <span class="badge badge-{lvl}" style="font-size:.72rem;padding:2px 10px;">
                {lvl.upper()} · CRI {r['cri']}
              </span>
            </div>
            """, unsafe_allow_html=True)

            if os.path.exists(path):
                with open(path, "rb") as f:
                    st.download_button(f"⬇ Download", f.read(), file_name=fname,
                                       mime="image/jpeg", use_container_width=True,
                                       key=f"dl_{fname}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab_valid:
    st.markdown("### Validation — Four-Viewpoint Comparison (Report Ch. 10)")
    st.caption("V1=Visual · V2=IS Code · V3=FE Response · V4=AI Risk Engine")

    VAL_CASES = [
        {
            "id": "V-01",
            "desc": "0.3 mm vertical crack, beam midspan soffit, secondary beam",
            "v1": "Moderate; visible, ~0.3 mm, vertical",
            "v2": "IS 456 Cl. 35.3.2: at serviceability limit (0.3mm); monitor",
            "v3": "FE-02 (25% depth): Ie ≈ 0.74 Ig; deflection +18%; within l/250",
            "inputs": dict(width_mm=0.30, depth_pct=25, orientation="Vertical (flexural)",
                           distance="Far from support/joint", activity="Unknown (single observation)",
                           importance="Secondary member", member_type="Beam"),
        },
        {
            "id": "V-02",
            "desc": "0.7 mm diagonal crack, beam near column, primary frame",
            "v1": "Severe; wide, diagonal, near support",
            "v2": "IS 456 Cl. 40: diagonal at column face — check shear and bond",
            "v3": "FE-03: support-zone redistribution; demand ratio 0.82",
            "inputs": dict(width_mm=0.70, depth_pct=30, orientation="Diagonal (shear/joint)",
                           distance="Near support/joint (<0.5d)", activity="Unknown (single observation)",
                           importance="Primary (lateral load frame)", member_type="Beam"),
        },
        {
            "id": "V-03",
            "desc": "<0.2 mm diagonal crack, beam-column joint panel — KEY CASE",
            "v1": "Minor visually; <0.2 mm; diagonal in joint",
            "v2": "First read: minor — BUT IS 13920:2016 Cl. 8.3.1 flags joint diagonal as CRITICAL",
            "v3": "FE-05: joint rotation +38%; storey drift amplified +22%",
            "inputs": dict(width_mm=0.15, depth_pct=20, orientation="Diagonal (shear/joint)",
                           distance="Near support/joint (<0.5d)", activity="Unknown (single observation)",
                           importance="Primary (lateral load frame)", member_type="Beam-Column Joint"),
        },
        {
            "id": "V-04",
            "desc": "Hairline vertical crack, secondary beam midspan",
            "v1": "Minor; hairline; vertical",
            "v2": "IS 456: <<0.3 mm; typical early cracking; no action",
            "v3": "FE-02 (10% depth): negligible stiffness change",
            "inputs": dict(width_mm=0.05, depth_pct=10, orientation="Vertical (flexural)",
                           distance="Far from support/joint", activity="Stable (no change)",
                           importance="Secondary member", member_type="Beam"),
        },
        {
            "id": "V-05",
            "desc": "0.5 mm horizontal crack, primary column face",
            "v1": "Visible; ~0.5 mm; horizontal at column face",
            "v2": "IS 456: horizontal at column face may indicate bond split; investigate",
            "v3": "FE-04: stress concentration; no cascade yet",
            "inputs": dict(width_mm=0.50, depth_pct=25, orientation="Horizontal",
                           distance="Near support/joint (<0.5d)", activity="Unknown (single observation)",
                           importance="Primary (lateral load frame)", member_type="Column"),
        },
    ]

    for vc in VAL_CASES:
        r = full_assessment(**vc["inputs"], exposure=exposure,
                            concrete_grade=concrete_grade, seismic_zone=seismic_zone)
        lvl   = r["risk_level"]
        is_key = vc["id"] == "V-03"

        with st.expander(
            f"{'🔴 KEY CASE — ' if is_key else ''}{vc['id']} — {vc['desc']}   |   "
            f"CRI={r['cri']}  MRI={r['mri']}  → {lvl.upper()}",
            expanded=is_key
        ):
            col_a, col_b = st.columns([1.6, 1])
            with col_a:
                data = [
                    ["Viewpoint", "Assessment"],
                    ["V1 — Visual Judgment", vc["v1"]],
                    ["V2 — IS Code Reasoning", vc["v2"]],
                    ["V3 — FE Response", vc["v3"]],
                    ["V4 — AI Risk Engine", f"CRI={r['cri']} · MRI={r['mri']} → {lvl} · {r['urgency']}"],
                ]
                import pandas as pd
                df = pd.DataFrame(data[1:], columns=data[0])
                st.table(df)
            with col_b:
                st.markdown(f"""
                <div class="risk-banner risk-{lvl}" style="padding:14px;">
                  <div style="font-size:.75rem;color:#555;">RISK LEVEL</div>
                  <span class="badge badge-{lvl}">{lvl.upper()}</span><br><br>
                  <b>CRI:</b> {r['cri']}<br>
                  <b>MRI:</b> {r['mri']}<br>
                  <b>Multiplier:</b> {r['member_multiplier']}×<br><br>
                  <small>{r['urgency']}</small>
                </div>
                """, unsafe_allow_html=True)
                if is_key:
                    st.info("**V-03 is the strongest validation:**\n\n"
                            "A visually minor crack (0.15 mm) produces a **Critical** "
                            "output because the joint location and IS 13920 multiplier "
                            "(1.45×) dominate. FE-05 independently shows 22% drift "
                            "amplification — two lines of evidence converge.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ABOUT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_about:
    col_l, col_r = st.columns([1.4, 1])
    with col_l:
        st.markdown("""
        ## About This Project

        ### What It Does
        This system takes a crack photograph and the structural context of where that
        crack sits in an RCC frame, and produces a risk assessment an engineer can act on —
        not just an image classification label.

        ### The Core Insight
        A 0.2 mm diagonal crack in a beam-column joint is more dangerous than a
        0.4 mm vertical crack at midspan. No purely visual system can tell you that.
        Location dominates structural consequence — not width alone.

        ### Three-Tier Risk Logic
        | Index | Formula | Basis |
        |---|---|---|
        | CRI | Σ(wᵢ × Sᵢ) | IS 456:2000 + IS 13920:2016 calibrated |
        | MRI | CRI × α_m | IS 13920:2016 failure mode hierarchy |
        | FRI | Mean(MRI) × C_cluster | FE-06 progressive distress evidence |

        ### IS Code References
        | Code | Clause Used |
        |---|---|
        | IS 456:2000 | Cl. 35.3.2 (crack width), Cl. 40 (shear), Cl. 40.5 (critical zone), Table 20 |
        | IS 13920:2016 | Cl. 8.1.3 (joint shear), Cl. 8.3.1 (joint criticality) |
        | IS 1893:2016 | Seismic zone factor for joint multiplier |
        | ACI 318-19 | §6.6.3.1 cracked-section Ie modifiers |

        ### Pipeline
        ```
        Site photo → OpenCV preprocessing → Crack mask + orientation
             ↓
        Structural context (member type, zone, distance, etc.)
             ↓
        CRI → MRI → FRI risk engine (IS-code calibrated)
             ↓
        Risk level + urgency + IS code action + PDF report
        ```
        """)
    with col_r:
        st.markdown("""
        ### Team
        | Name | Roll No. |
        |---|---|
        | Anshul Dhoundiyal | 2K22/CE/031 |
        | Uday Kiran Mudavath | 2K22/CE/139 |
        | Anurag Kumar | 2K22/CE/033 |

        **Guide:** Prof. Gokaran P. Awadhiya
        Dept. of Civil Engineering, DTU

        ### Tools Used

        - Python 3.10 / OpenCV 4.x
        - ResNet-50 (transfer learning)
        - Streamlit 1.x
        - IS 456:2000, IS 13920:2016

        ### CRI Variable Weights
        """)
        import pandas as pd
        wdf = pd.DataFrame({
            "Variable":   ["Distance/Joint","Crack Width","Importance","Depth Ratio","Activity","Orientation"],
            "Weight":     [0.19, 0.18, 0.18, 0.17, 0.14, 0.14],
            "IS Code":    ["Cl. 40.5","Cl. 35.3.2","Cl. 22","ACI Branson","Cl. 19.2","Cl. 40"],
        })
        st.dataframe(wdf, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-top:1px solid #1e293b;margin-top:24px;padding-top:14px;padding-bottom:12px;text-align:center;">
  <span style="font-size:.74rem;color:#334155;">
    Anshul Dhoundiyal &nbsp;·&nbsp; Uday Kiran Mudavath &nbsp;·&nbsp; Anurag Kumar
    &nbsp;&nbsp;|&nbsp;&nbsp;
    Guide: Prof. G.P. Awadhiya, Dept. of Civil Engineering, DTU &nbsp;·&nbsp; May 2026
  </span><br>
  <span style="font-size:.70rem;color:#1e3a5f;">
    IS 456:2000 &nbsp;·&nbsp; IS 13920:2016 &nbsp;·&nbsp; IS 1893:2016 &nbsp;·&nbsp; ACI 318-19 §6.6.3.1
  </span>
</div>
""", unsafe_allow_html=True)
