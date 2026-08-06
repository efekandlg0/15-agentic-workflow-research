"""Ajan node'ları. PHASE-1 yapısal (puanlı) veri üretir; diğer fazlar metin."""
import json

from research_agents import (
    literature_agent, verification_agent, gap_agent,
    methodology_agent, benchmark_agent, risk_agent,
    environment_agent, rl_coding_agent, training_agent, testing_agent,
    statistical_agent, ablation_agent, critic_agent,
    writing_agent, review_agent,
)
from .common import run_agent, run_agent_json, with_feedback as _fb, compute_final, compute_method_final


# ======================= PHASE-1 (yapısal + puanlı) =======================

# MOCK örnek makaleler — gerçek modda ajan JSON üretir, bunlar yedek.
_MOCK_PAPERS = [
    {
        "id": "p1",
        "title": "Wheel-legged locomotion with hierarchical reinforcement learning",
        "authors": "Lee, Park et al.", "year": 2023, "venue": "arXiv (preprint)",
        "doi": "arXiv:2310.01234",
        "scores": {
            "recency":   {"score": 10, "reason": "2023 — çok güncel; alandaki en yeni yaklaşımları içeriyor."},
            "relevance": {"score": 9,  "reason": "Başlıkta hem 'wheel-legged' hem 'RL' geçiyor; konu kesişimi birebir."},
            "citations": {"score": 4,  "reason": "~15 atıf (tahmini); yeni olduğu için düşük."},
            "repos":     {"score": 7,  "reason": "GitHub'da 1 resmi repo, ~250 yıldız (tahmini)."},
            "future_work": {"score": 8, "reason": "Future-work bölümünde enerji-farkında kontrol öneriliyor — konumuzla uyumlu."},
        },
    },
    {
        "id": "p2",
        "title": "Energy-efficient quadrupedal locomotion via soft actor-critic",
        "authors": "Yang, Zhang et al.", "year": 2022, "venue": "IEEE RA-L",
        "doi": "arXiv:2204.01906",
        "scores": {
            "recency":   {"score": 8, "reason": "2022 — güncel."},
            "relevance": {"score": 7, "reason": "Enerji + RL var ama 'quadruped'; wheel-legged değil — kısmi kesişim."},
            "citations": {"score": 7, "reason": "~60 atıf (tahmini); alanında iyi."},
            "repos":     {"score": 6, "reason": "Bir topluluk repo'su mevcut."},
            "future_work": {"score": 6, "reason": "Future-work'te terrain genelleme var; enerji-MARL yok."},
        },
    },
    {
        "id": "p3",
        "title": "Learning agile and dynamic motor skills for legged robots",
        "authors": "Hwangbo et al.", "year": 2019, "venue": "Science Robotics",
        "doi": "10.1126/scirobotics.aau5872",
        "scores": {
            "recency":   {"score": 5, "reason": "2019 — temel ama görece eski."},
            "relevance": {"score": 6, "reason": "Temel RL locomotion; wheel ve enerji odağı yok — daha uzak."},
            "citations": {"score": 10, "reason": "1500+ atıf; alanın temel taşı."},
            "repos":     {"score": 8, "reason": "Yaygın kullanılan resmi kod tabanı."},
            "future_work": {"score": 5, "reason": "Future-work genel; konumuza dolaylı değiniyor."},
        },
    },
]

# Agent-2'nin ekleyeceği venue puanları (mock).
_MOCK_VENUE = {
    "p1": {"score": 6,  "reason": "arXiv preprint — hakem denetimi yok ama alanda yaygın."},
    "p2": {"score": 9,  "reason": "IEEE RA-L — güçlü, hakemli robotik dergisi."},
    "p3": {"score": 10, "reason": "Science Robotics — alanın en prestijli yerlerinden."},
}

