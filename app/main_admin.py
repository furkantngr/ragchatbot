from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os
import shutil
import requests
from datetime import datetime

# Servisler ve Ayarlar
from app.services.rag_service import ingest_new_file, initialize_rag
from app.services.auth_service import verify_user
from app.services.logging_service import log_admin_action, get_admin_logs
from app.services.settings_service import get_current_model, set_current_model, get_available_models

# Config'den gerekli tüm yolları import ediyoruz
from app.core.config import (
    DATA_PATH, 
    STAGING_PATH, 
    PROMPT_FAST_PATH, 
    PROMPT_THINKING_PATH,
    # Eski uyumluluk için gerekirse kalsın
)

ADMIN_HTML_PATH = "admin.html"
CHAT_API_URL = "http://localhost:8000/refresh-db"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Admin API açılırken RAG sistemini başlatır.
    Dosya işlemek ve veritabanına yazmak için gereklidir.
    """
    print("🔧 Admin Paneli başlatılıyor...")
    initialize_rag()
    yield

app = FastAPI(title="Admin API (Yönetim)", version="5.0", lifespan=lifespan)

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# 1. ARAYÜZ VE GİRİŞ
# ==========================================================

@app.get("/")
async def admin_root():
    """Admin panelini (HTML) sunar"""
    if os.path.exists(ADMIN_HTML_PATH):
        return FileResponse(ADMIN_HTML_PATH)
    return {"error": "admin.html dosyası bulunamadı."}

@app.post("/api/login")
def login(username: str = Form(...), password: str = Form(...)):
    if verify_user(username, password):
        return {"status": "success", "message": "Giriş başarılı"}
    raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")

# ==========================================================
# 2. LOGLAMA İŞLEMLERİ
# ==========================================================

@app.post("/api/logs")
def list_logs(username: str = Form(...), password: str = Form(...)):
    """Son yönetici işlemlerini listeler"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401)
    return get_admin_logs(limit=100)

# ==========================================================
# 3. PROMPT YÖNETİMİ (ÇİFT MODLU)
# ==========================================================

