# TaiwanStockPicker

台股選股與監控工具（Streamlit 版），整合即時股價、歷史資料、技術指標、法人資訊、回測與分享功能。

## 主要功能

- 多頁面介面
  - `分析總覽`：分析結果、熱門榜、自選追蹤、AI 解讀卡、CSV 匯出
  - `技術圖表`：KD + 歷史股價折線、多時間框架（日/週）、多股比較
  - `警報中心`：異常雷達 + 自訂警報條件
  - `產業熱度`：產業熱力圖與統計
  - `回測與模擬`：簡易策略回測、Paper Portfolio 模擬倉位
  - `每日排行`：高分榜/漲幅榜/量能榜/反轉觀察
  - `分享卡片`：SVG 卡片預覽、下載、X/Facebook/LINE 一鍵分享

- 分析引擎
  - 技術面：RSI / MACD / KD / MA / 布林等
  - 法人面：三大法人資料（批次快取）
  - 基本面：PE / PB / 殖利率評分（可擴充營收、EPS、ROE）
  - 價量面：漲跌、量能、異常波動
  - 支撐壓力：關鍵價位與位置評分

- 進階決策功能
  - 事件行事曆：法說會/除權息/財報/月營收事件辨識與前後提醒
  - 風險控管引擎：ATR 停損、單筆風險、建議倉位
  - 交易日誌：本地 JSON 紀錄與訊號成效統計
  - 策略工坊：條件組合與參數掃描（Grid Search）
  - 多市場篩選：上市 / 上櫃 / ETF
  - 資料品質監控：資料來源與缺值異常統計

## 環境需求

- Python 3.10+（建議 3.11~3.14）
- Windows / macOS / Linux

## 安裝

```bash
pip install -r requirements.txt
```

## 啟動

```bash
streamlit run app.py
```

若你有既有啟動腳本（例如 `啟動.bat`），可直接使用。

## 快速驗證

```bash
python smoke_test.py
```

若看到 `SMOKE TEST PASSED` 代表核心模組可正常載入。

## 常用操作流程

1. 先到側欄按 `更新股票清單`
2. 設定選股模式與過濾條件（價格、權重、執行緒數）
3. 按 `開始分析`
4. 在各功能頁查看：
   - 分析總覽看候選股與理由
   - 技術圖表看 KD 與多時間框架
   - 警報中心看即時異常與自訂警報命中
   - 分享卡片輸出給社群

## 疑難排解

- 漲跌% 異常接近 0
  - 系統已做 `prev_close` 回退與數字清洗（逗號/字串轉換）
  - 若仍偶發，通常是來源 API 當下回傳異常或延遲，稍後重試即可

- 分享卡片預覽錯誤（PIL.UnidentifiedImageError）
  - 已改為 SVG HTML 預覽，不再走 PIL 圖片解析

- Streamlit 出現 `missing ScriptRunContext` 警告
  - 在執行 `smoke_test.py` 時屬正常，可忽略

## 專案結構（重點）

- `app.py`：Streamlit 主介面與多頁功能
- `data_fetcher.py`：即時/歷史/法人資料抓取與快取
- `technical_indicators.py`：技術指標計算
- `institutional_tracker.py`：法人分數
- `price_volume_alert.py`：價量警示
- `support_resistance.py`：支撐壓力分析
- `stock_list.py`：股票清單與分類
- `smoke_test.py`：最小健康檢查

## 免責聲明

本工具僅供研究與教學用途，不構成任何投資建議。請自行評估風險並做好資金控管。
