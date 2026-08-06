"""Arayüz bileşenleri — araştırma (akademik) temalı tasarım.

Burada UI'ın "görsel" katmanı toplanır; app.py yalnızca akış mantığını tutar.
- inject_css()        : global tema (parşömen zemin, serif başlık, kart stilleri)
- render_header()     : üst başlık + mod rozeti
- render_stepper()    : 5 fazlı yatay ilerleme çubuğu (tamamlandı/aktif/bekliyor)
- render_pipeline()   : 15 ajan + 5 GATE'in tam akış şeması (HTML, bağımlılıksız)
- gate_banner()       : aktif GATE için vurgulu banner
- history_item_html() : kenar çubuğu karar zaman çizelgesi öğesi
- render_agent_output(): Faz 3/4/5 serbest-metin ajan çıktısını puanlı-kart diliyle gösterir
"""
import html
import re

# ---------------------------------------------------------------- Pipeline verisi
# Tek doğruluk kaynağı workflow/graph.py'deki akıştır; burası onun görsel kopyası.
PHASES = [
    {
        "no": 1, "name": "Literatür Tarama", "type": "Ardışık",
        "agents": [(1, "Literature Search"), (2, "Verification"), (3, "Research Gap")],
        "flow": "seq",
        "gate": "GATE-1", "gate_q": "Puanlı kaynaklar + boşluklar → araştırma sorusunu İNSAN seçer",
    },
    {
        "no": 2, "name": "Yöntem Tasarımı", "type": "Paralel",
        "agents": [(4, "Methodology Design"), (5, "Benchmark"), (6, "Risk Analysis")],
        "flow": "par",
        "gate": "GATE-2", "gate_q": "Yöntem + metrikler + riskler → uygulamaya geçiş onayı",
    },
    {
        "no": 3, "name": "Uygulama & Deney", "type": "Ardışık",
        "agents": [(7, "Environment"), (8, "RL Coding"), (9, "Training"), (10, "Testing")],
        "flow": "seq",
        "gate": "GATE-3", "gate_q": "Eğitim paketi → insan kendi donanımında çalıştırır, sonucu getirir",
    },
    {
        "no": 4, "name": "Bilimsel Değerlendirme", "type": "Karma",
        "agents": [(11, "Statistical"), (12, "Ablation"), (13, "Scientific Critic")],
        "flow": "mix",  # (11 ∥ 12) → 13
        "gate": "GATE-4", "gate_q": "İstatistik + ablation + critic itirazları → katkı geçerli mi?",
    },
    {
        "no": 5, "name": "Yayın", "type": "Ardışık",
        "agents": [(14, "Writing"), (15, "Scientific Review")],
        "flow": "seq",
        "gate": "GATE-5", "gate_q": "Makale taslağı + hakem denetimi → gönderim kararı",
    },
]

GATE_TO_PHASE = {p["gate"]: p["no"] for p in PHASES}


