# Proje Yapısı

Kod artık tek dosyada değil; mantıksal paketlere bölündü.

```
agentic_research_starter/
├── run.py                    # Komut satırı sürücüsü (CLI)
├── app.py                    # Streamlit web arayüzü
├── requirements.txt
├── README.md / KURULUM.md / YAPI.md
│
├── research_agents/          # 15 AJAN — faz faz
│   ├── __init__.py           # hepsini tek yerden dışa açar
│   ├── tools.py              # 8 GERÇEK araç — 12 ajan bunları kullanır:
│   │                         #   arama: search_crossref, search_arxiv, search_github
│   │                         #   doğrulama: crossref_lookup, arxiv_lookup
│   │                         #   veri: citation_count (Semantic Scholar)
│   │                         #   hesap: describe_sample, welch_t_test
│   ├── phase1.py             # literature, verification, gap  (ikisi araçlı)
│   ├── phase2.py             # methodology, benchmark, risk
│   ├── phase3.py             # environment, rl_coding, training, testing
│   ├── phase4.py             # statistical, ablation, critic
│   └── phase5.py             # writing, review
│
└── workflow/                 # AKIŞ — graph + mantık
    ├── __init__.py           # graph'ı dışa açar
    ├── common.py             # ResearchState, yardımcılar, faz sabitleri
    ├── nodes.py              # ajan node'ları (faz faz gruplu)
    ├── gates.py              # GATE node'ları + router'lar (insan kontrolü)
    └── graph.py              # MONTAJ: her şeyi bir akışta birleştirir
```

## Neden bu paket adları?

- **`research_agents/`** (NOT `agents/`): `agents` ismi OpenAI'nin kütüphanesine ait;
  yerel paketi öyle adlandırırsak çakışır. O yüzden `research_agents`.
- **`workflow/`**: akışın iskeleti. İçinde sorumluluklar ayrı dosyalarda:
  *ne ürettiği* (nodes), *insan kontrolü* (gates), *nasıl bağlandığı* (graph).

## Hangi dosyayı ne zaman düzenlersin?

| İstediğin | Düzenlenecek dosya |
|-----------|---------------------|
| Bir ajanın talimatını/çıktısını değiştir | `research_agents/phaseN.py` |
| Ajanlara yeni bir dış kaynak aracı ekle | `research_agents/tools.py` |
| Bir ajana hangi araçların verildiğini değiştir | `research_agents/phaseN.py` → `tools=[...]` |
| Arayüz görünümü / ajan kartları | `ui.py` |
| Bir node'un mock metnini / girdisini değiştir | `workflow/nodes.py` |
| GATE mesajını veya karar mantığını değiştir | `workflow/gates.py` |
| Akışı (sıra, paralel, döngü) değiştir | `workflow/graph.py` |
| State'e yeni alan ekle | `workflow/common.py` |

## Çalıştırma

```bash
# Komut satırı:
MOCK_LLM=1 python run.py

# Web arayüzü:
MOCK_LLM=1 streamlit run app.py     # tarayıcıda açılır (genelde localhost:8501)
```

Gerçek model için `MOCK_LLM=1` koymadan çalıştır (.env içinde OPENAI_API_KEY gerekir).
