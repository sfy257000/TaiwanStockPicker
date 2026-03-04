import requests
import json
import os
from datetime import datetime, timedelta

CACHE_FILE = "stock_cache.json"

STOCK_LIST_API = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
COMPANY_INFO_API = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

STOCK_DATA_WITH_CATEGORIES = {}

def load_cache():
    """Load stock data from cache file"""
    global STOCK_DATA_WITH_CATEGORIES
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                STOCK_DATA_WITH_CATEGORIES = json.load(f)
            print(f"已從快取載入 {len(STOCK_DATA_WITH_CATEGORIES)} 檔股票資料")
            return True
        except Exception as e:
            print(f"載入快取失敗: {e}")
    return False

def save_cache():
    """Save stock data to cache file"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(STOCK_DATA_WITH_CATEGORIES, f, ensure_ascii=False, indent=2)
        print(f"已儲存快取")
        return True
    except Exception as e:
        print(f"儲存快取失敗: {e}")
        return False

load_cache()

_INDUSTRY_TO_CATEGORY_MAP = {
    "1": "水泥",
    "2": "食品",
    "3": "塑膠",
    "4": "紡織",
    "5": "電機",
    "6": "電線電纜",
    "7": "鋼鐵",
    "8": "化工",
    "9": "玻璃陶瓷",
    "10": "造紙",
    "11": "橡膠",
    "12": "汽車",
    "13": "電子",
    "14": "營建",
    "15": "航運",
    "16": "觀光",
    "17": "金融",
    "18": "貿易百貨",
    "19": "綜合",
    "20": "其他",
    "21": "化學",
    "22": "生技醫療",
    "23": "油電燃氣",
    "24": "半導體",
    "25": "電腦週邊",
    "26": "光電",
    "27": "通信網路",
    "28": "電子零組件",
    "29": "電子通路",
    "30": "資訊服務",
    "31": "其他電子",
    "32": "文化創意",
    "33": "農業科技",
    "34": "電子商務",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活"
}

_CATEGORY_INDUSTRY_MAP = {
    "01": "水泥",
    "02": "食品",
    "03": "塑膠",
    "04": "紡織",
    "05": "電機",
    "06": "電線電纜",
    "07": "鋼鐵",
    "08": "化工",
    "09": "玻璃陶瓷",
    "10": "造紙",
    "11": "橡膠",
    "12": "汽車",
    "13": "電子",
    "14": "營建",
    "15": "航運",
    "16": "觀光",
    "17": "金融",
    "18": "貿易百貨",
    "19": "綜合",
    "20": "其他",
    "21": "化學",
    "22": "生技醫療",
    "23": "油電燃氣",
    "24": "半導體",
    "25": "電腦週邊",
    "26": "光電",
    "27": "通信網路",
    "28": "電子零組件",
    "29": "電子通路",
    "30": "資訊服務",
    "31": "其他電子",
    "32": "文化創意",
    "33": "農業科技",
    "34": "電子商務",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
}


def _get_category_from_industry(industry_code):
    """Map TWSE industry code to internal category"""
    if not industry_code:
        return "其他"
    
    industry_code = industry_code.strip()
    
    if industry_code in _CATEGORY_INDUSTRY_MAP:
        return _CATEGORY_INDUSTRY_MAP[industry_code]
    
    return "其他"


def fetch_company_info():
    """Fetch company info and industry data from TWSE API"""
    print(f"正在從 {COMPANY_INFO_API} 獲取公司基本資料...")
    try:
        response = requests.get(COMPANY_INFO_API, verify=False, timeout=30)
        print(f"API 回應狀態: {response.status_code}")
        data = response.json()
        
        print(f"API 回傳資料筆數: {len(data) if isinstance(data, list) else '非列表'}")
        
        if not data or (isinstance(data, list) and len(data) == 0):
            print("API 回傳空資料")
            return False

        for item in data:
            code = item.get("公司代號", "")
            name = item.get("公司簡稱", "") or item.get("公司名稱", "")
            industry = item.get("產業別", "")

            if code and name:
                category = _get_category_from_industry(industry) if industry else "其他"
                STOCK_DATA_WITH_CATEGORIES[code] = {
                    "name": name,
                    "category": category,
                    "industry": industry
                }
        
        print(f"成功獲取並處理 {len(STOCK_DATA_WITH_CATEGORIES)} 家公司資料。")
        save_cache()
        return True
    except Exception as e:
        print(f"獲取公司資料失敗: {e}")
        return False


def fetch_company_info_fallback():
    """Fallback method using a different approach"""
    global STOCK_DATA_WITH_CATEGORIES
    
    print("使用備用方法載入股票分類...")
    
    fallback_data = {
        "2330": {"name": "台積電", "category": "半導體", "industry": "半導體業"},
        "2317": {"name": "鴻海", "category": "電子", "industry": "電腦及週邊設備業"},
        "2454": {"name": "聯發科", "category": "半導體", "industry": "半導體業"},
        "2881": {"name": "富邦金", "category": "金融", "industry": "金融業"},
        "2882": {"name": "國泰金", "category": "金融", "industry": "金融業"},
        "2609": {"name": "陽明", "category": "航運", "industry": "航運業"},
        "2615": {"name": "長榮", "category": "航運", "industry": "航運業"},
        "0050": {"name": "元大台灣50", "category": "ETF", "industry": "ETF"},
        "0051": {"name": "元大中型100", "category": "ETF", "industry": "ETF"},
        "00878": {"name": "國泰永續高股息", "category": "ETF", "industry": "ETF"},
        "00919": {"name": "群益台灣精選高息", "category": "ETF", "industry": "ETF"},
        "2303": {"name": "聯電", "category": "半導體", "industry": "半導體業"},
        "3034": {"name": "聯詠", "category": "電子", "industry": "電子元件業"},
        "2379": {"name": "瑞昱", "category": "電子", "industry": "電子元件業"},
        "2412": {"name": "中華電", "category": "通信網路", "industry": "通信網路業"},
        "3008": {"name": "大立光", "category": "光電", "industry": "光電業"},
        "2002": {"name": "中鋼", "category": "鋼鐵", "industry": "鋼鐵工業"},
        "1101": {"name": "台泥", "category": "水泥", "industry": "水泥工業"},
        "2542": {"name": "興富發", "category": "營建", "industry": "營建業"},
        "2912": {"name": "統一", "category": "食品", "industry": "食品工業"},
    }
    
    STOCK_DATA_WITH_CATEGORIES = fallback_data
    print(f"成功載入 {len(STOCK_DATA_WITH_CATEGORIES)} 家公司資料（備用資料）。")
    return True


def check_and_update_stock_list():
    """Check and update stock list"""
    if not STOCK_DATA_WITH_CATEGORIES:
        print("股票清單資料為空，正在嘗試載入...")
        fetch_company_info()
    else:
        print("股票清單已載入。")


def _apply_list_filter(stocks):
    """套用黑名單/白名單過濾"""
    from config import CONFIG
    lf = CONFIG.get('list_filter', {})

    # 白名單：只保留白名單內的股票
    if lf.get('enable_whitelist') and lf.get('whitelist'):
        whiteset = set(lf['whitelist'])
        stocks = [(code, name) for code, name in stocks if code in whiteset]

    # 黑名單：排除黑名單內的股票
    if lf.get('enable_blacklist') and lf.get('blacklist'):
        blackset = set(lf['blacklist'])
        stocks = [(code, name) for code, name in stocks if code not in blackset]

    return stocks


def get_all_stocks():
    """Return all stocks，套用黑白名單"""
    stocks = [(code, data['name']) for code, data in STOCK_DATA_WITH_CATEGORIES.items()]
    return _apply_list_filter(stocks)


def get_stock_count():
    """Return total stock count"""
    return len(STOCK_DATA_WITH_CATEGORIES)


def get_stocks_by_category(categories_str):
    """Return stocks filtered by category，套用黑白名單"""
    if not categories_str:
        return get_all_stocks()

    target_categories = {cat.strip() for cat in categories_str.split(',')}

    filtered_stocks = []
    for code, data in STOCK_DATA_WITH_CATEGORIES.items():
        if data.get('category') in target_categories:
            filtered_stocks.append((code, data['name']))

    return _apply_list_filter(filtered_stocks)


def generate_stock_list_from_api(min_volume=1000):
    """Query stock list from API with volume filter"""
    print(f"正在從TWSE API取得股票清單 (成交量>={min_volume}張)...")
    
    try:
        response = requests.get(STOCK_LIST_API, verify=False, timeout=30)
        print(f"STOCK_LIST_API 回應狀態: {response.status_code}")
        data = response.json()
        
        print(f"股票清單 API 回傳筆數: {len(data) if isinstance(data, list) else '非列表'}")
        if isinstance(data, list) and len(data) > 0:
            print(f"第一筆資料: {data[0]}")
        
        if not data or (isinstance(data, list) and len(data) == 0):
            print("API 回傳空資料")
            if not STOCK_DATA_WITH_CATEGORIES:
                fetch_company_info()
            return generate_categorized_from_fallback(min_volume)
    except Exception as e:
        print(f"取得股票清單失敗: {e}")
        if not STOCK_DATA_WITH_CATEGORIES:
            fetch_company_info()
        return generate_categorized_from_fallback(min_volume)

    if not STOCK_DATA_WITH_CATEGORIES:
        fetch_company_info()
    
    if not STOCK_DATA_WITH_CATEGORIES:
        print("無法取得公司分類資料，使用備用方法")
        return generate_categorized_from_fallback(min_volume)

    categorized = {}
    category_map = {}
    
    for item in data:
        code = item.get("Code", "")
        name = item.get("Name", "")
        
        try:
            volume = int(item.get("TradeVolume", 0))
        except:
            volume = 0
        
        if volume < min_volume * 1000:
            continue

        if code in STOCK_DATA_WITH_CATEGORIES:
            category = STOCK_DATA_WITH_CATEGORIES[code].get("category", "其他")
        else:
            category = "其他"
        
        if category not in categorized:
            categorized[category] = []
            category_map[category] = 0
        
        categorized[category].append((code, name))
        category_map[category] += 1

    total = sum(category_map.values())
    print(f"共取得 {total} 檔股票符合成交量門檻")
    
    return categorized, category_map


def generate_categorized_from_fallback(min_volume=1000):
    """Generate categorized stock list from fallback data"""
    if not STOCK_DATA_WITH_CATEGORIES:
        fetch_company_info()
    
    categorized = {}
    category_map = {}
    
    for code, data in STOCK_DATA_WITH_CATEGORIES.items():
        category = data.get("category", "其他")
        name = data.get("name", code)
        
        if category not in categorized:
            categorized[category] = []
            category_map[category] = 0
        
        categorized[category].append((code, name))
        category_map[category] += 1
    
    total = sum(category_map.values())
    print(f"使用備用資料，共 {total} 檔股票")
    
    return categorized, category_map


def export_stock_list_to_file(min_volume=1000):
    """Export stock list - queries from API and updates STOCK_DATA_WITH_CATEGORIES"""
    global STOCK_DATA_WITH_CATEGORIES
    categorized, category_map = generate_stock_list_from_api(min_volume)
    
    # 將過濾後的股票清單存回 STOCK_DATA_WITH_CATEGORIES，讓選項1分析時使用同一份清單
    new_stock_data = {}
    for category, stocks in categorized.items():
        for code, name in stocks:
            # 保留原本的 industry 欄位（若有），只更新 name 和 category
            existing = STOCK_DATA_WITH_CATEGORIES.get(code, {})
            new_stock_data[code] = {
                "name": name,
                "category": category,
                "industry": existing.get("industry", "")
            }
    
    STOCK_DATA_WITH_CATEGORIES = new_stock_data
    save_cache()
    print(f"✓ 股票清單已更新並儲存，共 {len(new_stock_data)} 檔")
    return True


STOCK_LIST = []