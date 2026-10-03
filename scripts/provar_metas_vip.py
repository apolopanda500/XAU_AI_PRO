# -*- coding: utf-8 -*-
"""Prova manual das regras de meta e trava do VIP.

Nao substitui `tests/test_metas_vip.py` — este script existe para rodar as
mesmas regras e MOSTRAR o resultado, para dar para conferir o comportamento
sem abrir um terminal de teste. Uso:

    .\.venv\Scripts\python.exe scripts\provar_metas_vip.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.metas_vip import METAS, PRECO_PRO_USD, avaliar, multi_model_liberado  # noqa: E402

OK = "\033[92mOK\033[0m"
NOK = "\033[91mFALHA\033[0m"
VOLUME_ALTO = {"cripto": 500_000.0, "forex_cfd": 5_000_000.0}
VOLUME_ZERO = {"cripto": 0.0, "forex_cfd": 0.0}

falhas: list[str] = []


def checa(descricao: str, obtido: object, esperado: object) -> None:
    ok = obtido == esperado
    if not ok:
        falhas.append(descricao)
    marca = OK if ok else NOK
    print(f"  [{marca}] {descricao}: {obtido!r} (esperado {esperado!r})")


print(f"\nPreco de referencia do PRO: US$ {PRECO_PRO_USD:.0f}")
print(f"Metas no catalogo: {', '.join(m.id for m in METAS)}\n")

print("REGRA DO DONO: FREE NUNCA USA MULTI")
checa("free sem volume", multi_model_liberado("free", VOLUME_ZERO), False)
checa("free com volume zero", multi_model_liberado("free", VOLUME_ZERO), False)
checa("free com volume que cumpre PRO", multi_model_liberado("free", VOLUME_ALTO), False)
checa("free com volume absurdo", multi_model_liberado("free", {"cripto": 9e12, "forex_cfd": 9e12}), False)

print("\nOS DOIS CAMINHOS (compra OU volume)")
checa("vip comprado sem volume", multi_model_liberado("vip", VOLUME_ZERO), True)
checa("vips comprado sem volume", multi_model_liberado("vips", VOLUME_ZERO), True)

print("\nVOLUME NAO COMPRA PLANO")
checa("free + volume alto", multi_model_liberado("free", VOLUME_ALTO), False)

print("\nFAIL-CLOSED (plano adulterado no disco)")
for plano in ["", "vip_pro", "admin", "SUPER", None, "lifetime"]:
    checa(f"plano {plano!r}", multi_model_liberado(plano, VOLUME_ZERO), False)

print("\nESCADA MOSTRA TODOS OS DEGRAUS")
estado = avaliar("vip", VOLUME_ZERO)
checa("total de degraus", len(estado["escada"]), len(METAS))
estados = [d["estado"] for d in estado["escada"]]
checa("livre e alcancado", estados[0], "alcancado")
checa("pro e alcancado (comprou vip)", estados[1], "alcancado")
checa("vip e o proximo", estados[2], "atual")
checa("metas alcancadas", [m["id"] for m in estado["metas_alcancadas"]], ["pro"])
checa("multi_model ligado", estado["multi_model"], True)
checa("live_execution nunca", estado["live_execution"], False)
checa("withdrawals nunca", estado["withdrawals_enabled"], False)

print("\nPROGRESSO PERCENTUAL")
# Cripto 100% (10k/10k) e forex 0%: o percentual e o do GRUPO MAIS ATRASADO.
# Mostrar 100% aqui seria dizer "meta cumprida" enquanto falta 100k no forex.
parcial = avaliar("free", {"cripto": 10_000.0, "forex_cfd": 0.0})
checa("PRO parcial usa o grupo mais atrasado", parcial["escada"][1]["percentual"], 0.0)
checa("PRO nao cumplriu", parcial["escada"][1]["estado"], "atual")
checa("falta no forex informada", parcial["proxima"]["falta_por_grupo"]["forex_cfd"], 100_000.0)
checa("falta no cripto e zero", parcial["proxima"]["falta_por_grupo"]["cripto"], 0.0)

meio = avaliar("free", {"cripto": 5_000.0, "forex_cfd": 50_000.0})
checa("PRO em 50% nos dois grupos", meio["escada"][1]["percentual"], 50.0)

cheio = avaliar("free", {"cripto": 10_000.0, "forex_cfd": 100_000.0})
checa("PRO completo", cheio["escada"][1]["percentual"], 100.0)
checa("PRO cumprido por volume", cheio["escada"][1]["estado"], "alcancado")
checa("caminho declarado", cheio["metas_alcancadas"][0]["caminhos"], ["volume"])

print("\nGRUPO MAIS ADIANTADO NAO CONTA SOZINHO")
misto = avaliar("vip", {"cripto": 10_000.0, "forex_cfd": 0.0})
checa("PRO nao cumpriu so com cripto", misto["escada"][1]["estado"], "alcancado")  # via compra
so_cripto = avaliar("free", {"cripto": 10_000.0, "forex_cfd": 0.0})
checa("free so com cripto nao cumpre", so_cripto["escada"][1]["estado"], "atual")

print()
if falhas:
    print(f"{len(falhas)} REGRA(S) FALHARAM:")
    for f in falhas:
        print(f"  - {f}")
    raise SystemExit(1)
print("Todas as regras de meta e trava conferidas.")