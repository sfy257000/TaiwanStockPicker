# -*- coding: utf-8 -*-
"""
股票清單 - 200+檔主要上市股票
"""

STOCK_LIST = [
    # === 半導體 (完整陣容) ===
    ('2330', '台積電'), ('2303', '聯電'), ('2454', '聯發科'),
    ('2337', '旺宏'), ('2408', '南亞科'), ('2344', '華邦電'),
    ('3443', '創意'), ('3034', '聯詠'), ('2379', '瑞昱'),
    ('2449', '京元電子'), ('3529', '力旺'),
    ('2338', '光罩'), ('2351', '順德'), ('5347', '世界'),
    ('3037', '欣興'), ('3189', '景碩'), ('6239', '力成'),
    ('8150', '南茂'), ('3533', '嘉澤'), ('5471', '松翰'),
    ('6136', '富鼎'), ('6415', '矽力-KY'), ('6515', '創惟'),
    ('6552', '展林'), ('6573', '虹冠電'), ('6641', '天虹'),
    ('6643', 'M31'), ('6756', '天擎'), ('6781', '呈效'),
    ('8016', '矽創'), ('8028', '旭隼'), ('8081', '致新'),
    ('8110', '華東'), ('8255', '朋程'), ('8299', '群聯'),
    ('8437', '大地-KY'), ('4952', '凌通'), ('5269', '祥碩'),
    ('6462', '神盾'), ('6669', '緯穎'), ('6683', '雍智科技'),
    ('6716', '應廣'), ('6732', '君安科技'), ('6751', '來頡'),

    # === AI/伺服器/高速傳輸 ===
    ('2382', '廣達'), ('3231', '緯創'), ('3665', '贸聯-KY'),
    ('6414', '樺漢'), ('2404', '漢唐'), ('3005', '神基'),
    ('6531', '愛普'), ('4938', '和碩'), ('2317', '鴻海'),
    ('2356', '英業達'), ('2324', '仁寶'), ('3708', '上銀'),
    ('1519', '華城'), ('1504', '東元'), ('1590', '亞德客-KY'),
    ('1597', '直得'), ('4528', '江興'), ('5285', '界霖'),
    ('4551', '智伸科'), ('4562', '京鼎'), ('6141', '柏承'),
    ('6257', '宣德'), ('6510', '精測'), ('6569', '醫揚'), ('6706', '惠特'),

    # === 電子代工/組裝 ===
    ('2347', '聯強'), ('3023', '信邦'), ('6153', '嘉聯益'),
    ('6213', '聯茂'), ('6269', '台郡'), ('6323', '洋華'),
    ('6442', '光群雷'), ('6582', '申豐'), ('6585', '點序'),

    # === 電子零組件 ===
    ('2308', '台達電'), ('2301', '光寶科'), ('2327', '國巨'),
    ('2357', '華碩'), ('2376', '技嘉'), ('2395', '研華'),
    ('2474', '可成'), ('2492', '華新科'), ('2439', '美律'),
    ('2360', '致茂'), ('2383', '台光電'), ('2409', '友達'),
    ('3481', '群創'), ('2352', '佳世達'), ('2451', '創見'),
    ('2458', '義隆'), ('2498', '宏達電'), ('2353', '宏碁'),
    ('2377', '微星'), ('3019', '陞泰'), ('3094', '聯杰'),
    ('3130', '一零四'), ('3164', '訊映'), ('3227', '原相'),
    ('3290', '東浦'), ('3296', '勝麗'), ('3324', '雙鴻'),
    ('3338', '泰碩'), ('3374', '精材'), ('3406', '玉晶光'),
    ('3438', '台名'), ('3450', '聯鈞'), ('3465', '博磊'),
    ('3483', '中美晶'), ('3508', '位速'), ('3515', '華擎'),
    ('3532', '台勝科'), ('3545', '敦泰'), ('3552', '同泰'),
    ('3563', '牧德'), ('3577', '耕興'), ('3583', '辛耘'),
    ('3588', '通嘉'), ('3593', '力山地'), ('3625', '西勝'),
    ('3630', '新鉅科'), ('3653', '健策'), ('3686', '達能'),
    ('3706', '神達'), ('3721', '眾達-KY'), ('4902', '聯強'),
    ('4915', '致伸'), ('4943', '康控'), ('4950', '牧東'),
    ('4971', 'IET-KY'), ('5230', '雷笛克'), ('6105', '瑞傳'),
    ('6117', '迎華'), ('6128', '上福'), ('6138', '魏橋'),
    ('6147', '高僑'), ('6156', '同欣電'), ('6177', '立敦'),
    ('6197', '研通'), ('6215', '和椿'), ('6225', '天瀚'),
    ('6226', '晶達'), ('6230', 'NAND-KY'), ('6235', '華孚'),
    ('6244', '茂迪'), ('6251', '定穎'), ('6259', '亨泰'),
    ('6263', '普萊'), ('6278', '台表'), ('6282', '康舒'),
    ('6287', '立凱-KY'), ('6291', '沛波'), ('6309', '鈞寶'),
    ('6315', '基泰'), ('6316', '秉翰'), ('6321', '優群'),
    ('6361', '精測'), ('6370', '美德'), ('6388', '堤維西'),
    ('6411', '晶焱'), ('6426', '鼎元'), ('6438', '迅杰'),
    ('6443', '元智'), ('6451', '訊芯-KY'), ('6468', '力旺'),
    ('6477', '安集'), ('6485', '點序'), ('6488', '撼訊'),
    ('6514', '立積'), ('6525', '捷敏-KY'), ('6532', '瑞耘'),
    ('6535', '創意'), ('6538', '聚積'), ('6548', '長科'),
    ('6556', '展基'), ('6568', '通測'), ('6574', '霈方'),
    ('6581', '台生材'), ('6588', '數位通'), ('6592', '合盈'),
    ('6594', '伍豐'), ('6597', '立凱'), ('6598', '世紀'),
    ('6613', '朋億'), ('6625', '必應'), ('6629', '泰博'),
    ('6631', '家登'), ('6637', '智微'), ('6649', '力致'),
    ('6651', '常珵'), ('6655', '大恭'), ('6661', '同致'),
    ('6662', '乐翻天'), ('6663', '环鸿'),

    # === 通信網路 ===
    ('2412', '中華電'), ('3045', '台灣大'), ('4904', '遠傳'),
    ('2345', '智邦'), ('6285', '啟碁'), ('5388', '中磊'),

    # === 金融保險 ===
    ('2881', '富邦金'), ('2882', '國泰金'), ('2883', '開發金'),
    ('2884', '玉山金'), ('2885', '元大金'), ('2886', '兆豐金'),
    ('2887', '台新金'), ('2888', '新光金'), ('2889', '國票金'),
    ('2890', '永豐金'), ('2891', '中信金'), ('2892', '第一金'),
    ('5876', '上海商銀'), ('5880', '合庫金'), ('2880', '華南金'),
    ('2834', '台企銀'), ('2845', '遠東銀'), ('2820', '華票'),
    ('2832', '台產'), ('2847', '大城'), ('2855', '統一證'),
    ('2867', '三商壽'), ('6005', '群益證'),

    # === 鋼鐵 ===
    ('2002', '中鋼'), ('2006', '東和鋼鐵'), ('2014', '中鴻'),
    ('2015', '豐興'), ('2013', '中鋼構'), ('2012', '春雨'),
    ('2010', '春源鋼鐵'), ('2031', '新光鋼'), ('2007', '燁興'),
    ('2008', '高興昌'), ('2017', '第一鋼'), ('2020', '美亞'),
    ('2022', '聚亨'), ('2023', '燁輝'), ('2024', '彰源'),
    ('2025', '久鋼'), ('2027', '大成鋼'), ('2028', '威致'),

    # === 水泥 ===
    ('1101', '台泥'), ('1102', '亞泥'), ('1103', '嘉泥'),
    ('1104', '環泥'), ('1108', '幸福'), ('1109', '信大'),

    # === 食品 ===
    ('1216', '統一'), ('1215', '卜蜂'), ('1210', '大成'),
    ('1201', '味全'), ('1227', '佳格'), ('1229', '聯華'),
    ('1231', '聯華食'), ('1232', '大統益'), ('1234', '黑松'),
    ('1218', '泰山'), ('1707', '葡萄王'), ('1722', '台肥'),

    # === 塑膠化工 ===
    ('1301', '台塑'), ('1303', '南亞'), ('1326', '台化'),
    ('6505', '台塑化'), ('1304', '台聚'), ('1308', '亞聚'),
    ('1312', '國喬'), ('1313', '聯成'), ('1314', '中石化'),
    ('1310', '台苯'), ('1315', '達新'), ('1702', '台硝'),

    # === 紡織 ===
    ('1402', '遠東新'), ('1409', '新纖'), ('1476', '儒鴻'),
    ('1477', '聚陽'), ('9910', '豐泰'),

    # === 航運 ===
    ('2603', '長榮'), ('2609', '陽明'), ('2615', '萬海'),
    ('2618', '長榮航'), ('2610', '華航'), ('2606', '裕民'),
    ('2634', '漢翔'), ('2633', '台灣高鐵'),

    # === 營建 ===
    ('2504', '國產'), ('2505', '國揚'), ('2520', '冠德'),
    ('2524', '京城'), ('2548', '華固'),

    # === 其他 ===
    ('9914', '美利達'), ('9921', '巨大'), ('9917', '中保科'),
    ('9904', '寶成'), ('1907', '永豐餘'), ('1904', '正隆'),
    ('2105', '正新'), ('9933', '中鼎'),

    # === ETF ===
    ('0050', '元大台灣50'), ('0051', '元大台灣單'),
    ('0052', '富邦科技'), ('0053', '元大電子'),
    ('0054', '元大中型100'), ('0055', '元大MSCI'),
    ('0056', '元大高股息'), ('0057', '富邦摩台'),
    ('00646', '元大S&P'), ('00690', '群益道瓊'),
    ('00701', '國泰5G+'), ('00713', '元大高股息低波'),
    ('00881', '國泰台灣5G+'), ('00891', '中信關鍵半導體'),
    ('00892', '台新永續高股息'), ('00904', '中信小資高價30'),
    ('00915', '凱基高股息'), ('00918', '群益高股息'),
    ('00922', '群益ESG'), ('00927', '群益半導體'),
    ('00934', '中信半導體'), ('00937', '群益ESG低碳'),
    ('00940', '元大台灣高股息'),

    # === 電機/重電 ===
    ('1503', '士電'), ('1513', '中興電'), ('1536', '和大'),
    ('8046', '南電'),

    # === 生技醫療 ===
    ('4743', '合一'), ('6446', '藥華藥'), ('4105', '皇將'),
    ('4163', '翔宇'), ('4164', '喆麗'), ('4165', '恒'),
    ('4166', '博醫'), ('4167', '欣'), ('4168', '霖'),

    # === 其他電子 ===
    ('3711', '日月光投控'), ('2385', '群光'), ('2414', '精誠'),
    ('2480', '敦陽科'), ('3036', '文曄'), ('6409', '旭隼'),
]

