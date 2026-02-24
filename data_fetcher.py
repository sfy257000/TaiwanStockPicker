# -*- coding: utf-8 -*-
"""
數據抓取模組
從證交所抓取股票數據（不依賴Yahoo API）
"""

import requests
import time
import os
import json
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DataFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        self._last_request_time = 0
        self._min_interval = 0.3  # 最少間隔0.3秒，避免被封
        self._stock_market_cache = {}  # code -> 'tse' or 'otc'
        self._institutional_cache = None  # 批次法人資料快取
        self._institutional_date = None
        self._cache_dir = 'cache'
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """確保快取目錄存在"""
        if not os.path.exists(self._cache_dir):
            try:
                os.makedirs(self._cache_dir)
            except:
                pass
    
    def _get_cache_path(self, code):
        """取得股票快取檔案路徑"""
        return os.path.join(self._cache_dir, f"{code}.json")
    
    def _load_from_cache(self, code):
        """從快取載入歷史資料"""
        cache_path = self._get_cache_path(code)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data
            except:
                pass
        return None
    
    def _save_to_cache(self, code, data):
        """儲存歷史資料到快取"""
        cache_path = self._get_cache_path(code)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except:
            pass
    
    def _throttle(self):
        """API請求節流"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _safe_float(self, val):
        try:
            return float(val) if val and val != '-' else 0
        except:
            return 0
    
    def _safe_int(self, val):
        try:
            return int(str(val).replace(',', '').strip()) if val and val != '-' and val != '--' else 0
        except:
            return 0
    
    def get_stock_price(self, code):
        """
        取得即時股價（支援盤前試撮，自動偵測上市/上櫃）
        """
        # 先嘗試快取的市場別，否則先試tse再試otc
        markets_to_try = []
        if code in self._stock_market_cache:
            markets_to_try = [self._stock_market_cache[code]]
        else:
            markets_to_try = ['tse', 'otc']
        
        for market in markets_to_try:
            try:
                self._throttle()
                url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={market}_{code}.tw&json=1&delay=0"
                response = requests.get(url, headers=self.headers, timeout=10, verify=False)
                data = response.json()
                
                if 'msgArray' not in data or len(data['msgArray']) == 0:
                    continue
                
                stock = data['msgArray'][0]
                
                # 驗證是否真的有這支股票（檢查ex欄位）
                actual_market = stock.get('ex', '')
                if not actual_market:
                    continue
                
                # 快取市場別
                self._stock_market_cache[code] = actual_market
                
                price = self._safe_float(stock.get('z', 0))
                prev_close = self._safe_float(stock.get('y', 0))
                
                # 檢查是否為盤前（僅在9:00前視為盤前）
                current_hour = datetime.now().hour
                is_premarket = current_hour < 9
                
                # 如果沒有即時價格但有昨收，且在開盤後，用昨收當價格（不算盤前）
                if price == 0 and prev_close > 0:
                    price = prev_close
                    # 開盤後無報價可能是API延遲，不標記為盤前
                
                if price == 0:
                    continue
                
                open_price = self._safe_float(stock.get('o', 0))
                high = self._safe_float(stock.get('h', 0))
                low = self._safe_float(stock.get('l', 0))
                
                # 盤前沒有開高低，用price填充
                if open_price == 0:
                    open_price = price
                if high == 0:
                    high = price
                if low == 0:
                    low = price
                
                return {
                    'price': price,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'volume': self._safe_int(stock.get('v', 0)),
                    'prev_close': prev_close,
                    'is_premarket': is_premarket,
                }
            except:
                continue
        
        return None
    
    def fetch_institutional_batch(self):
        """
        批次抓取所有股票的三大法人買賣超（T86 API）
        只需呼叫一次，結果快取起來
        返回: dict {code: {foreign, investment_trust, dealer, total}}
        """
        if self._institutional_cache is not None:
            return self._institutional_cache
        
        self._institutional_cache = {}
        
        # 嘗試最近5個日曆天
        for days_ago in range(1, 6):
            try:
                self._throttle()
                date = datetime.now() - timedelta(days=days_ago)
                date_str = date.strftime('%Y%m%d')
                url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL"
                response = requests.get(url, headers=self.headers, timeout=15, verify=False)
                data = response.json()
                
                rows = data.get('data', [])
                if not rows or len(rows) == 0:
                    continue
                
                self._institutional_date = date_str
                
                # T86 格式:
                # [0] 代碼, [1] 名稱,
                # [2] 外資買進, [3] 外資賣出, [4] 外資買賣超(不含外資自營),
                # [5] 外資自營買進, [6] 外資自營賣出, [7] 外資自營買賣超,
                # [8] 投信買進, [9] 投信賣出, [10] 投信買賣超,
                # [11] 自營商買賣超合計,
                # [12] 自營(自行)買進, [13] 自營(自行)賣出, [14] 自營(自行)買賣超,
                # [15] 自營(避險)買進, [16] 自營(避險)賣出, [17] 自營(避險)買賣超,
                # [18] 三大法人買賣超
                
                for row in rows:
                    try:
                        code = str(row[0]).strip()
                        if not code or not code[0].isdigit():
                            continue
                        
                        # 單位是「股」，需除以1000變「張」
                        foreign = self._safe_int(row[4]) // 1000       # 外資買賣超
                        trust = self._safe_int(row[10]) // 1000        # 投信買賣超
                        dealer = self._safe_int(row[11]) // 1000       # 自營商買賣超
                        total = self._safe_int(row[18]) // 1000        # 三大法人合計
                        
                        self._institutional_cache[code] = {
                            'foreign': foreign,
                            'investment_trust': trust,
                            'dealer': dealer,
                            'total': total,
                        }
                    except:
                        continue
                
                if self._institutional_cache:
                    break  # 找到資料就停
                    
            except:
                continue
        
        return self._institutional_cache
    
    def get_institutional_investors(self, code, days=5):
        """
        取得單一股票三大法人買賣超（從批次快取中取）
        """
        cache = self.fetch_institutional_batch()
        return cache.get(code, None)
    
    def get_historical_price(self, code, days=60, use_cache=True):
        """
        取得歷史股價 - 使用TWSE月成交資訊API
        支援增量更新：先檢查本地快取，只抓取新資料
        """
        cached_data = None
        if use_cache:
            cached_data = self._load_from_cache(code)
        
        last_date = None
        if cached_data and len(cached_data) > 0:
            last_date = cached_data[-1].get('date', '')
        
        all_prices = []
        
        if cached_data:
            all_prices = cached_data.copy()
        
        if last_date:
            try:
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
                days_since = (datetime.now() - last_dt).days
                if days_since <= 1:
                    if len(all_prices) >= days:
                        return all_prices[-days:]
                    return all_prices
            except:
                pass
        
        for months_ago in range(4, -1, -1):
            try:
                self._throttle()
                target_date = datetime.now() - timedelta(days=months_ago * 30)
                date_str = target_date.strftime('%Y%m01')
                
                url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}"
                response = requests.get(url, headers=self.headers, timeout=10, verify=False)
                data = response.json()
                
                if 'data' not in data or len(data['data']) == 0:
                    continue
                
                for row in data['data']:
                    try:
                        def safe_float(val):
                            try:
                                v = str(val).replace(',', '').replace('X', '').strip()
                                return float(v) if v and v != '--' and v != '-' else 0
                            except:
                                return 0
                        
                        # TWSE格式: [日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數]
                        close = safe_float(row[6])
                        if close == 0:
                            continue
                        
                        all_prices.append({
                            'date': row[0],
                            'open': safe_float(row[3]),
                            'high': safe_float(row[4]),
                            'low': safe_float(row[5]),
                            'close': close,
                            'volume': self._safe_int(row[1]) // 1000,  # 股數→張數
                        })
                    except:
                        continue
            except:
                continue
        
        # 去重（跨月可能重複）並取最近N天
        if all_prices:
            seen_dates = set()
            unique_prices = []
            for p in all_prices:
                if p['date'] not in seen_dates:
                    seen_dates.add(p['date'])
                    unique_prices.append(p)
            
            unique_prices.sort(key=lambda x: x['date'])
            
            if use_cache and len(unique_prices) >= days:
                self._save_to_cache(code, unique_prices)
            
            return unique_prices[-days:] if len(unique_prices) > days else unique_prices
        
        return None
    
    def get_stock_info_batch(self, stock_list):
        """
        批次取得股票資訊
        返回: dict {代碼: 價格資訊}
        """
        results = {}
        
        for code, name in stock_list:
            price_data = self.get_stock_price(code)
            if price_data:
                results[code] = {
                    'name': name,
                    **price_data
                }
        
        return results
