# -*- coding: utf-8 -*-
"""風險控管計算。"""

from __future__ import annotations


class RiskControlEngine:
    @staticmethod
    def calc_atr(historical_data: list[dict], period: int = 14) -> float | None:
        if not historical_data or len(historical_data) < period + 1:
            return None

        trs: list[float] = []
        for i in range(1, len(historical_data)):
            cur = historical_data[i]
            prev = historical_data[i - 1]
            high = float(cur.get('high') or 0)
            low = float(cur.get('low') or 0)
            prev_close = float(prev.get('close') or 0)
            if high <= 0 or low <= 0 or prev_close <= 0:
                continue
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)

        if len(trs) < period:
            return None
        sample = trs[-period:]
        return sum(sample) / len(sample)

    @staticmethod
    def suggest_position(
        price: float,
        atr: float | None,
        capital: float,
        risk_pct_per_trade: float = 1.0,
        stop_atr_multiple: float = 2.0,
    ) -> dict:
        if price <= 0 or capital <= 0:
            return {
                'stop_loss': None,
                'take_profit': None,
                'shares': 0,
                'risk_amount': 0.0,
                'position_value': 0.0,
                'position_pct': 0.0,
            }

        risk_amount = capital * (risk_pct_per_trade / 100.0)
        atr_val = atr if atr and atr > 0 else price * 0.03
        risk_per_share = atr_val * stop_atr_multiple
        shares = int(risk_amount // max(risk_per_share, 0.01))
        shares = max(0, shares)
        position_value = shares * price
        position_pct = (position_value / capital * 100.0) if capital > 0 else 0.0

        stop_loss = max(0.0, price - risk_per_share)
        take_profit = price + risk_per_share * 2
        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'shares': shares,
            'risk_amount': risk_amount,
            'position_value': position_value,
            'position_pct': position_pct,
            'risk_per_share': risk_per_share,
        }