_MOCK_GAPS = [
    {
        "id": "B1",
        "title": "Wheel-legged platformlarda enerji-verimli RL eksikliği",
        "score": {"score": 9, "reason": "Doğrulanmış kaynakların hiçbiri wheel-legged + enerji kesişimini işlemiyor; net açık."},
        "evidence": "Yang 2022 ve Hwangbo 2019 yalnızca quadruped/bacaklı; wheel-legged + enerji kombinasyonu yok.",
        "future_work_check": "Lee 2023'ün future-work'ü enerji-farkında kontrole değiniyor ama MARL ile değil.",
        "candidate_question": "Wheel-legged quadruped'lerde MARL ile enerji-verimli hareket kontrolü",
    },
    {
        "id": "B2",
        "title": "Sim-to-real transferinde enerji metriği ölçülmüyor",
        "score": {"score": 7, "reason": "Bazı çalışmalar sim-to-real yapıyor ama Cost of Transport raporlamıyor; kısmen açık."},
        "evidence": "Hwangbo 2019 sim-to-real başarıyor fakat enerji (CoT) metriği raporlamıyor.",
        "future_work_check": "İncelenen makalelerin future-work bölümlerinde enerji ölçümü açıkça hedeflenmemiş.",
        "candidate_question": "Enerji-farkında ödül tasarımının sim-to-real transferine etkisi",
    },
    {
        "id": "B3",
        "title": "AI önerisi: terrain-uyarlamalı enerji bütçesi",
        "score": {"score": 5, "reason": "Literatürde doğrudan kanıt zayıf; bu bir AI türevi öneri, temkinli."},
        "evidence": "AI önerisi: doğrudan kaynak yok; B1+B2'den türetildi.",
        "future_work_check": "—",
        "candidate_question": "Terrain zorluğuna göre dinamik enerji bütçesi ayarlayan RL kontrolü",
    },
]


def literature_node(state):
    papers = run_agent_json(
        literature_agent,
        _fb(f"Araştırma konusu: {state['topic']}", state.get("feedback", "")),
        _MOCK_PAPERS,
    )
    # Gerçek modda ajan id atlayabilir → sonraki node'lar id ile eşleştirdiği için garanti altına al.
    papers = [dict(p) for p in papers if isinstance(p, dict)]
    for i, p in enumerate(papers):
        p.setdefault("id", f"p{i+1}")
    # CLI için kısa metin özeti
    lines = [f"[{p['id']}] {p.get('title','(başlık yok)')} "
             f"({p.get('year','—')}, {p.get('venue','—')})" for p in papers]
    return {"papers": papers, "literature_output": "Puanlı literatür:\n" + "\n".join(lines)}


def _apply_mock_verification(papers):
    """MOCK yedeği: sabit doğrulama durumu + _MOCK_VENUE'dan venue puanı."""
    out = []
    for p in papers:
        q = dict(p)
        q["verification"] = {"status": "doğrulandı", "reason": "DOI/arXiv kaydı eşleşti (mock)."}
        q["venue_score"] = _MOCK_VENUE.get(p["id"], {"score": 5, "reason": "venue bilinmiyor."})
        out.append(q)
    return out


