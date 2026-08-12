"""Ortak parçalar: state, yardımcılar, sabitler. Tüm workflow bunları paylaşır."""
import os
import json
import re
import time
from typing import TypedDict

from dotenv import load_dotenv

# .env BURADA okunur: MOCK kararı anahtarın varlığına bakıyor ve bu modül,
# app.py/run.py içindeki load_dotenv() satırından ÖNCE içe aktarılıyor.
load_dotenv()

# Sahte ajanlar (ücretsiz, anahtarsız). MOCK_LLM=1 ile açıkça istenebilir; ayrıca
# ortamda OPENAI_API_KEY yoksa kendiliğinden devreye girer. Böylece anahtarsız bir
# kurulum (ör. herkese açık Spaces vitrini) ne çöker ne de kredi harcayabilir.
MOCK = os.getenv("MOCK_LLM") == "1" or not os.getenv("OPENAI_API_KEY")
if not MOCK:
    from agents import Runner

# Faz yapıları
PHASE2 = ["methodology", "benchmark", "risk"]
PHASE3_START = "environment"
PHASE4 = ["statistical", "ablation"]
PHASE5_START = "writing"

# =========================================================================
# PUANLAMA AĞIRLIKLARI — final puanı buradan ayarlarsın (fine-tuning tek yer).
# Her metrik 1-10 arası. Final = bu ağırlıklarla alınan ağırlıklı ortalama.
# Toplam 1.0 olmalı. Daha önemli metriğe daha yüksek ağırlık ver.
# =========================================================================
SCORE_WEIGHTS = {
    "relevance":   0.30,   # konuyla alaka — en önemli
    "venue":       0.20,   # yayınlandığı yerin sağlamlığı (Agent-2 ekler)
    "citations":   0.20,   # atıf sayısı
    "recency":     0.15,   # güncellik
    "repos":       0.10,   # kod/repo varlığı
    "future_work": 0.05,   # future-work uyumu
}

METRIC_LABELS = {
    "relevance": "Alaka", "venue": "Venue", "citations": "Atıf",
    "recency": "Güncellik", "repos": "Repo", "future_work": "Future work",
}


def _score_of(container: dict, key: str, default: int = 5) -> float:
    """container[key]['score'] — eksik/bozuk alanlarda default'a düşer.
    Gerçek modda model bir metriği atlayabilir; puanlama bu yüzden çökmemeli."""
    entry = (container or {}).get(key)
    if isinstance(entry, dict):
        val = entry.get("score", default)
    else:
        val = entry if entry is not None else default
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(default)


def compute_final(paper: dict) -> float:
    """Bir makalenin metrik puanlarından ağırlıklı final puanı (1-10) hesaplar."""
    scores = paper.get("scores", {})
    vals = {k: _score_of(scores, k) for k in SCORE_WEIGHTS if k != "venue"}
    vals["venue"] = _score_of(paper, "venue_score")
    total = sum(SCORE_WEIGHTS[k] * vals[k] for k in SCORE_WEIGHTS)
    return round(total, 1)


# =========================================================================
# PHASE-2 (yöntem) PUANLAMA — methodology önerileri için ayrı ağırlık şeması.
# Her öneri 3 metrikle (1-10) puanlanır; final = ağırlıklı ortalama.
# =========================================================================
METHOD_WEIGHTS = {
    "fit":                0.45,   # araştırma sorusuna uygunluk — en önemli
    "literature_support": 0.35,   # doğrulanmış literatürce desteklenme
    "maturity":           0.20,   # olgunluk / uygulama riski (yüksek = düşük risk)
}
METHOD_METRIC_LABELS = {
    "fit": "Uygunluk", "literature_support": "Literatür desteği", "maturity": "Olgunluk",
}


def compute_method_final(prop: dict) -> float:
    """Bir yöntem önerisinin 3 metrik puanından ağırlıklı final puanı hesaplar."""
    s = prop.get("scores", {})
    total = sum(METHOD_WEIGHTS[k] * _score_of(s, k) for k in METHOD_WEIGHTS)
    return round(total, 1)


# Bir workflow turu 15 ardışık API çağrısı yapar; tek bir geçici ağ hatası tüm turu
# düşürmemeli. Bağlantı/oran-sınırı hatalarında artan bekleme ile yeniden denenir.
_RETRIES = 3
_BACKOFF = 2.0


def _run_with_retry(agent, prompt):
    """Runner.run_sync — geçici hatalarda yeniden dener, son hatayı yükseltir."""
    last = None
    for attempt in range(_RETRIES):
        try:
            return Runner.run_sync(agent, prompt).final_output
        except Exception as e:
            name = type(e).__name__
            transient = ("Connection" in name or "Timeout" in name
                         or "RateLimit" in name or "InternalServer" in name
                         or "APIStatus" in name)
            if not transient or attempt == _RETRIES - 1:
                raise
            last = e
            wait = _BACKOFF * (2 ** attempt)
            print(f"[{agent.name}] {name} — {wait:.0f}s sonra yeniden deneniyor "
                  f"({attempt + 1}/{_RETRIES - 1})...")
            time.sleep(wait)
    raise last                                     # ulaşılmaz; güvenlik için


def run_agent(agent, prompt, mock_text):
    """Metin döndüren ajan çağrısı (text fazları için)."""
    if MOCK:
        return mock_text
    return _run_with_retry(agent, prompt)


