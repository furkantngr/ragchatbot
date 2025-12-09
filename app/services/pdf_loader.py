import os
import fitz  # pymupdf
import re
from langchain_core.documents import Document

def clean_text(text):
    """
    Metni temizler.
    """
    if not text: return ""
    # 1. Satır sonu tirelerini birleştir
    text = re.sub(r'-\n', '', text)
    # 2. Gereksiz satır sonlarını boşluk yap
    text = re.sub(r'\n', ' ', text)
    # 3. Çoklu boşlukları teke indir
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def load_single_pdf(file_path):
    """Admin paneli için tek dosya okuyucu"""
    documents = []
    if not os.path.exists(file_path): return []
    
    try:
        doc = fitz.open(file_path)
        filename = os.path.basename(file_path)
        full_text = ""
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                full_text += text + " "
        
        cleaned = clean_text(full_text)
        if cleaned:
            documents.append(Document(page_content=cleaned, metadata={"source": filename, "page": 1}))
            
        doc.close()
    except: pass
    return documents

def load_pdfs_text_only(directory_path):
    """
    Klasördeki PDF'leri okur (DEBUG MODU AKTİF)
    """
    documents = []
    
    if not os.path.exists(directory_path):
        print(f"❌ Klasör bulunamadı: {directory_path}")
        return []

    pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("⚠️ Klasörde PDF dosyası yok.")
        return []

    print(f"✨ PDF Okuma Başlıyor: {len(pdf_files)} dosya...")

    total_pages = 0
    empty_files = 0

    for filename in pdf_files:
        file_path = os.path.join(directory_path, filename)
        try:
            doc = fitz.open(file_path)
            file_text_length = 0
            
            for page_num, page in enumerate(doc):
                # En basit okuma yöntemi (blocks yerine text)
                raw_text = page.get_text()
                
                # Temizle
                cleaned_text = clean_text(raw_text)
                
                # Eğer sayfa doluysa ekle
                if len(cleaned_text) > 10: # En az 10 karakter olsun
                    documents.append(Document(
                        page_content=cleaned_text, 
                        metadata={"source": filename, "page": page_num+1}
                    ))
                    file_text_length += len(cleaned_text)
                    total_pages += 1
            
            doc.close()
            
            # --- DEBUG ÇIKTISI ---
            if file_text_length > 0:
                print(f"   ✅ {filename}: {file_text_length} karakter okundu.")
            else:
                print(f"   ⚠️ {filename}: BOŞ! (Metin okunamadı - Resim olabilir)")
                empty_files += 1
                
        except Exception as e:
            print(f"   ❌ Hata ({filename}): {e}")
            
    print(f"📊 SONUÇ: {len(documents)} parça metin çıkarıldı. {empty_files} dosya boş görünüyor.")
    return documents