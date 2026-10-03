"""Prova manual do copiloto. Nao substitui os testes — mostra o texto real."""
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend import copilot as c

PERGUNTAS = [
    "qual o pior problema do meu EA",
    "achado 4",
    "me mostra os controles de risco",
    "como funciona o OnTick",
    "o que acontece sem sinal de IA",
    "onde OrderSend e chamado",
    "o que o EA grava nos dados",
    "quem e voce",
    "qual o preco do ouro agora",
    "me inventa uma previsao de direcao",
]

for p in PERGUNTAS:
    r = c.perguntar(p)
    print("=" * 74)
    print("PERGUNTA:", p)
    print("intent :", r["intent"])
    print("-" * 74)
    print(r["resposta"][:900])
    print()
