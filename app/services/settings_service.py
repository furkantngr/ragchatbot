import json
import os
import requests
from app.core.config import SETTINGS_FILE_PATH

DEFAULT_MODEL = "gemma3:12b"

def get_current_model():
    """
    settings.json dosyasından seçili modeli okur.
    Dosya yoksa varsayılanı döner.
    """
    if not os.path.exists(SETTINGS_FILE_PATH):
        return DEFAULT_MODEL
    
    try:
        with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("chat_model", DEFAULT_MODEL)
    except:
        return DEFAULT_MODEL

def set_current_model(model_name):
    """
    Seçilen modeli dosyaya kaydeder.
    """
    data = {"chat_model": model_name}
    try:
        with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Ayar kaydetme hatası: {e}")
        return False

def get_available_models():
    """
    Ollama sunucusuna bağlanıp (localhost:11434) yüklü modelleri çeker.
    """
    try:
        # Ollama'nın standart API'si
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            # Sadece model isimlerini (name) listele
            return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        print(f"Ollama'ya bağlanılamadı: {e}")
    
    # Hata olursa manuel bir liste dön
    return ["gemma2:9b", "llama3.2", "mistral", "qwen2.5"]