# Ajanlar bazen düz liste yerine sarmalanmış JSON döndürür:
#   {"gaps": [...]}, {"papers": [...], "topic": "..."} gibi.
# Bu anahtarlar öncelikli olarak aranır; bulunamazsa en uzun sözlük listesi seçilir.
_LIST_KEYS = ("papers", "gaps", "proposals", "benchmarks", "risks",
              "results", "items", "data", "records", "list")


def normalize_list(data):
    """Ajan JSON çıktısını sözlük listesine normalize eder.
    -> list[dict]  (boş liste GEÇERLİ bir sonuçtur: 'hiçbiri kalmadı')
    -> None        (şekil tanınmadı; çağıran mock'a düşmeli)"""
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        for k in _LIST_KEYS:                       # bilinen sarmalayıcı anahtarlar
            v = data.get(k)
            if isinstance(v, list):
                return [d for d in v if isinstance(d, dict)]
        best = None                                # yoksa en uzun sözlük listesi
        for v in data.values():
            if isinstance(v, list):
                dicts = [d for d in v if isinstance(d, dict)]
                if dicts and (best is None or len(dicts) > len(best)):
                    best = dicts
        if best is not None:
            return best
        if data:                                   # tek kayıt döndürmüş olabilir
            return [data]
    return None


def run_agent_json(agent, prompt, mock_data):
    """JSON (yapısal veri) döndüren ajan çağrısı. MOCK'ta mock_data'yı döndürür;
    gerçek modda ajandan JSON ister, ayrıştırır ve sözlük listesine normalize eder.
    Ayrıştırma/normalizasyon başarısızsa mock_data'ya düşer."""
    if MOCK:
        return mock_data
    raw = _run_with_retry(agent, prompt + "\n\nSADECE geçerli JSON döndür, başka metin yazma.")
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
    except Exception:
        return mock_data
    normalized = normalize_list(parsed)
    return mock_data if normalized is None else normalized


def parse_decision(raw):
    """Kararı çözer → (action, note, agents).
    raw bir sözlük olabilir (arayüzden: {action, note, agents}) veya metin (CLI'dan)."""
    if isinstance(raw, dict):
        return raw.get("action", "onayla"), raw.get("note", ""), raw.get("agents")
    raw = (raw or "").strip()
    low = raw.lower()
    if low.startswith("tekrarla"):
        return "tekrarla", (raw.split(":", 1)[1].strip() if ":" in raw else ""), None
    if low.startswith("geri"):
        return "geri", (raw.split(":", 1)[1].strip() if ":" in raw else ""), None
    return "onayla", (raw.split(":", 1)[1].strip() if ":" in raw else raw), None


# =========================================================================
# İNCELİKLİ GERİ DÖNÜŞ: her fazın ajan sırası + 'tekrarla'da nereden başlanacağı.
# Kural: seçilen EN ERKEN ajandan itibaren faz yeniden akar (zincir bağımlılığı).
# Paralel fazlarda seçilen ajanların hepsi (liste) yeniden çalışır.
# =========================================================================
PHASE_ORDER = {
    "gate1": ["literature", "verification", "gap"],          # ardışık
    "gate2": ["methodology", "benchmark", "risk"],           # paralel
    "gate3": ["environment", "rl_coding", "training", "testing"],  # ardışık
    "gate4": ["statistical", "ablation", "critic"],          # karma (stat∥ablation → critic)
    "gate5": ["writing", "review"],                          # ardışık
}
SEQUENTIAL_GATES = {"gate1", "gate3", "gate5"}


def repeat_entry(gate, selected):
    """Seçilen ajanlara göre yeniden-başlama hedefini döndürür (str veya liste)."""
    order = PHASE_ORDER[gate]
    sel = [a for a in order if a in (selected or [])]
    if not sel:                                   # seçim yok → tüm faz
        if gate == "gate2":
            return order[:]                       # tüm paralel ajanlar
        if gate == "gate4":
            return ["statistical", "ablation"]    # critic bunlardan sonra otomatik
        return order[0]                           # ardışık: baştan
    if gate in SEQUENTIAL_GATES:
        return sel[0]                             # en erken; zincir gerisini taşır
    if gate == "gate2":
        return sel                                # seçilen paralel alt küme
    # gate4: stat/ablation seçiliyse onlar (critic downstream); değilse critic
    parents = [a for a in sel if a in ("statistical", "ablation")]
    return parents if parents else ["critic"]


def with_feedback(base, feedback):
    if feedback:
        return f"{base}\n\n[İNSAN GERİ BİLDİRİMİ — buna göre düzelt]: {feedback}"
    return base


class ResearchState(TypedDict, total=False):
    topic: str
    feedback: str
    repeat_target: object
    literature_output: str
    papers: list            # YAPISAL: puanlı makale listesi
    verification_output: str
    verification_summary: str
    gap_output: str
    gaps: list              # YAPISAL: puanlı boşluk listesi
    human_research_question: str
    gate1_action: str
    methodology_output: str
    proposals: list        # YAPISAL: puanlı yöntem önerileri
    benchmark_output: str
    benchmarks: list       # YAPISAL: puanlı baseline/metrik
    risk_output: str
    risks: list            # YAPISAL: risk matrisi
    gate2_action: str
    environment_output: str
    rl_coding_output: str
    training_output: str
    testing_output: str
    gate3_action: str
    phase3_run: int
    training_results: str
    statistical_output: str
    ablation_output: str
    critic_output: str
    gate4_action: str
    writing_output: str
    review_output: str
    gate5_action: str
    final_decision: str