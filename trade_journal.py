# -*- coding: utf-8 -*-
"""交易日誌管理。"""

from __future__ import annotations

import json
import os
from datetime import datetime


class TradeJournal:
    def __init__(self, path: str = 'history/trade_journal.json'):
        self.path = path
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)

    def load(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def save(self, entries: list[dict]) -> None:
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

    def add_entry(
        self,
        code: str,
        name: str,
        strategy: str,
        signal_tag: str,
        entry_price: float,
        exit_price: float,
        shares: int,
        note: str,
        trade_date: str | None = None,
    ) -> dict:
        entries = self.load()
        trade_date = trade_date or datetime.now().strftime('%Y-%m-%d')
        cost = entry_price * shares
        value = exit_price * shares
        pnl = value - cost
        pnl_pct = (pnl / cost * 100.0) if cost > 0 else 0.0
        row = {
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trade_date': trade_date,
            'code': code,
            'name': name,
            'strategy': strategy,
            'signal_tag': signal_tag,
            'entry_price': round(entry_price, 4),
            'exit_price': round(exit_price, 4),
            'shares': int(shares),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'note': note.strip(),
        }
        entries.append(row)
        self.save(entries)
        return row

    @staticmethod
    def summarize(entries: list[dict]) -> dict:
        if not entries:
            return {'count': 0, 'win_rate': 0.0, 'avg_pnl_pct': 0.0, 'by_signal': []}

        wins = [e for e in entries if float(e.get('pnl', 0)) > 0]
        avg = sum(float(e.get('pnl_pct', 0)) for e in entries) / len(entries)
        signal_map: dict[str, dict] = {}
        for e in entries:
            tag = str(e.get('signal_tag') or '未分類')
            row = signal_map.setdefault(tag, {'signal_tag': tag, 'count': 0, 'wins': 0, 'sum_pct': 0.0})
            row['count'] += 1
            if float(e.get('pnl', 0)) > 0:
                row['wins'] += 1
            row['sum_pct'] += float(e.get('pnl_pct', 0))

        by_signal = []
        for row in signal_map.values():
            count = max(1, row['count'])
            by_signal.append(
                {
                    '訊號': row['signal_tag'],
                    '交易數': row['count'],
                    '勝率%': round(row['wins'] / count * 100.0, 2),
                    '平均報酬%': round(row['sum_pct'] / count, 2),
                }
            )
        by_signal.sort(key=lambda x: (x['平均報酬%'], x['勝率%']), reverse=True)
        return {
            'count': len(entries),
            'win_rate': len(wins) / len(entries) * 100.0,
            'avg_pnl_pct': avg,
            'by_signal': by_signal,
        }

