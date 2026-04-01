# -*- coding: utf-8 -*-
"""策略工坊：條件組合與參數掃描。"""

from __future__ import annotations


class StrategyWorkshop:
    @staticmethod
    def filter_by_rules(
        results: list[dict],
        min_total_score: int,
        min_change_pct: float,
        min_volume: int,
        require_k_gt_d: bool,
        require_foreign_buy: bool,
    ) -> list[dict]:
        picks: list[dict] = []
        for r in results:
            if r.get('total_score', 0) < min_total_score:
                continue
            if r.get('change_pct', 0.0) < min_change_pct:
                continue
            if r.get('volume', 0) < min_volume:
                continue
            if require_k_gt_d:
                kd = (r.get('indicators') or {}).get('kd', {})
                if kd.get('k', 0) <= kd.get('d', 0):
                    continue
            if require_foreign_buy:
                inst = r.get('institutional') or {}
                if inst.get('foreign', 0) <= 0:
                    continue
            picks.append(r)
        return picks

    @staticmethod
    def grid_search_candidates(results: list[dict]) -> list[dict]:
        score_options = [10, 15, 20, 25]
        change_options = [-1.0, 0.0, 1.0]
        volume_options = [1000, 3000, 5000]
        rows: list[dict] = []
        total = max(1, len(results))

        for min_score in score_options:
            for min_change in change_options:
                for min_vol in volume_options:
                    picks = StrategyWorkshop.filter_by_rules(
                        results=results,
                        min_total_score=min_score,
                        min_change_pct=min_change,
                        min_volume=min_vol,
                        require_k_gt_d=False,
                        require_foreign_buy=False,
                    )
                    hit = len(picks)
                    avg_score = (sum(float(p.get('total_score', 0)) for p in picks) / hit) if hit > 0 else 0.0
                    avg_change = (sum(float(p.get('change_pct', 0)) for p in picks) / hit) if hit > 0 else 0.0
                    rows.append(
                        {
                            'min_score': min_score,
                            'min_change_pct': min_change,
                            'min_volume': min_vol,
                            '命中數': hit,
                            '命中率%': round(hit / total * 100.0, 2),
                            '平均總分': round(avg_score, 2),
                            '平均漲跌%': round(avg_change, 2),
                            '綜合分': round(avg_score + avg_change * 0.8, 2),
                        }
                    )
        rows.sort(key=lambda x: (x['綜合分'], x['命中率%']), reverse=True)
        return rows

