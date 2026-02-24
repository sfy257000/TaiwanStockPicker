# -*- coding: utf-8 -*-
"""
工具函數
共用的函數與工具
"""

import sys
import os
from datetime import datetime

def setup_encoding():
    """設定輸出編碼"""
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def create_folder(folder_path):
    """建立資料夾"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def format_number(num):
    """格式化數字（加上千分位）"""
    return f"{num:,}"

def format_percentage(num):
    """格式化百分比"""
    return f"{num:+.2f}%"

def format_price(price):
    """格式化價格"""
    return f"{price:.1f}"

def get_timestamp():
    """取得時間戳記"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_date():
    """取得日期"""
    return datetime.now().strftime('%Y-%m-%d')

def get_date_folder():
    """取得日期資料夾名稱"""
    return datetime.now().strftime('%Y%m%d')

def print_separator(char='=', length=70):
    """印出分隔線"""
    print(char * length)

def print_header(title):
    """印出標題"""
    print_separator()
    print(title)
    print_separator()
    print()

def print_subheader(title):
    """印出子標題"""
    print()
    print_separator(char='-', length=70)
    print(title)
    print_separator(char='-', length=70)

def safe_divide(numerator, denominator):
    """安全除法"""
    if denominator == 0:
        return 0
    return numerator / denominator

def clamp(value, min_val, max_val):
    """限制數值範圍"""
    return max(min_val, min(max_val, value))

def classify_score(score):
    """分類評分（與config.py score_threshold一致）"""
    if score >= 25:
        return '強力買進'
    elif score >= 15:
        return '買進'
    elif score >= 8:
        return '觀望'
    else:
        return '不建議'

def get_score_emoji(score):
    """取得評分表情符號（與config.py score_threshold一致）"""
    if score >= 25:
        return '🔥'
    elif score >= 15:
        return '✓'
    elif score >= 8:
        return '○'
    else:
        return '×'

def calculate_change_pct(current, previous):
    """計算漲跌幅"""
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def check_limit_up(change_pct, threshold=9.5):
    """檢查是否漲停"""
    return change_pct >= threshold

def check_limit_down(change_pct, threshold=-9.5):
    """檢查是否跌停"""
    return change_pct <= threshold

def check_volume_surge(current_vol, avg_vol, ratio=2.0):
    """檢查是否爆量"""
    if avg_vol == 0:
        return False
    return current_vol >= avg_vol * ratio

def check_price_surge(change_pct, threshold=5.0):
    """檢查是否暴漲"""
    return change_pct >= threshold

def check_price_drop(change_pct, threshold=-5.0):
    """檢查是否暴跌"""
    return change_pct <= threshold
