"""Gera Docs/MATRIZ_CAPABILIDADES.md a partir do registro real do gateway.

A matriz nao e escrita a mao: `backend/broker_registry.py` e a fonte, e o
gateway expoe a mesma informacao em `/api/capabilities` e
`/api/universal/capabilities`. Assim o documento nao pode prometer mais do que o
sistema entrega.

Uso:  .\\.venv\\Scripts\\python.exe scripts\\gerar_matriz_capacidades.py [--check]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.broker_registry import BROKERS, capability_matrix  # noqa: E402

DESTINO = ROOT / "Docs" / "MATRIZ_CAPABILIDADES.md"

AVISO = """# Matriz de capabilities por corretora e mercado

> Gerado por `scripts/gerar_matriz_capacidades.py` a partir de
> `backend/broker_registry.py`. **Nao editar a mao**: a fonte da verdade e o
> registro, e `--check` reprova se o arquivo estiver desatualizado.
>
> Dados publicos: {data}

## Como ler

- **OK**: o endpoint responde com dado real da corretora.
- **unavailable**: declarado honestamente pelo gateway. Ausencia de dado e
  declarada, nunca preenchida com valor inventado.
- **unsupported**: o adaptador nao implementa este endpoint para a corretora.
  O gateway responde com `status: unsupported` e lista vazia — nunca com `ok`
  e dado fabricated.

## Leitura de dados

{leitura}

## Execucao

Nenhuma corretora executa ordem real nesta versao. `execution` esta vazio em
todas as linhas e `withdrawals`/`transfers` sao `false` em todas. Isso e
intencional: a ordem real depende de uma etapa explicita e separada, com conta
demo validada, teste de rejeicao, auditoria e kill switch conferidos.

## Corretoras ainda planejadas

{planejadas}

## Cobertura por familia de dado

{cobertura}

## O que esta declarado e nao entregue

- **DOM e negocios recentes no MT5**: o terminal nao expoe book de ofertas via
  esta ponte. `/api/universal/depth?broker=mt5` responde `unavailable` com o
  motivo, e nao com lista vazia.
- **Conta em corretora de exchange** (Bybit, OKX, Binance, MEXC): exige
  credencial configurada pelo usuario via `backend/connection_store.py` com
  DPAPI. Sem credencial, o gateway declara `unavailable`; nunca tenta sem.
- **XM Global e demais corretoras MT5**: nao sao adaptadores separados. Toda
  corretora com terminal MT5 e acessada pelo adaptador `mt5`, que descobre os
  simbolos reais em `GET /api/assets`. XM Global, XM.COM, Pepperstone e
  qualquer outra MT5 funcionam pelo mesmo caminho.
"""


def _tabela(colunas: list[str], linhas: list[list[str]]) -> str:
    cabecalho = "| " + " | ".join(colunas) + " |"
    sep = "| " + " | ".join("---" for _ in colunas) + " |"
    corpo = ["| " + " | ".join(linha) + " |" for linha in linhas]
    return "\n".join([cabecalho, sep, *corpo])


def gerar() -> str:
    hoje = date.today().isoformat()
    matriz = capability_matrix(include_planned=True)

    leitura: list[list[str]] = []
    for row in matriz:
        if row["status"] == "planned":
            continue
        leitura.append([
            f"`{row['broker']}`",
            f"`{row['market']}`",
            "OK" if row["read_only"] else "nao",
            f"`{row['status']}`",
            ", ".join(f"`{c}`" for c in row["capabilities"]) or "nenhuma",
        ])

    planejadas = [
        [f"`{r['broker']}`", f"`{r['market']}`", "planejada", "nenhuma"]
        for r in matriz if r["status"] == "planned"
    ]
    if not planejadas:
        planejadas = [["-", "-", "-", "-"]]

    endpoints = [
        ("assets", "catalogo de ativos", "MT5 e as 4 exchanges"),
        ("quotes", "cotacao de um ativo", "MT5 e as 4 exchanges"),
        ("batch_quotes", "cotacao em lote", "MT5 e as 4 exchanges"),
        ("candles", "velas por timeframe", "MT5 e as 4 exchanges"),
        ("depth", "book de ofertas", "4 exchanges; MT5 nao expoe"),
        ("trades", "negocios recentes", "4 exchanges; MT5 nao expoe"),
        ("stats24h", "estatisticas 24h", "4 exchanges; MT5 nao expoe"),
        ("account", "conta e saldo", "MT5 e as 4 exchanges, com credencial"),
        ("positions", "posicoes abertas", "MT5 e as 4 exchanges, com credencial"),
        ("history", "historico de trades", "MT5 e as 4 exchanges, com credencial"),
        ("orders", "ordens", "somente MT5"),
        ("journal", "journal do terminal", "somente MT5"),
    ]
    cobertura = [f"| `{c[0]}` | {c[1]} | {c[2]} |" for c in endpoints]

    return AVISO.format(
        data=hoje,
        leitura=_tabela(["Corretora", "Mercado", "Leitura", "Status", "Capabilities"], leitura),
        planejadas=_tabela(["Corretora", "Mercado", "Status", "Capabilities"], planejadas),
        cobertura=_tabela(["Endpoint", "Dado", "Onde funciona"], cobertura),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera a matriz de capabilities")
    parser.add_argument("--check", action="store_true", help="verifica se o arquivo esta atualizado")
    args = parser.parse_args()

    conteudo = gerar()
    if args.check:
        atual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if atual != conteudo:
            print("MATRIZ_DESATUALIZADA: rode sem --check para regenerar.")
            return 1
        print("matriz atualizada.")
        return 0

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(conteudo, encoding="utf-8")
    print(f"gerado: {DESTINO.relative_to(ROOT)}")
    print(f"corretoras ativas: {', '.join(b.id for b in BROKERS.values() if b.status == 'active')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
