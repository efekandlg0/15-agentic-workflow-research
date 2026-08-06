"""
Streamlit arayüzü — puanlı literatür + insan kontrollü workflow + incelikli geri dönüş.

Çalıştırma:
  MOCK_LLM=1 streamlit run app.py    # ücretsiz, anahtarsız
  streamlit run app.py               # gerçek model (.env içinde OPENAI_API_KEY)
"""
import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command

import ui
from workflow import build_graph
from workflow.common import (
    METRIC_LABELS, SCORE_WEIGHTS, METHOD_METRIC_LABELS, METHOD_WEIGHTS,
)

load_dotenv()
st.set_page_config(page_title="Agentic Research Workflow", layout="wide")
ui.inject_css(st)

# Her GATE'in fazına ait ajanlar: (node_adı, görünen ad). 'tekrarla'da seçim için.
PHASE_AGENTS_UI = {
    "GATE-1": [("literature", "Literature Search Agent"), ("verification", "Verification Agent"),
               ("gap", "Research Gap Agent")],
    "GATE-2": [("methodology", "Methodology Design Agent"), ("benchmark", "Benchmark Agent"),
               ("risk", "Risk Analysis Agent")],
    "GATE-3": [("environment", "Environment Agent"), ("rl_coding", "RL Coding Agent"),
               ("training", "Training Agent"), ("testing", "Testing Agent")],
    "GATE-4": [("statistical", "Statistical Analysis Agent"), ("ablation", "Ablation Study Agent"),
               ("critic", "Scientific Critic Agent")],
    "GATE-5": [("writing", "Writing Agent"), ("review", "Scientific Review Agent")],
}


@st.cache_resource
def get_graph():
    return build_graph()


graph = get_graph()


def _why(label):
    return st.popover(label) if hasattr(st, "popover") else st.expander(label)


def _start():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.config = {"configurable": {"thread_id": st.session_state.thread_id}}
    st.session_state.history = []
    st.session_state.current = None
    st.session_state.done = False
    st.session_state.final = None
    _advance({"topic": st.session_state.topic})


def _advance(graph_input):
    result = graph.invoke(graph_input, st.session_state.config)
    if "__interrupt__" in result:
        st.session_state.current = result["__interrupt__"][0].value
    else:
        st.session_state.current = None
        st.session_state.done = True
        st.session_state.final = result.get("final_decision", "(yok)")


def _submit(resume):
    """resume: sözlük {action, note, agents?}. Kararı grafiğe geri verir."""
    payload = st.session_state.current
    lbl = resume["action"]
    if resume.get("agents"):
        lbl += " [" + ", ".join(resume["agents"]) + "]"
    if resume.get("note"):
        lbl += ": " + resume["note"]
    st.session_state.history.append({"gate": payload["gate"], "karar": lbl})
    _advance(Command(resume=resume))


def _txt(value, default="—"):
    """Ajan alanını görüntülenebilir metne çevirir.
    Gerçek modda model bir alanı liste/sözlük olarak döndürebilir (ör. evidence);
    doğrudan string birleştirmek TypeError verir."""
    if value is None or value == "":
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        parts = [_txt(v, "") for v in value if v not in (None, "")]
        return "\n\n".join(f"- {p}" for p in parts) if parts else default
    if isinstance(value, dict):
        return "\n\n".join(f"- **{k}:** {_txt(v, '')}" for k, v in value.items()) or default
    return str(value)


def _d(value):
    """Sözlük bekleyen alanlar için güvenli erişim: sözlük değilse boş sözlük."""
    return value if isinstance(value, dict) else {}


def _state_values():
    try:
        return graph.get_state(st.session_state.config).values
    except Exception:
        return {}


