# -*- coding: utf-8 -*-
"""
配置檔案
設定分析參數與條件
"""

# 分析設定
CONFIG = {
    # 評分權重（對應 tech/inst/pv/sr 四個分項）
    'weights': {
        'technical': 0.30,     # 技術面權重
        'institutional': 0.30, # 籌碼面權重
        'price_volume': 0.25,  # 價量權重
        'support_resistance': 0.15, # 支撐壓力權重
    },
    
    # 技術指標參數
    'technical': {
        'rsi_oversold': 30,     # RSI超賣區
        'rsi_overbought': 70,   # RSI超買區
        'rsi_period': 14,       # RSI週期
        
        'macd_fast': 12,        # MACD快線
        'macd_slow': 26,        # MACD慢線
        'macd_signal': 9,       # MACD訊號線
        
        'kd_period': 9,         # KD週期
        'k_smooth': 3,          # K值平滑
        'd_smooth': 3,          # D值平滑
        
        'ma_periods': [5, 10, 20, 60],  # 均線週期
        
        'bollinger_period': 20, # 布林通道週期
        'bollinger_std': 2,     # 布林通道標準差倍數
    },
    
    # 價量異常條件
    'alerts': {
        'volume_surge': 2.0,    # 成交量放大倍數
        'price_surge': 5.0,     # 價格暴漲%
        'price_drop': -5.0,     # 價格暴跌%
        'limit_up': 9.5,        # 漲停門檻%
        'limit_down': -9.5,     # 跌停門檻%
    },
    
    # 外資追蹤條件
    'institutional': {
        'foreign_buy_days': 3,    # 外資連續買超天數
        'foreign_buy_amount': 1000,  # 外資買超張數門檻
        'total_buy_amount': 5000,    # 三大法人合計買超門檻
    },
    
    # 支撐壓力設定
    'support_resistance': {
        'lookback_days': 60,    # 回顧天數
        'touch_count': 2,       # 觸碰次數
        'tolerance': 0.02,      # 容許誤差%
    },
    
    # 評分門檻（調降至25/15/8，配合盤前模式與市場情況）
    'score_threshold': {
        'strong_buy': 25,       # 強力買進
        'buy': 15,              # 買進
        'hold': 8,              # 觀望
        'sell': 0,              # 賣出
    },
    
    # 輸出設定
    'output': {
        'top_n': 20,            # 顯示前N名
        'save_history': True,   # 是否存檔
        'history_folder': 'history',  # 歷史資料夾
    },
    
    # 股票清單更新設定
    'stock_list': {
        'update_once_per_day': True,  # 每天只更新一次
        'last_update_file': 'last_update.txt',  # 記錄上次更新日期
    },
    
    # 篩選條件
    'filters': {
        'min_price': 10.0,       # 最低股價
        'max_price': 10000.0,    # 最高股價
        'min_volume': 100,       # 最低成交量(張)
    },
    
    # 隨機模式
    'random': {
        'default_count': 50,    # 隨機模式預設數量
        'enabled': True,        # 啟用隨機模式
    },
    
    # 黑名單/白名單篩選
    'list_filter': {
        'whitelist': [],        # 白名單：只分析這些股票（空=全部）
        'blacklist': [],        # 黑名單：排除這些股票
        'enable_whitelist': False,  # 啟用白名單
        'enable_blacklist': False,  # 啟用黑名單
    },
    
    # 平行處理設定
    'parallel': {
        'enabled': True,        # 啟用多執行緒
        'max_workers': 5,       # 最大執行緒數
    },

    # 交易下單設定
    'trading': {
        'mode': 'simulate',                   # 'simulate' 模擬 / 'live' 實盤
        'account_id': '',                     # 永豐帳號（請填入）
        'api_key': '',                        # 永豐 API Key（請填入）
        'api_secret': '',                     # 永豐 API Secret（請填入）
        'person_id': '',                       # 身份證字號（請填入）
        'ca_path': '',                         # CA 憑證路徑（請填入）
        'ca_password': '',                     # CA 憑證密碼（請填入）
        'simulate_initial_cash': 1000000,     # 模擬帳戶初始資金
        'commission_rate': 0.00142,           # 手續費率 0.142%
        'min_commission': 20,                  # 最低手續費
        'tax_rate': 0.003,                    # 證交稅 0.3%（賣出）
        'default_order_quantity': 1000,        # 預設每筆股數（需為1000的倍數）
        'order_storage_path': 'trading/orders',  # 委託單儲存路徑
        'position_storage_path': 'trading/positions.json',  # 部位儲存路徑
        'balance_storage_path': 'trading/balance.json',  # 餘額儲存路徑
    },
}