# ---------------------------------------------------------------- Tema (CSS)
_CSS = """
<style>
/* ---- Akademik tema: parşömen zemin, mürekkep metin, serif başlıklar ---- */
h1, h2, h3 {
    font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif !important;
    color: #1c2733 !important;
    letter-spacing: .2px;
}
[data-testid="stSidebar"] {
    background: #f4f0e6;
    border-right: 1px solid #e2dac6;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    font-size: 1.02rem !important;
}
/* Kenarlıklı kartlar (st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #fffdf9;
    border: 1px solid #e6dfcd !important;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(28,39,51,.06);
}
[data-testid="stMetricValue"] {
    font-family: Georgia, serif;
    color: #1d4e79;
}
.stButton > button { border-radius: 8px; font-weight: 600; }
hr { border-color: #e2dac6; }

/* ---- Üst başlık ---- */
.arw-header { padding: .2rem 0 .6rem 0; border-bottom: 3px double #b9a97c; margin-bottom: 1rem; }
.arw-title {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 1.9rem; font-weight: 700; color: #1c2733; margin: 0;
}
.arw-subtitle {
    color: #6b644f; font-size: .92rem; margin-top: .15rem;
    font-variant: small-caps; letter-spacing: 1.5px;
}
.arw-badge {
    display: inline-block; padding: .15rem .6rem; border-radius: 999px;
    font-size: .75rem; font-weight: 700; letter-spacing: .5px; vertical-align: middle;
}
.arw-badge-mock { background: #eef6ee; color: #2e7d4f; border: 1px solid #bcd9c4; }
.arw-badge-real { background: #eaf1f8; color: #1d4e79; border: 1px solid #b9cfe3; }

/* ---- Faz stepper ---- */
.arw-stepper { display: flex; align-items: flex-start; margin: .4rem 0 1.1rem 0; }
.arw-step { flex: 1; text-align: center; position: relative; }
.arw-step:not(:last-child)::after {
    content: ""; position: absolute; top: 16px; left: calc(50% + 22px);
    width: calc(100% - 44px); height: 2px; background: #d8cfb6;
}
.arw-step.done:not(:last-child)::after { background: #2e7d4f; }
.arw-dot {
    width: 32px; height: 32px; line-height: 30px; border-radius: 50%;
    margin: 0 auto; font-weight: 700; font-size: .85rem;
    background: #efe9d9; color: #8a8266; border: 2px solid #d8cfb6;
}
.arw-step.done .arw-dot { background: #2e7d4f; color: #fff; border-color: #2e7d4f; }
.arw-step.active .arw-dot {
    background: #1d4e79; color: #fff; border-color: #1d4e79;
    box-shadow: 0 0 0 5px rgba(29,78,121,.15);
}
.arw-step-name { font-size: .78rem; margin-top: .35rem; color: #8a8266; line-height: 1.25; }
.arw-step.done .arw-step-name { color: #2e7d4f; }
.arw-step.active .arw-step-name { color: #1d4e79; font-weight: 700; }
.arw-step-phase { font-size: .68rem; letter-spacing: 1px; color: inherit; opacity: .8; }

/* ---- Pipeline şeması ---- */
.arw-phase {
    background: #fffdf9; border: 1px solid #e6dfcd; border-left: 5px solid #b9a97c;
    border-radius: 10px; padding: .8rem 1rem; margin-bottom: 0;
}
.arw-phase.active { border-left-color: #1d4e79; box-shadow: 0 2px 8px rgba(29,78,121,.12); }
.arw-phase.done { border-left-color: #2e7d4f; }
.arw-phase-head { display: flex; align-items: baseline; gap: .6rem; margin-bottom: .55rem; }
.arw-phase-no {
    font-family: Georgia, serif; font-weight: 700; font-size: .95rem; color: #1d4e79;
    letter-spacing: 1px;
}
.arw-phase-name { font-family: Georgia, serif; font-weight: 700; color: #1c2733; }
.arw-flow-badge {
    font-size: .68rem; font-weight: 700; letter-spacing: .5px; padding: .1rem .5rem;
    border-radius: 999px; background: #f1ede3; color: #6b644f; border: 1px solid #ddd3ba;
}
.arw-phase-state { margin-left: auto; font-size: .72rem; font-weight: 700; }
.arw-phase.done .arw-phase-state { color: #2e7d4f; }
.arw-phase.active .arw-phase-state { color: #1d4e79; }
.arw-agents { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem .45rem; }
.arw-agent {
    display: inline-flex; align-items: center; gap: .4rem;
    background: #f7f4ec; border: 1px solid #ddd3ba; border-radius: 8px;
    padding: .25rem .6rem .25rem .3rem; font-size: .82rem; color: #1c2733; white-space: nowrap;
}
.arw-agent-no {
    background: #1d4e79; color: #fff; border-radius: 6px; font-size: .7rem;
    font-weight: 700; padding: .1rem .38rem;
}
.arw-conn { color: #a89d7f; font-weight: 700; font-size: .95rem; }
.arw-par-group {
    display: inline-flex; flex-direction: column; gap: .3rem;
    border: 1px dashed #c9bd9c; border-radius: 8px; padding: .35rem .45rem;
}
.arw-par-label { font-size: .64rem; color: #a89d7f; letter-spacing: 1px; text-align: center; }
.arw-gate {
    margin-top: .65rem; background: #fdf3f0; border: 1px solid #e8c9c0;
    border-left: 5px solid #8b2635; border-radius: 8px; padding: .45rem .7rem;
    font-size: .82rem; color: #5c2a22;
}
.arw-gate b { color: #8b2635; letter-spacing: .5px; }
.arw-vline { text-align: center; color: #b9a97c; font-size: 1.05rem; line-height: 1.4; margin: .15rem 0; }
.arw-legend {
    background: #f1ede3; border: 1px solid #ddd3ba; border-radius: 8px;
    padding: .5rem .8rem; font-size: .78rem; color: #6b644f; margin-top: .3rem;
}

/* ---- GATE banner ---- */
.arw-gate-banner {
    background: linear-gradient(135deg, #fdf6ee 0%, #fdf3f0 100%);
    border: 1px solid #e8c9c0; border-left: 6px solid #8b2635;
    border-radius: 10px; padding: .9rem 1.2rem; margin: .3rem 0 1rem 0;
}
.arw-gate-banner .g-tag {
    font-size: .7rem; font-weight: 700; letter-spacing: 2px; color: #8b2635;
}
.arw-gate-banner .g-title {
    font-family: Georgia, serif; font-size: 1.35rem; font-weight: 700;
    color: #1c2733; margin: .1rem 0;
}
.arw-gate-banner .g-msg { font-size: .9rem; color: #5c5642; }

/* ---- Faz 3/4/5 çıktı kartları (serbest metin ajanlar) ---- */
.arw-out-head { display:flex; align-items:center; gap:.5rem; margin-bottom:.4rem; flex-wrap: wrap; }
.arw-out-title { font-family: Georgia, serif; font-weight:700; color:#1c2733; }
.arw-out-dep {
    font-size:.68rem; color:#8a8266; background:#f1ede3; border:1px solid #ddd3ba;
    border-radius:999px; padding:.05rem .55rem;
}
.arw-out-caption { color:#6b644f; font-size:.82rem; margin-bottom:.5rem; font-style:italic; }
.arw-out-bullet { padding:.15rem 0; font-size:.9rem; color:#1c2733; line-height:1.4; }
.arw-out-label { color:#1d4e79; font-weight:700; }
.arw-out-why { color:#8a8266; font-size:.78rem; font-style:italic; margin:.05rem 0 .35rem 1rem; }
.arw-out-adapt {
    background:#fdf8ec; border:1px solid #e6d5a0; border-left:4px solid #b8932e;
    border-radius:6px; padding:.35rem .6rem; margin:.3rem 0; font-size:.82rem; color:#6b5518;
}
.arw-out-cta {
    background:#fdf3f0; border:1px solid #e8c9c0; border-left:4px solid #8b2635;
    border-radius:6px; padding:.4rem .7rem; margin-top:.5rem; font-size:.84rem;
    font-weight:700; color:#5c2a22;
}
.arw-out-fb { color:#1d4e79; font-size:.76rem; margin-top:.3rem; }
.arw-critic-box {
    background:#fdf6f5; border:1px dashed #d9a79e; border-radius:8px;
    padding:.5rem .7rem; margin-top:.2rem;
}

/* ---- Örnek metinler (placeholder): italik + soluk, gerçek içerikle karışmasın ---- */
.stTextArea textarea::placeholder, .stTextInput input::placeholder {
    font-style: italic; opacity: .55; color: #8a8266;
}

/* ---- Aktif proje kartı (kenar çubuğu üstü) ---- */
.arw-active {
    background: linear-gradient(135deg, #eaf1f8 0%, #f4f0e6 100%);
    border: 1px solid #b9cfe3; border-left: 5px solid #1d4e79;
    border-radius: 9px; padding: .55rem .75rem; margin-bottom: .7rem;
}
.arw-active .a-tag {
    font-size: .62rem; font-weight: 700; letter-spacing: 1.4px; color: #1d4e79;
}
.arw-active .a-name {
    font-family: Georgia, serif; font-size: .92rem; font-weight: 700;
    color: #1c2733; line-height: 1.3; margin: .15rem 0 .25rem 0;
    overflow-wrap: anywhere;
}
.arw-active .a-state {
    display: inline-block; font-size: .68rem; font-weight: 700; padding: .1rem .45rem;
    border-radius: 999px; background: #fff; border: 1px solid #b9cfe3; color: #1d4e79;
}
.arw-active.none {
    background: #f4f0e6; border-color: #ddd3ba; border-left-color: #b9a97c;
}
.arw-active.none .a-tag, .arw-active.none .a-name { color: #8a8266; }

/* ---- Ana ekranda açık proje şeridi ---- */
.arw-openbar {
    display: flex; align-items: baseline; gap: .5rem; flex-wrap: wrap;
    background: #f7f4ec; border: 1px solid #e6dfcd; border-radius: 8px;
    padding: .4rem .8rem; margin-bottom: .8rem; font-size: .84rem; color: #5c5642;
}
.arw-openbar .o-tag {
    font-size: .64rem; font-weight: 700; letter-spacing: 1.2px; color: #8a8266;
}
.arw-openbar .o-name { font-weight: 700; color: #1c2733; overflow-wrap: anywhere; }

/* ---- Kenar çubuğu karar zaman çizelgesi ---- */
.arw-hist {
    background: #fffdf9; border: 1px solid #e6dfcd; border-left: 4px solid #b9a97c;
    border-radius: 7px; padding: .35rem .6rem; margin-bottom: .35rem; font-size: .78rem;
}
.arw-hist b { color: #8b2635; }
.arw-hist code {
    background: #f1ede3; color: #1c2733; border-radius: 4px; padding: 0 .3rem; font-size: .74rem;
}
</style>
"""


