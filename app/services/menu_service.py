# app/services/menu_service.py
import requests
import json
import time
import warnings
from urllib3.exceptions import InsecureRequestWarning
from app.core.config import RAW_COOKIE

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

menu_cache = {
    "content": None,
    "last_fetch_time": 0
}

def fetch_menu_from_api() -> str | None:
    global menu_cache
    current_time = time.time()
    
    # 1 Saatlik Cache
    if (current_time - menu_cache["last_fetch_time"]) < 3600 and menu_cache["content"]:
        return menu_cache["content"]

    API_URL = "https://intranet/diningmenu/get"
    
    # Config'den gelen cookie'yi temizle
    cookie_clean = RAW_COOKIE.strip().replace('\n', '').replace('\r', '')

    if "BURAYA" in cookie_clean:
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Cookie': cookie_clean,
        'Origin': 'https://intranet',
        'Referer': 'https://intranet/diningmenu'
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json={}, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            formatted_menu = json.dumps(data, indent=2, ensure_ascii=False)
            
            menu_cache["content"] = formatted_menu
            menu_cache["last_fetch_time"] = current_time
            return formatted_menu
    except Exception as e:
        print(f"Menu API Hatası: {e}")
        return None