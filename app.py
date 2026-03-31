# -*- coding: utf-8 -*-
"""台股選股分析系統 - Streamlit 介面"""

import os
import random
import re
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import requests
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from data_fetcher import DataFetcher
from history_saver import HistorySaver
from institutional_tracker import InstitutionalTracker
from price_volume_alert import PriceVolumeAlert
from stock_list import (
    _INDUSTRY_TO_CATEGORY_MAP,
    STOCK_DATA_WITH_CATEGORIES,
    export_stock_list_to_file,
    get_all_stocks,
    get_stock_count,
    get_stocks_by_category,
    load_cache,
)
from support_resistance import SupportResistance
from technical_indicators import TechnicalIndicators

st.set_page_config(
    page_title='台股選股分析系統',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='expanded',
)

PAGE_OPTIONS = ['分析總覽', '技術圖表', '警報中心', '產業熱度', '回測與模擬', '每日排行', '分享卡片']


@st.cache_resource
def get_shared_fetcher() -> DataFetcher:
    return DataFetcher()


def score_badge(score: int) -> str:
    if score >= 25:
        return '🔥 強力買進'
    if score >= 15:
        return '✅ 建議買進'
    if score >= 8:
        return '🟡 觀察'
    return '⚪ 略過'


def fmt_vol(v: int) -> str:
    if v >= 10000:
        return f'{v / 10000:.1f}萬'
    if v >= 1000:
        return f'{v / 1000:.1f}千'
    return str(v)


@st.cache_data(ttl=1800)
def fetch_twse_news() -> list[dict]:
    news: list[dict] = []
    try:
        url = 'https://openapi.twse.com.tw/v1/news/news'
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False)
        for item in resp.json()[:100]:
            title = item.get('title', '') or item.get('Title', '')
            date = item.get('date', '') or item.get('Date', '')
            if title:
                news.append({'title': title, 'date': date})
    except Exception:
        pass
    return news


def get_news_sentiment(code: str, name: str, news_list: list[dict]) -> tuple[list[dict], int]:
    pos_kw = ['成長', '創高', '利多', '突破', '上修', '買超', '營收增', '獲利增']
    neg_kw = ['下修', '虧損', '衰退', '跌破', '利空', '賣超', '營收減', '獲利減']

    related = []
    total_score = 0
    for n in news_list:
        title = n.get('title', '')
        if code in title or name in title:
            pos = sum(1 for k in pos_kw if k in title)
            neg = sum(1 for k in neg_kw if k in title)
            sentiment = pos - neg
            related.append({**n, 'sentiment': sentiment})
            total_score += sentiment
    return related, total_score


def analyze_one(
    code: str,
    name: str,
    fetcher: DataFetcher,
    tech_ind: TechnicalIndicators,
    inst_tracker: InstitutionalTracker,
    pv_alert: PriceVolumeAlert,
    sr_calc: SupportResistance,
    news_list: list[dict],
) -> dict | None:
    try:
        price_data = fetcher.get_stock_price(code)
        historical_data = fetcher.get_historical_price(code, days=60)

        if (not price_data or price_data.get('price', 0) == 0) and historical_data:
            last = historical_data[-1]
            prev = historical_data[-2]['close'] if len(historical_data) >= 2 else last['close']
            price_data = {
                'price': last['close'],
                'open': last['open'],
                'high': last['high'],
                'low': last['low'],
                'volume': last['volume'],
                'prev_close': prev,
                'is_premarket': False,
            }

        if not price_data or price_data.get('price', 0) == 0:
            return None

        if not historical_data:
            historical_data = []

        tech_indicators = tech_ind.calculate_all(historical_data) if historical_data else None
        tech_score, tech_reasons = tech_ind.get_technical_score(tech_indicators) if tech_indicators else (0, [])

        inst_data = fetcher.get_institutional_investors(code)
        inst_result = inst_tracker.analyze_institutional(inst_data)
        inst_score = inst_result['score']
        inst_reasons = inst_result['reasons']

        pv_result = pv_alert.check_alerts(price_data, historical_data)
        pv_score = pv_result['score']
        pv_reasons = pv_result['reasons']

        sr_data = sr_calc.calculate(historical_data) if historical_data else None
        sr_score, sr_reasons = sr_calc.get_support_resistance_score(sr_data) if sr_data else (0, [])

        score = (
            tech_score * CONFIG['weights']['technical']
            + inst_score * CONFIG['weights']['institutional']
            + pv_score * CONFIG['weights']['price_volume']
            + sr_score * CONFIG['weights']['support_resistance']
        )

        related_news, news_score = get_news_sentiment(code, name, news_list)
        total_score = int(round(score + news_score))

        prev_close = float(price_data.get('prev_close') or 0)
        if prev_close <= 0 and historical_data:
            if len(historical_data) >= 2:
                prev_close = float(historical_data[-2].get('close') or 0)
            else:
                prev_close = float(historical_data[-1].get('close') or 0)
        price = float(price_data.get('price') or 0)
        change_pct = ((price - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0

        return {
            'code': code,
            'name': name,
            'price': price,
            'volume': int(price_data.get('volume') or 0),
            'change_pct': change_pct,
            'tech_score': tech_score,
            'inst_score': inst_score,
            'pv_score': pv_score,
            'sr_score': sr_score,
            'news_score': news_score,
            'total_score': total_score,
            'reasons': tech_reasons + inst_reasons + pv_reasons + sr_reasons,
            'institutional': inst_data,
            'alerts': pv_result,
            'support_resistance': sr_data,
            'indicators': tech_indicators,
            'news': related_news,
        }
    except Exception:
        return None


def run_analysis(stocks: list[tuple[str, str]], max_workers: int | None = None) -> list[dict]:
    fetcher = get_shared_fetcher()
    tech_ind = TechnicalIndicators()
    inst_tracker = InstitutionalTracker()
    pv_alert = PriceVolumeAlert()
    sr_calc = SupportResistance()
    news_list = fetch_twse_news()

    # 預抓一次法人批次資料，後續每檔僅做字典查詢
    fetcher.fetch_institutional_batch()

    results: list[dict] = []
    total = len(stocks)
    if max_workers is None:
        max_workers = min(8, max(2, (os.cpu_count() or 4)))
    prog = st.progress(0, text=f'分析中... (並行 {max_workers} 執行緒)')

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                analyze_one, code, name, fetcher, tech_ind, inst_tracker, pv_alert, sr_calc, news_list
            )
            for code, name in stocks
        ]
        for i, future in enumerate(as_completed(futures), start=1):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except Exception:
                pass
            prog.progress(i / total, text=f'分析中... {i}/{total}')

    prog.empty()
    results.sort(key=lambda x: x['total_score'], reverse=True)
    return results


