from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os

# Modeller ve Servisler
from app.models.schemas import Question, Answer
from app.services.rag_service import initialize_rag, get_answer
from app.services.logging_service import init_db

# Frontend Dosyası
INDEX_HTML_PATH = "index.html"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Sunucu açılırken çalışacak işlemler.
    1. Log veritabanını (SQLite) hazırla.
    2. RAG sistemini (LLM, Embedding, ChromaDB) belleğe yükle.
    """
    print("--- CHAT SUNUCUSU BAŞLATILIYOR ---")
    init_db()
    initialize_rag()
    yield
    print("--- CHAT SUNUCUSU KAPATILIYOR ---")

# Uygulamayı Oluştur
app = FastAPI(title="Chat API (User)", version="4.0", lifespan=lifespan)

# CORS Ayarları (Tüm ağdan erişim için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. ANA SAYFA (HTML Arayüzü) ---
@app.get("/")
async def root():
    """
    Kullanıcı tarayıcıdan girdiğinde index.html dosyasını sunar.
    """
    if os.path.exists(INDEX_HTML_PATH):
        return FileResponse(INDEX_HTML_PATH)
    return {"error": "index.html dosyası bulunamadı. Lütfen dosya yolunu kontrol edin."}

# --- 2. SOHBET API (IP & MOD DESTEKLİ) ---
@app.post("/soru-sor", response_model=Answer)
async def ask(
    raw_request: Request,      # IP adresini yakalamak için ham istek
    body: Question,            # Soru verisi (query ve mode içerir)
    background_tasks: BackgroundTasks
):
    """
    Kullanıcı sorularını cevaplar.
    - query: Soru metni
    - mode: 'fast' veya 'thinking' (Düşünen mod)
    """
    # 1. IP Adresini Yakala
    client_ip = raw_request.client.host
    
    # (Opsiyonel) Proxy arkasındaysanız gerçek IP 'x-forwarded-for' başlığında olabilir:
    # forwarded = raw_request.headers.get("x-forwarded-for")
    # if forwarded:
    #     client_ip = forwarded.split(",")[0]

    # 2. Servise Soruyu, Modu ve IP'yi Gönder
    response_text = await get_answer(
        query=body.query, 
        mode=body.mode,       # <-- "Hızlı" veya "Düşünen" mod bilgisi
        ip_address=client_ip, # <-- Loglama için IP adresi
        background_tasks=background_tasks
    )
    
    return Answer(response=response_text)

# --- 3. YENİLEME SİNYALİ (Admin API Burayı Tetikler) ---
@app.post("/refresh-db")
async def refresh_database():
    """
    Veritabanı güncellendiğinde veya Prompt/Model değiştiğinde
    Admin API bu endpointi çağırarak sistemi canlı olarak yeniler.
    """
    try:
        print("📥 YENİLEME SİNYALİ ALINDI. RAG sistemi güncelleniyor...")
        
        # RAG sistemini (LLM, Promptlar, Vektör DB) yeniden başlat
        initialize_rag()
        
        return {"status": "success", "message": "RAG sistemi başarıyla yenilendi."}
    except Exception as e:
        print(f"❌ Yenileme Hatası: {e}")
        return {"status": "error", "message": str(e)}