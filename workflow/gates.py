"""GATE node'ları (insan kontrolü) ve router'lar.
Karar: onayla (ileri) / tekrarla (seçilen ajanlardan yeniden) / geri (önceki kapıya).
Mesajlar KISA tutuldu; onayla/tekrarla/geri seçenekleri arayüz kontrolleriyle sunulur.
Her çıktı, üreten AJANIN adıyla etiketlenir.
"""
from langgraph.graph import END
from langgraph.types import interrupt

from .common import parse_decision, repeat_entry, PHASE2, PHASE3_START, PHASE4, PHASE5_START


# ----------------- GATE-1 -----------------
def gate1_node(state):
    raw = interrupt({
        "gate": "GATE-1",
        "mesaj": "Puanlı literatür ve boşluklarla devam edelim mi? Kararını aşağıdan ver.",
        "1 · Literature Search Agent": state["literature_output"],
        "2 · Verification Agent": state["verification_output"],
        "3 · Research Gap Agent": state["gap_output"],
    })
    a, fb, agents = parse_decision(raw)
    if a == "onayla":
        return {"gate1_action": "onayla", "human_research_question": fb, "feedback": ""}
    return {"gate1_action": "tekrarla", "feedback": fb, "repeat_target": repeat_entry("gate1", agents)}


def gate1_router(state):
    if state.get("gate1_action") == "onayla":
        return PHASE2
    return state.get("repeat_target", "literature")


# ----------------- GATE-2 -----------------
def gate2_node(state):
    raw = interrupt({
        "gate": "GATE-2",
        "mesaj": "Bu yöntemle uygulamaya geçelim mi? Kararını aşağıdan ver.",
        "4 · Methodology Design Agent": state["methodology_output"],
        "5 · Benchmark Agent": state["benchmark_output"],
        "6 · Risk Analysis Agent": state["risk_output"],
    })
    a, fb, agents = parse_decision(raw)
    out = {"gate2_action": a, "feedback": fb if a != "onayla" else ""}
    if a == "tekrarla":
        out["repeat_target"] = repeat_entry("gate2", agents)
    if a == "geri":
        out["human_research_question"] = ""
        out["gate1_action"] = ""
    return out


def gate2_router(state):
    a = state.get("gate2_action")
    if a == "onayla":
        return PHASE3_START
    if a == "geri":
        return "gate1"
    return state.get("repeat_target", PHASE2)


# ----------------- GATE-3 (Phase-2 yöntemine bağlı çıktılar) -----------------
def gate3_node(state):
    raw = interrupt({
        "gate": "GATE-3",
        "mesaj": ("Bu uygulama planıyla eğitime geçelim mi? Çıktılar Phase-2 yöntemine göre "
                  "türetildi. Eğitimi kendi donanımında çalıştırıp gerçek sonuçları 'onayla' notuna yaz."),
        "7 · Environment Agent (Phase-2 yöntemine bağlı)": state["environment_output"],
        "8 · RL Coding Agent (onaylanan algoritmaya bağlı)": state["rl_coding_output"],
        "9 · Training Agent (yöntemin doğasına bağlı)": state["training_output"],
        "10 · Testing Agent (Phase-2 metriklerine bağlı)": state["testing_output"],
    })
    a, fb, agents = parse_decision(raw)
    out = {"gate3_action": a, "feedback": fb if a != "onayla" else ""}
    if a == "onayla":
        out["training_results"] = fb or "(sonuç notu girilmedi)"
    if a == "tekrarla":
        out["repeat_target"] = repeat_entry("gate3", agents)
    if a == "geri":
        out["gate2_action"] = ""
    return out


def gate3_router(state):
    a = state.get("gate3_action")
    if a == "onayla":
        return PHASE4
    if a == "geri":
        return "gate2"
    return state.get("repeat_target", PHASE3_START)


# ----------------- GATE-4 -----------------
def gate4_node(state):
    raw = interrupt({
        "gate": "GATE-4",
        "mesaj": "Bilimsel katkı geçerli mi? Critic'in itirazlarını değerlendirip kararını ver.",
        "11 · Statistical Analysis Agent": state["statistical_output"],
        "12 · Ablation Study Agent": state["ablation_output"],
        "13 · Scientific Critic Agent": state["critic_output"],
    })
    a, fb, agents = parse_decision(raw)
    out = {"gate4_action": a, "feedback": fb if a != "onayla" else ""}
    if a == "tekrarla":
        out["repeat_target"] = repeat_entry("gate4", agents)
    if a == "geri":
        out["gate3_action"] = ""
    return out


def gate4_router(state):
    a = state.get("gate4_action")
    if a == "onayla":
        return PHASE5_START
    if a == "geri":
        return "gate3"
    return state.get("repeat_target", PHASE4)


# ----------------- GATE-5 -----------------
def gate5_node(state):
    raw = interrupt({
        "gate": "GATE-5",
        "mesaj": "Makale gönderime hazır mı? Kararını aşağıdan ver.",
        "14 · Writing Agent": state["writing_output"],
        "15 · Scientific Review Agent": state["review_output"],
    })
    a, fb, agents = parse_decision(raw)
    out = {"gate5_action": a, "feedback": fb if a != "onayla" else ""}
    if a == "onayla":
        out["final_decision"] = fb or "Makale gönderime hazır"
    if a == "tekrarla":
        out["repeat_target"] = repeat_entry("gate5", agents)
    if a == "geri":
        out["gate4_action"] = ""
    return out


def gate5_router(state):
    a = state.get("gate5_action")
    if a == "onayla":
        return END
    if a == "geri":
        return "gate4"
    return state.get("repeat_target", PHASE5_START)