# ---------------- Puanlı literatür (GATE-1) ----------------
def _render_papers(papers):
    st.subheader("Literature Search + Verification Agent — puanlı kaynaklar")
    st.caption("Puanlama: Literature Search Agent (5 metrik) + Verification Agent (venue). "
               "Final = ağırlıklı ortalama. Her puanın 'neden?' butonuyla gerekçesi açılır.")
    for p in papers:
        with st.container(border=True):
            top = st.columns([1, 5])
            with top[0]:
                st.metric("Final", f"{p.get('final_score','-')}/10")
            with top[1]:
                st.markdown(f"**{_txt(p.get('title'), '(başlık yok)')}**")
                vstat = _txt(_d(p.get("verification")).get("status"))
                authors = p.get("authors")
                authors = ", ".join(str(a) for a in authors) if isinstance(authors, list) \
                    else _txt(authors)
                st.caption(f"{authors} · {p.get('year','—')} · "
                           f"{_txt(p.get('venue'))} · {_txt(p.get('doi'))} · doğrulama: {vstat}")
            metric_keys = ["relevance", "venue", "citations", "recency", "repos", "future_work"]
            cols = st.columns(len(metric_keys))
            for col, key in zip(cols, metric_keys):
                with col:
                    sc = _d(p.get("venue_score")) if key == "venue" else _d(_d(p.get("scores")).get(key))
                    st.markdown(f"**{METRIC_LABELS[key]}**  \n{sc.get('score','-')}/10")
                    with _why("neden?"):
                        st.write(_txt(sc.get("reason"), "Gerekçe yok."))
            with st.expander("Final puan nasıl hesaplandı? (ağırlıklar)"):
                for k, w in SCORE_WEIGHTS.items():
                    s = (_d(p.get("venue_score")).get("score", "-") if k == "venue"
                         else _d(_d(p.get("scores")).get(k)).get("score", "-"))
                    st.write(f"- {METRIC_LABELS[k]}: puan {s} x ağırlık {w}")
                st.info("Ağırlıkları değiştirmek için: workflow/common.py -> SCORE_WEIGHTS")


def _render_gaps(gaps):
    st.subheader("Research Gap Agent — puanlı boşluklar")
    st.caption("Yüksek puan = literatürde net açık. 'Bu konuyla devam et' o soruyu seçer.")
    for i, g in enumerate(gaps):
        gid = _txt(g.get("id"), f"B{i+1}")
        score = g.get("score") if isinstance(g.get("score"), dict) else {}
        question = _txt(g.get("candidate_question"), "")
        with st.container(border=True):
            c = st.columns([1, 5])
            with c[0]:
                st.metric("Açıklık", f"{score.get('score','-')}/10")
            with c[1]:
                st.markdown(f"**{gid} · {g.get('title','(başlık yok)')}**")
                with _why("neden bu açık?"):
                    st.write("**Puan gerekçesi:** " + _txt(score.get("reason")))
                    st.write("**Kanıt:** " + _txt(g.get("evidence")))
                    st.write("**Future-work taraması:** " + _txt(g.get("future_work_check")))
                if question and st.button(f"→ Bu konuyla devam et: {question[:46]}…",
                                          key=f"gap_{gid}_{i}"):
                    _submit({"action": "onayla", "note": question})
                    st.rerun()


# ---------------- Puanlı yöntem (GATE-2) ----------------
def _render_methodology(props):
    st.subheader("Methodology Design Agent — puanlı yöntem önerileri")
    st.caption("Final = Uygunluk/Literatür/Olgunluk ağırlıklı ortalaması. "
               "Kaynak etiketi: literatür-temelli veya AI önerisi.")
    for p in props:
        with st.container(border=True):
            top = st.columns([1, 5])
            with top[0]:
                st.metric("Final", f"{p.get('final_score','-')}/10")
            with top[1]:
                st.markdown(f"**{p.get('component','—')} → {p.get('choice','—')}**")
                st.caption(f"Kaynak: **{p.get('source','—')}**")
            keys = ["fit", "literature_support", "maturity"]
            cols = st.columns(len(keys))
            for col, k in zip(cols, keys):
                with col:
                    sc = _d(_d(p.get("scores")).get(k))
                    st.markdown(f"**{METHOD_METRIC_LABELS[k]}**  \n{sc.get('score','-')}/10")
                    with _why("neden?"):
                        st.write(_txt(sc.get("reason"), "Gerekçe yok."))
            with _why("neden bu seçim? (gerekçe + alternatif)"):
                st.write("**NEDEN:** " + _txt(p.get("reason")))
                st.write("**Alternatif:** " + _txt(p.get("alternative")))
            with st.expander("Final puan nasıl hesaplandı? (ağırlıklar)"):
                for k, w in METHOD_WEIGHTS.items():
                    s = _d(_d(p.get("scores")).get(k)).get("score", "-")
                    st.write(f"- {METHOD_METRIC_LABELS[k]}: puan {s} x ağırlık {w}")
                st.info("Ağırlıkları değiştirmek için: workflow/common.py -> METHOD_WEIGHTS")


