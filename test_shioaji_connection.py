# -*- coding: utf-8 -*-
"""
Shioaji 連線測試腳本
用於診斷永豐 API 登入問題
"""

import os
import sys
import io

# 設定標準輸出編碼為 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_shioaji():
    """測試 Shioaji 基本功能"""
    print("=" * 50)
    print("Shioaji 連線測試")
    print("=" * 50)

    # 1. 測試 shioaji 是否已安裝
    print("\n[1] 檢查 shioaji 安裝狀態...")
    try:
        import shioaji as sj
        print(f"    shioaji 版本: {sj.__version__}")
        print("    ✓ shioaji 已安裝")
    except ImportError:
        print("    ✗ shioaji 未安裝，請執行: pip install shioaji")
        return False

    # 2. 測試網路連線
    print("\n[2] 測試網路連線...")
    import socket
    try:
        sock = socket.create_connection(("api.sinotrade.com.tw", 80), timeout=5)
        sock.close()
        print("    ✓ 可以連線到永豐伺服器")
    except OSError as e:
        print(f"    ✗ 無法連線: {e}")
        print("    請檢查網路或防火牆設定")
        return False

    # 3. 檢查環境變數或 config
    print("\n[3] 檢查 API 憑證...")

    # 嘗試從環境變數讀取
    api_key = os.environ.get("API_KEY", "")
    api_secret = os.environ.get("SECRET_KEY", "")

    # 如果環境變數為空，嘗試從 config 讀取
    if not api_key or not api_secret:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from config import CONFIG
            api_key = CONFIG['trading'].get('api_key', '')
            api_secret = CONFIG['trading'].get('api_secret', '')
        except Exception as e:
            print(f"    無法讀取 config: {e}")

    if not api_key or not api_secret:
        print("    ✗ 找不到 API 憑證")
        print("    請設定環境變數或填寫 config.py:")
        print("    - API_KEY")
        print("    - SECRET_KEY")
        print("\n    或在 config.py 的 trading 區塊填入 api_key 和 api_secret")
        return False

    print(f"    API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"    API Secret: {api_secret[:6]}...")
    print("    ✓ 找到 API 憑證")

    # 4. 測試登入（模擬模式）
    print("\n[4] 測試登入（模擬模式）...")
    try:
        api = sj.Shioaji(simulation=True)
        accounts = api.login(
            api_key=api_key,
            secret_key=api_secret,
            receive_window=60000,
        )
        print(f"    [OK] 登入成功！")
        print(f"    可用帳號: {accounts}")

        # 列出所有帳號
        print("\n    可用帳號列表:")
        for i, acc in enumerate(api.list_accounts()):
            print(f"      [{i+1}] {acc}")

        api.logout()
        print("\n    [OK] 模擬模式登入測試通過！")

    except Exception as e:
        print(f"    [FAIL] 登入失敗: {e}")
        print("\n    可能原因:")
        print("    1. API Key/Secret 已過期或無效")
        print("    2. 網頁交易密碼已過期")
        print("    3. 電腦時間不同步")
        print("\n    解決方案:")
        print("    - 請聯繫永豐營業員重新申請 API 憑證")
        print("    - 或登入券商系統確認憑證狀態")
        return False

    # 5. 測試實盤登入（可選）
    print("\n[5] 測試實盤登入（需要有效憑證）...")
    try:
        api_live = sj.Shioaji(simulation=False)
        accounts = api_live.login(
            api_key=api_key,
            secret_key=api_secret,
        )
        print(f"    ✓ 實盤登入成功！")
        print("    → 可以將 config.py 的 mode 改為 'live' 使用實盤交易")

        print("\n    可用帳號列表:")
        for i, acc in enumerate(api_live.list_accounts()):
            print(f"      [{i+1}] {acc}")

        api_live.logout()

    except Exception as e:
        print(f"    ✗ 實盤登入失敗: {e}")
        print("\n    實盤需要有效的 API 憑證")
        print("    目前使用模擬模式已經可以正常運作")

    print("\n" + "=" * 50)
    print("測試完成")
    print("=" * 50)
    return True


if __name__ == '__main__':
    test_shioaji()