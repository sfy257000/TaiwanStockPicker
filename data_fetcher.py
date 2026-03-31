# -*- coding: utf-8 -*-
"""資料抓取模組：即時股價、歷史股價、三大法人。"""

import json
import os
import threading
import time
from datetime import datetime, timedelta

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

        self._last_request_time = 0.0
        self._min_interval = 0.5

        self._stock_market_cache: dict[str, str] = {}
        self._institutional_cache: dict | None = None
        self._institutional_date: str | None = None

        self._cache_dir = 'cache'
        self._ensure_cache_dir()

        self._institutional_lock = threading.Lock()
        self._throttle_lock = threading.Lock()

    def _ensure_cache_dir(self) -> None:
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir, exist_ok=True)

    def _init_mis_session(self) -> None:
        if self._mis_initialized:
            return
        try:
            self._throttle()
            self._mis_session.get('https://mis.twse.com.tw/stock/fibest.jsp', timeout=10, verify=False)
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

    def _throttle(self) -> None:
        with self._throttle_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request_time = time.time()

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
                self._throttle()
                url = f'https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={market}_{code}.tw&json=1&delay=0'
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
                    self._throttle()
                    date_str = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
                    url = f'https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL'
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
            self._throttle()
            target_date = datetime.now() - timedelta(days=months_ago * 30)
            date_str = target_date.strftime('%Y%m01')
            url = f'https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}'
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
            self._throttle()
            target_date = datetime.now() - timedelta(days=months_ago * 30)
            roc_year = target_date.year - 1911
            date_str = f'{roc_year}/{target_date.month:02d}'
            url = (
                'https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/'
                f'st43_result.php?l=zh-tw&d={date_str}&stkno={code}&s=0,asc,0'
            )
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
