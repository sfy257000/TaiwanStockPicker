# -*- coding: utf-8 -*-
"""
台股選股分析系統 - Streamlit 網頁版
"""

import streamlit as st
import sys
import os
import time

# ── 路徑設定 ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from stock_list import (
    get_all_stocks, get_stock_count, get_stocks_by_category,
    load_cache, export_stock_list_to_file, STOCK_DATA_WITH_CATEGORIES,
    _INDUSTRY_TO_CATEGORY_MAP
)
from data_fetcher import DataFetcher
from technical_indicators import TechnicalIndicators
from institutional_tracker import InstitutionalTracker
from price_volume_alert import PriceVolumeAlert
from support_resistance import SupportResistance
from history_saver import HistorySaver

# ── 頁面設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="台股選股分析系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",  # 永遠展開
)

# ── 全域樣式 ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+TC:wght@400;500;700&display=swap');

:root {
    --bg:       #0a0e14;
    --surface:  #111720;
    --border:   #1e2d3d;
    --text:     #cdd9e5;
    --muted:    #637083;
    --accent:   #e6b450;
    --green:    #3fb950;
    --red:      #f85149;
    --blue:     #58a6ff;
    --purple:   #bc8cff;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Noto Sans TC', sans-serif;
}

/* 側邊欄 */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* 頂部標題列 */
.top-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 18px 0 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
}
.top-bar h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.04em;
    margin: 0;
}
.top-bar .subtitle {
    font-size: 0.78rem;
    color: var(--muted);
    font-family: 'IBM Plex Mono', monospace;
}

/* 指標卡片 */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
}
.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--accent);
}
.kpi-label {
    font-size: 0.72rem;
    color: var(--muted);
    font-family: 'IBM Plex Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    color: var(--accent);
    line-height: 1;
}
.kpi-sub {
    font-size: 0.72rem;
    color: var(--muted);
    margin-top: 4px;
}

/* 區塊標題 */
.section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin: 28px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

/* 股票列 */
.stock-row {
    display: grid;
    grid-template-columns: 80px 120px 90px 90px 120px 1fr 100px;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
    gap: 8px;
}
.stock-row:hover { background: rgba(230,180,80,0.04); }
.stock-row.header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 2px solid var(--border);
}
.code { font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: var(--blue); font-size: 0.9rem; }
.name { color: var(--text); font-size: 0.85rem; }
.price { font-family: 'IBM Plex Mono', monospace; color: var(--text); font-size: 0.9rem; }
.up   { color: var(--red) !important; font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; }
.down { color: var(--green) !important; font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; }
.vol  { color: var(--muted); font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; }

/* 評分條 */
.score-bar-wrap { display: flex; align-items: center; gap: 8px; }
.score-bar {
    height: 6px;
    border-radius: 3px;
    background: var(--border);
    flex: 1;
    overflow: hidden;
}
.score-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.4s ease;
}
.score-num { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; min-width: 28px; text-align: right; }

/* 標籤 */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.badge-fire  { background: rgba(248,81,73,0.15);  color: var(--red); }
.badge-buy   { background: rgba(63,185,80,0.15);  color: var(--green); }
.badge-hold  { background: rgba(88,166,255,0.15); color: var(--blue); }
.badge-pass  { background: rgba(99,112,131,0.15); color: var(--muted); }

/* 詳情卡 */
.detail-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 12px;
}
.detail-card h3 {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--accent);
    font-size: 1rem;
    margin: 0 0 16px;
}
.ind-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}
.ind-item { text-align: center; }
.ind-label { font-size: 0.7rem; color: var(--muted); font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; }
.ind-val { font-size: 1.2rem; font-weight: 700; font-family: 'IBM Plex Mono', monospace; color: var(--text); }

/* 警示 */
.alert-up   { background: rgba(248,81,73,0.08); border-left: 3px solid var(--red);   padding: 8px 12px; border-radius: 4px; margin: 4px 0; font-size: 0.85rem; }
.alert-down { background: rgba(63,185,80,0.08); border-left: 3px solid var(--green); padding: 8px 12px; border-radius: 4px; margin: 4px 0; font-size: 0.85rem; }

/* 隱藏 Streamlit 預設元件 */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* 隱藏側邊欄收合按鈕，讓側邊欄永遠固定展開 */
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }

/* 按鈕 */
.stButton > button {
    background: var(--accent) !important;
    color: #0a0e14 !important;
    border: none !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

/* selectbox / slider */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: var(--bg) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}
</style>
""", unsafe_allow_html=True)


# ── 分析核心函數 ──────────────────────────────────────────
@st.cache_resource
def get_shared_fetcher():
    return DataFetcher()

def analyze_one(code, name, fetcher, tech_ind, inst_tracker, pv_alert, sr_calc):
    try:
        price_data = fetcher.get_stock_price(code)
        if not price_data or price_data['price'] == 0:
            return None

        institutional_data = fetcher.get_institutional_investors(code)
        historical_data    = fetcher.get_historical_price(code, days=60)

        tech_score, tech_reasons = 0, []
        tech_indicators = None
        if historical_data:
            tech_indicators = tech_ind.calculate_all(historical_data)
            if tech_indicators:
                tech_score, tech_reasons = tech_ind.get_technical_score(tech_indicators)

        inst_result = inst_tracker.analyze_institutional(institutional_data)
        pv_result   = pv_alert.check_alerts(price_data, historical_data)

        sr_data, sr_score, sr_reasons = None, 0, []
        if historical_data:
            sr_data = sr_calc.calculate(historical_data)
            if sr_data:
                sr_score, sr_reasons = sr_calc.get_support_resistance_score(sr_data)

        w = CONFIG['weights']
        total_score = round(
            tech_score             * w['technical'] +
            inst_result['score']   * w['institutional'] +
            pv_result['score']     * w['price_volume'] +
            sr_score               * w['support_resistance']
        )

        prev = price_data['prev_close']
        change_pct = ((price_data['price'] - prev) / prev * 100) if prev > 0 else 0

        return {
            'code': code, 'name': name,
            'price': price_data['price'],
            'change_pct': change_pct,
            'volume': price_data['volume'],
            'high': price_data['high'],
            'low': price_data['low'],
            'is_premarket': price_data.get('is_premarket', False),
            'tech_score': tech_score,
            'inst_score': inst_result['score'],
            'pv_score': pv_result['score'],
            'sr_score': sr_score,
            'total_score': total_score,
            'reasons': tech_reasons + inst_result['reasons'] + pv_result['reasons'] + sr_reasons,
            'institutional': institutional_data,
            'indicators': tech_indicators,
            'support_resistance': sr_data,
        }
    except Exception:
        return None


def run_analysis(stocks):
    fetcher      = get_shared_fetcher()
    tech_ind     = TechnicalIndicators()
    inst_tracker = InstitutionalTracker()
    pv_alert     = PriceVolumeAlert()
    sr_calc      = SupportResistance()

    total    = len(stocks)
    results  = []
    prog_bar = st.progress(0, text="準備中…")
    status   = st.empty()

    for i, (code, name) in enumerate(stocks, 1):
        status.caption(f"分析中：{code} {name}")
        r = analyze_one(code, name, fetcher, tech_ind, inst_tracker, pv_alert, sr_calc)
        if r:
            results.append(r)
        prog_bar.progress(i / total, text=f"分析中… {i}/{total}")

    prog_bar.empty()
    status.empty()
    return results


# ── 輔助渲染函數 ──────────────────────────────────────────
def score_badge(score):
    if score >= 25:
        return '<span class="badge badge-fire">🔥 強買</span>'
    elif score >= 15:
        return '<span class="badge badge-buy">✓ 買進</span>'
    elif score >= 8:
        return '<span class="badge badge-hold">○ 觀望</span>'
    else:
        return '<span class="badge badge-pass">× 不建議</span>'

def score_color(score):
    if score >= 25: return '#f85149'
    if score >= 15: return '#3fb950'
    if score >= 8:  return '#58a6ff'
    return '#637083'

def change_class(pct):
    return 'up' if pct > 0 else ('down' if pct < 0 else 'price')

def fmt_vol(v):
    if v >= 10000: return f'{v/10000:.1f}萬'
    if v >= 1000:  return f'{v/1000:.1f}千'
    return str(v)


# ── 側邊欄 ────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("### 📊 分析設定")
        st.markdown("---")

        mode = st.selectbox(
            "分析模式",
            ["全部股票", "依類別篩選", "隨機抽樣"],
            key="mode"
        )

        selected_cats = []
        if mode == "依類別篩選":
            cat_options = sorted(set(_INDUSTRY_TO_CATEGORY_MAP.values()))
            selected_cats = st.multiselect("選擇類別", cat_options, key="cats")

        random_n = 50
        if mode == "隨機抽樣":
            random_n = st.slider("抽樣數量", 10, 200, 50, 10, key="random_n")

        st.markdown("---")
        st.markdown("### ⚙️ 評分權重")

        w_tech = st.slider("技術面",   0, 100, 30, 5, key="w_tech")
        w_inst = st.slider("籌碼面",   0, 100, 30, 5, key="w_inst")
        w_pv   = st.slider("價量",     0, 100, 25, 5, key="w_pv")
        w_sr   = st.slider("支撐壓力", 0, 100, 15, 5, key="w_sr")
        total_w = w_tech + w_inst + w_pv + w_sr
        if total_w > 0:
            CONFIG["weights"]["technical"]          = w_tech / total_w
            CONFIG["weights"]["institutional"]      = w_inst / total_w
            CONFIG["weights"]["price_volume"]       = w_pv   / total_w
            CONFIG["weights"]["support_resistance"] = w_sr   / total_w

        st.markdown("---")
        st.markdown("### 🔍 結果篩選")
        min_score = st.slider("最低評分顯示", -20, 50, 0, 1, key="min_score")
        top_n     = st.slider("顯示筆數", 10, 200, 50, 10, key="top_n")

        st.markdown("---")
        st.markdown("### 🚫 黑名單")
        blacklist_input = st.text_input("輸入代碼（逗號分隔）", placeholder="例：2330,2317", key="blacklist")
        if blacklist_input:
            codes = [c.strip() for c in blacklist_input.split(",") if c.strip()]
            CONFIG["list_filter"]["blacklist"]        = codes
            CONFIG["list_filter"]["enable_blacklist"] = True
        else:
            CONFIG["list_filter"]["enable_blacklist"] = False

        st.markdown("---")
        run_btn = st.button("▶  開始分析", use_container_width=True, key="run_btn")

        st.markdown("---")
        st.markdown("### 🔄 更新股票清單")
        min_vol = st.number_input(
            "最低成交量（張）", min_value=100, max_value=50000,
            value=1000, step=100, key="min_vol",
            help="過濾掉成交量太低的冷門股"
        )
        update_btn = st.button("更新清單", use_container_width=True, key="update_btn")

        count = get_stock_count()
        if count > 0:
            st.caption(f"目前清單：{count} 檔股票")
        else:
            st.caption("⚠️ 股票清單是空的，請先更新")

    return mode, selected_cats, random_n, min_score, top_n, run_btn, update_btn, int(min_vol)


# ── 主頁面：KPI 卡 ─────────────────────────────────────────
def render_kpi(results):
    buy     = [r for r in results if r['total_score'] >= 15]
    strong  = [r for r in results if r['total_score'] >= 25]
    limit_u = [r for r in results if r['change_pct'] >= 9.5]
    limit_d = [r for r in results if r['change_pct'] <= -9.5]

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">分析股票</div>
            <div class="kpi-value">{len(results)}</div>
            <div class="kpi-sub">今日掃描</div>
        </div>
        <div class="kpi-card" style="--accent:#3fb950">
            <div class="kpi-label">推薦買進</div>
            <div class="kpi-value" style="color:#3fb950">{len(buy)}</div>
            <div class="kpi-sub">其中強買 {len(strong)} 檔</div>
        </div>
        <div class="kpi-card" style="--accent:#f85149">
            <div class="kpi-label">漲停股</div>
            <div class="kpi-value" style="color:#f85149">{len(limit_u)}</div>
            <div class="kpi-sub">跌停 {len(limit_d)} 檔</div>
        </div>
        <div class="kpi-card" style="--accent:#58a6ff">
            <div class="kpi-label">平均評分</div>
            <div class="kpi-value" style="color:#58a6ff">{sum(r['total_score'] for r in results)/len(results):.1f}</div>
            <div class="kpi-sub">滿分約 50 分</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── 主頁面：推薦表格 ──────────────────────────────────────
def render_table(results, min_score, top_n):
    import plotly.graph_objects as go

    filtered = [r for r in results if r['total_score'] >= min_score]
    filtered.sort(key=lambda x: x['total_score'], reverse=True)
    filtered = filtered[:top_n]

    st.markdown('<div class="section-title">推薦清單</div>', unsafe_allow_html=True)

    # 表頭
    st.markdown("""
    <div class="stock-row header">
        <span>代碼</span>
        <span>名稱</span>
        <span>現價</span>
        <span>漲跌%</span>
        <span>成交量</span>
        <span>評分</span>
        <span>建議</span>
    </div>
    """, unsafe_allow_html=True)

    for r in filtered:
        sc   = r['total_score']
        pct  = r['change_pct']
        cc   = change_class(pct)
        pct_sign = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
        bar_w = max(0, min(100, (sc + 20) * 100 / 70))
        fill_color = score_color(sc)

        st.markdown(f"""
        <div class="stock-row">
            <span class="code">{r['code']}</span>
            <span class="name">{r['name']}</span>
            <span class="price">{r['price']:.1f}</span>
            <span class="{cc}">{pct_sign}</span>
            <span class="vol">{fmt_vol(r['volume'])}張</span>
            <div class="score-bar-wrap">
                <div class="score-bar">
                    <div class="score-fill" style="width:{bar_w}%;background:{fill_color}"></div>
                </div>
                <span class="score-num" style="color:{fill_color}">{sc}</span>
            </div>
            {score_badge(sc)}
        </div>
        """, unsafe_allow_html=True)

    # 評分分布圖 — 最多顯示30筆，柱子才夠寬
    if filtered:
        st.markdown('<div class="section-title">評分分布（前30名）</div>', unsafe_allow_html=True)
        chart_data = filtered[:30]
        if len(filtered) > 30:
            st.caption(f"顯示評分最高的 30 筆（共 {len(filtered)} 筆）")

        scores = [r['total_score'] for r in chart_data]
        # 用 "代碼 名稱" 當 label，強制加空格前綴讓 plotly 當文字處理
        labels = [f"{r['code']} {r['name']}" for r in chart_data]
        colors = [score_color(s) for s in scores]

        fig = go.Figure(go.Bar(
            x=labels,
            y=scores,
            marker_color=colors,
            marker_line_width=0,
            text=scores,               # 柱子上顯示分數
            textposition='outside',
            textfont=dict(size=10, color='#cdd9e5'),
            hovertemplate='<b>%{x}</b><br>評分: %{y}<extra></extra>',
        ))
        fig.update_layout(
            paper_bgcolor='#0a0e14',
            plot_bgcolor='#0a0e14',
            font=dict(color='#637083', family='IBM Plex Mono', size=11),
            margin=dict(l=40, r=10, t=30, b=80),
            height=320,
            xaxis=dict(
                type='category',       # 強制當文字，不當數字
                showgrid=False,
                tickfont=dict(size=10),
                tickangle=-40,
            ),
            yaxis=dict(
                showgrid=True, gridcolor='#1e2d3d',
                zeroline=True, zerolinecolor='#1e2d3d',
                range=[min(0, min(scores)) - 2, max(scores) + 5],
            ),
            bargap=0.25,
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# ── 主頁面：技術指標詳情 ─────────────────────────────────
def render_technicals(results):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    st.markdown('<div class="section-title">技術指標詳情 (前10名)</div>', unsafe_allow_html=True)

    top10 = sorted(results, key=lambda x: x['total_score'], reverse=True)[:10]
    top10 = [r for r in top10 if r['indicators']]

    if not top10:
        st.info("沒有足夠的技術指標資料")
        return

    cols = st.columns(2)
    for idx, r in enumerate(top10):
        ind = r['indicators']
        rsi = ind.get('rsi', {})
        kd  = ind.get('kd', {})
        macd = ind.get('macd', {})
        bb  = ind.get('bollinger', {})

        with cols[idx % 2]:
            rsi_val  = rsi.get('rsi', 50)
            k_val    = kd.get('k', 50)
            d_val    = kd.get('d', 50)
            macd_val = macd.get('hist', 0)
            bb_pos   = bb.get('position', 50)

            rsi_color  = '#f85149' if rsi_val > 70 else ('#3fb950' if rsi_val < 30 else '#58a6ff')
            macd_color = '#f85149' if macd_val > 0 else '#3fb950'

            st.markdown(f"""
            <div class="detail-card">
                <h3>{r['code']} {r['name']} <small style="color:#637083;font-size:0.75rem">評分 {r['total_score']}</small></h3>
                <div class="ind-grid">
                    <div class="ind-item">
                        <div class="ind-label">RSI(14)</div>
                        <div class="ind-val" style="color:{rsi_color}">{rsi_val:.1f}</div>
                    </div>
                    <div class="ind-item">
                        <div class="ind-label">K / D</div>
                        <div class="ind-val">{k_val:.1f} / {d_val:.1f}</div>
                    </div>
                    <div class="ind-item">
                        <div class="ind-label">MACD柱</div>
                        <div class="ind-val" style="color:{macd_color}">{macd_val:+.3f}</div>
                    </div>
                    <div class="ind-item">
                        <div class="ind-label">布林位置</div>
                        <div class="ind-val">{bb_pos:.0f}%</div>
                    </div>
                    <div class="ind-item">
                        <div class="ind-label">技術分</div>
                        <div class="ind-val" style="color:{score_color(r['tech_score'])}">{r['tech_score']}</div>
                    </div>
                    <div class="ind-item">
                        <div class="ind-label">籌碼分</div>
                        <div class="ind-val" style="color:{score_color(r['inst_score'])}">{r['inst_score']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── 主頁面：外資追蹤 ──────────────────────────────────────
def render_institutional(results):
    import plotly.graph_objects as go

    st.markdown('<div class="section-title">外資籌碼 TOP 15</div>', unsafe_allow_html=True)

    inst_data = []
    for r in results:
        if r['institutional']:
            inst = r['institutional']
            inst_data.append({
                'code': r['code'],
                'name': r['name'],
                'foreign': inst.get('foreign', 0),
                'trust':   inst.get('investment_trust', 0),
                'dealer':  inst.get('dealer', 0),
                'total':   inst.get('total', 0),
            })

    if not inst_data:
        st.info("無法人資料")
        return

    inst_data.sort(key=lambda x: abs(x['total']), reverse=True)
    top15 = inst_data[:15]

    labels  = [f"{d['code']}" for d in top15]
    foreign = [d['foreign'] for d in top15]
    trust   = [d['trust']   for d in top15]
    dealer  = [d['dealer']  for d in top15]

    fig = go.Figure()
    fig.add_trace(go.Bar(name='外資', x=labels, y=foreign,
                         marker_color='#58a6ff', marker_line_width=0))
    fig.add_trace(go.Bar(name='投信', x=labels, y=trust,
                         marker_color='#bc8cff', marker_line_width=0))
    fig.add_trace(go.Bar(name='自營', x=labels, y=dealer,
                         marker_color='#e6b450', marker_line_width=0))

    fig.update_layout(
        barmode='group',
        paper_bgcolor='#0a0e14',
        plot_bgcolor='#0a0e14',
        font=dict(color='#637083', family='IBM Plex Mono', size=11),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#cdd9e5'),
                    orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=50, r=10, t=30, b=60),
        height=340,
        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=10), type='category'),
        yaxis=dict(showgrid=True, gridcolor='#1e2d3d',
                   title=dict(text='張', font=dict(color='#637083'))),
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# ── 主頁面：漲跌停 ────────────────────────────────────────
def render_alerts(results):
    limit_up   = [r for r in results if r['change_pct'] >= 9.5]
    near_up    = [r for r in results if 8.5 <= r['change_pct'] < 9.5]
    limit_down = [r for r in results if r['change_pct'] <= -9.5]

    st.markdown('<div class="section-title">漲跌停監控</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🔥 漲停**")
        if limit_up:
            for r in limit_up:
                st.markdown(f'<div class="alert-up">🔴 <b>{r["code"]}</b> {r["name"]} &nbsp; {r["price"]:.1f}元 &nbsp; <b>{r["change_pct"]:+.2f}%</b></div>', unsafe_allow_html=True)
        else:
            st.caption("今日無漲停")
        if near_up:
            st.markdown("**⚡ 接近漲停**")
            for r in near_up:
                st.markdown(f'<div class="alert-up" style="opacity:0.7">🟡 <b>{r["code"]}</b> {r["name"]} &nbsp; {r["change_pct"]:+.2f}%</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("**📉 跌停**")
        if limit_down:
            for r in limit_down:
                st.markdown(f'<div class="alert-down">🟢 <b>{r["code"]}</b> {r["name"]} &nbsp; {r["price"]:.1f}元 &nbsp; <b>{r["change_pct"]:+.2f}%</b></div>', unsafe_allow_html=True)
        else:
            st.caption("今日無跌停")


# ── 理由展開區 ────────────────────────────────────────────
def render_reasons(results):
    st.markdown('<div class="section-title">強買股票詳細理由</div>', unsafe_allow_html=True)
    strong = [r for r in results if r['total_score'] >= 25]
    strong.sort(key=lambda x: x['total_score'], reverse=True)

    if not strong:
        st.info("目前沒有評分 ≥ 25 的股票")
        return

    for r in strong[:10]:
        with st.expander(f"🔥 {r['code']} {r['name']}  —  評分 {r['total_score']}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("技術", r['tech_score'])
            c2.metric("籌碼", r['inst_score'])
            c3.metric("價量", r['pv_score'])
            c4.metric("支撐", r['sr_score'])
            st.markdown("**訊號：**")
            for reason in r['reasons']:
                st.markdown(f"- {reason}")
            if r['support_resistance']:
                sr = r['support_resistance']
                if sr.get('support'):
                    st.markdown(f"**支撐位：** {', '.join(f'{p:.1f}' for p in sr['support'][:3])}")
                if sr.get('resistance'):
                    st.markdown(f"**壓力位：** {', '.join(f'{p:.1f}' for p in sr['resistance'][:3])}")


# ── 主程式 ────────────────────────────────────────────────
def main():
    # 標題列
    st.markdown("""
    <div class="top-bar">
        <div>
            <h1>台股選股分析系統</h1>
            <div class="subtitle">TAIWAN STOCK PICKER  ·  POWERED BY TWSE/TPEX API</div>
        </div>
    </div>
    """, unsafe_allow_html=True)



    mode, selected_cats, random_n, min_score, top_n, run_btn, update_btn, min_vol = render_sidebar()

    # session state 初始化
    if "results" not in st.session_state:
        st.session_state.results = []
    if "analyzed" not in st.session_state:
        st.session_state.analyzed = False

    # 更新股票清單
    if update_btn:
        with st.spinner(f"正在從 TWSE API 更新股票清單（成交量 ≥ {min_vol} 張）…"):
            export_stock_list_to_file(min_vol)
        st.success(f"✓ 股票清單已更新，共 {get_stock_count()} 檔")

    # 股票清單狀態
    if get_stock_count() == 0:
        st.warning("⚠️ 股票清單是空的，請先點側邊欄的「更新清單」")
        return

    # 開始分析
    if run_btn:
        if mode == "全部股票":
            stocks = get_all_stocks()
        elif mode == "依類別篩選":
            if not selected_cats:
                st.warning("請先選擇至少一個類別")
                stocks = []
            else:
                stocks = get_stocks_by_category(",".join(selected_cats))
        else:
            import random
            all_s = get_all_stocks()
            random.shuffle(all_s)
            stocks = all_s[:random_n]

        if stocks:
            st.info(f"開始分析 **{len(stocks)}** 檔股票，請稍候…")
            results = run_analysis(stocks)
            st.session_state.results  = results
            st.session_state.analyzed = True
            # 不用 rerun，讓下方直接顯示

    # 顯示結果
    if st.session_state.analyzed and st.session_state.results:
        results = st.session_state.results
        render_kpi(results)

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["📋 推薦清單", "📊 技術指標", "🏛 外資籌碼", "🚨 漲跌停", "🔍 詳細理由"]
        )
        with tab1: render_table(results, min_score, top_n)
        with tab2: render_technicals(results)
        with tab3: render_institutional(results)
        with tab4: render_alerts(results)
        with tab5: render_reasons(results)

        if CONFIG["output"]["save_history"]:
            HistorySaver().save_analysis(results)

    elif not st.session_state.analyzed:
        st.markdown("""
        <div style="text-align:center; padding: 80px 0; color: #637083;">
            <div style="font-size:3rem; margin-bottom:16px">📈</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1rem; margin-bottom:8px; color:#cdd9e5">
                準備好了
            </div>
            <div style="font-size:0.85rem">在左側設定參數，然後點擊「開始分析」</div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