def get_all_stocks():
    """取得所有股票（去除重複）"""
    seen = set()
    unique = []
    for code, name in STOCK_LIST:
        if code not in seen:
            seen.add(code)
            unique.append((code, name))
    return unique

def get_stock_count():
    """取得股票數量"""
    return len(get_all_stocks())

# ============================================================================
# 新增功能：每日股票清單更新與互動式選擇
# ============================================================================

import os
import random
import requests
import urllib3
from datetime import datetime
from config import CONFIG

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_base_dir():
    """取得程式根目錄"""
    return os.path.dirname(os.path.abspath(__file__))


def check_and_update_stock_list():
    """檢查並更新股票清單（每天只更新一次）- 現在預設關閉"""
    config = CONFIG['stock_list']
    if not config.get('update_once_per_day', True):
        return False
    
    last_update_file = os.path.join(_get_base_dir(), config.get('last_update_file', 'last_update.txt'))
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 檢查是否今天已經更新過
    if os.path.exists(last_update_file):
        with open(last_update_file, 'r', encoding='utf-8') as f:
            last_date = f.read().strip()
        if last_date == today:
            return False
    
    # 需要更新 - 但 TWSE API 目前有問題，先跳過
    print("\n" + "="*50)
    print("股票清單更新")
    print("="*50)
    print("⚠ 注意：TWSE API 目前無法自動取得最新股票清單")
    print("  現有股票清單包含 342 檔，已足夠分析使用")
    print("  如需更新，請手動修改 stock_list.py")
    
    # 記錄今天已檢查過（即使失敗也記錄，避免重試）
    try:
        with open(last_update_file, 'w', encoding='utf-8') as f:
            f.write(today)
    except:
        pass
    
    return False


