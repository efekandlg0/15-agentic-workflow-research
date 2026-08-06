# Kurulum Kılavuzu (macOS)

Bu projeyi sıfırdan bir Mac'e kurmak için adım adım rehber.
Daha önce hiç Python kullanmamış biri bile takip edebilir.

---

## 0. Önce neye ihtiyacın var?

- **Python 3.11 veya üstü** (proje 3.9'da ÇALIŞMAZ).
  Kontrol et: terminalde `python3 --version` yaz.
  3.11+ değilse → https://www.python.org/downloads/ adresinden indir ve kur.
- **VS Code** (zorunlu değil ama önerilir): https://code.visualstudio.com
- (Sadece gerçek model için) bir **OpenAI API anahtarı**. Mock modda gerekmez.

---

## 1. Proje dosyalarını yerleştir

Şu 5 dosya bir klasörde olmalı (örn. `agentic_research_starter`):

    agentic_research_starter/
    ├── run.py
    ├── graph.py
    ├── agents_def.py
    ├── requirements.txt
    └── README.md

> NOT: `.venv` klasörünü ASLA başka bilgisayardan kopyalama. O makineye özeldir.
> Yeni makinede aşağıdaki adımlarla sıfırdan oluşturulur.

---

## 2. Terminali doğru klasörde aç

En kolayı: VS Code'da `File → Open Folder` ile klasörü aç, sonra `Terminal → New Terminal`.
Terminalde `ls` yazınca `run.py`, `requirements.txt` vb. görünmeli.

---

## 3. Sanal ortam (venv) oluştur ve aktive et

```bash
# Python 3.14 kuruluysa (3.11+ olan komutu kullan):
python3.14 -m venv .venv

# Aktive et:
source .venv/bin/activate
```

Başarılıysa satır başında **(.venv)** belirir. Her yeni terminalde sadece bu
aktivasyon komutunu tekrarlaman yeter (venv'i bir kez kurarsın).

---

## 4. Kütüphaneleri kur

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

`Successfully installed ...` ile bitmeli. (pip sürüm uyarısı zararsızdır.)

---

## 5. Çalıştır

### A) Mock modu — API anahtarı GEREKMEZ, ücretsiz
```bash
MOCK_LLM=1 python run.py
```
Ajanlar sahte cevap döndürür; GATE'ler, paralel akış ve insan duraklamaları gerçektir.
GATE'lerde program durur, senden girdi ister. Bir şey yazıp Enter'a bas.

### B) Gerçek model — API anahtarı GEREKİR
1. Proje klasöründe `.env` dosyası oluştur, içine:
   ```
   OPENAI_API_KEY=sk-...senin-anahtarın...
   ```
2. Çalıştır (MOCK_LLM olmadan):
   ```bash
   python run.py
   ```

---

## Sık karşılaşılan hatalar

| Hata | Sebep / Çözüm |
|------|----------------|
| `command not found: pip` | venv aktif değil → `source .venv/bin/activate` |
| `No module named 'dotenv'` (veya başka modül) | paketler kurulmamış → `pip install -r requirements.txt` |
| `TypeError: ... 'float \| None'` | Python sürümü çok eski (3.9) → 3.11+ ile venv'i yeniden kur |
| `No module named 'agents'` | klasörde `agents/` adlı alt klasör paketi gölgeliyor olabilir; ya da paket kurulmadı |
| Grafik GATE'te durmuyor | `graph.py`'de checkpointer eksik olabilir |

---

## Her şeyi sıfırlamak istersen

```bash
deactivate          # venv'i kapat (açıksa)
rm -rf .venv        # izole ortamı sil
# sonra 3. adımdan baştan kur
```

Kod dosyaların bundan etkilenmez; sadece kütüphane kutusu silinir.
