# Agentic Research Workflow — Başlangıç İskeleti

RL tabanlı bacaklı robot araştırması için **insan kontrollü (human-in-the-loop)** çok ajanlı workflow.

**Mimari karar:**
- **LangGraph** → workflow iskeleti: node'lar, GATE'ler (insan kontrolü), paralel dallar, state, kalıcılık.
- **OpenAI Agents SDK** → her node'un *içinde* çalışan ajan (`Agent` + `Runner`).
- **GATE'ler ajan değildir** → `interrupt()` çağıran ayrı LangGraph node'larıdır. İnsan, birinci sınıf bir karar düğümüdür.

Bu iskelet senin diyagramını birebir uygular:

```
literature  →  GATE-1 (insan)  →  ┌── methodology ──┐  →  GATE-2 (insan)  →  END
                                  └── benchmark ────┘
                                       (paralel)
```

---

## 1. Ortam Kurulumu (VS Code üzerinden)

### Gereksinimler
- Python **3.11+** (3.10 da çalışır)
- VS Code + **Python** eklentisi (Microsoft)
- Bir OpenAI API anahtarı

### Adımlar

**1.1** Bu klasörü VS Code'da aç: `File → Open Folder → agentic_research_starter`

**1.2** VS Code'da terminal aç (`Terminal → New Terminal`) ve sanal ortam (venv) oluştur:

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

> Terminal başında `(.venv)` görünmeli. VS Code sağ altta "select interpreter" sorarsa `.venv` içindekini seç.

**1.3** Bağımlılıkları kur:

```bash
pip install -r requirements.txt
```

**1.4** API anahtarını ayarla. Proje klasöründe `.env` dosyası oluştur:

```
OPENAI_API_KEY=sk-...buraya-kendi-anahtarın...
```

> `.env` dosyasını **asla** Git'e ekleme (`.gitignore`'a `.env` yaz).

---

## 2. Çalıştırma

```bash
python run.py
```

Program akışı:
1. **Literature Agent** çalışır, literatür özeti üretir.
2. Ekranda **GATE-1** belirir, durur ve senden araştırma sorusunu ister.
   Sen yazıp Enter'a basana kadar grafik **donmuş** halde bekler (state diske yazılı).
3. Senin girdiğin soruyla **Methodology** ve **Benchmark** ajanları **paralel** çalışır.
4. **GATE-2** belirir, iki öneriyi de gösterir, kararını ister.
5. Workflow tamamlanır.

---

## 3. Dosya Yapısı

| Dosya | Görevi |
|-------|--------|
| `agents_def.py` | OpenAI SDK ajan tanımları (Literature, Methodology, Benchmark) |
| `graph.py` | LangGraph workflow: node'lar, GATE'ler (`interrupt`), paralel fan-out/join |
| `run.py` | Sürücü: grafiği çalıştırır, interrupt yakalar, insan girdisini `Command(resume=...)` ile geri verir |
| `requirements.txt` | Bağımlılıklar |

---

## 4. İnsan Kontrolü Nasıl Çalışıyor? (Önemli)

GATE node'u şunu yapar:

```python
def gate1_node(state):
    karar = interrupt({                       # ← grafik BURADA donar, state diske yazılır
        "gate": "GATE-1",
        "mesaj": "Araştırma sorusunu belirle.",
        "literatur_ozeti": state["literature_output"],
    })
    return {"human_research_question": karar}  # ← resume'dan sonra devam eder
```

`run.py` içindeki sürücü döngüsü interrupt'ı yakalar, sana gösterir, cevabını alır ve
`Command(resume="senin cevabın")` ile grafiği kaldığı yerden devam ettirir.

> **Kritik kural:** `interrupt()` çağrısını **asla** `try/except` içine sarma — özel
> kesinti exception'ını yakalarsan grafik düzgün duraklamaz. Ayrıca `interrupt()` çağrıldığında
> node baştan yeniden çalışır, bu yüzden node içinde interrupt'tan önce ağır/yan etkili iş yapma.

---

## 5. 15 Ajana Genişletme

Bu iskelet 3 ajan + 2 GATE içeriyor. Tam workflow'a (15 ajan + 5 GATE) genişletmek için:

1. **`agents_def.py`** içine her ajanı (Agent Specification Sheet'lerine göre) ekle.
   Her ajanın `instructions`'ı kartındaki Rol + Amaç + Kısıtlar + Karar Yetkisi'ni içermeli.
2. **`graph.py`** içine her ajan için bir node, her faz sonuna bir GATE node ekle.
3. State'e (`ResearchState`) her ajanın çıktı alanını ekle.
4. Kenarları (edge) zincire göre bağla; paralel olanları fan-out/join ile kur
   (örn. Methodology ∥ Benchmark ∥ Risk → tek GATE'e).
5. Kalıcılık için `InMemorySaver` yerine `AsyncSqliteSaver` kullan
   (sunucu yeniden başlasa bile workflow hayatta kalır).

### Karar yetkisini koda dökmek
Her ajanın "veremez" kısıtları `instructions` içinde açıkça yazılmalı. Örn. Training Agent için:
`"Hiçbir koşulda seed seçme/eleme yapma. Tüm tohumları raporla. Başarısız run'ları gizleme."`
Bu, ajanı kart üzerindeki karar sınırına bağlar.

---

## 6. Sık Karşılaşılan Sorunlar

- `ModuleNotFoundError: No module named 'agents'` → proje klasöründe `agents/` adlı bir
  alt klasör varsa paketi gölgeler. Klasörü yeniden adlandır, venv'in aktif olduğundan emin ol.
- Grafik interrupt'ta donmuyor / sonsuz dönüyor → `compile(checkpointer=...)` unutulmuş olabilir.
  **Checkpointer olmadan interrupt çalışmaz.**
- Aynı `thread_id` ile tekrar çalıştırırsan eski state'ten devam eder; sıfırdan başlamak için
  yeni bir `thread_id` üret.