def _fetch_all_twse_stocks():
    """從 TWSE API 抓取所有上市股票"""
    stocks = []
    
    try:
        # 抓取上市公司
        url = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date=&type=ALL&include=true"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        data = response.json()
        
        if 'data1' in data:
            for row in data['data1']:
                try:
                    if len(row) >= 2:
                        code = str(row[0]).strip()
                        name = str(row[1]).strip() if len(row) > 1 else ''
                        if code and code.isdigit() and len(code) == 4:
                            stocks.append((code, name))
                except:
                    continue
        
        print(f"  上市公司: {len(stocks)} 檔")
    except Exception as e:
        print(f"  ⚠ 取得上市公司失敗: {e}")
    
    return stocks


def _fetch_all_otc_stocks():
    """從 TPEX API 抓取所有上櫃股票"""
    stocks = []
    
    try:
        # 抓取上櫃公司
        url = "https://www.tpex.org.tw/web/stock/company/list.php?l=zh-tw"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        # 嘗試 JSON API
        url2 = "https://www.tpex.org.tw/web/stock/company/company_list.php?l=zh-tw&o=json"
        response2 = requests.get(url2, headers=headers, timeout=30, verify=False)
        
        if response2.status_code == 200:
            try:
                data = response2.json()
                if 'aaData' in data:
                    for row in data['aaData']:
                        try:
                            if len(row) >= 2:
                                code = str(row[0]).strip()
                                name = str(row[1]).strip() if len(row) > 1 else ''
                                if code and code.isdigit() and len(code) == 4:
                                    stocks.append((code, name))
                        except:
                            continue
            except:
                pass
        
        print(f"  上櫃公司: {len(stocks)} 檔")
    except Exception as e:
        print(f"  ⚠ 取得上櫃公司失敗: {e}")
    
    return stocks