def verification_node(state):
    papers = [dict(p) for p in state.get("papers", [])]
    if not papers:
        return {"papers": [], "verification_output": "Doğrulanacak kaynak yok.",
                "verification_summary": "Doğrulanacak kaynak yok."}

    # Agent-2 gerçek modda crossref_lookup/arxiv_lookup araçlarıyla GERÇEK doğrulama yapar;
    # MOCK'ta yedek veri kullanılır. Ajandan yalnızca verification + venue_score isteriz —
    # 5 metrik puanı Agent-1'e ait, o yüzden çıktıyı orijinal kayda id ile BİRLEŞTİRİRİZ.
    fallback = _apply_mock_verification(papers)
    judged = run_agent_json(
        verification_agent,
        _fb("Aşağıdaki makaleleri araçlarınla DOI/arXiv üzerinden doğrula ve her birine "
            "venue puanı ver.\nHer kayıt için SADECE şu alanları döndür: "
            '{"id", "verification": {"status","reason"}, "venue_score": {"score":1-10,"reason"}}. '
            "SADECE status='bulunamadı' olanları listeden çıkar; diğerlerini listede tut.\n\n"
            "MAKALELER:\n" + json.dumps(papers, ensure_ascii=False),
            state.get("feedback", "")),
        fallback,
    )

    # judged is fallback  ->  MOCK modu veya ajan çıktısı ayrıştırılamadı.
    # Aksi halde ajanın kararına saygı duyarız: boş liste = "hepsi uydurma çıktı" demektir,
    # bu durumda yedeğe DÖNMEYİZ (yoksa doğrulanmamış kayıtlar 'doğrulandı' diye geri gelir).
    if judged is fallback:
        merged = fallback
    else:
        by_id = {str(p["id"]): p for p in papers}
        merged = []
        for item in judged if isinstance(judged, list) else []:
            if not isinstance(item, dict):
                continue
            base = by_id.get(str(item.get("id")))
            if base is None:                   # ajan bilinmeyen id uydurduysa atla
                continue
            q = dict(base)
            q["verification"] = item.get("verification") or {
                "status": "belirsiz", "reason": "Ajan doğrulama durumu döndürmedi."}
            q["venue_score"] = item.get("venue_score") or {
                "score": 5, "reason": "Ajan venue puanı döndürmedi."}
            merged.append(q)

    for p in merged:
        # Final puan: Python deterministik hesaplar (SCORE_WEIGHTS)
        p["final_score"] = compute_final(p)
    merged.sort(key=lambda x: x["final_score"], reverse=True)

    dropped = len(papers) - len(merged)
    if not merged:
        msg = (f"Doğrulama sonucu: {len(papers)} kaynağın hiçbiri doğrulanamadı "
               "(DOI/arXiv kaydı bulunamadı). Literature Search Agent'ı 'tekrarla' ile "
               "yeniden çalıştırıp gerçek DOI'li kaynaklar istemelisin.")
        return {"papers": [], "verification_output": msg, "verification_summary": msg}
    summary = "Doğrulama + venue puanı eklendi; final puanlar hesaplandı.\n" + \
              "\n".join(f"{p['id']}: final {p['final_score']}/10 "
                        f"({p.get('venue','—')}) · {p.get('verification',{}).get('status','—')}"
                        for p in merged)
    if dropped > 0:
        summary += f"\n({dropped} kayıt doğrulanamadığı için çıkarıldı.)"
    return {"papers": merged, "verification_output": summary, "verification_summary": summary}


def gap_node(state):
    gaps = run_agent_json(
        gap_agent,
        _fb("Doğrulanmış literatüre göre puanlı boşlukları çıkar.", state.get("feedback", "")),
        _MOCK_GAPS,
    )
    lines = [f"{g.get('id','B?')} ({g.get('score',{}).get('score','-')}/10): "
             f"{g.get('title','(başlık yok)')}" for g in gaps]
    return {"gaps": gaps, "gap_output": "Puanlı boşluklar:\n" + "\n".join(lines)}


