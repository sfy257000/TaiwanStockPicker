# -*- coding: utf-8 -*-
"""
簡單的 Shioaji 登入測試
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 讀取 config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CONFIG

trading = CONFIG['trading']
api_key = trading.get('api_key', '')
api_secret = trading.get('api_secret', '')
account_id = trading.get('account_id', '')

print(f"API Key: {api_key[:15]}..." if api_key else "API Key: [空的]")
print(f"API Secret: {api_secret[:15]}..." if api_secret else "API Secret: [空的]")
print(f"Account ID: {account_id}")
print()

import shioaji as sj

# 方法 1: 模擬模式測試
print("=" * 50)
print("測試 1: 模擬模式登入")
print("=" * 50)
try:
    api = sj.Shioaji(simulation=True)
    result = api.login(api_key=api_key, secret_key=api_secret)
    print(f"[OK] 模擬模式登入成功！")
    print(f"帳號列表: {api.list_accounts()}")
    api.logout()
except Exception as e:
    print(f"[FAIL] 模擬模式登入失敗: {e}")

# 方法 2: 實盤模式測試（增加 receive_window）
print()
print("=" * 50)
print("測試 2: 實盤模式登入")
print("=" * 50)
try:
    api2 = sj.Shioaji(
        simulation=False,
        receive_window=60000,
        fetch_contract=False,
    )
    result = api2.login(
        api_key=api_key,
        secret_key=api_secret,
        receive_window=60000,
    )
    print(f"[OK] 實盤模式登入成功！")
    print(f"帳號列表: {api2.list_accounts()}")

    # 測試啟用 CA
    ca_path = trading.get('ca_path', '')
    ca_password = trading.get('ca_password', '')
    if ca_path and ca_password:
        print(f"\n嘗試啟用 CA...")
        api2.activate_ca(ca_path=ca_path, ca_passwd=ca_password)
        print(f"[OK] CA 啟用成功！")
    else:
        print(f"\n[注意] 未設定 CA 路徑和密碼")

    api2.logout()
except Exception as e:
    print(f"[FAIL] 實盤模式登入失敗: {e}")

# 方法 3: 實盤模式（不設定 fetch_contract）
print()
print("=" * 50)
print("測試 3: 實盤模式（fetch_contract=True）")
print("=" * 50)
try:
    api3 = sj.Shioaji(simulation=False)
    result = api3.login(api_key=api_key, secret_key=api_secret)
    print(f"[OK] 登入成功！")
    print(f"帳號列表: {api3.list_accounts()}")
    api3.logout()
except Exception as e:
    print(f"[FAIL] 登入失敗: {e}")

print()
print("=" * 50)
print("測試完成")
print("=" * 50)