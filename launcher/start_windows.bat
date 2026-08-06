@echo off
REM ============================================================
REM  Masaustu baslatici (Windows)
REM  - Sanal ortami kullanarak sunucuyu baslatir
REM  - .env varsa GERCEK model, yoksa MOCK (ucretsiz) mod
REM  - Arayuzu Edge "uygulama penceresi" olarak acar
REM ============================================================
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo HATA: .venv bulunamadi. Once kurulum yapin:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

if exist ".env" (set "MOCK_LLM=") else (set "MOCK_LLM=1")

start "" /B ".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8501

REM Sunucunun ayaga kalkmasini bekle
timeout /t 4 /nobreak >nul

REM Edge varsa kendi penceresinde (adres cubugu olmadan, uygulama gibi) ac;
REM yoksa varsayilan tarayicida ac.
set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
    start "" "%EDGE%" --app=http://localhost:8501
) else (
    start "" http://localhost:8501
)
