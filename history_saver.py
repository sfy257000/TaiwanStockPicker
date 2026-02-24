# -*- coding: utf-8 -*-
"""
歷史數據存檔模組
儲存每日分析結果與價格數據
"""

import os
import json
from datetime import datetime, timedelta
from config import CONFIG

class HistorySaver:
    def __init__(self, base_folder=None):
        if base_folder:
            self.base_folder = base_folder
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.base_folder = os.path.join(script_dir, CONFIG['output']['history_folder'])
        self._ensure_folders()
    
    def _ensure_folders(self):
        """確保資料夾存在"""
        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder)
    
    def save_analysis(self, results, date_str=None):
        """儲存分析結果"""
        if not CONFIG['output']['save_history']:
            return
        
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        filename = os.path.join(self.base_folder, f'analysis_{date_str}.json')
        
        clean_results = []
        for r in results:
            clean = {
                'code': r.get('code', ''),
                'name': r.get('name', ''),
                'price': r.get('price', 0),
                'change_pct': r.get('change_pct', 0),
                'volume': r.get('volume', 0),
                'high': r.get('high', 0),
                'low': r.get('low', 0),
                'total_score': r.get('total_score', 0),
                'tech_score': r.get('tech_score', 0),
                'inst_score': r.get('inst_score', 0),
                'reasons': r.get('reasons', []),
            }
            clean_results.append(clean)
        
        data = {
            'date': date_str,
            'timestamp': datetime.now().isoformat(),
            'count': len(clean_results),
            'results': clean_results,
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"  已儲存至: {filename}")
    
    def load_history(self, date_str):
        """載入歷史數據"""
        filename = os.path.join(self.base_folder, f'analysis_{date_str}.json')
        
        if not os.path.exists(filename):
            return None
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def get_recent_history(self, days=5):
        """取得最近幾天的歷史"""
        history = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y%m%d')
            
            data = self.load_history(date_str)
            if data:
                history.append(data)
        
        return history
    
    def compare_with_previous(self, current_results, previous_date=None):
        """與前一日比較"""
        if previous_date is None:
            previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
        previous_data = self.load_history(previous_date)
        
        if not previous_data:
            return None
        
        previous_results = {r['code']: r for r in previous_data.get('results', [])}
        
        score_up = []
        score_down = []
        
        for current in current_results:
            code = current.get('code', '')
            if code in previous_results:
                prev = previous_results[code]
                score_diff = current.get('total_score', 0) - prev.get('total_score', 0)
                if score_diff >= 15:
                    score_up.append({
                        'code': code,
                        'name': current.get('name', ''),
                        'change': score_diff,
                    })
                elif score_diff <= -15:
                    score_down.append({
                        'code': code,
                        'name': current.get('name', ''),
                        'change': score_diff,
                    })
        
        return {
            'score_up': score_up,
            'score_down': score_down,
        }