@app.post("/api/get-prompt")
def get_prompt(
    prompt_type: str = Form(...), # 'fast' veya 'thinking'
    username: str = Form(...), 
    password: str = Form(...)
):
    """Seçilen modun prompt dosyasını okur"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401)
    
    # Hangi dosyaya bakılacağını seç
    if prompt_type == "thinking":
        target_file = PROMPT_THINKING_PATH
    else:
        target_file = PROMPT_FAST_PATH # Varsayılan fast
    
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        except Exception as e:
            return JSONResponse(status_code=500, content={"detail": str(e)})
            
    return {"content": "Bu mod için henüz bir prompt dosyası oluşturulmamış."}

@app.post("/api/save-prompt")
def save_prompt(
    content: str = Form(...),
    prompt_type: str = Form(...), 
    username: str = Form(...), 
    password: str = Form(...)
):
    """Seçilen modun prompt dosyasını kaydeder ve Chatbot'u yeniler"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401)
    
    # Hedef dosyayı belirle
    if prompt_type == "thinking":
        target_file = PROMPT_THINKING_PATH
    else:
        target_file = PROMPT_FAST_PATH
        
    log_action = f"update_prompt_{prompt_type}"

    try:
        # 1. Dosyaya Yaz
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        log_admin_action(log_action, os.path.basename(target_file), username)
        
        # 2. Chatbot'u Dürt (Yenile)
        try:
            requests.post(CHAT_API_URL, timeout=5)
        except:
            print("⚠️ Chatbot yenilenemedi (Kapalı olabilir).")

        return {"message": f"{prompt_type.upper()} Prompt başarıyla güncellendi."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

# ==========================================================
# 4. MODEL YÖNETİMİ
# ==========================================================

@app.post("/api/get-model-info")
def get_model_info(username: str = Form(...), password: str = Form(...)):
    """Mevcut modeli ve yüklü model listesini döner"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401)
    
    return {
        "current_model": get_current_model(),
        "available_models": get_available_models()
    }

@app.post("/api/set-model")
def update_model(
    model_name: str = Form(...),
    username: str = Form(...), 
    password: str = Form(...)
):
    """Modeli değiştirir ve sistemi yeniler"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401)
    
    # 1. Ayarı Kaydet
    if set_current_model(model_name):
        log_admin_action("change_model", model_name, username)
        
        # 2. Chatbot'u Yenile
        try:
            requests.post(CHAT_API_URL, timeout=10)
        except:
            print("Chatbot yenilenemedi.")
            
        # 3. Admin tarafındaki RAG servisini de yenile
        initialize_rag()
        
        return {"message": f"Model '{model_name}' olarak güncellendi."}
    
    return JSONResponse(status_code=500, content={"detail": "Model kaydedilemedi."})

# ==========================================================
# 5. TASLAK (STAGING) DOSYA İŞLEMLERİ
# ==========================================================

@app.post("/api/list-files")
def list_staging_files(username: str = Form(...), password: str = Form(...)):
    """Taslak klasöründeki dosyaları listeler"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")
    
    files = []
    if os.path.exists(STAGING_PATH):
        files = [f for f in os.listdir(STAGING_PATH) if f.lower().endswith(".pdf")]
    return {"files": sorted(files, reverse=True)}

@app.post("/api/upload")
def upload_staging(
    file: UploadFile = File(...), 
    username: str = Form(...), 
    password: str = Form(...)
):
    """Dosyaya zaman damgası ekleyerek taslağa kaydeder"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")
    
    try:
        if not os.path.exists(STAGING_PATH):
            os.makedirs(STAGING_PATH)

        # Zaman damgası ekleme
        filename_base, file_extension = os.path.splitext(file.filename)
        timestamp = datetime.now().strftime("%d.%m.%Y-%H.%M.%S")
        new_filename = f"{filename_base}_{timestamp}{file_extension}"
        
        file_path = os.path.join(STAGING_PATH, new_filename)
        
        with open(file_path, "wb+") as f:
            shutil.copyfileobj(file.file, f)
            
        log_admin_action("upload", new_filename, username)
        return {"message": f"'{new_filename}' olarak taslaklara eklendi."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/delete")
def delete_staging_file(
    filename: str = Form(...), 
    username: str = Form(...), 
    password: str = Form(...)
):
    """Taslak klasöründen dosya siler (Kalıcı silme)"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")
    
    file_path = os.path.join(STAGING_PATH, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        log_admin_action("delete_draft", filename, username)
        return {"message": f"'{filename}' silindi."}
    
    return JSONResponse(status_code=404, content={"detail": "Dosya bulunamadı"})

# ==========================================================
# 6. CANLI (PRODUCTION) DOSYA İŞLEMLERİ
# ==========================================================

@app.post("/api/list-production-files")
def list_production_files(username: str = Form(...), password: str = Form(...)):
    """Canlı 'belgelerim' klasörünü listeler"""
    if not verify_user(username, password): 
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")
    
    files = []
    if os.path.exists(DATA_PATH):
        files = [f for f in os.listdir(DATA_PATH) if f.lower().endswith(".pdf")]
    return {"files": sorted(files, reverse=True)}

@app.post("/api/delete-production")
def unpublish_file(
    filename: str = Form(...), 
    username: str = Form(...), 
    password: str = Form(...)
):
    """
    Canlı dosyayı SİLMEZ, TASLAK (Staging) klasörüne geri taşır.
    (Yayından kaldırma / Unpublish işlemi)
    """
    if not verify_user(username, password): 
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")
    
    prod_file = os.path.join(DATA_PATH, filename)
    staging_target = os.path.join(STAGING_PATH, filename)

    if os.path.exists(prod_file):
        try:
            # SİLME YERİNE TAŞIMA
            shutil.move(prod_file, staging_target)
            
            log_admin_action("unpublish", filename, username)
            
            # Chatbot'un (Port 8000) veritabanını yenilemesi için sinyal gönderiyoruz.
            try:
                requests.post(CHAT_API_URL, timeout=2)
            except:
                pass
                
            return {"message": f"'{filename}' yayından kaldırıldı ve taslağa taşındı."}
        except Exception as e:
            return JSONResponse(status_code=500, content={"detail": f"Taşıma hatası: {str(e)}"})
    
    return JSONResponse(status_code=404, content={"detail": "Dosya canlıda bulunamadı"})

# ==========================================================
# 7. DOSYA İŞLEME (PROCESS & INGEST)
# ==========================================================

@app.post("/api/process")
def process_file(
    background_tasks: BackgroundTasks,
    filename: str = Form(...), 
    username: str = Form(...), 
    password: str = Form(...)
):
    """
    1. Dosyayı Taslak -> Canlı (belgelerim) klasörüne taşır.
    2. Veritabanına işler (Ingest).
    3. Chat API'ye 'Yenilen' sinyali gönderir.
    """
    if not verify_user(username, password): 
        raise HTTPException(status_code=401, detail="Yetkisiz erişim")

    staging_file = os.path.join(STAGING_PATH, filename)
    prod_file = os.path.join(DATA_PATH, filename)

    if not os.path.exists(staging_file): 
        raise HTTPException(status_code=404, detail="Dosya taslaklarda bulunamadı.")

    try:
        # A. Dosyayı Taşı
        shutil.move(staging_file, prod_file)
        
        log_admin_action("process", filename, username)

        # B. Arkaplanda işlemleri başlat (Kullanıcıyı bekletmemek için)
        background_tasks.add_task(ingest_and_notify, prod_file)

        return {"message": f"'{filename}' onaylandı. İşleniyor..."}
    except Exception as e: 
        return JSONResponse(status_code=500, content={"detail": str(e)})

def ingest_and_notify(file_path):
    print(f"⚙️ Admin: İşleniyor -> {file_path}")
    success = ingest_new_file(file_path)
    if success:
        print(f"✅ Admin: Veritabanı güncellendi. Chat API ({CHAT_API_URL}) uyarılıyor...")
        try:
            # 2. Chat API'yi dürt (Webhook)
            r = requests.post(CHAT_API_URL, timeout=5)
            if r.status_code == 200:
                print("✅ Chat API başarıyla yenilendi.")
            else:
                print(f"⚠️ Chat API yenilenemedi: {r.status_code}")
        except Exception as e:
            print(f"❌ Chat API'ye ulaşılamadı (Kapalı olabilir): {e}")