def _render_benchmarks(items):
    st.subheader("Benchmark Agent — baseline ve metrikler")
    for b in items:
        sc = _d(b.get("score"))
        with st.container(border=True):
            c = st.columns([1, 5])
            with c[0]:
                st.metric("Puan", f"{sc.get('score','-')}/10")
            with c[1]:
                st.markdown(f"**[{b.get('kind','—')}] {b.get('choice','—')}**")
                st.caption(f"Kaynak: **{b.get('source','—')}**")
                with _why("neden?"):
                    st.write("**NEDEN:** " + _txt(b.get("reason")))
                    st.write("**Puan gerekçesi:** " + _txt(sc.get("reason")))


def _render_risks(items):
    st.subheader("Risk Analysis Agent — risk matrisi")
    for r in items:
        with st.container(border=True):
            st.markdown(f"**{r.get('risk','—')} — SEVİYE: {r.get('level','—')}**")
            st.caption(f"Kaynak: **{r.get('source','—')}**")
            with _why("detay (neden + azaltma)"):
                st.write("**NEDEN:** " + _txt(r.get("reason")))
                st.write("**Azaltma:** " + _txt(r.get("mitigation")))


def _render_generic(payload):
    """Bilinmeyen/eşleşmeyen GATE için son çare: ham metin açılırlarda."""
    for key, value in payload.items():
        if key in ("gate", "mesaj"):
            continue
        with st.expander(f"{key}", expanded=False):
            st.text(value)


def _render_agent_outputs(payload):
    """Faz 3/4/5 ajan çıktılarını sırayla kartlara döker.
    İlk ajan açık, diğerleri katlanmış gelir (gerçek çıktılar çok uzun olabiliyor)."""
    items = [(k, v) for k, v in payload.items() if k not in ("gate", "mesaj")]
    for i, (key, value) in enumerate(items):
        ui.render_agent_output(st, key, value,
                               critic="Critic" in key, expanded=(i == 0))


# ---------------- Uygulama & Deney (GATE-3) ----------------
def _render_phase3(payload, vals):
    st.subheader("Uygulama & Deney — Faz-2 yöntemine bağlı çıktılar")
    st.caption("Bu 4 ajanın 3'ü onaylanan YÖNTEME, Testing ise onaylanan BENCHMARK'a bağımlı "
               "türetim yapıyor. Eğitim paketini kendi donanımında çalıştırıp gerçek sonuçları "
               "aşağıdaki karar notuna yaz — o not Faz-4'e girdi olarak gidecek.")
    with st.expander("Faz-2'den taşınan veri (yöntem / benchmark özeti)", expanded=False):
        st.markdown("**Onaylanan yöntem:**")
        st.code(vals.get("methodology_output", "—"), language=None)
        st.markdown("**Onaylanan benchmark:**")
        st.code(vals.get("benchmark_output", "—"), language=None)
    _render_agent_outputs(payload)


# ---------------- Bilimsel Değerlendirme (GATE-4) ----------------
def _render_phase4(payload):
    st.subheader("Bilimsel Değerlendirme — istatistik, ablation, eleştiri")
    st.caption("Scientific Critic KASITLI olarak eleştirel yaklaşır (devil's advocate); "
               "itirazlarını değerlendirmeden onaylama.")
    _render_agent_outputs(payload)


# ---------------- Yayın (GATE-5) ----------------
def _render_phase5(payload):
    st.subheader("Yayın — makale taslağı ve hakem incelemesi")
    st.caption("Review Agent taslağı hakem gözüyle denetler; düzeltme/tutarsızlık notlarını "
               "onaylamadan önce değerlendir.")
    _render_agent_outputs(payload)


# ---------------- Karar kontrolleri ----------------
_ACTION_LABELS = {"onayla": "Onayla — ileri",
                  "tekrarla": "Tekrarla — seçilen ajanlar yeniden",
                  "geri": "Geri — önceki kapıya"}


