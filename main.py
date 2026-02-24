# -*- coding: utf-8 -*-
"""
台股選股分析系統 - 主程式
整合所有模組進行完整分析
"""

import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG
from stock_list import (
    STOCK_LIST, get_all_stocks, get_stock_count,
    check_and_update_stock_list, interactive_stock_selection
)
from data_fetcher import DataFetcher
from technical_indicators import TechnicalIndicators
from institutional_tracker import InstitutionalTracker
from price_volume_alert import PriceVolumeAlert
from support_resistance import SupportResistance
from history_saver import HistorySaver
from utils import *


class StockAnalyzer:
    def __init__(self):
        setup_encoding()
        
        self.fetcher = DataFetcher()
        self.tech_indicators = TechnicalIndicators()
        self.inst_tracker = InstitutionalTracker()
        self.pv_alert = PriceVolumeAlert()
        self.sr_calculator = SupportResistance()
        self.history_saver = HistorySaver()
        
        self.results = []
    
    def analyze_stock(self, code, name):
        """分析單一股票"""
        print(f"分析 {code} {name}...", end=' ')
        
        price_data = self.fetcher.get_stock_price(code)
        
        if not price_data or price_data['price'] == 0:
            print("× 無數據")
            return None
        
        institutional_data = self.fetcher.get_institutional_investors(code)
        
        historical_data = self.fetcher.get_historical_price(code, days=60)
        
        tech_indicators = None
        tech_score = 0
        tech_reasons = []
        
        if historical_data:
            tech_indicators = self.tech_indicators.calculate_all(historical_data)
            if tech_indicators:
                tech_score, tech_reasons = self.tech_indicators.get_technical_score(tech_indicators)
        
        inst_result = self.inst_tracker.analyze_institutional(institutional_data)
        inst_score = inst_result['score']
        inst_reasons = inst_result['reasons']
        
        pv_result = self.pv_alert.check_alerts(price_data, historical_data)
        pv_score = pv_result['score']
        pv_reasons = pv_result['reasons']
        
        sr_data = None
        sr_score = 0
        sr_reasons = []
        
        if historical_data:
            sr_data = self.sr_calculator.calculate(historical_data)
            if sr_data:
                sr_score, sr_reasons = self.sr_calculator.get_support_resistance_score(sr_data)
        
        weights = CONFIG['weights']
        total_score = (
            tech_score * 0.3 +
            inst_score * 0.3 +
            pv_score * 0.25 +
            sr_score * 0.15
        )
        
        total_score = round(total_score)
        
        all_reasons = tech_reasons + inst_reasons + pv_reasons + sr_reasons
        
        if price_data['prev_close'] > 0:
            change_pct = ((price_data['price'] - price_data['prev_close']) / price_data['prev_close']) * 100
        else:
            change_pct = 0
        
        is_premarket = price_data.get('is_premarket', False)
        
        result = {
            'code': code,
            'name': name,
            'price': price_data['price'],
            'change_pct': change_pct,
            'volume': price_data['volume'],
            'high': price_data['high'],
            'low': price_data['low'],
            'is_premarket': is_premarket,
            'tech_score': tech_score,
            'inst_score': inst_score,
            'pv_score': pv_score,
            'sr_score': sr_score,
            'total_score': total_score,
            'reasons': all_reasons,
            'institutional': institutional_data,
            'indicators': tech_indicators,
            'support_resistance': sr_data,
        }
        
        emoji = get_score_emoji(total_score)
        classification = classify_score(total_score)
        pre_tag = " [盤前]" if is_premarket else ""
        print(f"{emoji} {classification} (評分:{total_score}){pre_tag}")
        
        return result
    
    def _analyze_stock_silent(self, code, name):
        """安靜分析股票（不回傳，內部使用）"""
        price_data = self.fetcher.get_stock_price(code)
        
        if not price_data or price_data['price'] == 0:
            return None
        
        institutional_data = self.fetcher.get_institutional_investors(code)
        historical_data = self.fetcher.get_historical_price(code, days=60)
        
        tech_indicators = None
        tech_score = 0
        tech_reasons = []
        
        if historical_data:
            tech_indicators = self.tech_indicators.calculate_all(historical_data)
            if tech_indicators:
                tech_score, tech_reasons = self.tech_indicators.get_technical_score(tech_indicators)
        
        inst_result = self.inst_tracker.analyze_institutional(institutional_data)
        inst_score = inst_result['score']
        inst_reasons = inst_result['reasons']
        
        pv_result = self.pv_alert.check_alerts(price_data, historical_data)
        pv_score = pv_result['score']
        pv_reasons = pv_result['reasons']
        
        sr_data = None
        sr_score = 0
        sr_reasons = []
        
        if historical_data:
            sr_data = self.sr_calculator.calculate(historical_data)
            if sr_data:
                sr_score, sr_reasons = self.sr_calculator.get_support_resistance_score(sr_data)
        
        total_score = (
            tech_score * 0.3 +
            inst_score * 0.3 +
            pv_score * 0.25 +
            sr_score * 0.15
        )
        total_score = round(total_score)
        
        all_reasons = tech_reasons + inst_reasons + pv_reasons + sr_reasons
        
        if price_data['prev_close'] > 0:
            change_pct = ((price_data['price'] - price_data['prev_close']) / price_data['prev_close']) * 100
        else:
            change_pct = 0
        
        is_premarket = price_data.get('is_premarket', False)
        
        result = {
            'code': code,
            'name': name,
            'price': price_data['price'],
            'change_pct': change_pct,
            'volume': price_data['volume'],
            'high': price_data['high'],
            'low': price_data['low'],
            'tech_score': tech_score,
            'inst_score': inst_score,
            'pv_score': pv_score,
            'sr_score': sr_score,
            'total_score': total_score,
            'reasons': all_reasons,
            'institutional': institutional_data,
            'indicators': tech_indicators,
            'support_resistance': sr_data,
            'is_premarket': is_premarket,
        }
        
        return result
    
    def _run_sequential(self, stocks):
        """順序執行分析"""
        results = []
        total_stocks = len(stocks)
        processed = 0
        
        for code, name in stocks:
            result = self._analyze_stock_silent(code, name)
            if result:
                results.append(result)
            
            processed += 1
            self._print_progress(processed, total_stocks)
        
        print()
        return results
    
    def _run_parallel(self, stocks, max_workers=5):
        """平行執行分析"""
        results = []
        total_stocks = len(stocks)
        processed = 0
        lock = __import__('threading').Lock()
        
        def analyze_with_progress(code, name):
            nonlocal processed
            result = self._analyze_stock_silent(code, name)
            with lock:
                processed += 1
                if result:
                    results.append(result)
                self._print_progress(processed, total_stocks)
            return result
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(analyze_with_progress, code, name) 
                      for code, name in stocks]
            for future in as_completed(futures):
                try:
                    future.result()
                except:
                    pass
        
        print()
        return results
    
    def _print_progress(self, processed, total):
        """顯示進度"""
        elapsed = 0
        avg_time = 0
        remaining = 0
        percent = int(processed * 100 / total)
        bar_len = 20
        filled = int(bar_len * processed / total)
        bar = '█' * filled + '░' * (bar_len - filled)
        
        if remaining < 60:
            eta = f"{int(remaining)}秒"
        elif remaining < 3600:
            eta = f"{int(remaining/60)}分"
        else:
            eta = f"{int(remaining/3600)}時{int((remaining%3600)/60)}分"
        
        print(f"\r[{bar}] {percent}% ({processed}/{total}) | 預估剩餘: {eta}", end='', flush=True)
    
    def run(self, stock_count=None, mode='all', categories='', extra_stocks='', random_count=50):
        """執行完整分析"""
        print_header("台股選股分析系統 - 完整版")
        
        print(f"分析時間: {get_timestamp()}")
        
        # 檢查並更新股票清單（每天一次）
        check_and_update_stock_list()
        
        # 根據模式選擇股票
        stocks = interactive_stock_selection(
            mode=mode,
            categories=categories,
            extra_stocks=extra_stocks,
            random_count=random_count
        )
        
        # 如果有指定數量限制
        if stock_count and stock_count < len(stocks):
            stocks = stocks[:stock_count]
        
        total_stocks = len(stocks)
        print(f"\n分析股票數: {total_stocks} 檔")
        
        parallel_config = CONFIG.get('parallel', {})
        use_parallel = parallel_config.get('enabled', True)
        max_workers = parallel_config.get('max_workers', 5)
        
        start_time = time.time()
        
        print("\n正在分析股票，請稍候...")
        print("-" * 50)
        
        if use_parallel and total_stocks > 1:
            self.results = self._run_parallel(stocks, max_workers)
        else:
            self.results = self._run_sequential(stocks)
        
        success_count = len(self.results)
        print("-" * 50)
        
        total_elapsed = time.time() - start_time
        if total_elapsed < 60:
            total_str = f"{int(total_elapsed)}秒"
        elif total_elapsed < 3600:
            total_str = f"{int(total_elapsed/60)}分"
        else:
            total_str = f"{int(total_elapsed/3600)}時{int((total_elapsed%3600)/60)}分"
        
        print(f"✓ 分析完成！共分析 {success_count} 檔，總耗时: {total_str}")
        print()
        
        self._print_summary()
        
        self._print_recommendations()
        
        self._print_limit_monitor()
        
        self._print_technical_analysis()
        
        self._print_institutional_tracking()
        
        self._print_support_resistance()
        
        self._save_results()
        
        self._print_usage()
    
    def _print_summary(self):
        """印出總覽"""
        print_subheader("股價總覽")
        
        self.results.sort(key=lambda x: x['change_pct'], reverse=True)
        
        print(f"{'代碼':<8} {'名稱':<10} {'現價':<10} {'漲跌%':<10} {'成交量':<15} {'評分':<8}")
        print("-" * 70)
        
        for r in self.results[:30]:
            change_str = format_percentage(r['change_pct'])
            vol_str = format_number(r['volume'])
            print(f"{r['code']:<8} {r['name']:<10} {r['price']:<10.1f} {change_str:<10} {vol_str:>12}張   {r['total_score']:<8}")
    
    def _print_recommendations(self):
        """印出推薦清單"""
        print_subheader(f"推薦買進清單 TOP {CONFIG['output']['top_n']}")
        
        self.results.sort(key=lambda x: x['total_score'], reverse=True)
        
        buy_threshold = CONFIG['score_threshold']['buy']
        recommended = [r for r in self.results if r['total_score'] >= buy_threshold]
        
        if not recommended:
            print("目前沒有高分推薦股票")
            return
        
        for i, r in enumerate(recommended[:CONFIG['output']['top_n']], 1):
            emoji = get_score_emoji(r['total_score'])
            print(f"\n【{i}. {emoji} {r['code']} {r['name']}】評分: {r['total_score']} 分")
            print(f"  現價: {r['price']:.1f} 元 | 漲跌: {format_percentage(r['change_pct'])} | 成交量: {format_number(r['volume'])}張")
            print(f"  最高: {r['high']:.1f} | 最低: {r['low']:.1f}")
            print(f"  技術:{r['tech_score']} | 籌碼:{r['inst_score']} | 價量:{r['pv_score']} | 支撐:{r['sr_score']}")
            print(f"  理由:")
            for reason in r['reasons'][:5]:
                print(f"    • {reason}")
            
            if r['institutional']:
                inst = r['institutional']
                print(f"  三大法人:")
                print(f"    外資:{inst['foreign']:+,}張 | 投信:{inst['investment_trust']:+,}張 | 自營:{inst['dealer']:+,}張")
                print(f"    合計:{inst['total']:+,}張")
            
            if r['indicators']:
                ind = r['indicators']
                rsi = ind.get('rsi', {}).get('rsi', 50)
                kd = ind.get('kd', {})
                print(f"  技術指標:")
                print(f"    RSI:{rsi:.1f} | K:{kd.get('k', 50):.1f} D:{kd.get('d', 50):.1f}")
            
            if r['support_resistance']:
                sr = r['support_resistance']
                support = sr.get('support', [])
                resistance = sr.get('resistance', [])
                if support or resistance:
                    print(f"  支撐壓力:")
                    if support:
                        print(f"    支撐: {', '.join([f'{p:.1f}' for p in support[:2]])}")
                    if resistance:
                        print(f"    壓力: {', '.join([f'{p:.1f}' for p in resistance[:2]])}")
    
    def _print_limit_monitor(self):
        """印出漲跌停監控"""
        print_subheader("漲跌停監控")
        
        limit_up = [r for r in self.results if r['change_pct'] >= CONFIG['alerts']['limit_up']]
        near_limit_up = [r for r in self.results if CONFIG['alerts']['limit_up'] - 1 <= r['change_pct'] < CONFIG['alerts']['limit_up']]
        limit_down = [r for r in self.results if r['change_pct'] <= CONFIG['alerts']['limit_down']]
        
        if limit_up:
            print("\n【漲停股】")
            for r in limit_up:
                print(f"  🔥 {r['code']} {r['name']} {r['price']:.1f}元 ({format_percentage(r['change_pct'])})")
        else:
            print("\n【漲停股】無")
        
        if near_limit_up:
            print("\n【接近漲停】")
            for r in near_limit_up:
                print(f"  ⚡ {r['code']} {r['name']} {r['price']:.1f}元 ({format_percentage(r['change_pct'])})")
        
        if limit_down:
            print("\n【跌停股】")
            for r in limit_down:
                print(f"  📉 {r['code']} {r['name']} {r['price']:.1f}元 ({format_percentage(r['change_pct'])})")
        else:
            print("\n【跌停股】無")
    
    def _print_technical_analysis(self):
        """印出技術分析亮點"""
        print_subheader("技術指標亮點")
        
        rsi_oversold = []
        rsi_overbought = []
        kd_golden_cross = []
        macd_bullish = []
        
        for r in self.results:
            if r['indicators']:
                ind = r['indicators']
                
                rsi_data = ind.get('rsi', {})
                if rsi_data.get('signal') == 'oversold':
                    rsi_oversold.append((r['code'], r['name'], rsi_data['rsi']))
                elif rsi_data.get('signal') == 'overbought':
                    rsi_overbought.append((r['code'], r['name'], rsi_data['rsi']))
                
                macd_data = ind.get('macd', {})
                if macd_data.get('trend') == 'bullish':
                    macd_bullish.append((r['code'], r['name']))
        
        if rsi_oversold:
            print("\n【RSI超賣（可能反彈）】")
            for code, name, rsi in rsi_oversold[:10]:
                print(f"  {code} {name} RSI:{rsi:.1f}")
        
        if rsi_overbought:
            print("\n【RSI超買（注意回檔）】")
            for code, name, rsi in rsi_overbought[:10]:
                print(f"  {code} {name} RSI:{rsi:.1f}")
        
        if macd_bullish:
            print("\n【MACD多頭訊號】")
            for code, name in macd_bullish[:10]:
                print(f"  {code} {name}")
    
    def _print_institutional_tracking(self):
        """印出外資追蹤"""
        print_subheader("外資籌碼追蹤")
        
        foreign_buy = []
        foreign_sell = []
        
        for r in self.results:
            if r['institutional']:
                inst = r['institutional']
                foreign = inst.get('foreign', 0)
                
                if foreign > 1000:
                    foreign_buy.append((r['code'], r['name'], foreign))
                elif foreign < -1000:
                    foreign_sell.append((r['code'], r['name'], foreign))
        
        foreign_buy.sort(key=lambda x: x[2], reverse=True)
        foreign_sell.sort(key=lambda x: x[2])
        
        if foreign_buy:
            print("\n【外資大買TOP 10】")
            for code, name, amount in foreign_buy[:10]:
                print(f"  {code} {name} 買超{format_number(amount)}張")
        
        if foreign_sell:
            print("\n【外資大賣TOP 10】")
            for code, name, amount in foreign_sell[:10]:
                print(f"  {code} {name} 賣超{format_number(abs(amount))}張")
    
    def _print_support_resistance(self):
        """印出支撐壓力分析"""
        print_subheader("支撐壓力位分析")
        
        near_support = []
        near_resistance = []
        
        for r in self.results:
            if r['support_resistance']:
                sr = r['support_resistance']
                position = sr.get('position', '')
                
                if position == 'near_support':
                    near_support.append((r['code'], r['name'], r['price'], sr.get('support', [])))
                elif position == 'near_resistance':
                    near_resistance.append((r['code'], r['name'], r['price'], sr.get('resistance', [])))
        
        if near_support:
            print("\n【接近支撐位（有支撐）】")
            for code, name, price, supports in near_support[:10]:
                support_str = ', '.join([f'{p:.1f}' for p in supports[:2]])
                print(f"  {code} {name} 現價{price:.1f} 支撐:{support_str}")
        
        if near_resistance:
            print("\n【接近壓力位（有壓力）】")
            for code, name, price, resistances in near_resistance[:10]:
                res_str = ', '.join([f'{p:.1f}' for p in resistances[:2]])
                print(f"  {code} {name} 現價{price:.1f} 壓力:{res_str}")
    
    def _save_results(self):
        """儲存結果"""
        if CONFIG['output']['save_history']:
            self.history_saver.save_analysis(self.results)
            print(f"\n✓ 分析結果已儲存")
    
    def _print_usage(self):
        """印出使用說明"""
        print_subheader("評分標準")
        print(f"評分 ≥ {CONFIG['score_threshold']['strong_buy']}分：強力買進 🔥")
        print(f"評分 {CONFIG['score_threshold']['buy']}-{CONFIG['score_threshold']['strong_buy']-1}分：買進 ✓")
        print(f"評分 {CONFIG['score_threshold']['hold']}-{CONFIG['score_threshold']['buy']-1}分：觀望 ○")
        print(f"評分 < {CONFIG['score_threshold']['hold']}分：不建議 ×")
        
        print_subheader("投資建議")
        print("1. 優先關注評分≥15分的股票")
        print("2. RSI超賣+外资買超 = 反彈機會")
        print("3. 接近支撐位+大量成交 = 有主力進駐")
        print("4. 漲停股注意追高風險")
        print("5. 跌停股暫時避開")
        print("6. 記得設定停損停利")
        print("7. 此為參考工具，投資需自行判斷風險")
        
        print_separator()


