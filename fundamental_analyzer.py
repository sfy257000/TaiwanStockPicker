# -*- coding: utf-8 -*-
"""基本面資料抓取與評分。"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

import requests


class FundamentalAnalyzer:
    def __init__(self):
        self._headers = {'User-Agent': 'Mozilla/5.0'}
        self._bwibbu_cache: dict[str, dict] | None = None
        self._bwibbu_cache_time = 0.0
        self._cache_ttl = 60 * 60 * 6
        self._lock = threading.Lock()

    @staticmethod
    def _safe_float(val) -> float | None:
        try:
            if val in (None, '', '-', '--', 'N/A'):
                return None
            return float(str(val).replace(',', '').replace('%', '').strip())
        except Exception:
            return None

    def _need_refresh(self) -> bool:
        return (time.time() - self._bwibbu_cache_time) > self._cache_ttl or self._bwibbu_cache is None

    def _fetch_bwibbu(self) -> dict[str, dict]:
        with self._lock:
            if not self._need_refresh():
                return self._bwibbu_cache or {}

            parsed: dict[str, dict] = {}
            # 往前回溯可用交易日，避免「當日尚未更新」造成整批空值
            for days_ago in range(0, 14):
                date_str = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
                urls = [
                    f'https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?response=json&date={date_str}&selectType=ALL',
                    f'https://www.twse.com.tw/exchangeReport/BWIBBU_d?response=json&date={date_str}&selectType=ALL',
                ]
                for url in urls:
                    try:
                        payload = requests.get(url, headers=self._headers, timeout=15, verify=False).json()
                        rows = payload.get('data', [])
                        fields = payload.get('fields', []) or []
                        if not rows:
                            continue
                        field_idx = {str(f).strip(): i for i, f in enumerate(fields)}
                        idx_code = field_idx.get('證券代號', 0)
                        idx_pe = field_idx.get('本益比', 5)
                        idx_pb = field_idx.get('股價淨值比', 6)
                        idx_dy = field_idx.get('殖利率(%)', 3)
                        for row in rows:
                            if len(row) < 4:
                                continue
                            code = str(row[idx_code] if len(row) > idx_code else row[0]).strip()
                            if not code:
                                continue
                            parsed[code] = {
                                'pe_ratio': self._safe_float(row[idx_pe] if len(row) > idx_pe else None),
                                'pb_ratio': self._safe_float(row[idx_pb] if len(row) > idx_pb else None),
                                'dividend_yield': self._safe_float(row[idx_dy] if len(row) > idx_dy else None),
                            }
                        if parsed:
                            break
                    except Exception:
                        continue
                if parsed:
                    break

            self._bwibbu_cache = parsed
            self._bwibbu_cache_time = time.time()
            return parsed

    def get_fundamental_data(self, code: str) -> dict:
        raw = self._fetch_bwibbu().get(code, {})
        return {
            'pe_ratio': raw.get('pe_ratio'),
            'pb_ratio': raw.get('pb_ratio'),
            'dividend_yield': raw.get('dividend_yield'),
            # 先保留欄位，後續可再串財報 API
            'revenue_yoy': None,
            'eps_growth': None,
            'roe': None,
        }

    def score(self, data: dict) -> tuple[int, list[str]]:
        pe = data.get('pe_ratio')
        pb = data.get('pb_ratio')
        dy = data.get('dividend_yield')
        revenue_yoy = data.get('revenue_yoy')
        eps_growth = data.get('eps_growth')
        roe = data.get('roe')

        score = 0
        reasons: list[str] = []

        if pe is not None:
            if 8 <= pe <= 20:
                score += 3
                reasons.append(f'本益比合理（PE={pe:.1f}）')
            elif pe > 30:
                score -= 3
                reasons.append(f'本益比偏高（PE={pe:.1f}）')

        if pb is not None:
            if pb <= 2:
                score += 2
                reasons.append(f'股價淨值比偏低（PB={pb:.2f}）')
            elif pb >= 4:
                score -= 2
                reasons.append(f'股價淨值比偏高（PB={pb:.2f}）')

        if dy is not None:
            if dy >= 3:
                score += 3
                reasons.append(f'殖利率具吸引力（{dy:.2f}%）')
            elif dy < 1:
                score -= 1
                reasons.append(f'殖利率偏低（{dy:.2f}%）')

        if revenue_yoy is not None:
            if revenue_yoy >= 10:
                score += 3
                reasons.append(f'營收年增強勁（YoY={revenue_yoy:.1f}%）')
            elif revenue_yoy <= -10:
                score -= 3
                reasons.append(f'營收年減明顯（YoY={revenue_yoy:.1f}%）')

        if eps_growth is not None:
            if eps_growth >= 10:
                score += 2
                reasons.append(f'EPS 成長良好（{eps_growth:.1f}%）')
            elif eps_growth < 0:
                score -= 2
                reasons.append(f'EPS 衰退（{eps_growth:.1f}%）')

        if roe is not None:
            if roe >= 10:
                score += 2
                reasons.append(f'ROE 健康（{roe:.1f}%）')
            elif roe < 5:
                score -= 1
                reasons.append(f'ROE 偏低（{roe:.1f}%）')

        return max(-12, min(12, int(round(score)))), reasons
