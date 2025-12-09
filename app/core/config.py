import os
from pathlib import Path

# --- 1. INTRANET ERİŞİMİ ---
# Eğer API ile menü çekiyorsanız buraya F12'den aldığınız Cookie'yi yapıştırın.
# Şimdilik boş veya eski cookie kalabilir, RAG servisi bunu kullanmıyorsa sorun yaratmaz.
RAW_COOKIE = """BURAYA_KOPYALADIGINIZ_UZUN_COOKIE_YAZISI"""

# --- 3. DOSYA YOLLARI ---
# Dosyanın bulunduğu yerden geriye giderek Ana Dizini (agent/) buluyoruz.
# agent/app/core/config.py -> parent(core) -> parent(app) -> parent(agent)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Klasörler (String formatında)
CHAT_MODEL = "gemma2:9b" 
DATA_PATH = str(BASE_DIR / "belgelerim")         # Canlı (Yayındaki) Belgeler
STAGING_PATH = str(BASE_DIR / "taslak_belgeler") # Yönetici onayını bekleyen belgeler
CHROMA_PATH = str(BASE_DIR / "chroma_db_text")   # Vektör Veritabanı
LOCAL_EMBEDDING_PATH = str(BASE_DIR / "local_models" / "bge-m3") # Embedding Modeli
SETTINGS_FILE_PATH = str(BASE_DIR / "settings.json") # <-- YENİ
USERS_JSON_PATH = str(BASE_DIR / "users.json") 
PROMPT_FAST_PATH = str(BASE_DIR / "prompt_fast.txt")       # Hızlı Mod
PROMPT_THINKING_PATH = str(BASE_DIR / "prompt_thinking.txt") # Düşünen Mod

# Veritabanı Dosyaları (Loglar)
LOG_DB_PATH = str(BASE_DIR / "chat_history.db")      # Sohbet kayıtları
ADMIN_LOG_DB_PATH = str(BASE_DIR / "admin_logs.db")  # Yönetici işlem kayıtları

# --- 4. KLASÖR KONTROLÜ ---
# Gerekli klasörler yoksa otomatik oluştur.
for path in [DATA_PATH, STAGING_PATH]:
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"📂 Klasör oluşturuldu: {path}")

# --- 5. UYGULAMA LİNKLERİ (Link Enjeksiyonu) ---
# Kullanıcı sorusunda bu anahtar kelimeler geçerse, cevap içine link eklenir.
APP_LINKS = {
    "okr": "http://bz-srv-spp01:180/",
    "kaizen": "http://bz-srv-spp01:20255/",
    "kazanılmış dersler": "http://bz-srv-spp01:20255/",
    "epcr": "http://bz-srv-spp01:20259/",
    "e-pcr": "http://bz-srv-spp01:20259/",
    "envanter": "http://bz-srv-spp01:167/",
    "erm": "http://bz-srv-spp02:166/",
    "hololens": "http://bz-srv-app03:306/",
    "iletişim": "http://bz-srv-spp01:112/",
    "kpi": "http://bz-srv-spp01:99/",
    "wsa": "https://wsaapi.bize.com/",
    "legalmech": "http://bz-srv-spp01:8025/",
    "mikado": "http://10.90.2.200:8082/mikado/",
    "polivalans raporu": "http://bz-srv-tia/Reports/powerbi/Polivalans?rs:embed=true",
    "polivalans": "https://polivalans.bize360.com/"
}