def render_sidebar():
    with st.sidebar:
        if 'page_selector' not in st.session_state or st.session_state.page_selector not in PAGE_OPTIONS:
            st.session_state.page_selector = PAGE_OPTIONS[0]
        page = st.selectbox(
            '功能頁面',
            PAGE_OPTIONS,
            key='page_selector',
        )
        st.markdown('---')
        st.markdown('### 分析設定')

        mode = st.selectbox('選股模式', ['全部股票', '依產業類別', '隨機抽樣', '自訂股票'])

        selected_cats: list[str] = []
        if mode == '依產業類別':
            cat_options = sorted(set(_INDUSTRY_TO_CATEGORY_MAP.values()))
            selected_cats = st.multiselect('產業類別', cat_options)

        random_n = 50
        if mode == '隨機抽樣':
            random_n = st.slider('抽樣數量', 10, 200, 50, 10)

        custom_codes: list[str] = []
        if mode == '自訂股票':
            custom_input = st.text_area('股票代碼（逗號/空白/換行分隔）', placeholder='2330, 2317\n2454')
            if custom_input:
                custom_codes = [c.strip() for c in re.split(r'[,\n\s]+', custom_input) if c.strip()]
            st.caption(f'已輸入 {len(custom_codes)} 檔')

        st.markdown('---')
        st.markdown('### 價格過濾')
        col1, col2 = st.columns(2)
        with col1:
            price_min = st.number_input('最低價', min_value=0, max_value=99999, value=0, step=1)
        with col2:
            price_max = st.number_input('最高價', min_value=0, max_value=99999, value=0, step=1)

        st.markdown('---')
        st.markdown('### 評分權重')
        w_tech = st.slider('技術面', 0, 100, 30, 5)
        w_inst = st.slider('法人', 0, 100, 30, 5)
        w_pv = st.slider('價量', 0, 100, 25, 5)
        w_sr = st.slider('支撐壓力', 0, 100, 15, 5)
        total_w = w_tech + w_inst + w_pv + w_sr
        if total_w > 0:
            CONFIG['weights']['technical'] = w_tech / total_w
            CONFIG['weights']['institutional'] = w_inst / total_w
            CONFIG['weights']['price_volume'] = w_pv / total_w
            CONFIG['weights']['support_resistance'] = w_sr / total_w

        st.markdown('---')
        min_score = st.slider('最低總分', -20, 50, 0, 1)
        top_n = st.slider('顯示筆數', 10, 200, 50, 10)
        max_workers = st.slider('並行執行緒數', 1, 12, min(8, max(2, (os.cpu_count() or 4))), 1)

        st.markdown('---')
        min_vol = st.number_input('更新最低成交量（張）', min_value=100, max_value=50000, value=1000, step=100)
        update_btn = st.button('更新股票清單', use_container_width=True)

        st.markdown('---')
        run_btn = st.button('開始分析', use_container_width=True, type='primary')
        st.caption(f'目前股票檔數：{get_stock_count()}')

    return (
        page,
        mode,
        selected_cats,
        random_n,
        min_score,
        top_n,
        max_workers,
        run_btn,
        update_btn,
        int(min_vol),
        int(price_min),
        int(price_max),
        custom_codes,
    )


def render_kpi(results: list[dict]) -> None:
    if not results:
        return
    buy = [r for r in results if r['total_score'] >= 15]
    strong = [r for r in results if r['total_score'] >= 25]
    avg = sum(r['total_score'] for r in results) / len(results)

    c1, c2, c3 = st.columns(3)
    c1.metric('分析股票數', len(results))
    c2.metric('建議買進', len(buy), f'強力買進 {len(strong)}')
    c3.metric('平均分數', f'{avg:.1f}')