def interactive_parameter_menu():
    """互動式參數調整選單"""
    from config import CONFIG
    import json
    
    while True:
        print("\n" + "="*50)
        print("參數設定")
        print("="*50)
        print("1) 評分門檻 (現為: 強買>={}, 買進>={}, 觀望>={})".format(
            CONFIG['score_threshold']['strong_buy'],
            CONFIG['score_threshold']['buy'],
            CONFIG['score_threshold']['hold']
        ))
        print("2) RSI 參數 (超賣: {}, 超買: {}, 週期: {})".format(
            CONFIG['technical']['rsi_oversold'],
            CONFIG['technical']['rsi_overbought'],
            CONFIG['technical']['rsi_period']
        ))
        print("3) 篩選條件 (最低價: {}, 最低量: {})".format(
            CONFIG['filters']['min_price'],
            CONFIG['filters']['min_volume']
        ))
        print("4) 黑名單管理")
        print("5) 白名單管理")
        print("6) 平行處理 (啟用: {}, 最大執行緒: {})".format(
            CONFIG['parallel']['enabled'],
            CONFIG['parallel']['max_workers']
        ))
        print("0) 返回主選單")
        
        try:
            choice = input("\n請選擇: ").strip()
        except EOFError:
            break
        
        if choice == '0':
            break
        elif choice == '1':
            print("\n--- 評分門檻設定 ---")
            try:
                sb = int(input(f"強烈買進分數 [預設{ CONFIG['score_threshold']['strong_buy']}]: ").strip() or CONFIG['score_threshold']['strong_buy'])
                b = int(input(f"買進分數 [預設{ CONFIG['score_threshold']['buy']}]: ").strip() or CONFIG['score_threshold']['buy'])
                h = int(input(f"觀望分數 [預設{ CONFIG['score_threshold']['hold']}]: ").strip() or CONFIG['score_threshold']['hold'])
                CONFIG['score_threshold']['strong_buy'] = sb
                CONFIG['score_threshold']['buy'] = b
                CONFIG['score_threshold']['hold'] = h
                print("✓ 評分門檻已更新")
            except ValueError:
                print("× 輸入無效")
        elif choice == '2':
            print("\n--- RSI 參數設定 ---")
            try:
                ro = int(input(f"RSI超賣 [預設{ CONFIG['technical']['rsi_oversold']}]: ").strip() or CONFIG['technical']['rsi_oversold'])
                rb = int(input(f"RSI超買 [預設{ CONFIG['technical']['rsi_overbought']}]: ").strip() or CONFIG['technical']['rsi_overbought'])
                rp = int(input(f"RSI週期 [預設{ CONFIG['technical']['rsi_period']}]: ").strip() or CONFIG['technical']['rsi_period'])
                CONFIG['technical']['rsi_oversold'] = ro
                CONFIG['technical']['rsi_overbought'] = rb
                CONFIG['technical']['rsi_period'] = rp
                print("✓ RSI 參數已更新")
            except ValueError:
                print("× 輸入無效")
        elif choice == '3':
            print("\n--- 篩選條件設定 ---")
            try:
                mp = float(input(f"最低股價 [預設{ CONFIG['filters']['min_price']}]: ").strip() or CONFIG['filters']['min_price'])
                mv = int(input(f"最低成交量 [預設{ CONFIG['filters']['min_volume']}]: ").strip() or CONFIG['filters']['min_volume'])
                CONFIG['filters']['min_price'] = mp
                CONFIG['filters']['min_volume'] = mv
                print("✓ 篩選條件已更新")
            except ValueError:
                print("× 輸入無效")
        elif choice == '4':
            print("\n--- 黑名單管理 ---")
            print("目前黑名單: {}".format(', '.join(CONFIG['list_filter']['blacklist']) or '無'))
            print("選項: 1)加入  2)清除  0)返回")
            try:
                sub = input("請選擇: ").strip()
                if sub == '1':
                    codes = input("輸入股票代碼（逗號分隔）: ").strip()
                    if codes:
                        for c in codes.split(','):
                            c = c.strip()
                            if c and c not in CONFIG['list_filter']['blacklist']:
                                CONFIG['list_filter']['blacklist'].append(c)
                        CONFIG['list_filter']['enable_blacklist'] = True
                        print("✓ 已加入黑名單")
                elif sub == '2':
                    CONFIG['list_filter']['blacklist'] = []
                    CONFIG['list_filter']['enable_blacklist'] = False
                    print("✓ 黑名單已清除")
            except EOFError:
                pass
        elif choice == '5':
            print("\n--- 白名單管理 ---")
            print("目前白名單: {}".format(', '.join(CONFIG['list_filter']['whitelist']) or '無'))
            print("選項: 1)加入  2)清除  0)返回")
            try:
                sub = input("請選擇: ").strip()
                if sub == '1':
                    codes = input("輸入股票代碼（逗號分隔）: ").strip()
                    if codes:
                        CONFIG['list_filter']['whitelist'] = []
                        for c in codes.split(','):
                            c = c.strip()
                            if c and c not in CONFIG['list_filter']['whitelist']:
                                CONFIG['list_filter']['whitelist'].append(c)
                        CONFIG['list_filter']['enable_whitelist'] = True
                        print("✓ 已設定白名單")
                elif sub == '2':
                    CONFIG['list_filter']['whitelist'] = []
                    CONFIG['list_filter']['enable_whitelist'] = False
                    print("✓ 白名單已清除")
            except EOFError:
                pass
        elif choice == '6':
            print("\n--- 平行處理設定 ---")
            try:
                enabled = input(f"啟用多執行緒？ (y/N) [預設{'y' if CONFIG['parallel']['enabled'] else 'N'}]: ").strip().lower()
                if enabled == 'y':
                    CONFIG['parallel']['enabled'] = True
                elif enabled == 'n' or not enabled:
                    CONFIG['parallel']['enabled'] = False
                
                mw = int(input(f"最大執行緒數 [預設{ CONFIG['parallel']['max_workers']}]: ").strip() or CONFIG['parallel']['max_workers'])
                CONFIG['parallel']['max_workers'] = mw
                print("✓ 平行處理設定已更新")
            except ValueError:
                print("× 輸入無效")
    
    print("\n返回主選單")


