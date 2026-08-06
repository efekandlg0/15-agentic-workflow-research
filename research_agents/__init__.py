"""15 araştırma ajanı, faz faz tanımlı. Hepsini tek yerden içe aktarır."""
from .phase1 import literature_agent, verification_agent, gap_agent
from .phase2 import methodology_agent, benchmark_agent, risk_agent
from .phase3 import environment_agent, rl_coding_agent, training_agent, testing_agent
from .phase4 import statistical_agent, ablation_agent, critic_agent
from .phase5 import writing_agent, review_agent

__all__ = [
    "literature_agent", "verification_agent", "gap_agent",
    "methodology_agent", "benchmark_agent", "risk_agent",
    "environment_agent", "rl_coding_agent", "training_agent", "testing_agent",
    "statistical_agent", "ablation_agent", "critic_agent",
    "writing_agent", "review_agent",
]