def build_rows(results: list[dict], min_score: int, top_n: int) -> list[dict]:
    filtered = [r for r in results if r['total_score'] >= min_score]
    filtered = sorted(filtered, key=lambda x: x['total_score'], reverse=True)[:top_n]
    rows = []
    for r in filtered:
        rows.append(
            {
                '代碼': r['code'],
                '名稱': r['name'],
                '價格': round(r['price'], 2),
                '漲跌%': round(r['change_pct'], 2),
                '成交量': fmt_vol(r['volume']),
                '技術': r['tech_score'],
                '法人': r['inst_score'],
                '價量': r['pv_score'],
                '支撐壓力': r['sr_score'],
                '新聞': r['news_score'],
                '總分': r['total_score'],
                '建議': score_badge(r['total_score']),
            }
        )
    return rows


def render_table(results: list[dict], min_score: int, top_n: int) -> list[dict]:
    rows = build_rows(results, min_score, top_n)

    if not rows:
        st.info('沒有符合條件的股票。')
        return []

    st.dataframe(rows, use_container_width=True, hide_index=True)

    filtered = [r for r in results if r['total_score'] >= min_score]
    filtered = sorted(filtered, key=lambda x: x['total_score'], reverse=True)[:top_n]
    with st.expander('查看前 10 檔分析理由'):
        for r in filtered[:10]:
            st.markdown(f"**{r['code']} {r['name']}** | 分數: {r['total_score']}")
            for reason in r.get('reasons', [])[:6]:
                st.write(f'- {reason}')
    return rows


def render_market_board(results: list[dict]) -> None:
    if not results:
        return
    st.markdown('### 🔥 熱門榜單')
    c1, c2, c3 = st.columns(3)
    top_up = sorted(results, key=lambda x: x['change_pct'], reverse=True)[:5]
    top_down = sorted(results, key=lambda x: x['change_pct'])[:5]
    top_volume = sorted(results, key=lambda x: x['volume'], reverse=True)[:5]

    with c1:
        st.caption('漲幅 Top 5')
        for r in top_up:
            st.write(f"{r['code']} {r['name']} {r['change_pct']:+.2f}%")
    with c2:
        st.caption('跌幅 Top 5')
        for r in top_down:
            st.write(f"{r['code']} {r['name']} {r['change_pct']:+.2f}%")
    with c3:
        st.caption('成交量 Top 5')
        for r in top_volume:
            st.write(f"{r['code']} {r['name']} {fmt_vol(r['volume'])}")


def generate_ai_summary(result: dict) -> str:
    score = result.get('total_score', 0)
    change = result.get('change_pct', 0.0)
    tech = result.get('tech_score', 0)
    inst = result.get('inst_score', 0)
    pv = result.get('pv_score', 0)
    sr = result.get('sr_score', 0)

    if score >= 25:
        level = '強勢候選'
    elif score >= 15:
        level = '偏多觀察'
    elif score >= 8:
        level = '中性觀察'
    else:
        level = '保守觀望'

    drivers = sorted(
        [('技術', tech), ('法人', inst), ('價量', pv), ('支撐壓力', sr)],
        key=lambda x: x[1],
        reverse=True,
    )
    top_driver = drivers[0][0]
    weak_driver = sorted(drivers, key=lambda x: x[1])[0][0]

    risk_text = '短線波動偏大' if abs(change) >= 5 else '波動相對可控'
    return (
        f"{result['code']} {result['name']} 目前屬於「{level}」，"
        f"主要加分來源是{top_driver}，相對弱項是{weak_driver}。"
        f"當日漲跌 {change:+.2f}%（{risk_text}），建議搭配停損與倉位控管。"
    )


def render_ai_summary_card(results: list[dict]) -> None:
    st.markdown('### 🤖 AI 解讀卡')
    if not results:
        st.info('請先執行分析。')
        return
    options = [f"{r['code']} {r['name']}" for r in results[:50]]
    selected = st.selectbox('選擇股票生成解讀', options, key='ai_summary_stock')
    code = selected.split(' ')[0]
    target = next((r for r in results if r['code'] == code), None)
    if not target:
        st.info('找不到資料。')
        return
    summary = generate_ai_summary(target)
    st.success(summary)
    st.caption('此解讀卡為規則式自動生成，僅供研究參考。')


def render_watchlist(results: list[dict]) -> None:
    st.markdown('### ⭐ 自選股追蹤')
    watchlist_input = st.text_input('輸入自選代碼（逗號分隔）', placeholder='2330,2317,2454')
    if not watchlist_input:
        return
    codes = {c.strip() for c in watchlist_input.split(',') if c.strip()}
    picked = [r for r in results if r['code'] in codes]
    if not picked:
        st.info('自選清單目前沒有命中分析結果。')
        return
    picked_rows = build_rows(picked, min_score=-999, top_n=999)
    st.dataframe(picked_rows, use_container_width=True, hide_index=True)


