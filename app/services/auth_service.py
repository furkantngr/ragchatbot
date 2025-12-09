import json
import os
from app.core.config import USERS_JSON_PATH

def verify_user(username, password):
    """
    Kullanıcı adı ve şifreyi users.json dosyasından kontrol eder.
    """
    if not os.path.exists(USERS_JSON_PATH):
        return False # Dosya yoksa kimse giremez

    try:
        with open(USERS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            users = data.get("users", [])
            
            for user in users:
                if user["username"] == username and user["password"] == password:
                    return True
    except Exception as e:
        print(f"Auth Hatası: {e}")
        return False
    
    return False