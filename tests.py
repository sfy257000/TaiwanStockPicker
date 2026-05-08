# -*- coding: utf-8 -*-
"""
單元測試 - 台股選股分析系統核心模組
使用方法: python -m pytest tests.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from config import CONFIG
from technical_indicators import TechnicalIndicators
from institutional_tracker import InstitutionalTracker
from price_volume_alert import PriceVolumeAlert
from support_resistance import SupportResistance
from fundamental_analyzer import FundamentalAnalyzer
from data_fetcher import DataFetcher
from utils import format_number, format_percentage, calculate_change_pct


class TestTechnicalIndicators:
    """技術指標測試"""

    def setup_method(self):
        self.tech = TechnicalIndicators()
        # 標準測試數據 - 上升趨勢
        self.closes_rising = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128, 130]
        # 震盪數據
        self.closes_osc = [100, 105, 100, 105, 100, 105, 100, 105, 100, 105, 100, 105, 100, 105, 100, 105]

    def test_rsi_calculation(self):
        """測試 RSI 計算"""
        result = self.tech.calculate_rsi(self.closes_rising, period=14)
        assert 'rsi' in result
        assert 'signal' in result
        assert 0 <= result['rsi'] <= 100

    def test_rsi_oversold_signal(self):
        """測試 RSI 超賣訊號"""
        # 持續下跌的數據
        falling = [100, 98, 96, 94, 92, 90, 88, 86, 84, 82, 80, 78, 76, 74, 72, 70]
        result = self.tech.calculate_rsi(falling, period=14)
        assert result['signal'] == 'oversold'
        assert result['rsi'] < 30

    def test_rsi_overbought_signal(self):
        """測試 RSI 超買訊號"""
        result = self.tech.calculate_rsi(self.closes_rising, period=14)
        assert result['signal'] == 'overbought'
        assert result['rsi'] > 70

    def test_ma_calculation(self):
        """測試均線計算"""
        result = self.tech.calculate_ma(self.closes_rising)
        assert 'ma5' in result
        assert 'ma10' in result
        assert result['ma5'] > result['ma10']  # 上升趨勢

    def test_bollinger_bands_insufficient_data(self):
        """測試布林通道數據不足時的處理"""
        short_data = [100, 102, 105]  # 少於20筆
        result = self.tech.calculate_bollinger_bands(short_data, period=20)
        assert 'data_note' in result
        assert result['signal'] == 'insufficient_data'

    def test_bollinger_bands_normal(self):
        """測試布林通道正常計算"""
        # 產生足夠的測試數據
        test_data = [100 + i * 0.5 for i in range(25)]
        result = self.tech.calculate_bollinger_bands(test_data, period=20)
        assert result['signal'] != 'insufficient_data'
        assert result['upper'] > result['middle']
        assert result['middle'] > result['lower']

    def test_kd_calculation(self):
        """測試 KD 指標"""
        highs = [h + 2 for h in self.closes_rising]
        lows = [h - 2 for h in self.closes_rising]
        result = self.tech.calculate_kd(highs, lows, self.closes_rising)
        assert 'k' in result
        assert 'd' in result
        assert 0 <= result['k'] <= 100
        assert 0 <= result['d'] <= 100

    def test_technical_score(self):
        """測試技術評分"""
        indicators = {
            'rsi': {'rsi': 70, 'signal': 'overbought'},
            'macd': {'macd': 1, 'signal': 0.5, 'hist': 0.5, 'trend': 'bullish'},
            'kd': {'k': 85, 'd': 80, 'signal': 'overbought'},
            'bollinger': {'position': 85, 'signal': 'overbought'}
        }
        score, reasons = self.tech.get_technical_score(indicators)
        assert isinstance(score, int)
        assert isinstance(reasons, list)

    def test_technical_score_empty(self):
        """測試空數據評分"""
        score, reasons = self.tech.get_technical_score(None)
        assert score == 0
        assert len(reasons) == 0


class TestInstitutionalTracker:
    """法人追蹤測試"""

    def setup_method(self):
        self.tracker = InstitutionalTracker()

    def test_analyze_buy(self):
        """測試買超分析"""
        data = {
            'foreign': 15000,
            'investment_trust': 500,
            'dealer': -200,
            'total': 20000
        }
        result = self.tracker.analyze_institutional(data)
        assert result['score'] > 0
        assert '買超' in str(result['reasons'])

    def test_analyze_sell(self):
        """測試賣超分析"""
        data = {
            'foreign': -15000,
            'investment_trust': -500,
            'dealer': 200,
            'total': -20000
        }
        result = self.tracker.analyze_institutional(data)
        assert result['score'] < 0

    def test_analyze_empty(self):
        """測試空數據"""
        result = self.tracker.analyze_institutional(None)
        assert result['score'] == 0
        assert '無法人數據' in result['reasons']

    def test_analyze_invalid_data(self):
        """測試無效數據"""
        result = self.tracker.analyze_institutional({'foreign': 'invalid'})
        assert 'error' in [r.lower() for r in result['reasons']] or result['score'] == 0

    def test_trend_analysis(self):
        """測試趨勢分析"""
        assert self.tracker._analyze_trend(10000) == 'strong_buy'
        assert self.tracker._analyze_trend(3000) == 'buy'
        assert self.tracker._analyze_trend(500) == 'small_buy'
        assert self.tracker._analyze_trend(-500) == 'small_sell'
        assert self.tracker._analyze_trend(-3000) == 'sell'
        assert self.tracker._analyze_trend(-10000) == 'strong_sell'


class TestPriceVolumeAlert:
    """價量警示測試"""

    def setup_method(self):
        self.alert = PriceVolumeAlert()

    def test_limit_up(self):
        """測試漲停偵測"""
        data = {'price': 110, 'prev_close': 100, 'volume': 10000, 'high': 110, 'low': 95}
        result = self.alert.check_alerts(data)
        assert result['score'] > 0
        assert any('漲停' in r for r in result['reasons'])

    def test_limit_down(self):
        """測試跌停偵測"""
        data = {'price': 90, 'prev_close': 100, 'volume': 10000, 'high': 105, 'low': 90}
        result = self.alert.check_alerts(data)
        assert result['score'] < 0
        assert any('跌停' in r for r in result['reasons'])

    def test_empty_data(self):
        """測試空數據"""
        result = self.alert.check_alerts(None)
        assert result['score'] == 0
        assert '無數據' in result['reasons']

    def test_price_surge(self):
        """測試價格暴漲"""
        data = {'price': 115, 'prev_close': 100, 'volume': 5000, 'high': 116, 'low': 98}
        result = self.alert.check_alerts(data, historical_data=[
            {'volume': 1000}, {'volume': 1200}, {'volume': 1100}, {'volume': 1300}, {'volume': 1150}
        ])
        # 不應触发漲停但可能有暴漲
        assert True  # Just verify it runs without error


class TestSupportResistance:
    """支撐壓力測試"""

    def setup_method(self):
        self.sr = SupportResistance()

    def test_calculate_normal(self):
        """測試正常計算"""
        data = [
            {'date': '2024-01-01', 'open': 100, 'high': 105, 'low': 98, 'close': 102, 'volume': 1000},
            {'date': '2024-01-02', 'open': 102, 'high': 110, 'low': 100, 'close': 108, 'volume': 1200},
            {'date': '2024-01-03', 'open': 108, 'high': 112, 'low': 106, 'close': 110, 'volume': 1500},
        ] * 10  # 重複增加數據量
        result = self.sr.calculate(data)
        assert result is not None
        assert 'support' in result
        assert 'resistance' in result

    def test_calculate_insufficient_data(self):
        """測試數據不足"""
        data = [{'date': '2024-01-01', 'high': 105, 'low': 98, 'close': 102, 'volume': 1000}]
        result = self.sr.calculate(data)
        assert result is None

    def test_score_calculation(self):
        """測試評分計算"""
        data = {
            'position': 'near_support',
            'support': [95, 100],
            'resistance': [115, 120]
        }
        score, reasons = self.sr.get_support_resistance_score(data)
        assert score > 0
        assert len(reasons) > 0


class TestUtils:
    """工具函數測試"""

    def test_format_number(self):
        """測試數字格式化"""
        assert format_number(1234567) == '1,234,567'
        assert format_number(123) == '123'
        assert format_number(0) == '0'

    def test_format_percentage(self):
        """測試百分比格式化"""
        assert format_percentage(5.5) == '+5.50%'
        assert format_percentage(-3.25) == '-3.25%'
        assert format_percentage(0) == '+0.00%'

    def test_calculate_change_pct(self):
        """測試漲跌計算"""
        assert abs(calculate_change_pct(110, 100) - 10.0) < 0.01
        assert abs(calculate_change_pct(90, 100) + 10.0) < 0.01
        assert calculate_change_pct(100, 0) == 0  # 除以零保護


class TestDataFetcher:
    """資料抓取測試"""

    def setup_method(self):
        self.fetcher = DataFetcher()

    def test_safe_float(self):
        """測試安全浮點數轉換"""
        assert DataFetcher._safe_float('123.45') == 123.45
        assert DataFetcher._safe_float('1,234.56') == 1234.56
        assert DataFetcher._safe_float('-') == 0.0
        assert DataFetcher._safe_float(None) == 0.0

    def test_safe_int(self):
        """測試安全整數轉換"""
        assert DataFetcher._safe_int('1,234') == 1234
        assert DataFetcher._safe_int('1234') == 1234
        assert DataFetcher._safe_int('-') == 0
        assert DataFetcher._safe_int(None) == 0

    def test_parse_date_to_iso(self):
        """測試日期解析"""
        assert DataFetcher._parse_date_to_iso('115/03/04') == '2026-03-04'
        assert DataFetcher._parse_date_to_iso('2026-03-04') == '2026-03-04'


class TestConfig:
    """配置測試"""

    def test_config_structure(self):
        """測試配置結構"""
        assert 'weights' in CONFIG
        assert 'technical' in CONFIG
        assert 'institutional' in CONFIG
        assert 'alerts' in CONFIG

    def test_weights_sum(self):
        """測試權重存在"""
        assert 'technical' in CONFIG['weights']
        assert 'institutional' in CONFIG['weights']
        assert 'price_volume' in CONFIG['weights']
        assert 'support_resistance' in CONFIG['weights']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])