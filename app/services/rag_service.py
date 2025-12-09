import os
import torch
from fastapi import BackgroundTasks
from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

# Config ve Servis Importları
# DİKKAT: İki ayrı prompt yolu import edildi
from app.core.config import CHAT_MODEL, CHROMA_PATH, LOCAL_EMBEDDING_PATH, DATA_PATH, APP_LINKS, PROMPT_FAST_PATH, PROMPT_THINKING_PATH
from app.services.pdf_loader import load_pdfs_text_only, load_single_pdf
from app.services.logging_service import log_conversation
from app.services.settings_service import get_current_model

# Global Değişkenler
rag_chain_fast = None      # Hızlı Mod Zinciri
rag_chain_thinking = None  # Düşünen Mod Zinciri
retriever = None
vectorstore = None
embeddings = None
current_active_model = None

def load_prompt_from_file(file_path, default_text):
    """
    Belirtilen dosyadan prompt metnini okur.
    Dosya yoksa varsayılan metni hem döner hem de dosyayı oluşturur.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    print(f"✅ Prompt yüklendi: {os.path.basename(file_path)}")
                    return content
        except Exception as e:
            print(f"❌ Hata ({file_path}): {e}")
    
    # Dosya yoksa varsayılanı oluştur (Admin panelinde boş görünmesin diye)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(default_text)
    except: pass
    
    return default_text

def initialize_rag():
    global rag_chain_fast, rag_chain_thinking, retriever, vectorstore, embeddings, current_active_model
    
    # Güncel modeli ayardan oku
    selected_model = get_current_model()
    current_active_model = selected_model
    
    print(f"🔄 RAG Sistemi başlatılıyor... Model: {selected_model}")

    # --- 1. DONANIM KONTROLÜ ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    gpu_name = torch.cuda.get_device_name(0) if device == "cuda" else "İşlemci"
    print(f"🚀 DONANIM: {gpu_name} (ID: {device.upper()}) AKTİF.")

    # --- 2. EMBEDDING MODELİ ---
    print("📚 Embedding modeli yükleniyor...")
    # HuggingFaceEmbeddings kullanıyoruz (Yerel Klasörden)
    model_kwargs = {'device': device}
    encode_kwargs = {'normalize_embeddings': True, 'batch_size': 32}
    
    embeddings = HuggingFaceEmbeddings(
        model_name=LOCAL_EMBEDDING_PATH,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

    # --- 3. VEKTÖR VERİTABANI ---
    if not os.path.exists(CHROMA_PATH):
        print(f"📂 Veritabanı ({CHROMA_PATH}) bulunamadı, sıfırdan oluşturuluyor...")
        docs = load_pdfs_text_only(DATA_PATH)
        if docs:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200, length_function=len)
            chunks = splitter.split_documents(docs)
            vectorstore = Chroma.from_documents(chunks, embedding=embeddings, persist_directory=CHROMA_PATH)
            print(f"✅ {len(chunks)} parça bilgi veritabanına işlendi.")
        else:
            print("⚠️ UYARI: Klasörde okunacak PDF bulunamadı. Boş veritabanı oluşturuluyor.")
            vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    else:
        print(f"💾 Mevcut veritabanı yükleniyor: {CHROMA_PATH}")
        vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    # --- 4. LLM AYARLARI ---
    print(f"🤖 Sohbet Modeli: {selected_model}")
    llm = OllamaLLM(
        model=selected_model,
        temperature=0.1,
        num_gpu=-1,       
        num_ctx=4096,     
        num_thread=8      
    )

    # --- 5. PROMPTLAR (İKİ AYRI MOD İÇİN) ---
    
    # A. Hızlı Mod Varsayılanı
    default_fast = """Sen kurumsal bir asistansın. Görevin sadece bilgi vermektir.
    Sadece aşağıdaki 'Bağlam' içindeki bilgileri kullan.
    Cevaba doğrudan başla. Kısa, net ve öz ol.
    
    Bağlam: {context}
    Soru: {question}
    Cevap:"""

    # B. Düşünen Mod Varsayılanı
    default_thinking = """Sen kıdemli bir analist ve kurumsal danışmansın.
    Görevin:
    1. Aşağıdaki 'Bağlam' bilgisini detaylıca analiz et.
    2. Soruyu cevaplamadan önce, bağlamdaki bilgilerin soruyla ilişkisini kur.
    3. Adım adım düşün ve detaylı, kapsamlı bir açıklama yap.
    4. Eğer varsa, prosedürleri madde madde açıkla.

    Bağlam (Dokümanlar):
    {context}

    Soru:
    {question}

    Detaylı Analiz ve Cevap:"""

    # Dosyalardan Yükle
    text_fast = load_prompt_from_file(PROMPT_FAST_PATH, default_fast)
    text_thinking = load_prompt_from_file(PROMPT_THINKING_PATH, default_thinking)

    prompt_fast = ChatPromptTemplate.from_template(text_fast)
    prompt_thinking = ChatPromptTemplate.from_template(text_thinking)

    # --- 6. ZİNCİRLERİ OLUŞTUR ---
    
    # Zincir 1: Hızlı (Fast)
    rag_chain_fast = (
        {
            "question": lambda x: x["question"],
            "context": lambda x: _get_context_with_links(x["question"])
        } 
        | prompt_fast 
        | llm 
        | StrOutputParser()
    )

    # Zincir 2: Düşünen (Thinking)
    rag_chain_thinking = (
        {
            "question": lambda x: x["question"],
            "context": lambda x: _get_context_with_links(x["question"])
        } 
        | prompt_thinking 
        | llm 
        | StrOutputParser()
    )
    
    print("⚡ RAG Sistemi Hazır (Çift Modlu)!")

def _get_context_with_links(query):
    # Link Enjeksiyonu
    injected_links = ""
    query_lower = query.lower()
    found_links = []
    
    for app_name, link in APP_LINKS.items():
        if app_name in query_lower:
            found_links.append(f"- {app_name.upper()} Erişim Linki: {link}")
    
    if found_links:
        injected_links = "\n\n[SİSTEM TARAFINDAN BULUNAN ERİŞİM LİNKLERİ]:\n" + "\n".join(found_links) + "\n(Kullanıcıya bu linki vererek cevapla.)\n"

    # PDF Araması
    docs = retriever.invoke(query)
    
    # Debug Çıktısı
    print("\n" + "="*40)
    print(f"🔍 SORU: {query}")
    if found_links: print(f"🔗 BULUNAN LİNKLER: {found_links}")
    print(f"📄 PDF PARÇASI: {len(docs)}")
    for i, doc in enumerate(docs):
        src = os.path.basename(doc.metadata.get('source', 'Bilinmiyor'))
        print(f"   [{i+1}] {src}")
    print("="*40 + "\n")

    pdf_context = "\n\n".join([d.page_content for d in docs])
    return pdf_context + injected_links

# --- ADMIN: CANLI BELGE EKLEME ---
def ingest_new_file(file_path):
    global vectorstore, embeddings
    if not vectorstore: initialize_rag()

    print(f"🔄 Yeni dosya işleniyor: {file_path}")
    new_docs = load_single_pdf(file_path)
    
    if new_docs:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200, length_function=len)
        chunks = splitter.split_documents(new_docs)
        vectorstore.add_documents(chunks)
        print(f"✅ Eklendi.")
        return True
    return False

# --- KULLANICI: CEVAP ÜRETME (MOD SEÇİMLİ) ---
async def get_answer(query: str, mode: str, ip_address: str, background_tasks: BackgroundTasks):
    """
    Mode parametresine göre ('fast' veya 'thinking') ilgili zinciri çalıştırır.
    """
    if not rag_chain_fast: return "Sistem hazırlanıyor..."
    
    # Zincir Seçimi
    if mode == "thinking":
        chain = rag_chain_thinking
        log_context = "PDF (Thinking Mode)"
    else:
        chain = rag_chain_fast
        log_context = "PDF (Fast Mode)"
    
    # Çalıştır
    response = await chain.ainvoke({"question": query})
    
    # Asenkron Loglama
    background_tasks.add_task(
        log_conversation,
        query=query,
        response=response,
        context=log_context, 
        model=current_active_model,
        ip_address=ip_address
    )
    
    return response