def main():
    """主程式進入點"""
    import argparse
    
    parser = argparse.ArgumentParser(description='台股選股分析系統')
    parser.add_argument('-n', '--number', type=int, default=None,
                        help='分析股票數量')
    parser.add_argument('-m', '--mode', type=str, default=None,
                        choices=['all', 'random', 'category'],
                        help='選擇模式: all=全部, random=隨機50檔, category=依類型')
    parser.add_argument('-c', '--categories', type=str, default='',
                        help='類型代碼(逗號分隔): 1=半導體, 2=電子, 3=金融, 4=傳產, 5=ETF')
    parser.add_argument('-s', '--stocks', type=str, default='',
                        help='額外指定的股票代碼(逗號分隔)')
    parser.add_argument('-r', '--random-count', type=int, default=50,
                        help='隨機模式數量(預設50)')
    
    args = parser.parse_args()
    
    # 如果沒有提供任何參數，顯示互動式選單
    if args.mode is None:
        while True:
            print("\n" + "="*50)
            print("台股選股分析系統")
            print("="*50)
            print("1) 分析全部股票")
            print("2) 依類型選擇")
            print("3) 隨機選取 50 檔")
            print("4) 參數設定")
            print("5) 離開")
            
            try:
                choice = input("\n請選擇 (1/2/3/4/5): ").strip()
            except EOFError:
                choice = '1'
            
            if choice == '1':
                args.mode = 'all'
                break
            elif choice == '2':
                args.mode = 'category'
                print("\n類型代碼:")
                print("  1=半導體  2=電子  3=金融  4=水泥/化工")
                print("  5=ETF  6=鋼鐵/營建  7=航運  8=其他")
                try:
                    cat_input = input("請輸入類型編號（逗號分隔，可多選）: ").strip()
                    args.categories = cat_input
                except EOFError:
                    args.categories = '1,2'
                
                try:
                    extra_input = input("是否要另外指定個股代碼？(y/N): ").strip().lower()
                    if extra_input == 'y':
                        args.stocks = input("請輸入股票代碼（逗號分隔）: ").strip()
                except EOFError:
                    pass
                break
                    
            elif choice == '3':
                args.mode = 'random'
                break
            elif choice == '4':
                interactive_parameter_menu()
            elif choice == '5':
                print("感謝使用！")
                return
            else:
                print("請輸入 1-5 的選項")
    
    analyzer = StockAnalyzer()
    
    # 傳遞選擇參數給 run 方法
    analyzer.run(
        stock_count=args.number,
        mode=args.mode if args.mode else 'all',
        categories=args.categories if args.categories else '',
        extra_stocks=args.stocks if args.stocks else '',
        random_count=args.random_count
    )


if __name__ == "__main__":
    main()
