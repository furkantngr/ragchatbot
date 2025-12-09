@echo off
echo AI Asistan Baslatiliyor...

:: Backend'i baslat (Yeni pencerede)
start "Backend API" cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Biraz bekle ki backend kendine gelsin
timeout /t 5

:: Frontend'i baslat (Yeni pencerede)
start "Frontend UI" cmd /k "streamlit run frontend/ui.py --server.address 0.0.0.0 --server.port 8501"

echo Sistem hazir! IP Adresinle erisebilirsin.
pause