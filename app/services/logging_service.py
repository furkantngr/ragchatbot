import sqlite3
from datetime import datetime
# Config dosyasından tanımladığımız iki ayrı veritabanı yolunu alıyoruz
from app.core.config import LOG_DB_PATH, ADMIN_LOG_DB_PATH

def init_db():
    """
    Veritabanlarını ve gerekli tabloları yoksa oluşturur.
    Artık 2 ayrı dosya yönetiliyor.
    """
    # 1. Chat Logları (Kullanıcı Sohbetleri) - chat_history.db
    try:
        conn = sqlite3.connect(LOG_DB_PATH)
        cursor = conn.cursor()
        # Kullanıcı logları tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_query TEXT,
                bot_response TEXT,
                context_used TEXT,
                model_name TEXT,
                ip_address TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Chat DB Başlatma Hatası: {e}")

    # 2. Admin Logları (Yönetici İşlemleri) - admin_logs.db
    try:
        conn_admin = sqlite3.connect(ADMIN_LOG_DB_PATH)
        cursor_admin = conn_admin.cursor()
        # Yönetici logları tablosu
        cursor_admin.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                filename TEXT,
                user TEXT
            )
        ''')
        conn_admin.commit()
        conn_admin.close()
    except Exception as e:
        print(f"Admin DB Başlatma Hatası: {e}")
        
    print(f"📁 Log veritabanları kontrol edildi:\n   - Sohbet: {LOG_DB_PATH}\n   - Admin:  {ADMIN_LOG_DB_PATH}")

def log_conversation(query: str, response: str, context: str, model: str, ip_address: str = "Bilinmiyor"):
    """
    Kullanıcı sohbetini 'chat_history.db' dosyasına kaydeder.
    """
    try:
        conn = sqlite3.connect(LOG_DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO conversation_logs (timestamp, user_query, bot_response, context_used, model_name, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now, query, response, context, model, ip_address))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Sohbet Loglama Hatası: {e}")

def log_admin_action(action, filename, user):
    """
    Yönetici işlemlerini (Yükleme, Silme vb.) 'admin_logs.db' dosyasına kaydeder.
    """
    try:
        conn = sqlite3.connect(ADMIN_LOG_DB_PATH) # <-- Admin DB kullanılır
        cursor = conn.cursor()
        
        # action: 'upload', 'delete', 'process' vb.
        cursor.execute('INSERT INTO admin_logs (action, filename, user) VALUES (?, ?, ?)', (action, filename, user))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Admin Loglama Hatası: {e}")

def get_admin_logs(limit=50):
    """
    Admin paneli arayüzünde göstermek için son logları çeker.
    """
    try:
        conn = sqlite3.connect(ADMIN_LOG_DB_PATH)
        cursor = conn.cursor()
        
        # En son yapılan işlem en üstte görünsün diye DESC sıralama yapıyoruz
        cursor.execute('SELECT action, filename, user, timestamp FROM admin_logs ORDER BY id DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        # Frontend'in kolay okuması için list of dicts formatına çeviriyoruz
        return [{"action": r[0], "filename": r[1], "user": r[2], "date": r[3]} for r in rows]
    except Exception as e:
        print(f"Log Okuma Hatası: {e}")
        return []