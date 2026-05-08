# -*- coding: utf-8 -*-
"""
外援連續買賣超追蹤模組
追蹤外援、投信、自營商連續買賣超
"""

from config import CONFIG


class InstitutionalTracker:
    def __init__(self):
        self.params = CONFIG['institutional']

    def analyze_institutional(self, institutional_data):
        """
        分析三大法人買賣超
        返回: {
            'score': 評分,
            'reasons': 理由,
            'foreign_trend': 外資趨勢,
            'trust_trend': 投信趨勢,
        }
        """
        if not institutional_data:
            return {
                'score': 0,
                'reasons': ['無法人數據'],
                'foreign_trend': 'unknown',
                'trust_trend': 'unknown',
            }

        score = 0
        reasons = []

        # 安全地取得數值，處理 None 和類型錯誤
        try:
            foreign = int(institutional_data.get('foreign', 0) or 0)
            trust = int(institutional_data.get('investment_trust', 0) or 0)
            dealer = int(institutional_data.get('dealer', 0) or 0)
            total = int(institutional_data.get('total', 0) or 0)
        except (ValueError, TypeError):
            return {
                'score': 0,
                'reasons': ['法人數據格式錯誤'],
                'foreign_trend': 'unknown',
                'trust_trend': 'unknown',
            }

        foreign_trend = self._analyze_trend(foreign)
        trust_trend = self._analyze_trend(trust)

        # 三大法人合計分析
        if total > self.params['total_buy_amount']:
            score += 25
            reasons.append(f"三大法人買超{total:,}張")
        elif total > 0:
            score += 15
            reasons.append(f"三大法人買超{total:,}張")
        elif total < -self.params['total_buy_amount']:
            score -= 20
            reasons.append(f"三大法人賣超{abs(total):,}張")
        elif total < 0:
            score -= 10
            reasons.append(f"三大法人賣超{abs(total):,}張")

        # 外資分析 - 顯示千張為主，張數為輔
        foreign_thousands = foreign // 1000
        if foreign > self.params['foreign_buy_amount'] * 5:
            score += 15
            if foreign_thousands != 0:
                reasons.append(f"外援大買{foreign_thousands:,}千張")
            else:
                reasons.append(f"外援大買{foreign}張")
        elif foreign > self.params['foreign_buy_amount']:
            score += 10
            if foreign_thousands != 0:
                reasons.append(f"外援買超{foreign_thousands:,}千張")
            else:
                reasons.append(f"外援買超{foreign}張")
        elif foreign > 0:
            score += 5
            reasons.append(f"外援買超{foreign:,}張")
        elif foreign < -self.params['foreign_buy_amount'] * 5:
            score -= 15
            if foreign_thousands != 0:
                reasons.append(f"外援大賣{abs(foreign_thousands):,}千張")
            else:
                reasons.append(f"外援大賣{abs(foreign)}張")
        elif foreign < -self.params['foreign_buy_amount']:
            score -= 10
            if foreign_thousands != 0:
                reasons.append(f"外援賣超{abs(foreign_thousands):,}千張")
            else:
                reasons.append(f"外援賣超{abs(foreign)}張")
        elif foreign < 0:
            score -= 5
            reasons.append(f"外援賣超{abs(foreign):,}張")

        # 投信分析
        if trust > 1000:
            score += 5
            reasons.append(f"投信買超{trust:,}張")
        elif trust < -1000:
            score -= 5
            reasons.append(f"投信賣超{abs(trust):,}張")

        return {
            'score': score,
            'reasons': reasons,
            'foreign_trend': foreign_trend,
            'trust_trend': trust_trend,
        }

    def _analyze_trend(self, amount):
        """分析趨勢"""
        if amount > 5000:
            return 'strong_buy'
        elif amount > 1000:
            return 'buy'
        elif amount > 0:
            return 'small_buy'
        elif amount > -1000:
            return 'small_sell'
        elif amount > -5000:
            return 'sell'
        else:
            return 'strong_sell'

    def check_continuous_buy(self, history_data, days=3):
        """
        檢查連續買超
        history_data: 歷史買賣超數據
        返回: (是否連續買超, 連續天數)
        """
        if not history_data or len(history_data) < days:
            return False, 0

        continuous_days = 0
        for data in history_data[-days:]:
            if data.get('total', 0) > 0:
                continuous_days += 1
            else:
                break

        return continuous_days >= days, continuous_days

    def get_institutional_summary(self, institutional_data):
        """
        取得法人摘要
        """
        if not institutional_data:
            return "無數據"

        try:
            foreign = int(institutional_data.get('foreign', 0) or 0)
            trust = int(institutional_data.get('investment_trust', 0) or 0)
            dealer = int(institutional_data.get('dealer', 0) or 0)
            total = int(institutional_data.get('total', 0) or 0)
        except (ValueError, TypeError):
            return "數據格式錯誤"

        parts = []

        if abs(foreign) >= 1000:
            parts.append(f"外援{foreign:+,}張")
        if abs(trust) >= 100:
            parts.append(f"投信{trust:+,}張")
        if abs(dealer) >= 100:
            parts.append(f"自營{dealer:+,}張")

        if not parts:
            return f"合計{total:+,}張"

        return ' | '.join(parts)