def render_kd_price_chart(results: list[dict]) -> None:
    if not results:
        return

    st.markdown('### 📈 KD 與歷史股價折線圖')
    options = [f"{r['code']} {r['name']}" for r in results]
    selected = st.selectbox('選擇股票', options, key='kd_price_chart_stock')
    code = selected.split(' ')[0]

    fetcher = get_shared_fetcher()
    hist = fetcher.get_historical_price(code, days=120)
    if not hist or len(hist) < 20:
        st.info('歷史資料不足，無法繪製 KD。')
        return

    dates = [h['date'] for h in hist]
    closes = [h['close'] for h in hist]
    highs = [h['high'] for h in hist]
    lows = [h['low'] for h in hist]

    tech = TechnicalIndicators()
    k_values: list[float] = []
    d_values: list[float] = []
    for i in range(len(hist)):
        window_highs = highs[: i + 1]
        window_lows = lows[: i + 1]
        window_closes = closes[: i + 1]
        kd = tech.calculate_kd(window_highs, window_lows, window_closes)
        k_values.append(float(kd.get('k', 50)))
        d_values.append(float(kd.get('d', 50)))

    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.08,
        subplot_titles=('歷史收盤價', 'KD 指標'),
    )
    fig.add_trace(
        go.Scatter(x=dates, y=closes, mode='lines', name='收盤價', line=dict(color='#1f77b4', width=2)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=k_values, mode='lines', name='K', line=dict(color='#e67e22', width=1.8)),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=d_values, mode='lines', name='D', line=dict(color='#16a085', width=1.8)),
        row=2,
        col=1,
    )
    fig.add_hline(y=80, line_dash='dot', line_color='red', row=2, col=1)
    fig.add_hline(y=20, line_dash='dot', line_color='green', row=2, col=1)
    fig.update_layout(height=620, margin=dict(l=30, r=20, t=40, b=20), legend=dict(orientation='h'))
    fig.update_yaxes(title_text='價格', row=1, col=1)
    fig.update_yaxes(title_text='KD', range=[0, 100], row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"最新 KD：K={k_values[-1]:.2f} / D={d_values[-1]:.2f}")


