"""Montaj: tüm node'ları ve GATE'leri tek bir LangGraph akışında birleştirir.

  PHASE-1  literature → verification → gap → GATE-1
  PHASE-2  [methodology ∥ benchmark ∥ risk] → GATE-2
  PHASE-3  environment → rl_coding → training → testing → GATE-3
  PHASE-4  [statistical ∥ ablation] → critic → GATE-4
  PHASE-5  writing → review → GATE-5 → (bitir)
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .common import ResearchState, PHASE2, PHASE3_START, PHASE4, PHASE5_START
from .nodes import (
    literature_node, verification_node, gap_node,
    methodology_node, benchmark_node, risk_node,
    environment_node, rl_coding_node, training_node, testing_node,
    statistical_node, ablation_node, critic_node,
    writing_node, review_node,
)
from .gates import (
    gate1_node, gate1_router, gate2_node, gate2_router,
    gate3_node, gate3_router, gate4_node, gate4_router,
    gate5_node, gate5_router,
)


def build_graph(checkpointer=None):
    b = StateGraph(ResearchState)
    nodes = [
        ("literature", literature_node), ("verification", verification_node), ("gap", gap_node),
        ("gate1", gate1_node),
        ("methodology", methodology_node), ("benchmark", benchmark_node), ("risk", risk_node),
        ("gate2", gate2_node),
        ("environment", environment_node), ("rl_coding", rl_coding_node),
        ("training", training_node), ("testing", testing_node), ("gate3", gate3_node),
        ("statistical", statistical_node), ("ablation", ablation_node), ("critic", critic_node),
        ("gate4", gate4_node),
        ("writing", writing_node), ("review", review_node), ("gate5", gate5_node),
    ]
    for name, fn in nodes:
        b.add_node(name, fn)

    # PHASE-1
    b.add_edge(START, "literature")
    b.add_edge("literature", "verification")
    b.add_edge("verification", "gap")
    b.add_edge("gap", "gate1")
    b.add_conditional_edges("gate1", gate1_router,
                            ["literature", "verification", "gap"] + PHASE2)

    # PHASE-2 → GATE-2
    for n in PHASE2:
        b.add_edge(n, "gate2")
    b.add_conditional_edges("gate2", gate2_router, PHASE2 + ["gate1", PHASE3_START])

    # PHASE-3 → GATE-3
    b.add_edge("environment", "rl_coding")
    b.add_edge("rl_coding", "training")
    b.add_edge("training", "testing")
    b.add_edge("testing", "gate3")
    b.add_conditional_edges("gate3", gate3_router,
                            ["environment", "rl_coding", "training", "testing"]
                            + PHASE4 + ["gate2"])

    # PHASE-4: [statistical ∥ ablation] → critic → GATE-4
    b.add_edge("statistical", "critic")
    b.add_edge("ablation", "critic")
    b.add_edge("critic", "gate4")
    b.add_conditional_edges("gate4", gate4_router,
                            PHASE4 + ["critic", PHASE5_START, "gate3"])

    # PHASE-5: writing → review → GATE-5
    b.add_edge("writing", "review")
    b.add_edge("review", "gate5")
    b.add_conditional_edges("gate5", gate5_router,
                            ["writing", "review", "gate4", END])

    return b.compile(checkpointer=checkpointer or InMemorySaver())


graph = build_graph()