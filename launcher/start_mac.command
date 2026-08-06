#!/bin/bash
# Masaüstü başlatıcı (macOS) — çift tıklayınca sunucuyu başlatır ve arayüzü açar.
# .env varsa GERÇEK model, yoksa MOCK (ücretsiz) mod.
cd "$(dirname "$0")/.."

if [ ! -x ".venv/bin/python" ]; then
    echo "HATA: .venv bulunamadı. Önce kurulum: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    read -r -p "Kapatmak için Enter'a bas..."
    exit 1
fi

if [ -f ".env" ]; then unset MOCK_LLM; else export MOCK_LLM=1; fi

.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8501 &
sleep 4
open "http://localhost:8501"
wait
