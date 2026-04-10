# -*- coding: utf-8 -*-
"""資料抓取模組：即時股價、歷史股價、三大法人。"""

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DataFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Referer': 'https://mis.twse.com.tw/stock/fibest.jsp',
            'Origin': 'https://mis.twse.com.tw',
            'Connection': 'keep-alive',
        }
        self._mis_session = requests.Session()
        self._mis_session.headers.update(self.headers)
        self._mis_initialized = False

        # 依 host 節流，避免多執行緒被全域鎖完全序列化
        self._host_min_interval = {
            'mis.twse.com.tw': 0.06,
            'www.twse.com.tw': 0.12,
            'www.tpex.org.tw': 0.12,
        }
        self._default_min_interval = 0.10
        self._host_last_request_time: dict[str, float] = {}
        self._host_locks: dict[str, threading.Lock] = {}
        self._host_locks_guard = threading.Lock()

        self._stock_market_cache: dict[str, str] = {}
        self._institutional_cache: dict | None = None
        self._institutional_date: str | None = None

        self._cache_dir = 'cache'
        self._ensure_cache_dir()

        self._institutional_lock = threading.Lock()
        self._init_lock = threading.Lock()

    def _ensure_cache_dir(self) -> None:
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir, exist_ok=True)

    def _init_mis_session(self) -> None:
        if self._mis_initialized:
            return
        with self._init_lock:
            if self._mis_initialized:
                return
            try:
                url = 'https://mis.twse.com.tw/stock/fibest.jsp'
                self._throttle(url)
                self._mis_session.get(url, timeout=10, verify=False)
            except Exception:
                pass
            self._mis_initialized = True

    def _get_cache_path(self, code: str) -> str:
        return os.path.join(self._cache_dir, f'{code}.json')

    def _load_from_cache(self, code: str):
        cache_path = self._get_cache_path(code)
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _save_to_cache(self, code: str, data) -> None:
        cache_path = self._get_cache_path(code)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        with self._host_locks_guard:
            lock = self._host_locks.get(host)
            if lock is None:
                lock = threading.Lock()
                self._host_locks[host] = lock
        min_interval = self._host_min_interval.get(host, self._default_min_interval)
        with lock:
            now = time.time()
            last = self._host_last_request_time.get(host, 0.0)
            elapsed = now - last
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._host_last_request_time[host] = time.time()

    @staticmethod
    def _safe_float(val) -> float:
        try:
            if not val or val in ('-', '--'):
                return 0.0
            cleaned = str(val).replace(',', '').replace('X', '').strip()
            return float(cleaned) if cleaned and cleaned not in ('-', '--') else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _safe_int(val) -> int:
        try:
            if not val or val in ('-', '--'):
                return 0
            return int(str(val).replace(',', '').strip())
        except Exception:
            return 0

    def get_stock_price(self, code: str):
        self._init_mis_session()
        markets_to_try = [self._stock_market_cache[code]] if code in self._stock_market_cache else ['tse', 'otc']

        for market in markets_to_try:
            try:
                url = f'https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={market}_{code}.tw&json=1&delay=0'
                self._throttle(url)
                data = self._mis_session.get(url, timeout=10, verify=False).json()
                msg = data.get('msgArray', [])
                if not msg:
                    continue

                stock = msg[0]
                actual_market = stock.get('ex', '')
                if not actual_market:
                    continue
                self._stock_market_cache[code] = actual_market

                price = self._safe_float(stock.get('z', 0))
                prev_close = self._safe_float(stock.get('y', 0))
                if price == 0 and prev_close > 0:
                    price = prev_close
                if price == 0:
                    continue

                return {
                    'price': price,
                    'open': self._safe_float(stock.get('o', 0)) or price,
                    'high': self._safe_float(stock.get('h', 0)) or price,
                    'low': self._safe_float(stock.get('l', 0)) or price,
                    'volume': self._safe_int(stock.get('v', 0)),
                    'prev_close': prev_close,
                    'is_premarket': datetime.now().hour < 9,
                    'market': actual_market,
                }
            except Exception:
                continue

        return None

    def fetch_institutional_batch(self):
        if self._institutional_cache is not None:
            return self._institutional_cache

        with self._institutional_lock:
            if self._institutional_cache is not None:
                return self._institutional_cache

            latest_data = {}
            latest_date = None
            for days_ago in range(1, 6):
                try:
                    date_str = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
                    url = f'https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL'
                    self._throttle(url)
                    rows = requests.get(url, headers=self.headers, timeout=15, verify=False).json().get('data', [])
                    if not rows:
                        continue

                    day_data = {}
                    for row in rows:
                        try:
                            code = str(row[0]).strip()
                            if not code or not code[0].isdigit():
                                continue
                            day_data[code] = {
                                'foreign': self._safe_int(row[4]) // 1000,
                                'investment_trust': self._safe_int(row[10]) // 1000,
                                'dealer': self._safe_int(row[11]) // 1000,
                                'total': self._safe_int(row[18]) // 1000,
                            }
                        except Exception:
                            continue

                    if day_data:
                        latest_data = day_data
                        latest_date = date_str
                        break
                except Exception:
                    continue

            self._institutional_cache = latest_data
            self._institutional_date = latest_date
            return self._institutional_cache

    def get_institutional_investors(self, code: str, days: int = 5):
        cache = self.fetch_institutional_batch()
        return cache.get(code, None)

    @staticmethod
    def _parse_date_to_iso(date_str: str) -> str:
        date_str = str(date_str).strip()
        if len(date_str) == 10 and date_str[4] == '-':
            return date_str
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                try:
                    roc_year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    return f'{roc_year + 1911}-{month:02d}-{day:02d}'
                except Exception:
                    pass
        return date_str

    def _fetch_historical_tse(self, code: str, months_ago: int) -> list[dict]:
        prices = []
        try:
            target_date = datetime.now() - timedelta(days=months_ago * 30)
            date_str = target_date.strftime('%Y%m01')
            url = f'https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}'
            self._throttle(url)
            rows = requests.get(url, headers=self.headers, timeout=10, verify=False).json().get('data', [])
            for row in rows:
                close = self._safe_float(str(row[6]).replace(',', '').replace('X', '').strip())
                if close == 0:
                    continue
                prices.append(
                    {
                        'date': self._parse_date_to_iso(row[0]),
                        'open': self._safe_float(str(row[3]).replace(',', '').replace('X', '').strip()),
                        'high': self._safe_float(str(row[4]).replace(',', '').replace('X', '').strip()),
                        'low': self._safe_float(str(row[5]).replace(',', '').replace('X', '').strip()),
                        'close': close,
                        'volume': self._safe_int(row[1]) // 1000,
                    }
                )
        except Exception:
            pass
        return prices

    def _fetch_historical_otc(self, code: str, months_ago: int) -> list[dict]:
        prices = []
        try:
            target_date = datetime.now() - timedelta(days=months_ago * 30)
            roc_year = target_date.year - 1911
            date_str = f'{roc_year}/{target_date.month:02d}'
            url = (
                'https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/'
                f'st43_result.php?l=zh-tw&d={date_str}&stkno={code}&s=0,asc,0'
            )
            self._throttle(url)
            rows = requests.get(url, headers=self.headers, timeout=10, verify=False).json().get('aaData', [])
            for row in rows:
                close = self._safe_float(str(row[6]).replace(',', '').replace('X', '').strip())
                if close == 0:
                    continue
                prices.append(
                    {
                        'date': self._parse_date_to_iso(row[0]),
                        'open': self._safe_float(str(row[3]).replace(',', '').replace('X', '').strip()),
                        'high': self._safe_float(str(row[4]).replace(',', '').replace('X', '').strip()),
                        'low': self._safe_float(str(row[5]).replace(',', '').replace('X', '').strip()),
                        'close': close,
                        'volume': self._safe_int(row[1]) // 1000,
                    }
                )
        except Exception:
            pass
        return prices

    def get_historical_price(self, code: str, days: int = 60, use_cache: bool = True):
        cached_data = self._load_from_cache(code) if use_cache else None
        all_prices = cached_data.copy() if cached_data else []

        if cached_data:
            last_date = cached_data[-1].get('date', '')
            try:
                last_dt = datetime.strptime(self._parse_date_to_iso(last_date), '%Y-%m-%d')
                if (datetime.now() - last_dt).days <= 1:
                    return all_prices[-days:] if len(all_prices) >= days else all_prices
            except Exception:
                pass

        market = self._stock_market_cache.get(code)
        for months_ago in range(4, -1, -1):
            if market == 'otc':
                new_prices = self._fetch_historical_otc(code, months_ago)
            elif market == 'tse':
                new_prices = self._fetch_historical_tse(code, months_ago)
            else:
                new_prices = self._fetch_historical_tse(code, months_ago)
                if not new_prices:
                    new_prices = self._fetch_historical_otc(code, months_ago)
                    if new_prices:
                        self._stock_market_cache[code] = 'otc'
                else:
                    self._stock_market_cache[code] = 'tse'
            all_prices.extend(new_prices)

        if not all_prices:
            return None

        seen = set()
        unique_prices = []
        for p in all_prices:
            iso = self._parse_date_to_iso(p['date'])
            p['date'] = iso
            if iso in seen:
                continue
            seen.add(iso)
            unique_prices.append(p)

        unique_prices.sort(key=lambda x: x['date'])
        if use_cache and len(unique_prices) >= days:
            self._save_to_cache(code, unique_prices)

        return unique_prices[-days:] if len(unique_prices) > days else unique_prices

    def get_stock_info_batch(self, stock_list: list[tuple[str, str]]):
        results = {}
        for code, name in stock_list:
            price_data = self.get_stock_price(code)
            if price_data:
                results[code] = {'name': name, **price_data}
        return results

    def _get_json(self, url: str, timeout: int = 12, use_session: bool = False) -> dict | None:
        try:
            self._throttle(url)
            if use_session:
                resp = self._mis_session.get(url, timeout=timeout, verify=False)
            else:
                resp = requests.get(url, headers=self.headers, timeout=timeout, verify=False)
            return resp.json() if resp.ok else None
        except Exception:
            return None

    def _fetch_yahoo_quote_single(self, symbol: str) -> dict | None:
        encoded = quote(symbol, safe='')
        url = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={encoded}'
        payload = self._get_json(url, timeout=12)
        if not payload:
            return None
        rows = payload.get('quoteResponse', {}).get('result', [])
        if not rows:
            return None

        q = rows[0]
        change_pct = self._safe_float(q.get('regularMarketChangePercent'))
        price = self._safe_float(q.get('regularMarketPrice'))
        if price <= 0:
            return None
        return {
            'symbol': str(q.get('symbol') or symbol),
            'name': str(q.get('shortName') or q.get('longName') or symbol),
            'price': price,
            'change_pct': change_pct,
            'change': self._safe_float(q.get('regularMarketChange')),
            'market_state': str(q.get('marketState') or ''),
            'timestamp': int(q.get('regularMarketTime') or 0),
        }

    def _fetch_stooq_quote_single(self, symbol: str) -> dict | None:
        stooq_map = {
            '^GSPC': 'spy.us',
            '^IXIC': 'qqq.us',
            '^DJI': 'dia.us',
            '^SOX': 'soxx.us',
            'ES=F': 'spy.us',
            'NQ=F': 'qqq.us',
            '^TWII': None,
        }
        if symbol in stooq_map and stooq_map[symbol] is None:
            return None
        stooq_symbol = stooq_map.get(symbol, f'{symbol.lower()}.us')
        url = f'https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2cp&h&e=csv'
        try:
            self._throttle(url)
            resp = requests.get(url, headers=self.headers, timeout=12, verify=False)
            if not resp.ok:
                return None
            lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
            if len(lines) < 2:
                return None
            cols = lines[1].split(',')
            if len(cols) < 5:
                return None
            close = self._safe_float(cols[3])
            prev = self._safe_float(cols[4])
            if close <= 0:
                return None
            change = close - prev
            change_pct = (change / prev * 100.0) if prev > 0 else 0.0
            return {
                'symbol': symbol,
                'name': symbol,
                'price': close,
                'change_pct': round(change_pct, 2),
                'change': round(change, 2),
                'market_state': 'CLOSED',
                'timestamp': 0,
                'source': 'stooq',
            }
        except Exception:
            return None

    def _fetch_quote_with_fallback(self, symbol: str) -> dict | None:
        q = self._fetch_yahoo_quote_single(symbol)
        if q:
            q.setdefault('source', 'yahoo')
            return q
        return self._fetch_stooq_quote_single(symbol)

    @staticmethod
    def _extract_numeric(text: str) -> float:
        s = str(text or '').replace(',', '').strip()
        m = re.search(r'[-+]?\d+(?:\.\d+)?', s)
        return float(m.group(0)) if m else 0.0

    def _fetch_taifex_tx_night_quote(self, max_lookback_days: int = 7) -> dict | None:
        for d in range(max_lookback_days + 1):
            query_dt = datetime.now() - timedelta(days=d)
            date_str = query_dt.strftime('%Y/%m/%d')
            url = (
                'https://www.taifex.com.tw/cht/3/futDailyMarketReport'
                f'?queryType=2&marketCode=0&commodity_id=TX&queryDate={date_str}'
            )
            try:
                self._throttle(url)
                resp = requests.get(url, headers=self.headers, timeout=15, verify=False)
                if not resp.ok:
                    continue
                html = resp.text
                body_match = re.search(r'<tbody>(.*?)</tbody>', html, re.S | re.I)
                if not body_match:
                    continue
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', body_match.group(1), re.S | re.I)
                if not rows:
                    continue

                tx_row = None
                for row_html in rows:
                    cols = [
                        re.sub(r'<.*?>', '', c).replace('\r', '').replace('\n', '').replace('\t', '').strip()
                        for c in re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.S | re.I)
                    ]
                    if len(cols) >= 10 and str(cols[0]).strip().upper() == 'TX':
                        tx_row = cols
                        break

                if not tx_row:
                    continue

                night_vol = int(self._extract_numeric(tx_row[8]))
                change_pct = self._extract_numeric(tx_row[7])
                last_price = self._extract_numeric(tx_row[5])
                if last_price <= 0:
                    continue

                return {
                    'symbol': 'TX-NIGHT',
                    'name': '台指期夜盤',
                    'price': last_price,
                    'change_pct': change_pct,
                    'change': self._extract_numeric(tx_row[6]),
                    'market_state': 'CLOSED',
                    'timestamp': int(query_dt.timestamp()),
                    'night_volume': night_vol,
                    'session_date': query_dt.strftime('%Y-%m-%d'),
                    'source': 'taifex',
                }
            except Exception:
                continue
        return None

    @staticmethod
    def _map_tw_category_to_us_proxy(category: str) -> tuple[str, list[str]]:
        c = str(category or '')
        mapping = {
            'ETF': ('美股大盤ETF', ['SPY', 'QQQ']),
            '半導體': ('美股半導體', ['SOXX', 'SMH']),
            '其他電子': ('美股科技', ['XLK', 'QQQ']),
            '電子零組件': ('美股科技硬體', ['XLK', 'SOXX']),
            '電腦週邊': ('美股科技硬體', ['XLK', 'QQQ']),
            '通信網路': ('美股通訊服務', ['XLC', 'QQQ']),
            '資訊服務': ('美股軟體科技', ['XLK', 'QQQ']),
            '電子通路': ('美股科技通路', ['XLK', 'XLY']),
            '金融': ('美股金融', ['XLF']),
            '航運': ('美股運輸', ['IYT']),
            '油電燃氣': ('美股能源', ['XLE']),
            '生技醫療': ('美股醫療', ['XLV', 'IBB']),
            '化學': ('美股原物料', ['XLB']),
            '化工': ('美股原物料', ['XLB']),
            '塑膠': ('美股原物料', ['XLB']),
            '橡膠': ('美股原物料', ['XLB']),
            '鋼鐵': ('美股原物料', ['XLB']),
            '電機': ('美股工業', ['XLI']),
            '汽車': ('美股非必需消費', ['XLY']),
            '營建': ('美股工業/房地產', ['XLI', 'XLRE']),
            '紡織': ('美股非必需消費', ['XLY']),
            '食品': ('美股必需消費', ['XLP']),
            '造紙': ('美股原物料', ['XLB']),
            '觀光': ('美股非必需消費', ['XLY']),
            '貿易百貨': ('美股零售消費', ['XRT', 'XLY']),
            '綠能環保': ('美股公用事業/潔能', ['XLU', 'ICLN']),
            '水泥': ('美股原物料', ['XLB']),
            '玻璃陶瓷': ('美股原物料', ['XLB']),
            '電線電纜': ('美股工業', ['XLI']),
            '運動休閒': ('美股非必需消費', ['XLY']),
        }
        return mapping.get(c, ('美股大盤', ['SPY', 'QQQ']))

    def get_us_sector_quote_for_category(self, category: str) -> dict:
        label, symbols = self._map_tw_category_to_us_proxy(category)
        for sym in symbols:
            q = self._fetch_quote_with_fallback(sym)
            if q:
                return {'label': label, 'category': category, 'proxy_symbol': sym, **q}
        return {'label': label, 'category': category, 'proxy_symbol': symbols[0], 'unavailable': True}

    @staticmethod
    def _tw_market_phase(now_dt: datetime) -> tuple[str, str]:
        hm = now_dt.hour * 60 + now_dt.minute
        if hm < 9 * 60:
            return 'pre_open', '開盤前'
        if hm <= 13 * 60 + 30:
            return 'intraday', '盤中'
        return 'post_close', '收盤後'

    @staticmethod
    def _score_direction(change_pct: float, strong: float = 0.7, mild: float = 0.25) -> int:
        if change_pct >= strong:
            return 2
        if change_pct >= mild:
            return 1
        if change_pct <= -strong:
            return -2
        if change_pct <= -mild:
            return -1
        return 0

    def get_opening_market_context(self) -> dict:
        now_dt = datetime.now()
        phase, phase_label = self._tw_market_phase(now_dt)

        # 台指夜盤來源：優先台期所官方頁面，失敗才改用外部代號嘗試。
        night_quote = self._fetch_taifex_tx_night_quote(max_lookback_days=7)
        if not night_quote:
            night_candidates = ['WTX&', 'TXF1!', 'TX00.TW']
            for sym in night_candidates:
                night_quote = self._fetch_yahoo_quote_single(sym)
                if night_quote:
                    break

        spx = self._fetch_quote_with_fallback('^GSPC')
        nasdaq = self._fetch_quote_with_fallback('^IXIC')
        dow = self._fetch_quote_with_fallback('^DJI')
        sox = self._fetch_quote_with_fallback('^SOX')
        es = self._fetch_quote_with_fallback('ES=F')
        nq = self._fetch_quote_with_fallback('NQ=F')
        twii = self._fetch_quote_with_fallback('^TWII')

        us_major = [q for q in [spx, nasdaq, dow] if q]
        us_futures = [q for q in [es, nq] if q]
        us_for_avg = us_major if us_major else us_futures
        us_avg = 0.0
        if us_for_avg:
            us_avg = sum(float(q.get('change_pct') or 0.0) for q in us_for_avg) / len(us_for_avg)

        score = self._score_direction(us_avg, strong=0.8, mild=0.3)
        if night_quote:
            score += self._score_direction(float(night_quote.get('change_pct') or 0.0), strong=0.8, mild=0.3)
        if phase == 'intraday' and twii:
            score += self._score_direction(float(twii.get('change_pct') or 0.0), strong=0.6, mild=0.2)

        if score >= 3:
            bias = '偏多'
        elif score <= -3:
            bias = '偏空'
        else:
            bias = '中性'

        confidence = '中'
        signals = sum(1 for q in [night_quote, spx, nasdaq, dow, es, nq, twii] if q)
        if signals >= 5:
            confidence = '高'
        elif signals <= 2:
            confidence = '低'

        return {
            'generated_at': now_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'phase': phase,
            'phase_label': phase_label,
            'bias': bias,
            'confidence': confidence,
            'score': score,
            'us_avg_change_pct': round(us_avg, 2),
            'night_quote': night_quote,
            'twii': twii,
            'us': {
                'spx': spx,
                'nasdaq': nasdaq,
                'dow': dow,
                'sox': sox,
                'es_fut': es,
                'nq_fut': nq,
            },
            'notes': [
                '夜盤優先使用台期所資料，抓不到時才改用外部代號/美股期貨代理訊號。',
                '此模組用於盤前/盤中情境研判，不構成投資建議。',
            ],
        }