# ======================= PHASE-2 (yapısal + puanlı + kaynak etiketli) =======================
_MOCK_PROPOSALS = [
    {"id": "M1", "component": "Mimari", "choice": "Hiyerarşik MARL (bacak + tekerlek ayrı politika)",
     "reason": "Bacak ve tekerlek farklı dinamiklere sahip; ayrı politikalar koordinasyonu ve enerji "
               "paylaşımını kolaylaştırır (B1 boşluğuna yanıt).",
     "alternative": "Tek-ajan PPO — daha basit ama modlar arası koordinasyon zayıf.",
     "source": "literatür-temelli",
     "scores": {"fit": {"score": 9, "reason": "wheel-legged ayrımına birebir uyuyor"},
                "literature_support": {"score": 7, "reason": "MARL locomotion örnekleri var; wheel-legged'e tam örnek sınırlı"},
                "maturity": {"score": 6, "reason": "hiyerarşik MARL görece yeni; uygulama riski orta"}}},
    {"id": "M2", "component": "Algoritma", "choice": "PPO",
     "reason": "On-policy, stabil; bacaklı locomotion'da güçlü kanıt (Hwangbo 2019).",
     "alternative": "SAC — örnek-verimli ama ayar hassasiyeti yüksek.",
     "source": "literatür-temelli",
     "scores": {"fit": {"score": 8, "reason": "sürekli kontrol + stabilite ihtiyacına uygun"},
                "literature_support": {"score": 9, "reason": "çok sayıda doğrulanmış locomotion çalışması PPO kullanıyor"},
                "maturity": {"score": 9, "reason": "olgun, yaygın, iyi anlaşılmış"}}},
    {"id": "M3", "component": "Ödül", "choice": "ilerleme(+) + stabilite(+) + enerji cezası(−)",
     "reason": "Enerji verimliliği birincil hedef; ceza terimi Cost of Transport'u doğrudan optimize eder.",
     "alternative": "Yalnız ilerleme ödülü — enerjiyi göz ardı eder, hedefe aykırı.",
     "source": "literatür-temelli",
     "scores": {"fit": {"score": 10, "reason": "araştırma sorusunun çekirdeği enerji; ödül bunu hedefliyor"},
                "literature_support": {"score": 6, "reason": "enerji cezası bazı çalışmalarda var ama standart değil"},
                "maturity": {"score": 7, "reason": "ödül şekillendirme bilinen bir teknik"}}},
    {"id": "M4", "component": "Gözlem uzayı", "choice": "propriyosepsiyon + yerel terrain yükseklik haritası",
     "reason": "AI ÖNERİSİ: terrain haritası engebeli arazide öngörülü kontrolü güçlendirebilir; "
               "doğrudan literatür kanıtı sınırlı, B1+B2'den türetilmiş bir öneri.",
     "alternative": "Yalnız propriyoseptif gözlem — daha basit, sim-to-real'de daha sağlam.",
     "source": "AI önerisi",
     "scores": {"fit": {"score": 7, "reason": "engebeli arazi hedefine uygun"},
                "literature_support": {"score": 4, "reason": "yerel yükseklik haritası faydası çalışmalarda karışık"},
                "maturity": {"score": 5, "reason": "sim-to-real'de harita gürültüsü risk yaratır"}}},
]

_MOCK_BENCHMARKS = [
    {"id": "BL1", "kind": "baseline", "choice": "Saf PPO (enerji terimi yok)",
     "reason": "yöntemin enerji katkısını izole etmek için", "source": "literatür-temelli",
     "score": {"score": 9, "reason": "en adil temel; yalnızca ödül farkı"}},
    {"id": "BL2", "kind": "baseline", "choice": "MPC (model-tabanlı kontrol)",
     "reason": "klasik kontrol paradigmasıyla karşılaştırma", "source": "literatür-temelli",
     "score": {"score": 7, "reason": "güçlü ama farklı paradigma; adil ayarı zor"}},
    {"id": "MT1", "kind": "metrik", "choice": "Cost of Transport (birincil)",
     "reason": "enerji verimliliğinin doğrudan ölçüsü", "source": "literatür-temelli",
     "score": {"score": 10, "reason": "araştırma sorusunun ana metriği"}},
    {"id": "MT2", "kind": "metrik", "choice": "Başarı oranı + devrilme oranı",
     "reason": "kontrol kalitesi ve güvenlik", "source": "literatür-temelli",
     "score": {"score": 8, "reason": "standart locomotion metrikleri"}},
    {"id": "MT3", "kind": "metrik", "choice": "Enerji-başarı Pareto eğrisi",
     "reason": "AI ÖNERİSİ: enerji-başarı ödünleşimini tek grafikte göstermek analizi güçlendirir",
     "source": "AI önerisi", "score": {"score": 6, "reason": "faydalı görselleştirme ama zorunlu değil"}},
]

_MOCK_RISKS = [
    {"id": "R1", "risk": "Sim-to-real boşluğu", "level": "KRİTİK",
     "reason": "enerji-optimize politika simülasyon eserlerine aşırı uyabilir",
     "mitigation": "domain randomization + gerçek robotta doğrulama", "source": "literatür-temelli"},
    {"id": "R2", "risk": "Tek terrain'e overfitting", "level": "orta-yüksek",
     "reason": "dar terrain dağılımı genellemeyi bozar",
     "mitigation": "terrain curriculum + çeşitlilik", "source": "literatür-temelli"},
    {"id": "R3", "risk": "Enerji cezası hareketi durdurabilir", "level": "orta",
     "reason": "AI ÖNERİSİ: aşırı enerji cezası ajanı hareketsizliğe (yerel minimum) itebilir",
     "mitigation": "ceza ağırlığını kademeli artır (curriculum)", "source": "AI önerisi"},
]


