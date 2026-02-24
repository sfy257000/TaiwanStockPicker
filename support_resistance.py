# -*- coding: utf-8 -*-
"""
支撐壓力位計算模組
計算股票的支撐與壓力價位
"""

from config import CONFIG

class SupportResistance:
    def __init__(self):
        self.params = CONFIG['support_resistance']
    
    def calculate(self, historical_data):
        """
        計算支撐壓力位
        historical_data: 歷史價格數據
        返回: {
            'support': 支撐位列表,
            'resistance': 壓力位列表,
            'current_price': 現價,
            'position': 位置評估,
        }
        """
        if not historical_data or len(historical_data) < 10:
            return None
        
        lookback = min(self.params['lookback_days'], len(historical_data))
        recent_data = historical_data[-lookback:]
        
        current_price = recent_data[-1]['close']
        
        price_levels = self._find_price_levels(recent_data)
        
        support_levels = self._identify_support(price_levels, current_price)
        resistance_levels = self._identify_resistance(price_levels, current_price)
        
        position = self._evaluate_position(current_price, support_levels, resistance_levels)
        
        return {
            'support': support_levels[:3],
            'resistance': resistance_levels[:3],
            'current_price': current_price,
            'position': position,
        }
    
    def _find_price_levels(self, data):
        """找出關鍵價位"""
        price_levels = []
        
        for i in range(1, len(data) - 1):
            high = data[i]['high']
            low = data[i]['low']
            prev_high = data[i-1]['high']
            prev_low = data[i-1]['low']
            next_high = data[i+1]['high']
            next_low = data[i+1]['low']
            
            if high > prev_high and high > next_high:
                price_levels.append({
                    'price': high,
                    'type': 'resistance',
                    'strength': 1,
                })
            
            if low < prev_low and low < next_low:
                price_levels.append({
                    'price': low,
                    'type': 'support',
                    'strength': 1,
                })
        
        return self._merge_similar_levels(price_levels)
    
    def _merge_similar_levels(self, levels):
        """合併相近的價位"""
        if not levels:
            return []
        
        tolerance = self.params['tolerance']
        merged = []
        
        levels.sort(key=lambda x: x['price'])
        
        for level in levels:
            if not merged:
                merged.append(level)
                continue
            
            last = merged[-1]
            price_diff = abs(level['price'] - last['price']) / last['price']
            
            if price_diff < tolerance:
                last['strength'] += 1
                last['price'] = (last['price'] + level['price']) / 2
            else:
                merged.append(level)
        
        return merged
    
    def _identify_support(self, price_levels, current_price):
        """識別支撐位"""
        support = [l for l in price_levels 
                   if l['type'] == 'support' and l['price'] < current_price]
        
        support.sort(key=lambda x: x['price'], reverse=True)
        
        return [s['price'] for s in support if s['strength'] >= self.params['touch_count']]
    
    def _identify_resistance(self, price_levels, current_price):
        """識別壓力位"""
        resistance = [l for l in price_levels 
                      if l['type'] == 'resistance' and l['price'] > current_price]
        
        resistance.sort(key=lambda x: x['price'])
        
        return [r['price'] for r in resistance if r['strength'] >= self.params['touch_count']]
    
    def _evaluate_position(self, current_price, support_levels, resistance_levels):
        """評估目前位置"""
        if not support_levels and not resistance_levels:
            return 'unknown'
        
        nearest_support = support_levels[0] if support_levels else None
        nearest_resistance = resistance_levels[0] if resistance_levels else None
        
        if nearest_support and nearest_resistance:
            support_distance = (current_price - nearest_support) / current_price
            resistance_distance = (nearest_resistance - current_price) / current_price
            
            if support_distance < 0.03:
                return 'near_support'
            elif resistance_distance < 0.03:
                return 'near_resistance'
            elif support_distance < resistance_distance:
                return 'above_support'
            else:
                return 'below_resistance'
        
        elif nearest_support:
            support_distance = (current_price - nearest_support) / current_price
            if support_distance < 0.03:
                return 'near_support'
            else:
                return 'above_support'
        
        elif nearest_resistance:
            resistance_distance = (nearest_resistance - current_price) / current_price
            if resistance_distance < 0.03:
                return 'near_resistance'
            else:
                return 'below_resistance'
        
        return 'unknown'
    
    def get_support_resistance_score(self, sr_data):
        """
        根據支撐壓力計算評分
        """
        if not sr_data:
            return 0, []
        
        score = 0
        reasons = []
        
        position = sr_data.get('position', 'unknown')
        
        if position == 'near_support':
            score += 15
            reasons.append("接近支撐位，有支撐")
        elif position == 'near_resistance':
            score -= 10
            reasons.append("接近壓力位，有壓力")
        elif position == 'above_support':
            score += 10
            reasons.append("在支撐之上")
        elif position == 'below_resistance':
            score += 5
            reasons.append("在壓力之下")
        
        support = sr_data.get('support', [])
        resistance = sr_data.get('resistance', [])
        
        if support:
            reasons.append(f"支撐位: {', '.join([f'{p:.1f}' for p in support[:2]])}")
        if resistance:
            reasons.append(f"壓力位: {', '.join([f'{p:.1f}' for p in resistance[:2]])}")
        
        return score, reasons
