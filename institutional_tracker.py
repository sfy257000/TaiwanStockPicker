# -*- coding: utf-8 -*-
"""
外資連續買賣超追蹤模組
追蹤外資、投信、自營商連續買賣超
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
        
        foreign = institutional_data.get('foreign', 0)
        trust = institutional_data.get('investment_trust', 0)
        dealer = institutional_data.get('dealer', 0)
        total = institutional_data.get('total', 0)
        
        foreign_trend = self._analyze_trend(foreign)
        trust_trend = self._analyze_trend(trust)
        
        if total > self.params['total_buy_amount']:
            score += 25
            reasons.append(f"三大法人買超{total//1000}千張")
        elif total > 0:
            score += 15
            reasons.append(f"三大法人買超{total}張")
        elif total < -self.params['total_buy_amount']:
            score -= 20
            reasons.append(f"三大法人賣超{abs(total)//1000}千張")
        elif total < 0:
            score -= 10
            reasons.append(f"三大法人賣超{abs(total)}張")
        
        if foreign > self.params['foreign_buy_amount'] * 5:
            score += 15
            reasons.append(f"外資大買{foreign//1000}千張")
        elif foreign > self.params['foreign_buy_amount']:
            score += 10
            reasons.append(f"外資買超{foreign//1000}千張")
        elif foreign > 0:
            score += 5
            reasons.append(f"外資買超{foreign}張")
        elif foreign < -self.params['foreign_buy_amount'] * 5:
            score -= 15
            reasons.append(f"外資大賣{abs(foreign)//1000}千張")
        elif foreign < -self.params['foreign_buy_amount']:
            score -= 10
            reasons.append(f"外資賣超{abs(foreign)//1000}千張")
        elif foreign < 0:
            score -= 5
            reasons.append(f"外資賣超{abs(foreign)}張")
        
        if trust > 1000:
            score += 5
            reasons.append(f"投信買超{trust}張")
        elif trust < -1000:
            score -= 5
            reasons.append(f"投信賣超{abs(trust)}張")
        
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
        
        foreign = institutional_data.get('foreign', 0)
        trust = institutional_data.get('investment_trust', 0)
        dealer = institutional_data.get('dealer', 0)
        total = institutional_data.get('total', 0)
        
        parts = []
        
        if abs(foreign) >= 1000:
            parts.append(f"外資{foreign:+,}張")
        if abs(trust) >= 100:
            parts.append(f"投信{trust:+,}張")
        if abs(dealer) >= 100:
            parts.append(f"自營{dealer:+,}張")
        
        if not parts:
            return f"合計{total:+,}張"
        
        return ' | '.join(parts)