def _merge_stock_list(new_stocks):
    """合併新舊股票清單，保留現有分類"""
    global STOCK_LIST
    
    # 取得現有股票代碼
    existing_codes = {code for code, _ in STOCK_LIST}
    
    # 加入新股票（還沒在清單中的）
    new_count = 0
    for code, name in new_stocks:
        if code not in existing_codes:
            # 加入到「其他上市」分類
            STOCK_LIST.append((code, name if name else code))
            new_count += 1
    
    print(f"  新增股票: {new_count} 檔")


def build_category_map():
    """建立股票分類地圖"""
    category_map = {}
    current_category = "未分類"
    
    for code, name in STOCK_LIST:
        # 嘗試從股票代碼判斷類型
        if code.startswith('00'):
            category = 'ETF'
        elif code.startswith('1'):
            category = '水泥/化工'
        elif code.startswith('2'):
            category = '鋼鐵/營建'
        elif code.startswith('28'):
            category = '金融'
        elif code in ['2330', '2303', '2454', '2451'] or code.startswith('3'):
            category = '半導體'
        elif code.startswith('6'):
            category = '電子'
        else:
            category = '其他'
        
        if category not in category_map:
            category_map[category] = []
        category_map[category].append((code, name))
    
    # 加入「全部」分類
    category_map['全部'] = [(code, name) for code, name in STOCK_LIST]
    
    return category_map


def interactive_stock_selection(mode='all', categories='', extra_stocks='', random_count=50):
    """股票選擇（支援命令列參數）"""
    import random
    from config import CONFIG
    
    category_map = build_category_map()
    category_list = [c for c in category_map.keys() if c != '全部']
    
    # 建立分類對應
    cat_mapping = {
        '1': '半導體', '2': '電子', '3': '金融', 
        '4': '水泥/化工', '5': 'ETF', '6': '鋼鐵/營建',
        '7': '航運', '8': '其他'
    }
    
    if mode == 'all':
        # 全部股票
        selected = category_map['全部']
        print(f"\n✓ 分析全部股票: {len(selected)} 檔")
        
    elif mode == 'random':
        # 隨機選取
        all_stocks = category_map['全部']
        count = min(random_count, len(all_stocks))
        selected = random.sample(all_stocks, count)
        print(f"\n✓ 隨機選取: {count} 檔")
        
    elif mode == 'category':
        # 依類型選擇
        selected = []
        if categories:
            for cat_id in categories.split(','):
                cat_id = cat_id.strip()
                cat_name = cat_mapping.get(cat_id, cat_id)
                if cat_name in category_map:
                    selected.extend(category_map[cat_name])
                    print(f"  + {cat_name}: {len(category_map[cat_name])} 檔")
        
        # 加入額外指定的個股
        if extra_stocks:
            all_stocks_dict = {c: n for c, n in category_map['全部']}
            for code in extra_stocks.split(','):
                code = code.strip()
                if code in all_stocks_dict:
                    if (code, all_stocks_dict[code]) not in selected:
                        selected.append((code, all_stocks_dict[code]))
            print(f"  + 額外指定: {len(extra_stocks.split(','))} 檔")
        
        if not selected:
            selected = category_map['全部']
        print(f"\n✓ 依類型選擇: {len(selected)} 檔")
    
    else:
        selected = category_map['全部']
    
    return selected