def aggregate_weekly(hist: list[dict]) -> list[dict]:
    weekly_map: dict[str, dict] = {}
    for row in hist:
        dt = datetime.strptime(row['date'], '%Y-%m-%d')
        key = f'{dt.isocalendar().year}-W{dt.isocalendar().week:02d}'
        if key not in weekly_map:
            weekly_map[key] = {
                'date': row['date'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row.get('volume', 0),
            }
        else:
            w = weekly_map[key]
            w['high'] = max(w['high'], row['high'])
            w['low'] = min(w['low'], row['low'])
            w['close'] = row['close']
            w['volume'] += row.get('volume', 0)
    return [weekly_map[k] for k in sorted(weekly_map.keys())]


def timeframe_signal(hist: list[dict], tech: TechnicalIndicators) -> tuple[str, dict]:
    indicators = tech.calculate_all(hist) if hist else None
    if not indicators:
        return '資料不足', {}
    ma20 = indicators.get('ma', {}).get('ma20')
    kd = indicators.get('kd', {})
    k = kd.get('k', 50)
    d = kd.get('d', 50)
    last_close = hist[-1]['close'] if hist else 0
    if ma20 and last_close > ma20 and k > d:
        return '偏多', indicators
    if ma20 and last_close < ma20 and k < d:
        return '偏空', indicators
    return '盤整', indicators


def render_multi_timeframe(results: list[dict]) -> None:
    st.markdown('### 🕒 多時間框架（日線 / 週線）')
    if not results:
        st.info('請先執行分析。')
        return
    options = [f"{r['code']} {r['name']}" for r in results]
    selected = st.selectbox('多時間框架股票', options, key='mtf_stock')
    code = selected.split(' ')[0]

    fetcher = get_shared_fetcher()
    hist_daily = fetcher.get_historical_price(code, days=180)
    if not hist_daily or len(hist_daily) < 30:
        st.info('歷史資料不足。')
        return
    hist_weekly = aggregate_weekly(hist_daily)
    tech = TechnicalIndicators()

    daily_sig, daily_ind = timeframe_signal(hist_daily, tech)
    weekly_sig, weekly_ind = timeframe_signal(hist_weekly, tech)

    c1, c2 = st.columns(2)
    with c1:
        st.metric('日線訊號', daily_sig)
        kd = daily_ind.get('kd', {})
        st.caption(f"K={kd.get('k', 0):.2f} / D={kd.get('d', 0):.2f}")
    with c2:
        st.metric('週線訊號', weekly_sig)
        kd = weekly_ind.get('kd', {})
        st.caption(f"K={kd.get('k', 0):.2f} / D={kd.get('d', 0):.2f}")


def render_comparison_mode(results: list[dict]) -> None:
    st.markdown('### 🆚 比較模式（多股同圖）')
    if not results:
        st.info('請先執行分析。')
        return

    options = [f"{r['code']} {r['name']}" for r in results[:80]]
    selected = st.multiselect('選擇 2~5 檔股票', options, default=options[:2], max_selections=5, key='cmp_stocks')
    if len(selected) < 2:
        st.info('請至少選 2 檔。')
        return

    fetcher = get_shared_fetcher()
    import plotly.graph_objects as go

    fig = go.Figure()
    for s in selected:
        code = s.split(' ')[0]
        hist = fetcher.get_historical_price(code, days=90)
        if not hist or len(hist) < 10:
            continue
        dates = [h['date'] for h in hist]
        closes = [h['close'] for h in hist]
        base = closes[0] if closes and closes[0] > 0 else 1
        norm = [c / base * 100 for c in closes]
        fig.add_trace(go.Scatter(x=dates, y=norm, mode='lines', name=s))

    fig.update_layout(
        title='基準化走勢比較（起始=100）',
        yaxis_title='基準化價格',
        height=430,
        margin=dict(l=20, r=20, t=45, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_anomaly_radar(results: list[dict]) -> None:
    st.markdown('### 🚨 即時異常雷達')
    if not results:
        st.info('目前沒有可分析資料。')
        return

    volumes = sorted([r.get('volume', 0) for r in results])
    q75 = volumes[int(len(volumes) * 0.75)] if volumes else 0
    anomalies: list[dict] = []

    for r in results:
        reasons: list[str] = []
        if r.get('total_score', 0) >= 20 and r.get('change_pct', 0) < -1:
            reasons.append('高分但轉弱')
        if abs(r.get('change_pct', 0)) <= 0.2 and r.get('volume', 0) >= q75:
            reasons.append('爆量但不漲')
        if r.get('change_pct', 0) >= 9.0:
            reasons.append('接近漲停')
        if r.get('change_pct', 0) <= -9.0:
            reasons.append('接近跌停')
        if reasons:
            anomalies.append(
                {
                    '代碼': r['code'],
                    '名稱': r['name'],
                    '價格': round(r['price'], 2),
                    '漲跌%': round(r['change_pct'], 2),
                    '成交量': fmt_vol(r.get('volume', 0)),
                    '異常訊號': ' / '.join(reasons),
                }
            )

    if not anomalies:
        st.success('目前未偵測到顯著異常。')
        return

    st.dataframe(anomalies, use_container_width=True, hide_index=True)


def render_custom_alert_center(results: list[dict]) -> None:
    st.markdown('### 🔔 自訂警報中心')
    if not results:
        st.info('請先執行分析。')
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        min_score = st.slider('最低總分條件', -20, 50, 15, 1, key='alert_min_score')
    with c2:
        min_change = st.slider('最低漲跌%條件', -10.0, 10.0, 0.0, 0.1, key='alert_min_change')
    with c3:
        min_volume = st.number_input('最低成交量條件', min_value=0, value=1000, step=100, key='alert_min_volume')

    require_k_over_d = st.checkbox('需要 KD 黃金交叉（K > D）', value=False, key='alert_k_gt_d')
    require_foreign_buy = st.checkbox('需要外資買超（foreign > 0）', value=False, key='alert_foreign_buy')

    matches = []
    for r in results:
        if r.get('total_score', 0) < min_score:
            continue
        if r.get('change_pct', 0.0) < min_change:
            continue
        if r.get('volume', 0) < min_volume:
            continue
        if require_k_over_d:
            kd = (r.get('indicators') or {}).get('kd', {})
            if kd.get('k', 0) <= kd.get('d', 0):
                continue
        if require_foreign_buy:
            inst = r.get('institutional') or {}
            if inst.get('foreign', 0) <= 0:
                continue
        matches.append(r)

    if not matches:
        st.warning('目前沒有符合自訂警報條件的股票。')
        return

    rows = build_rows(matches, min_score=-999, top_n=999)
    st.success(f'命中 {len(rows)} 檔。')
    st.dataframe(rows, use_container_width=True, hide_index=True)


def run_simple_backtest_for_stock(
    fetcher: DataFetcher, tech: TechnicalIndicators, code: str, hold_days: int, lookback_days: int
) -> list[float]:
    hist = fetcher.get_historical_price(code, days=lookback_days)
    if not hist or len(hist) < 40:
        return []

    closes = [h['close'] for h in hist]
    highs = [h['high'] for h in hist]
    lows = [h['low'] for h in hist]
    returns: list[float] = []

    for i in range(30, len(hist) - hold_days):
        window = hist[: i + 1]
        indicators = tech.calculate_all(window)
        if not indicators:
            continue
        ma20 = indicators.get('ma', {}).get('ma20')
        kd = indicators.get('kd', {})
        k = kd.get('k', 50)
        d = kd.get('d', 50)

        if not ma20:
            continue
        # 策略: 收盤站上 MA20 且 K>D 視為買進
        if closes[i] > ma20 and k > d:
            buy = closes[i]
            sell = closes[i + hold_days]
            if buy > 0:
                returns.append((sell - buy) / buy)
    return returns


def render_backtest(results: list[dict]) -> None:
    st.markdown('### 🧪 多策略回測')
    if not results:
        st.info('請先執行分析後再做回測。')
        return

    candidates = sorted(results, key=lambda x: x['total_score'], reverse=True)[:30]
    options = [f"{r['code']} {r['name']}" for r in candidates]
    selected = st.multiselect('選擇回測股票（最多 20 檔）', options, default=options[:10], max_selections=20)
    hold_days = st.slider('持有天數', 1, 15, 5, 1, key='bt_hold_days')
    lookback_days = st.slider('回溯天數', 90, 360, 180, 30, key='bt_lookback')

    if not selected:
        st.info('請至少選擇一檔股票。')
        return

    fetcher = get_shared_fetcher()
    tech = TechnicalIndicators()
    all_returns: list[float] = []
    for item in selected:
        code = item.split(' ')[0]
        all_returns.extend(run_simple_backtest_for_stock(fetcher, tech, code, hold_days, lookback_days))

    if not all_returns:
        st.warning('目前條件下沒有產生交易訊號。')
        return

    wins = [r for r in all_returns if r > 0]
    avg_ret = sum(all_returns) / len(all_returns)
    win_rate = len(wins) / len(all_returns) * 100

    equity = 1.0
    equity_curve = [equity]
    for r in all_returns:
        equity *= (1 + r)
        equity_curve.append(equity)
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('交易次數', len(all_returns))
    c2.metric('勝率', f'{win_rate:.1f}%')
    c3.metric('平均報酬', f'{avg_ret * 100:.2f}%')
    c4.metric('最大回撤', f'{max_dd * 100:.2f}%')

    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=equity_curve, mode='lines', name='Equity', line=dict(width=2)))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20), title='策略資金曲線')
    st.plotly_chart(fig, use_container_width=True)


