# -*- coding: utf-8 -*-
"""
價量異常警示模組
監控爆量、價量背離、漲跌停等異常情況
"""

from config import CONFIG
from utils import format_percentage, format_number

class PriceVolumeAlert:
    def __init__(self):
        self.params = CONFIG['alerts']
    
    def check_alerts(self, current_data, historical_data=None):
        """
        檢查價量異常
        返回: {
            'alerts': 警示列表,
            'score': 評分,
            'reasons': 理由,
        }
        """
        alerts = []
        score = 0
        reasons = []
        
        if not current_data:
            return {'alerts': [], 'score': 0, 'reasons': ['無數據']}
        
        price = current_data.get('price', 0)
        prev_close = current_data.get('prev_close', 0)
        volume = current_data.get('volume', 0)
        high = current_data.get('high', 0)
        low = current_data.get('low', 0)
        
        if prev_close > 0:
            change_pct = ((price - prev_close) / prev_close) * 100
        else:
            change_pct = 0
        
        limit_up_alert = self._check_limit_up(change_pct)
        if limit_up_alert:
            alerts.append(limit_up_alert)
            score += 20
            reasons.append(f"漲停({format_percentage(change_pct)})")
        
        limit_down_alert = self._check_limit_down(change_pct)
        if limit_down_alert:
            alerts.append(limit_down_alert)
            score -= 20
            reasons.append(f"跌停({format_percentage(change_pct)})")
        
        price_surge_alert = self._check_price_surge(change_pct)
        if price_surge_alert:
            alerts.append(price_surge_alert)
            score += 15
            reasons.append(f"價格暴漲{format_percentage(change_pct)}")
        
        price_drop_alert = self._check_price_drop(change_pct)
        if price_drop_alert:
            alerts.append(price_drop_alert)
            score -= 15
            reasons.append(f"價格暴跌{format_percentage(change_pct)}")
        
        if historical_data and len(historical_data) > 5:
            avg_volume = sum([d.get('volume', 0) for d in historical_data[-5:]]) / 5
            volume_surge_alert = self._check_volume_surge(volume, avg_volume)
            
            if volume_surge_alert:
                alerts.append(volume_surge_alert)
                score += 10
                reasons.append(f"成交量爆量({format_number(volume)}張)")
        
        if high > 0 and low > 0 and prev_close > 0:
            price_range_alert = self._check_price_range(high, low, prev_close)
            if price_range_alert:
                alerts.append(price_range_alert)
                score += 5
                reasons.append(f"震幅大，波動機會")
        
        return {
            'alerts': alerts,
            'score': score,
            'reasons': reasons,
        }
    
    def _check_limit_up(self, change_pct):
        """檢查漲停"""
        threshold = self.params['limit_up']
        
        if change_pct >= threshold:
            return {
                'type': 'limit_up',
                'severity': 'high',
                'message': f'漲停警示：漲幅 {format_percentage(change_pct)}',
            }
        
        return None
    
    def _check_limit_down(self, change_pct):
        """檢查跌停"""
        threshold = self.params['limit_down']
        
        if change_pct <= threshold:
            return {
                'type': 'limit_down',
                'severity': 'high',
                'message': f'跌停警示：跌幅 {format_percentage(change_pct)}',
            }
        
        return None
    
    def _check_price_surge(self, change_pct):
        """檢查價格暴漲"""
        threshold = self.params['price_surge']
        
        if change_pct >= threshold:
            return {
                'type': 'price_surge',
                'severity': 'medium',
                'message': f'價格暴漲：{format_percentage(change_pct)}',
            }
        
        return None
    
    def _check_price_drop(self, change_pct):
        """檢查價格暴跌"""
        threshold = self.params['price_drop']
        
        if change_pct <= threshold:
            return {
                'type': 'price_drop',
                'severity': 'medium',
                'message': f'價格暴跌：{format_percentage(change_pct)}',
            }
        
        return None
    
    def _check_volume_surge(self, current_vol, avg_vol):
        """檢查爆量"""
        if avg_vol == 0:
            return None
        
        ratio = current_vol / avg_vol
        threshold = self.params['volume_surge']
        
        if ratio >= threshold:
            return {
                'type': 'volume_surge',
                'severity': 'medium',
                'message': f'成交量爆量：{format_number(current_vol)}張（平均{format_number(int(avg_vol))}張的{ratio:.1f}倍）',
            }
        
        return None
    
    def _check_price_range(self, high, low, prev_close):
        """檢查價格震幅"""
        if prev_close == 0:
            return None
        
        range_pct = ((high - low) / prev_close) * 100
        
        if range_pct > 7:
            return {
                'type': 'price_range',
                'severity': 'low',
                'message': f'震幅大：{format_percentage(range_pct)}',
            }
        
        return None
    
    def get_limit_monitor(self, stock_list, price_data_dict):
        """
        漲跌停監控
        返回: {
            'limit_up': 漲停股列表,
            'limit_down': 跌停股列表,
            'near_limit_up': 接近漲停列表,
        }
        """
        limit_up = []
        limit_down = []
        near_limit_up = []
        
        for code, name in stock_list:
            data = price_data_dict.get(code)
            if not data:
                continue
            
            price = data.get('price', 0)
            prev_close = data.get('prev_close', 0)
            
            if prev_close > 0:
                change_pct = ((price - prev_close) / prev_close) * 100
            else:
                continue
            
            limit_up_threshold = self.params['limit_up']
            limit_down_threshold = self.params['limit_down']
            
            if change_pct >= limit_up_threshold:
                limit_up.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change_pct': change_pct,
                })
            elif change_pct >= limit_up_threshold - 1:
                near_limit_up.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change_pct': change_pct,
                })
            elif change_pct <= limit_down_threshold:
                limit_down.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change_pct': change_pct,
                })
        
        return {
            'limit_up': limit_up,
            'limit_down': limit_down,
            'near_limit_up': near_limit_up,
        }
