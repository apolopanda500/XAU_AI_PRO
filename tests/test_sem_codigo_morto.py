"""Nenhuma pasta de codigo de produto pode ficar sem ninguem a importar.

O QUE HOUVE
===========
A remocao das integracoes (Vercel, Sentry, Slack, Kilo e a CDN de modelos)
deixou dois arquivos inteiros sem nenhum import: `app/deploy_vercel.py` e
`Python/model_manager.py`. Os dois continuaram no repositorio e passaram por
toda revisao, porque codigo morto **nao falha** — ele apenas nao faz nada.
Nem o CI nem o build detectam: a suite passa (arquivo orfao nao quebra
teste) e o PyInstaller so embaralha o que ja existe.

O MESMO PROBLEMA, MENOR
========================
`app/tabs/settings.py` importava `model_max_ram_mb` e `model_n_jobs` sem
usar nenhum dos dois. Orfao antes de qualquer remocao.

POR QUE BUSCA POR NOME, E NAO POR IMPORT
=========================================
A primeira versao deste teste procurava `from risk_manager import ...` e
declarou 103 arquivos "mortos". Errado: `Python/core/trade_gate.py` importa
`risk_manager` de dentro do mesmo pacote, e o caminho relativo
(`from .risk_manager import` ou `from risk_manager import` executado com
`Python/core` no `sys.path`) nao casa com o padrao de import absoluto.

Ou seja: **a busca precisa ser pelo NOME, em qualquer forma de uso** —
import, `importlib`, atributo, string de configuracao. So assim a pergunta
"alguem usa isto?" tem a resposta certa.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# Arquivos que sao executados direto (ponto de entrada) e portanto nao
# precisam ser importados. Os `__init__.py` tambem entram aqui.
PONTOS_DE_ENTRADA = {
    "__init__.py",
    "conftest.py",
    "setup.py",
}

# Extensoes em que a referencia por nome conta como uso.
EXTENSOES = ("*.py", "*.cjs", "*.mjs", "*.ts", "*.tsx", "*.rs", "*.spec",
             "*.bat", "*.ps1", "*.mqh", "*.mq5")


def _git_grep(termo: str) -> list[str]:
    """Arquivos versionados que citam `termo` em codigo (nao em Docs)."""
    try:
        proc = subprocess.run(
            ["git", "grep", "-l", "-I", "-E", rf"\b{termo}\b", "--", *EXTENSOES],
            cwd=RAIZ, capture_output=True, text=True, timeout=180,
        )
    except (OSError, subprocess.SubprocessError):
        return []  # sem git: nao afirmar codigo morto
    return [linha for linha in proc.stdout.splitlines() if linha.strip()]


class TestSemCodigoMorto:
    """Cada modulo de produto precisa ter pelo menos um consumidor."""

    def _modulos_de_produto(self) -> list[Path]:
        achados: list[Path] = []
        for pasta in ("app", "backend", "Python", "core/src", "mcp", "core"):
            base = RAIZ / pasta
            if not base.exists():
                continue
            for p in base.rglob("*.py"):
                partes = set(p.parts)
                if "__pycache__" in partes or "node_modules" in partes:
                    continue
                achados.append(p)
        return sorted(set(achados))

    def test_todo_modulo_de_produto_tem_consumidor(self):
        """Varre o repositorio inteiro e devolve a lista do que sobrou orfao.

        Fica como UM teste em vez de varios porque a saida precisa ser a
        lista inteira: um `assert` por arquivo mostraria so o primeiro
        orfao e esconderia o resto.
        """
        mortos: dict[str, str] = {}

        for arquivo in self._modulos_de_produto():
            if arquivo.name in PONTOS_DE_ENTRADA:
                continue
            rel = arquivo.relative_to(RAIZ).as_posix()

            # Arquivo de teste nao e modulo de produto: e verificado pela
            # propria suite, nao por import.
            if arquivo.name.startswith("test_"):
                continue

            nome = arquivo.stem
            citadas = {c.replace("\\", "/") for c in _git_grep(nome)}

            # O PROPRIO arquivo nao conta como consumidor: `ai_inference.py`
            # define o nome, nao o usa. Sem esta exclusao o teste acusou 101
            # modulos "mortos" que sao o produto inteiro.
            citadas.discard(rel)

            # Executavel por comando tem ponto de entrada em `__main__` e nao
            # precisa de import: `forward_test.py` e `stress_test.py` sao
            # rodados direto, e sao justamente o que a AGENTS.md exige antes
            # de ordem real.
            if "__main__" in arquivo.read_text(encoding="utf-8", errors="replace"):
                continue

            if not citadas:
                mortos[rel] = "nenhum arquivo de codigo cita este nome"

        assert not mortos, (
            "modulos de produto sem nenhum consumidor (codigo morto):\n"
            + "\n".join(f"  - {k}: {v}" for k, v in sorted(mortos.items()))
            + "\n\nOu cada modulo entra no produto (importe onde faz sentido), "
              "ou sai do git. Arquivo orfao nao falha em teste nenhum: por "
              "isso precisa deste teste."
        )