def methodology_node(state):
    props = run_agent_json(methodology_agent,
        _fb(f"Onaylanan soru: {state['human_research_question']}", state.get("feedback", "")),
        _MOCK_PROPOSALS)
    props = [dict(p) for p in props if isinstance(p, dict)]
    for i, p in enumerate(props):
        p.setdefault("id", f"M{i+1}")
        p["final_score"] = compute_method_final(p)
    props.sort(key=lambda x: x["final_score"], reverse=True)
    lines = [f"{p['id']} {p['final_score']}/10 · {p.get('component','—')}: "
             f"{p.get('choice','—')} [{p.get('source','—')}]" for p in props]
    return {"proposals": props, "methodology_output": "Puanlı yöntem önerileri:\n" + "\n".join(lines)}


def benchmark_node(state):
    items = run_agent_json(benchmark_agent,
        _fb(f"Onaylanan soru: {state['human_research_question']}", state.get("feedback", "")),
        _MOCK_BENCHMARKS)
    lines = [f"[{b.get('kind','—')}] {b.get('choice','—')} "
             f"({b.get('score',{}).get('score','-')}/10) [{b.get('source','—')}]" for b in items]
    return {"benchmarks": items, "benchmark_output": "Benchmark önerileri:\n" + "\n".join(lines)}


def risk_node(state):
    items = run_agent_json(risk_agent,
        _fb(f"Riskleri analiz et: {state['human_research_question']}", state.get("feedback", "")),
        _MOCK_RISKS)
    lines = [f"{r.get('risk','—')} — {r.get('level','—')} [{r.get('source','—')}]" for r in items]
    return {"risks": items, "risk_output": "Risk matrisi:\n" + "\n".join(lines)}


# ======================= PHASE-3 (gerekçeli + yöntemden türetilmiş + tekrarda değişken) =======================
# Değişkenlik: her Phase-3 çalıştırmasında 'phase3_run' sayacı artar; varyant onunla seçilir.
# → 'tekrarla' her seferinde FARKLI bir öneri gösterir (gerçek yeniden-çalıştırma hissi).
# Gerçek modda bu varyasyonu modelin kendisi + geri bildirim üretir.

def _fbnote(state):
    fb = state.get("feedback", "")
    return f"\n(↻ geri bildirim işlendi: {fb})" if fb else ""


_SIMS = ["IsaacLab", "MuJoCo", "PyBullet"]
_TERRAINS = ["rampa + basamak + rastgele engebe",
             "eğimli zemin + düşük sürtünme yamaları",
             "merdiven + boşluk (gap) + engebeli arazi"]
_REWARDS = ["ilerleme(+) + stabilite(+) + enerji cezası(−)",
            "ilerleme(+) + enerji cezası(−) + eylem-yumuşaklığı(−)",
            "hız-takibi(+) + stabilite(+) + Cost-of-Transport(−)"]
_LRS = ["3e-4", "1e-4", "5e-4"]
_SEEDS = [5, 3, 8]
_STEPS = ["50M", "20M", "100M"]
_SCENARIOS = ["yeni terrain + sensör gürültüsü + push-recovery",
              "görülmemiş eğim + rüzgar bozması + yük değişimi",
              "düşük sürtünme + eklem gecikmesi + kısmi sensör arızası"]


