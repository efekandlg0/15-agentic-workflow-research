"""Komut satırı sürücüsü (CLI). GATE'lerde durur, insan girdisini alır, devam eder.

Çalıştırma:
  MOCK_LLM=1 python run.py     # ücretsiz, anahtarsız (sahte ajanlar)
  python run.py                # gerçek model (.env içinde OPENAI_API_KEY gerekir)
"""
import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from workflow import graph

load_dotenv()


def _print_gate(payload):
    print("\n" + "=" * 64)
    print(f"  🚪 {payload['gate']} — İNSAN KONTROLÜ GEREKLİ")
    print("=" * 64)
    print(payload["mesaj"])
    for key, value in payload.items():
        if key in ("gate", "mesaj"):
            continue
        print(f"\n--- {key} ---\n{value}")
    print("-" * 64)


def main():
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    state_input = {
        "topic": "RL tabanlı wheel-legged quadruped robotlarda enerji verimli hareket kontrolü"
    }
    while True:
        result = graph.invoke(state_input, config)
        if "__interrupt__" in result:
            _print_gate(result["__interrupt__"][0].value)
            cevap = input("Kararınız > ").strip()
            state_input = Command(resume=cevap)
        else:
            print("\n✅ Workflow tamamlandı.")
            print("\nNihai karar:", result.get("final_decision", "(yok)"))
            break


if __name__ == "__main__":
    main()