def inject_css(st):
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header(st, mock: bool):
    badge = ('<span class="arw-badge arw-badge-mock">● MOCK MOD — ücretsiz</span>' if mock
             else '<span class="arw-badge arw-badge-real">● GERÇEK MODEL — API</span>')
    st.markdown(
        '<div class="arw-header">'
        f'<div class="arw-title">Utonium &nbsp;{badge}</div>'
        '<div class="arw-subtitle">agentic research workflow — 15 ajan · 5 faz · '
        '5 insan kapısı</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _phase_state(phase_no: int, current_gate: str | None, done: bool) -> str:
    """'done' | 'active' | 'pending' — stepper ve şema aynı mantığı kullanır."""
    if done:
        return "done"
    if current_gate is None:
        return "pending"
    cur = GATE_TO_PHASE.get(current_gate, 0)
    if phase_no < cur:
        return "done"
    if phase_no == cur:
        return "active"
    return "pending"


def render_stepper(st, current_gate: str | None, done: bool):
    steps = []
    for p in PHASES:
        state = _phase_state(p["no"], current_gate, done)
        mark = "✓" if state == "done" else str(p["no"])
        steps.append(
            f'<div class="arw-step {state}">'
            f'<div class="arw-dot">{mark}</div>'
            f'<div class="arw-step-name"><span class="arw-step-phase">FAZ {p["no"]}</span><br>'
            f'{p["name"]}</div></div>'
        )
    st.markdown('<div class="arw-stepper">' + "".join(steps) + "</div>",
                unsafe_allow_html=True)


def _agent_chip(no: int, name: str) -> str:
    return (f'<span class="arw-agent"><span class="arw-agent-no">{no}</span>'
            f'{name} Agent</span>')


def _agents_html(p) -> str:
    chips = [_agent_chip(no, name) for no, name in p["agents"]]
    arrow = '<span class="arw-conn">→</span>'
    if p["flow"] == "seq":
        return arrow.join(chips)
    if p["flow"] == "par":
        return ('<span class="arw-par-group"><span class="arw-par-label">PARALEL ∥</span>'
                + "".join(chips) + "</span>")
    # mix: (11 ∥ 12) → 13
    par = ('<span class="arw-par-group"><span class="arw-par-label">PARALEL ∥</span>'
           + "".join(chips[:-1]) + "</span>")
    return par + arrow + chips[-1]


_STATE_LABEL = {"done": "✓ TAMAMLANDI", "active": "► AKTİF", "pending": ""}


def _phase_block(p, state: str) -> str:
    """Tek bir fazın kartı (başlık + ajan zinciri + GATE satırı)."""
    return (
        f'<div class="arw-phase {state}">'
        f'<div class="arw-phase-head">'
        f'<span class="arw-phase-no">FAZ {p["no"]}</span>'
        f'<span class="arw-phase-name">{p["name"]}</span>'
        f'<span class="arw-flow-badge">{p["type"]}</span>'
        f'<span class="arw-phase-state">{_STATE_LABEL[state]}</span>'
        f'</div>'
        f'<div class="arw-agents">{_agents_html(p)}</div>'
        f'<div class="arw-gate"><b>{p["gate"]} · İNSAN KONTROLÜ</b> — {p["gate_q"]}</div>'
        f'</div>'
    )


def render_current_phase(st, current_gate: str):
    """'Neredeyim?' — yalnızca aktif fazın kartı; tam şema ayrı tuşla açılır."""
    p = next(ph for ph in PHASES if ph["gate"] == current_gate)
    st.markdown(
        f'<div class="arw-legend">Faz {p["no"]} / {len(PHASES)} — '
        f'bu fazın sonunda karar kapısı: <b>{p["gate"]}</b></div>'
        + _phase_block(p, "active"),
        unsafe_allow_html=True,
    )


def render_pipeline(st, current_gate: str | None = None, done: bool = False):
    """15 ajan + 5 GATE'in tam akış şeması. Çalışma sırasında aktif faz vurgulanır."""
    parts = []
    for i, p in enumerate(PHASES):
        parts.append(_phase_block(p, _phase_state(p["no"], current_gate, done)))
        if i < len(PHASES) - 1:
            parts.append('<div class="arw-vline">▼</div>')
    parts.append(
        '<div class="arw-vline">▼</div>'
        '<div class="arw-legend"><b>BİTİŞ</b> — GATE-5 onayı makaleyi gönderime hazır işaretler.<br>'
        'Her kapıda üç karar: <b>onayla</b> (ileri) · <b>tekrarla</b> (seçilen ajanlar '
        'geri bildirimle yeniden çalışır) · <b>geri</b> (önceki kapıya döner).</div>'
    )
    st.markdown("".join(parts), unsafe_allow_html=True)


def gate_banner(st, gate: str, mesaj: str):
    phase = next(p for p in PHASES if p["gate"] == gate)
    st.markdown(
        '<div class="arw-gate-banner">'
        f'<div class="g-tag">FAZ {phase["no"]} · {phase["name"].upper()} · İNSAN KONTROLÜ GEREKLİ</div>'
        f'<div class="g-title">{gate}</div>'
        f'<div class="g-msg">{mesaj}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_active_project(st, project):
    """Kenar çubuğunun EN ÜSTÜ: şu an hangi projede olduğunu net gösterir."""
    if not project:
        st.sidebar.markdown(
            '<div class="arw-active none"><div class="a-tag">AÇIK PROJE</div>'
            '<div class="a-name">— henüz proje açılmadı —</div></div>',
            unsafe_allow_html=True)
        return
    st.sidebar.markdown(
        '<div class="arw-active">'
        '<div class="a-tag">AÇIK PROJE</div>'
        f'<div class="a-name">{_esc(project["topic"])}</div>'
        f'<span class="a-state">{_esc(project.get("status", "—"))}</span>'
        '</div>',
        unsafe_allow_html=True)


def render_open_bar(st, project):
    """Ana ekranın üstünde ince şerit: çalışılan projeyi hatırlatır."""
    if not project:
        return
    st.markdown(
        '<div class="arw-openbar"><span class="o-tag">ÇALIŞILAN PROJE</span>'
        f'<span class="o-name">{_esc(project["topic"])}</span></div>',
        unsafe_allow_html=True)


def history_item_html(gate: str, karar: str) -> str:
    return f'<div class="arw-hist"><b>{gate}</b> · <code>{karar}</code></div>'


# ---------------------------------------------------------------- Faz 3/4/5 çıktı kartları
# Faz 3/4/5 ajanları JSON değil SERBEST METİN üretir ("• madde\n  NEDEN: gerekçe" kalıbı,
# ver. nodes.py mock metinleri + research_agents/phase3.py '_COMMON' talimatı). Bu ayrıştırıcı
# o kalıbı puanlı kartlarla (GATE-1/2) aynı görsel dile çevirir; kalıp tutmazsa ham metne düşer.

def _parse_agent_text(text: str):
    """-> (title, bullets[{label,body,why,kind}], trailing[(kind, content)]).
    kind: 'normal' | 'adapt' (UYGULANABİLİRLİK). trailing kind: 'cta' | 'feedback' | 'note'."""
    lines = text.strip("\n").split("\n")
    title, start = None, 0
    if lines and lines[0].strip() and not lines[0].lstrip().startswith(("•", ">>>")):
        title, start = lines[0].strip(), 1

    bullets, trailing, cur = [], [], None
    for line in lines[start:]:
        s = line.strip()
        if not s:
            continue
        if s.startswith(">>>"):
            trailing.append(("cta", s.strip(">").strip("<").strip()))
        elif s.startswith("(↻"):
            trailing.append(("feedback", s.strip("()")))
        elif s.startswith("•"):
            if cur:
                bullets.append(cur)
            body = s.lstrip("•").strip()
            kind = "adapt" if body.upper().startswith("UYGULANABİLİRLİK") else "normal"
            cur = {"label": None, "body": body, "why": None, "kind": kind}
        elif s.upper().startswith("NEDEN:") and cur is not None:
            cur["why"] = s.split(":", 1)[1].strip()
        elif cur is not None:
            cur["body"] += " " + s
        else:
            trailing.append(("note", s))
    if cur:
        bullets.append(cur)

    for b in bullets:
        if b["kind"] == "normal" and ":" in b["body"]:
            label, rest = b["body"].split(":", 1)
            if 0 < len(label) <= 40:
                b["label"], b["body"] = label.strip(), rest.strip()
    return title, bullets, trailing


def parse_gate_key(key: str):
    """'7 · Environment Agent (Phase-2 yöntemine bağlı)' -> (7, 'Environment Agent', 'Phase-2 yöntemine bağlı')."""
    m = re.match(r"^\s*(\d+)\s*·\s*([^(]+?)\s*(?:\(([^)]+)\))?\s*$", key)
    if not m:
        return None, key, None
    no, name, dep = m.groups()
    return int(no), name.strip(), dep


_MD_HINT = re.compile(r"^\s{0,3}(#{1,6}\s|[-*+]\s|\d+\.\s|\||```)|\*\*", re.M)


def looks_like_markdown(text: str) -> bool:
    """Gerçek model çıktısı Markdown üretir (## başlık, **kalın**, - madde);
    MOCK metinleri ise '• madde / NEDEN:' kalıbındadır. Hangisi olduğunu ayırt eder."""
    return bool(_MD_HINT.search(text or ""))


# Gerçek model çıktıları çok uzun olabilir (binlerce karakter). Bu eşiği aşan çıktılar
# katlanabilir bir bölüme alınır; aksi halde karar kontrollerine ulaşmak için çok scroll gerekir.
_LONG_OUTPUT = 1200


def render_agent_output(st, key: str, text: str, critic: bool = False,
                        expanded: bool = True):
    """Faz 3/4/5 tek bir ajan çıktısını GATE-1/2 ile aynı kart dilinde gösterir.
    Markdown çıktı (gerçek model) doğrudan render edilir; '•/NEDEN' kalıbı (mock)
    yapılandırılmış kartlara çevrilir. Uzun çıktılar katlanabilir bölüme alınır.
    critic=True: itiraz niteliğindeki çıktıyı (Scientific Critic) ayrı kutuda vurgular."""
    no, name, dep = parse_gate_key(key)

    if looks_like_markdown(text):
        def _body():
            if critic:
                st.markdown('<div class="arw-critic-box">', unsafe_allow_html=True)
            st.markdown(text)                      # Streamlit'in kendi Markdown motoru
            if critic:
                st.markdown("</div>", unsafe_allow_html=True)

        if len(text) > _LONG_OUTPUT:
            label = f"{no} · {name}" if no is not None else name
            if dep:
                label += f"  ({dep})"
            with st.expander(label, expanded=expanded):
                _body()
        else:
            with st.container(border=True):
                head = ['<div class="arw-out-head">']
                if no is not None:
                    head.append(f'<span class="arw-agent-no">{no}</span> ')
                head.append(f'<span class="arw-out-title">{html.escape(name)}</span>')
                if dep:
                    head.append(f' <span class="arw-out-dep">{html.escape(dep)}</span>')
                head.append("</div>")
                st.markdown("".join(head), unsafe_allow_html=True)
                _body()
        return

    parts = ['<div class="arw-out-head">']
    if no is not None:
        parts.append(f'<span class="arw-agent-no">{no}</span> ')
    parts.append(f'<span class="arw-out-title">{html.escape(name)}</span>')
    if dep:
        parts.append(f' <span class="arw-out-dep">{html.escape(dep)}</span>')
    parts.append('</div>')

    title, bullets, trailing = _parse_agent_text(text)
    if title:
        parts.append(f'<div class="arw-out-caption">{html.escape(title)}</div>')

    body_parts = []
    if bullets:
        for b in bullets:
            if b["kind"] == "adapt":
                body_parts.append(f'<div class="arw-out-adapt">⚠ {html.escape(b["body"])}</div>')
                continue
            label_html = (f'<span class="arw-out-label">{html.escape(b["label"])}:</span> '
                          if b["label"] else "")
            body_parts.append(f'<div class="arw-out-bullet">{label_html}{html.escape(b["body"])}</div>')
            if b["why"]:
                body_parts.append(f'<div class="arw-out-why">NEDEN: {html.escape(b["why"])}</div>')
    else:
        body_parts.append(f'<div class="arw-out-bullet">{html.escape(text).replace(chr(10), "<br>")}</div>')

    body_html = "".join(body_parts)
    if critic:
        body_html = f'<div class="arw-critic-box">{body_html}</div>'
    parts.append(body_html)

    for kind, content in trailing:
        if kind == "cta":
            parts.append(f'<div class="arw-out-cta">▶ {html.escape(content)}</div>')
        elif kind == "feedback":
            parts.append(f'<div class="arw-out-fb">↻ {html.escape(content)}</div>')
        elif kind == "note":
            parts.append(f'<div class="arw-out-why">{html.escape(content)}</div>')

    with st.container(border=True):
        st.markdown("".join(parts), unsafe_allow_html=True)
