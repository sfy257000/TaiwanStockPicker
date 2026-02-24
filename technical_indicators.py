# -*- coding: utf-8 -*-
"""
技術指標模組
計算 RSI、MACD、KD、MA 等技術指標
"""

from config import CONFIG

class TechnicalIndicators:
    def __init__(self):
        self.params = CONFIG['technical']
    
    def calculate_all(self, price_data_list):
        """
        計算所有技術指標
        price_data_list: 歷史價格列表
        返回: dict 包含所有指標
        """
        if not price_data_list or len(price_data_list) < 20:
            return None
        
        closes = [p['close'] for p in price_data_list if p['close'] > 0]
        highs = [p['high'] for p in price_data_list if p['high'] > 0]
        lows = [p['low'] for p in price_data_list if p['low'] > 0]
        volumes = [p['volume'] for p in price_data_list]
        
        if len(closes) < 20:
            return None
        
        indicators = {}
        
        indicators['rsi'] = self.calculate_rsi(closes)
        indicators['macd'] = self.calculate_macd(closes)
        indicators['kd'] = self.calculate_kd(highs, lows, closes)
        indicators['ma'] = self.calculate_ma(closes)
        indicators['bias'] = self.calculate_bias(closes)
        indicators['bollinger'] = self.calculate_bollinger_bands(closes)
        
        return indicators
    
    def calculate_rsi(self, closes, period=None):
        """
        計算 RSI
        返回: {'rsi': 數值, 'signal': 訊號}
        """
        if period is None:
            period = self.params['rsi_period']
        
        if len(closes) < period + 1:
            return {'rsi': 50, 'signal': 'neutral'}
        
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = [c if c > 0 else 0 for c in changes[-period:]]
        losses = [-c if c < 0 else 0 for c in changes[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        oversold = self.params['rsi_oversold']
        overbought = self.params['rsi_overbought']
        
        if rsi < oversold:
            signal = 'oversold'
        elif rsi > overbought:
            signal = 'overbought'
        else:
            signal = 'neutral'
        
        return {
            'rsi': round(rsi, 2),
            'signal': signal
        }
    
    def calculate_macd(self, closes):
        """
        計算 MACD
        返回: {'macd': 值, 'signal': 訊號線, 'hist': 柱狀圖, 'trend': 趨勢}
        """
        fast_period = self.params['macd_fast']
        slow_period = self.params['macd_slow']
        signal_period = self.params['macd_signal']
        
        if len(closes) < slow_period + signal_period:
            return {'macd': 0, 'signal': 0, 'hist': 0, 'trend': 'neutral'}
        
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_val = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_val.append((price - ema_val[-1]) * multiplier + ema_val[-1])
            return ema_val
        
        ema_fast = ema(closes, fast_period)
        ema_slow = ema(closes, slow_period)
        
        min_len = min(len(ema_fast), len(ema_slow))
        macd_line = [ema_fast[-min_len + i] - ema_slow[-min_len + i] for i in range(min_len)]
        
        signal_line = ema(macd_line, signal_period)
        
        macd = macd_line[-1] if macd_line else 0
        signal = signal_line[-1] if signal_line else 0
        hist = macd - signal
        
        if hist > 0:
            trend = 'bullish'
        elif hist < 0:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        return {
            'macd': round(macd, 4),
            'signal': round(signal, 4),
            'hist': round(hist, 4),
            'trend': trend
        }
    
    def calculate_kd(self, highs, lows, closes, period=None):
        """
        計算 KD 指標
        返回: {'k': K值, 'd': D值, 'signal': 訊號}
        """
        if period is None:
            period = self.params['kd_period']
        
        if len(closes) < period:
            return {'k': 50, 'd': 50, 'signal': 'neutral'}
        
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        current_close = closes[-1]
        
        highest = max(recent_highs)
        lowest = min(recent_lows)
        
        if highest == lowest:
            rsv = 50
        else:
            rsv = ((current_close - lowest) / (highest - lowest)) * 100
        
        k_smooth = self.params['k_smooth']
        d_smooth = self.params['d_smooth']
        
        k = rsv
        d = rsv
        
        return {
            'k': round(k, 2),
            'd': round(d, 2),
            'signal': 'oversold' if k < 20 else ('overbought' if k > 80 else 'neutral')
        }
    
    def calculate_ma(self, closes):
        """
        計算移動平均線
        返回: {週期: 均線值}
        """
        ma_values = {}
        
        for period in self.params['ma_periods']:
            if len(closes) >= period:
                ma_values[f'ma{period}'] = round(sum(closes[-period:]) / period, 2)
        
        return ma_values
    
    def calculate_bias(self, closes):
        """
        計算乖離率
        返回: {週期: 乖離率}
        """
        bias_values = {}
        
        for period in [6, 12, 24]:
            if len(closes) >= period:
                ma = sum(closes[-period:]) / period
                bias = ((closes[-1] - ma) / ma) * 100
                bias_values[f'bias{period}'] = round(bias, 2)
        
        return bias_values
    
    def calculate_bollinger_bands(self, closes, period=20, std_dev=2):
        """
        計算布林通道
        period: 均線週期（預設20日）
        std_dev: 標準差倍數（預設2倍）
        返回: {'upper': 上軌, 'middle': 中軌, 'lower': 下軌, 'bandwidth': 頻寬, 'position': 位置%}
        """
        if len(closes) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0, 'bandwidth': 0, 'position': 50, 'signal': 'neutral'}
        
        recent_closes = closes[-period:]
        middle = sum(recent_closes) / period
        
        variance = sum((x - middle) ** 2 for x in recent_closes) / period
        std = variance ** 0.5
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        bandwidth = ((upper - lower) / middle) * 100 if middle > 0 else 0
        
        current_price = closes[-1]
        if upper != lower:
            position = ((current_price - lower) / (upper - lower)) * 100
        else:
            position = 50
        
        if position < 20:
            signal = 'oversold'
        elif position > 80:
            signal = 'overbought'
        else:
            signal = 'neutral'
        
        return {
            'upper': round(upper, 2),
            'middle': round(middle, 2),
            'lower': round(lower, 2),
            'bandwidth': round(bandwidth, 2),
            'position': round(position, 2),
            'signal': signal
        }
    
    def get_technical_score(self, indicators):
        """
        根據技術指標計算評分
        """
        if not indicators:
            return 0, []
        
        score = 0
        reasons = []
        
        rsi_data = indicators.get('rsi', {})
        rsi = rsi_data.get('rsi', 50)
        rsi_signal = rsi_data.get('signal', 'neutral')
        
        if rsi_signal == 'oversold':
            score += 15
            reasons.append(f"RSI超賣({rsi:.1f})，可能反彈")
        elif rsi_signal == 'overbought':
            score -= 10
            reasons.append(f"RSI超買({rsi:.1f})，注意回檔")
        elif 40 <= rsi <= 60:
            score += 10
            reasons.append(f"RSI正常({rsi:.1f})")
        
        macd_data = indicators.get('macd', {})
        hist = macd_data.get('hist', 0)
        trend = macd_data.get('trend', 'neutral')
        
        if trend == 'bullish' and hist > 0:
            score += 15
            reasons.append(f"MACD多頭訊號")
        elif trend == 'bearish' and hist < 0:
            score -= 10
            reasons.append(f"MACD空頭訊號")
        
        kd_data = indicators.get('kd', {})
        k = kd_data.get('k', 50)
        kd_signal = kd_data.get('signal', 'neutral')
        
        if kd_signal == 'oversold':
            score += 10
            reasons.append(f"KD超賣(K={k:.1f})")
        elif kd_signal == 'overbought':
            score -= 5
            reasons.append(f"KD超買(K={k:.1f})")
        
        bb_data = indicators.get('bollinger', {})
        bb_signal = bb_data.get('signal', 'neutral')
        bb_position = bb_data.get('position', 50)
        
        if bb_signal == 'oversold':
            score += 10
            reasons.append(f"布林下軌支撐(位置{bb_position:.1f}%)")
        elif bb_signal == 'overbought':
            score -= 5
            reasons.append(f"布林上軌壓力(位置{bb_position:.1f}%)")
        
        return score, reasons