def render_portfolio_simulator(results: list[dict]) -> None:
    st.markdown('### 💼 交易清單模擬')
    if not results:
        st.info('請先執行分析。')
        return

    if 'paper_portfolio' not in st.session_state:
        st.session_state.paper_portfolio = []

    price_map = {r['code']: r for r in results}
    options = [f"{r['code']} {r['name']}" for r in results[:100]]

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        selected = st.selectbox('新增持倉股票', options, key='portfolio_add_stock')
    with c2:
        shares = st.number_input('股數', min_value=1, value=1000, step=100, key='portfolio_shares')
    with c3:
        if st.button('加入持倉', key='portfolio_add_btn', use_container_width=True):
            code = selected.split(' ')[0]
            info = price_map.get(code)
            if info:
                st.session_state.paper_portfolio.append(
                    {
                        'code': code,
                        'name': info['name'],
                        'buy_price': float(info['price']),
                        'shares': int(shares),
                    }
                )

    if not st.session_state.paper_portfolio:
        st.info('尚未有模擬持倉。')
        return

    rows = []
    total_cost = 0.0
    total_value = 0.0
    remove_idx = None
    for idx, p in enumerate(st.session_state.paper_portfolio):
        current = float(price_map.get(p['code'], {}).get('price', p['buy_price']))
        cost = p['buy_price'] * p['shares']
        value = current * p['shares']
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0
        total_cost += cost
        total_value += value
        rows.append(
            {
                '索引': idx,
                '代碼': p['code'],
                '名稱': p['name'],
                '買入價': round(p['buy_price'], 2),
                '現價': round(current, 2),
                '股數': p['shares'],
                '損益': round(pnl, 2),
                '損益%': round(pnl_pct, 2),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric('總成本', f'{total_cost:,.0f}')
    c2.metric('總市值', f'{total_value:,.0f}')
    c3.metric('總損益', f'{total_pnl:,.0f}', f'{total_pnl_pct:+.2f}%')

    remove_idx = st.number_input('刪除持倉索引', min_value=-1, max_value=len(rows) - 1, value=-1, step=1)
    if st.button('刪除指定持倉', key='portfolio_remove_btn') and remove_idx >= 0:
        st.session_state.paper_portfolio.pop(int(remove_idx))


def render_industry_heatmap(results: list[dict]) -> None:
    st.markdown('### 🧭 產業熱度儀表板')
    if not STOCK_DATA_WITH_CATEGORIES:
        load_cache()
    if not results:
        st.info('請先執行分析。')
        return

    industry_rows: dict[str, dict] = {}
    for r in results:
        meta = STOCK_DATA_WITH_CATEGORIES.get(r['code'], {})
        cat = meta.get('category', '其他')
        row = industry_rows.setdefault(cat, {'category': cat, 'count': 0, 'score_sum': 0.0, 'chg_sum': 0.0, 'vol_sum': 0})
        row['count'] += 1
        row['score_sum'] += r.get('total_score', 0)
        row['chg_sum'] += r.get('change_pct', 0.0)
        row['vol_sum'] += int(r.get('volume', 0))

    agg = []
    for cat, row in industry_rows.items():
        cnt = max(1, row['count'])
        agg.append(
            {
                '產業': cat,
                '檔數': row['count'],
                '平均分數': round(row['score_sum'] / cnt, 2),
                '平均漲跌%': round(row['chg_sum'] / cnt, 2),
                '平均成交量': int(row['vol_sum'] / cnt),
            }
        )
    agg = sorted(agg, key=lambda x: x['平均分數'], reverse=True)
    st.dataframe(agg, use_container_width=True, hide_index=True)

    import plotly.graph_objects as go

    fig = go.Figure(
        data=go.Scatter(
            x=[x['平均漲跌%'] for x in agg],
            y=[x['平均分數'] for x in agg],
            mode='markers+text',
            text=[x['產業'] for x in agg],
            textposition='top center',
            marker=dict(
                size=[max(10, min(45, int((x['檔數'] ** 0.5) * 6))) for x in agg],
                color=[x['平均分數'] for x in agg],
                colorscale='RdYlGn',
                showscale=True,
            ),
        )
    )
    fig.update_layout(
        title='產業熱力圖（X=平均漲跌%, Y=平均分數, 泡泡=檔數）',
        height=430,
        margin=dict(l=30, r=20, t=60, b=20),
        xaxis_title='平均漲跌%',
        yaxis_title='平均分數',
    )
    st.plotly_chart(fig, use_container_width=True)


def render_daily_rankings(results: list[dict]) -> None:
    st.markdown('### 🏆 每日排行')
    st.caption(f"榜單時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if not results:
        st.info('請先執行分析。')
        return

    top_score = sorted(results, key=lambda x: x['total_score'], reverse=True)[:20]
    top_up = sorted(results, key=lambda x: x['change_pct'], reverse=True)[:20]
    top_volume = sorted(results, key=lambda x: x['volume'], reverse=True)[:20]
    reversal = [r for r in results if r['total_score'] >= 15 and r['change_pct'] < 0]
    reversal = sorted(reversal, key=lambda x: x['total_score'], reverse=True)[:20]

    tab1, tab2, tab3, tab4 = st.tabs(['高分榜', '漲幅榜', '量能榜', '反轉觀察'])
    with tab1:
        st.dataframe(build_rows(top_score, -999, 999), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(build_rows(top_up, -999, 999), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(build_rows(top_volume, -999, 999), use_container_width=True, hide_index=True)
    with tab4:
        st.dataframe(build_rows(reversal, -999, 999), use_container_width=True, hide_index=True)


def render_share_card(results: list[dict]) -> None:
    st.markdown('### 🖼️ 一鍵分享卡片')
    if not results:
        st.info('請先執行分析。')
        return
    options = [f"{r['code']} {r['name']}" for r in results[:50]]
    selected = st.selectbox('選擇要分享的股票', options, key='share_stock')
    code = selected.split(' ')[0]
    r = next((x for x in results if x['code'] == code), None)
    if not r:
        return

    summary = generate_ai_summary(r)
    reasons = (r.get('reasons') or [])[:3]
    reason_lines = ' / '.join(reasons) if reasons else '無'
    share_text = (
        f"【{r['code']} {r['name']}】"
        f"價格 {r['price']:.2f}，漲跌 {r['change_pct']:+.2f}%，"
        f"總分 {r['total_score']}。{summary}"
    )
    default_url = 'https://www.twse.com.tw/'
    share_url = st.text_input('分享連結（可改成你要導流的網址）', value=default_url, key='share_target_url')

    def esc(s: str) -> str:
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def wrap_text(text: str, width: int = 44, max_lines: int = 3) -> list[str]:
        t = text.strip()
        lines = []
        while len(t) > width and len(lines) < max_lines - 1:
            cut = t.rfind(' ', 0, width)
            if cut <= 0:
                cut = width
            lines.append(t[:cut].strip())
            t = t[cut:].strip()
        if t:
            lines.append(t[:width + 8] + ('...' if len(t) > width + 8 else ''))
        return lines[:max_lines]

    reason_wrapped = wrap_text(f'重點原因: {reason_lines}', width=48, max_lines=2)
    summary_wrapped = wrap_text(summary, width=52, max_lines=3)
    why_line_1 = esc(reason_wrapped[0] if reason_wrapped else '重點原因: 無')
    why_line_2 = esc(reason_wrapped[1] if len(reason_wrapped) > 1 else '')
    sum_line_1 = esc(summary_wrapped[0] if summary_wrapped else '')
    sum_line_2 = esc(summary_wrapped[1] if len(summary_wrapped) > 1 else '')
    sum_line_3 = esc(summary_wrapped[2] if len(summary_wrapped) > 2 else '')

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='920' height='420'>
<rect width='100%' height='100%' fill='#0f172a'/>
<rect x='24' y='24' width='872' height='372' rx='18' fill='#111827' stroke='#334155' stroke-width='2'/>
<text x='48' y='72' fill='#f8fafc' font-size='28' font-family='Arial'>台股分析分享卡</text>
<text x='48' y='114' fill='#93c5fd' font-size='26' font-family='Arial'>{esc(r['code'])} {esc(r['name'])}</text>
<text x='48' y='154' fill='#e2e8f0' font-size='20' font-family='Arial'>價格: {r['price']:.2f} / 漲跌: {r['change_pct']:+.2f}%</text>
<text x='48' y='186' fill='#fde68a' font-size='20' font-family='Arial'>總分: {r['total_score']} / 建議: {esc(score_badge(r['total_score']))}</text>
<text x='48' y='228' fill='#cbd5e1' font-size='17' font-family='Arial'>{why_line_1}</text>
<text x='48' y='252' fill='#cbd5e1' font-size='17' font-family='Arial'>{why_line_2}</text>
<text x='48' y='292' fill='#a7f3d0' font-size='16' font-family='Arial'>{sum_line_1}</text>
<text x='48' y='316' fill='#a7f3d0' font-size='16' font-family='Arial'>{sum_line_2}</text>
<text x='48' y='340' fill='#a7f3d0' font-size='16' font-family='Arial'>{sum_line_3}</text>
<text x='48' y='374' fill='#64748b' font-size='13' font-family='Arial'>Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</text>
</svg>"""

    st.markdown('#### 預覽')
    st.markdown(svg, unsafe_allow_html=True)
    st.markdown('#### 一鍵分享到社群')
    x_url = f"https://twitter.com/intent/tweet?text={quote(share_text)}&url={quote(share_url)}"
    fb_url = f"https://www.facebook.com/sharer/sharer.php?u={quote(share_url)}"
    line_url = f"https://social-plugins.line.me/lineit/share?url={quote(share_url)}"
    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button('分享到 X', x_url, use_container_width=True)
    with c2:
        st.link_button('分享到 Facebook', fb_url, use_container_width=True)
    with c3:
        st.link_button('分享到 LINE', line_url, use_container_width=True)
    st.text_area('貼文文字（可複製）', value=share_text, height=120, key='share_text_box')
    st.download_button(
        label='下載 SVG 分享卡',
        data=svg.encode('utf-8'),
        file_name=f"share_card_{r['code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg",
        mime='image/svg+xml',
    )
    st.download_button(
        label='下載摘要文字',
        data=(summary + '\n\n' + reason_lines).encode('utf-8'),
        file_name=f"share_summary_{r['code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime='text/plain',
    )


def render_export(rows: list[dict]) -> None:
    if not rows:
        return
    st.markdown('### 📥 匯出')
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button(
        label='下載分析結果 CSV',
        data=output.getvalue().encode('utf-8-sig'),
        file_name=f"stock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime='text/csv',
    )


def main():
    st.title('台股選股分析系統')
    st.caption(f'更新時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

    (
        page,
        mode,
        selected_cats,
        random_n,
        min_score,
        top_n,
        max_workers,
        run_btn,
        update_btn,
        min_vol,
        price_min,
        price_max,
        custom_codes,
    ) = render_sidebar()

    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'analyzed' not in st.session_state:
        st.session_state.analyzed = False

    if update_btn:
        with st.spinner(f'更新股票清單中（最低成交量 {min_vol} 張）...'):
            export_stock_list_to_file(min_vol)
        st.success(f'已更新股票清單，共 {get_stock_count()} 檔。')

    if get_stock_count() == 0:
        st.warning('目前沒有股票清單，請先按「更新股票清單」。')
        return

    if run_btn:
        stocks: list[tuple[str, str]] = []
        if mode == '全部股票':
            stocks = get_all_stocks()
        elif mode == '依產業類別':
            if not selected_cats:
                st.warning('請至少選一個產業類別。')
            else:
                stocks = get_stocks_by_category(','.join(selected_cats))
        elif mode == '隨機抽樣':
            all_s = get_all_stocks()
            random.shuffle(all_s)
            stocks = all_s[:random_n]
        elif mode == '自訂股票':
            if custom_codes:
                all_dict = dict(get_all_stocks())
                stocks = [(c, all_dict.get(c, c)) for c in custom_codes]
            else:
                st.warning('請輸入至少一個股票代碼。')

        if stocks and (price_min > 0 or price_max > 0):
            fetcher = get_shared_fetcher()
            filtered = []
            for code, name in stocks:
                p = fetcher.get_stock_price(code)
                if not p:
                    continue
                price = float(p.get('price', 0) or 0)
                if price_min > 0 and price < price_min:
                    continue
                if price_max > 0 and price > price_max:
                    continue
                filtered.append((code, name))
            stocks = filtered

        if stocks:
            results = run_analysis(stocks, max_workers=max_workers)
            st.session_state.results = results
            st.session_state.analyzed = True
            if CONFIG['output'].get('save_history', False) and results:
                HistorySaver().save_analysis(results)

    if st.session_state.analyzed:
        results = st.session_state.results
        if page == '分析總覽':
            render_kpi(results)
            render_market_board(results)
            rows = render_table(results, min_score, top_n)
            render_ai_summary_card(results)
            render_watchlist(results)
            render_export(rows)
        elif page == '技術圖表':
            render_kd_price_chart(results)
            render_multi_timeframe(results)
            render_comparison_mode(results)
        elif page == '警報中心':
            render_anomaly_radar(results)
            render_custom_alert_center(results)
        elif page == '產業熱度':
            render_industry_heatmap(results)
        elif page == '回測與模擬':
            render_backtest(results)
            render_portfolio_simulator(results)
        elif page == '每日排行':
            render_daily_rankings(results)
        elif page == '分享卡片':
            render_share_card(results)


if __name__ == '__main__':
    main()