def _decision_controls(payload):
    gate = payload["gate"]
    # Widget key'leri karar sayacını içerir: her gönderimde YENİ widget doğar, böylece
    # bir GATE'in notu (ör. GATE-3'ün deney sonucu) sonraki GATE'e sessizce taşınmaz.
    turn = f"{gate}_{len(st.session_state.get('history', []))}"
    st.divider()
    st.subheader("Kararın")
    options = ["onayla", "tekrarla"] + (["geri"] if gate != "GATE-1" else [])
    action = st.radio("Aksiyon", options, key=f"action_{turn}", horizontal=True,
                      format_func=_ACTION_LABELS.get)

    picked_labels = []
    if action == "tekrarla":
        agents_ui = PHASE_AGENTS_UI.get(gate, [])
        picked_labels = st.multiselect(
            "Hangi ajan(lar) yeniden çalışsın? (boş bırakırsan tüm faz yeniden çalışır)",
            [label for _, label in agents_ui],
            key=f"agents_{turn}",
            help="Ardışık fazlarda seçtiğin en erken ajandan itibaren zincir yeniden akar.",
        )

    ph = {"onayla": "onayla -> araştırma sorusu / not.",
          "tekrarla": "tekrarla -> seçilen ajanlara ne düzelteceğini yaz.",
          "geri": "geri -> önceki kapıya not."}[action]
    if gate == "GATE-3" and action == "onayla":
        ph = ("onayla -> kendi donanımında çalıştırdığın GERÇEK deney sonuçlarını buraya yaz "
              "(bu not Faz-4'e girdi olarak gidecek).")
    note = st.text_area("Not / geri bildirim", key=f"note_{turn}", height=90, placeholder=ph)

    if st.button("Kararı gönder", type="primary", key=f"submit_{turn}"):
        resume = {"action": action, "note": note.strip()}
        if action == "tekrarla":
            agents_ui = PHASE_AGENTS_UI.get(gate, [])
            picked = [node for node, label in agents_ui if label in picked_labels]
            resume["agents"] = picked or None
        _submit(resume)
        st.rerun()


# ======================= Arayüz =======================
mock = os.getenv("MOCK_LLM") == "1"
ui.render_header(st, mock)

# ---- Kenar çubuğu ----
st.sidebar.markdown("### Kontrol Paneli")
if "topic" not in st.session_state:
    st.session_state.topic = (
        "RL tabanlı wheel-legged quadruped robotlarda enerji verimli hareket kontrolü"
    )
st.sidebar.text_area("Araştırma konusu", key="topic", height=110)
if st.sidebar.button("Başlat / Yeniden başlat", use_container_width=True, type="primary"):
    _start()

if st.session_state.get("history"):
    st.sidebar.markdown("### Verilen kararlar")
    st.sidebar.markdown(
        "".join(ui.history_item_html(h["gate"], h["karar"]) for h in st.session_state.history),
        unsafe_allow_html=True,
    )

# ---- Aktif durum (stepper her ekranda görünür) ----
_current_gate = (st.session_state.get("current") or {}).get("gate")
_done = bool(st.session_state.get("done"))
ui.render_stepper(st, _current_gate, _done)

if not st.session_state.get("config"):
    st.info("Soldan araştırma konusunu gir ve **Başlat**'a bas. "
            "Akış ilk insan kapısına (GATE-1) kadar otomatik çalışır.")
    st.markdown("### Pipeline — sistem sırası ile nasıl ilerliyor?")
    ui.render_pipeline(st)

elif _done:
    st.success("Workflow tamamlandı — 15 ajan ve 5 insan kapısının tamamı geçildi.")
    st.subheader("Nihai karar")
    st.write(st.session_state.final)
    with st.expander("Pipeline şeması", expanded=False):
        ui.render_pipeline(st, done=True)

elif st.session_state.get("current"):
    payload = st.session_state.current
    ui.gate_banner(st, payload["gate"], payload["mesaj"])

    vals = _state_values()
    if payload["gate"] == "GATE-1" and vals.get("papers"):
        _render_papers(vals["papers"])
        if vals.get("gaps"):
            _render_gaps(vals["gaps"])
    elif payload["gate"] == "GATE-2" and vals.get("proposals"):
        _render_methodology(vals["proposals"])
        if vals.get("benchmarks"):
            _render_benchmarks(vals["benchmarks"])
        if vals.get("risks"):
            _render_risks(vals["risks"])
    elif payload["gate"] == "GATE-3":
        _render_phase3(payload, vals)
    elif payload["gate"] == "GATE-4":
        _render_phase4(payload)
    elif payload["gate"] == "GATE-5":
        _render_phase5(payload)
    else:
        _render_generic(payload)
    _decision_controls(payload)

    st.divider()
    st.markdown("#### Neredeyim?")
    ui.render_current_phase(st, payload["gate"])
    if st.toggle("Tüm pipeline şemasını göster", key="show_full_pipeline"):
        ui.render_pipeline(st, current_gate=payload["gate"]) 