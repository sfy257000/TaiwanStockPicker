# -*- coding: utf-8 -*-
"""資料品質監控。"""

from __future__ import annotations


class DataQualityMonitor:
    @staticmethod
    def summarize(results: list[dict]) -> dict:
        total = len(results)
        if total == 0:
            return {
                'total': 0,
                'price_from_history': 0,
                'unknown_market': 0,
                'missing_fundamental': 0,
                'zero_volume': 0,
                'negative_price': 0,
                'bad_rows': [],
            }

        price_from_history = 0
        unknown_market = 0
        missing_fundamental = 0
        zero_volume = 0
        negative_price = 0
        bad_rows: list[dict] = []

        for r in results:
            qa = r.get('qa', {}) or {}
            price_source = str(qa.get('price_source') or '').strip()
            if price_source == 'history_fallback':
                price_from_history += 1

            # 看「原始市場欄位」是否可用，比分類後市場更能反映資料品質
            raw_market = str(qa.get('market_raw') or '').strip().lower()
            if raw_market not in {'tse', 'otc'}:
                unknown_market += 1

            f = r.get('fundamental') or {}
            if f.get('pe_ratio') is None and f.get('pb_ratio') is None and f.get('dividend_yield') is None:
                missing_fundamental += 1

            volume = int(r.get('volume', 0) or 0)
            price = float(r.get('price', 0) or 0)
            if volume <= 0:
                zero_volume += 1
            if price <= 0:
                negative_price += 1

            if volume <= 0 or price <= 0 or raw_market not in {'tse', 'otc'}:
                bad_rows.append(
                    {
                        '代碼': r.get('code', ''),
                        '名稱': r.get('name', ''),
                        '市場(分類)': r.get('market', ''),
                        '市場(原始)': raw_market or 'N/A',
                        '價格': price,
                        '成交量': volume,
                        'price_source': price_source or 'N/A',
                    }
                )

        return {
            'total': total,
            'price_from_history': price_from_history,
            'unknown_market': unknown_market,
            'missing_fundamental': missing_fundamental,
            'zero_volume': zero_volume,
            'negative_price': negative_price,
            'bad_rows': bad_rows[:200],
        }