def environment_node(state):
    run = state.get("phase3_run", 0) + 1          # bu Phase-3 turunu say
    i = run % 3
    method = state.get("methodology_output", "")
    out = run_agent(environment_agent,
        _fb(f"Onaylanan yönteme göre ortam türet.\nYöntem: {method}\n"
            f"Soru: {state.get('human_research_question','')}", state.get("feedback", "")),
        f"[MOCK] ORTAM KURULUMU (yönteme göre türetildi · tur {run})\n"
        f"• Simülatör: {_SIMS[i]}\n  NEDEN: yöntem GPU-hızlandırmalı paralel ortam gerektiriyor.\n"
        f"• Terrain: {_TERRAINS[i]}\n  NEDEN: araştırma sorusu engebeli arazi dayanıklılığı içeriyor.\n"
        f"• Robot modeli: wheel-legged URDF — doğrulama (kütle/atalet, eklem limitleri) TAMAM.\n"
        f"• UYGULANABİLİRLİK: Yönteminiz gerçek simülasyon gerektirmiyorsa bu adım atlanabilir."
        + _fbnote(state))
    return {"environment_output": out, "phase3_run": run}


def rl_coding_node(state):
    i = state.get("phase3_run", 1) % 3
    method = state.get("methodology_output", "")
    out = run_agent(rl_coding_agent,
        _fb(f"Onaylanan algoritmaya göre kod planı türet.\nYöntem: {method}", state.get("feedback", "")),
        f"[MOCK] RL KOD PLANI (algoritmaya göre)\n"
        f"• Eğitim döngüsü: PPO, vektörel ortam.\n  NEDEN: Phase-2'de onaylanan algoritma PPO.\n"
        f"• Ödül terimleri: {_REWARDS[i]}\n  NEDEN: araştırma sorusunun çekirdeği enerji verimliliği.\n"
        f"• Logging: seed başına checkpoint + öğrenme eğrisi + hiperparametre.\n"
        f"  NEDEN: tekrarlanabilirlik ve tam provenans için."
        + _fbnote(state))
    return {"rl_coding_output": out}


def training_node(state):
    i = state.get("phase3_run", 1) % 3
    out = run_agent(training_agent,
        _fb(f"Onaylanan yöntemin doğasına göre eğitim paketi + plan türet.\n"
            f"Araştırma sorusu: {state.get('human_research_question','')}\n"
            f"Onaylanan yöntem:\n{state.get('methodology_output','')}\n"
            f"Kod planı:\n{state.get('rl_coding_output','')}\n"
            f"Ortam:\n{state.get('environment_output','')}",
            state.get("feedback", "")),
        f"[MOCK] EĞİTİM PAKETİ + PLAN (yönteme göre uyarlandı)\n"
        f"• Hiperparametre: lr={_LRS[i]}, batch=4096, {_STEPS[i]} adım.\n"
        f"  NEDEN: PPO için stabil aralık; yöntemin on-policy doğasına uygun.\n"
        f"• {_SEEDS[i]} SEED (hepsi raporlanacak).\n"
        f"  NEDEN: istatistiksel anlamlılık için tekrar; cherry-pick YOK.\n"
        f"• UYGULANABİLİRLİK: Yönteminiz eğitim gerektirmiyorsa (analitik/model-tabanlı kontrol), "
        f"bu adım atlanır — doğrudan değerlendirmeye geçilir.\n"
        f">>> BU PAKETİ KENDİ DONANIMINDA ÇALIŞTIR ve gerçek sonuçları GATE-3'e getir. <<<"
        + _fbnote(state))
    return {"training_output": out}


def testing_node(state):
    i = state.get("phase3_run", 1) % 3
    bench = state.get("benchmark_output", "")
    out = run_agent(testing_agent,
        _fb(f"Phase-2 metriklerinden değerlendirme protokolü türet.\nBenchmark: {bench}",
            state.get("feedback", "")),
        f"[MOCK] DEĞERLENDİRME PROTOKOLÜ (Phase-2 metriklerinden türetildi)\n"
        f"• Metrikler: başarı oranı, Cost of Transport (enerji), devrilme oranı.\n"
        f"  NEDEN: Phase-2'de onaylanan benchmark metrikleriyle birebir uyumlu.\n"
        f"• Test senaryoları: {_SCENARIOS[i]}.\n"
        f"  NEDEN: sim-to-real dayanıklılığını ve genellemeyi ölçmek için."
        + _fbnote(state))
    return {"testing_output": out}


# ======================= PHASE-4 =======================
def statistical_node(state):
    out = run_agent(statistical_agent,
        _fb(f"Araştırma sorusu: {state.get('human_research_question','')}\n"
            f"Değerlendirme protokolü:\n{state.get('testing_output','')}\n\n"
            f"Şu gerçek sonuçları analiz et:\n{state.get('training_results','(sonuç girilmedi)')}",
            state.get("feedback", "")),
        "[MOCK] İSTATİSTİK ANALİZİ\n• 5 seed ortalama başarı: %88 ± 4 (95% GA).\n"
        "• Yöntem vs saf PPO: p<0.05 (önceden tanımlı t-test).\n"
        "• Enerji (CoT): yöntem 0.42, PPO 0.58 → %28 iyileşme.")
    return {"statistical_output": out}


def ablation_node(state):
    out = run_agent(ablation_agent,
        _fb(f"Araştırma sorusu: {state.get('human_research_question','')}\n"
            f"Yöntemin bileşenleri (ablation adayları):\n{state.get('methodology_output','')}\n\n"
            f"Şu sonuçlar üzerinden ablation:\n{state.get('training_results','(sonuç girilmedi)')}",
            state.get("feedback", "")),
        "[MOCK] ABLATION RAPORU\n• Enerji ödül terimi kaldırıldı → CoT %25 kötüleşti.\n"
        "• MARL koordinatör kaldırıldı → başarı %12 düştü.\n• Terrain curriculum kaldırıldı → %6 düşüş.")
    return {"ablation_output": out}


def critic_node(state):
    out = run_agent(critic_agent,
        _fb(f"Araştırma sorusu: {state.get('human_research_question','')}\n"
            f"Bilinen riskler (Phase-2):\n{state.get('risk_output','')}\n\n"
            f"İstatistik:\n{state['statistical_output']}\n\nAblation:\n{state['ablation_output']}",
            state.get("feedback", "")),
        "[MOCK] ELEŞTİREL DEĞERLENDİRME\n• Zayıflık: sim-to-real gerçek robotta test edilmedi.\n"
        "• Alternatif açıklama: enerji kazanımı ödül ağırlığından da gelebilir.\n"
        "• Hakem itirazı: baseline'lar güçlü mü? SOTA eklenmeli.")
    return {"critic_output": out}


# ======================= PHASE-5 =======================
def writing_node(state):
    out = run_agent(writing_agent,
        _fb(f"Makale taslağı yaz.\n"
            f"Araştırma sorusu: {state.get('human_research_question','')}\n"
            f"Doğrulanmış literatür (Related Work için):\n{state.get('verification_output','')}\n"
            f"Yöntem (Methodology için):\n{state.get('methodology_output','')}\n"
            f"Değerlendirme protokolü:\n{state.get('testing_output','')}\n"
            f"İstatistik:\n{state['statistical_output']}\n"
            f"Ablation:\n{state['ablation_output']}\n"
            f"Hakem itirazları (bunlara karşı overclaim YAPMA):\n{state.get('critic_output','')}",
            state.get("feedback", "")),
        "[MOCK] MAKALE TASLAĞI\n• Introduction: wheel-legged enerji-verimli kontrol.\n"
        "• Methodology: Hiyerarşik MARL + PPO + enerji-farkında ödül.\n"
        "• Experiments: %28 enerji iyileşmesi, p<0.05.\n• Conclusion: katkı + sim-to-real gelecek iş.")
    return {"writing_output": out}


def review_node(state):
    out = run_agent(review_agent,
        _fb(f"Bu taslağı hakem gözüyle denetle:\n{state['writing_output']}", state.get("feedback", "")),
        "[MOCK] HAKEM RAPORU\n• Tutarlılık: iddialar sonuçlarla uyumlu.\n"
        "• Atıf: tüm atıflar doğrulanmış kaynaklarla eşleşiyor.\n"
        "• Düzeltme: seed sayısı belirtilmeli; sim-to-real sınırı vurgulanmalı.")
    return {"review_output": out}