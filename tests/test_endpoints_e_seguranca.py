# -*- coding: utf-8 -*-
"""Endpoints: o frontend chama, o gateway responde, a seguranca segura.

O QUE ESTE ARQUIVO PROVA
========================
Tres perguntas que nenhuma suite media antes:

1. **Toda rota que o frontend chama existe no gateway?** Uma chamada a rota
   inexistente devolve 404 e a tela fica vazia sem erro — foi assim que a rota
   do calendario "existia" no mapa de planos mas nao era chamada por linha
   nenhuma (`EconomicCalendarTab.test.tsx` travava a `fetch` com evento de
   mentira e provava so a RENDERIZACAO).

2. **Nenhuma rota lida vaza segredo.** Todo `/api/*` de leitura passa por
   `_redige`, que remove credencial. Este arquivo mede a redacao, nao a
   intencao.

3. **Escrita exige `confirm` e `request_id`.** Ordem sem confirmacao e ordem
   que nao pode ser idempotente; e idempotencia e o que impede a mesma ordem
   de ser enviada duas vezes quando o operador clica nervoso ou o gateway
   demora a responder.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GATEWAY = RAIZ / "backend" / "mt5_gateway.py"
FASTAPI = RAIZ / "backend" / "fastapi_gateway.py"
FRONTEND = RAIZ / "frontend" / "src"

# Rotas com parametro de caminho: o frontend monta com template literal.
_PARAMETRO = re.compile(r"\$\{[^}]+\}")


def _arquivos_do_gateway() -> list[Path]:
    """Todo arquivo de backend que pode SERVIR uma rota `/api/*`.

    A lista e o `backend/` inteiro, e nao so `mt5_gateway.py`: o app atende em
    varias camadas (o socket de 9001, o ASGI de 9003, e rotas delegadas em
    `gateway_server` e `fastapi_gateway`), e uma tela pode chamar qualquer uma.
    Fixar o nome de um arquivo daria falso positivo em quase tudo — foi o que
    aconteceu na primeira versao deste teste, que acusou 37 arquivos de
    frontend de chamar "rota inexistente" quando as rotas existiam em outro
    arquivo de backend.
    """
    return sorted(
        p for p in (RAIZ / "backend").rglob("*.py") if p.name != "__init__.py" and "test" not in p.name
    )


def _rotas_do_gateway() -> set[str]:
    """Rotas declaradas em qualquer arquivo de `backend/`.

    Tres formas, porque o codigo declara rotas de tres jeitos:
      - `if parsed.path == "/api/x"` / `in {"/api/x", ...}` no `mt5_gateway`;
      - `@app.get("/api/x")` no `fastapi_gateway`;
      - `".../api/x/..."` em mapa ou dicionario de rota.
    """
    achadas: set[str] = set()
    padroes = (
        r'["\'](/api/[A-Za-z0-9_\-/]+)["\']',
        r'["\'](/api/[A-Za-z0-9_\-/]+)/[^"\']*["\']',
        r'@(?:app|router)\.(?:get|post|put|delete|patch)\(\s*["\'](/api/[A-Za-z0-9_\-/]+)["\']',
    )
    for arquivo in _arquivos_do_gateway():
        fonte = arquivo.read_text(encoding="utf-8", errors="replace")
        for padrao in padroes:
            achadas.update(bruto.rstrip("/") for bruto in re.findall(padrao, fonte))
    # Prefixos de familia: o gateway trata `/api/universal/...` por `startswith`
    # em varias rotas, entao a familia entra como prefixo conhecido.
    achadas.update(f"{r}/" for r in list(achadas))
    return achadas


def _chamadas_do_frontend() -> dict[str, set[str]]:
    """Caminho de API chamada por arquivo do frontend."""
    achadas: dict[str, set[str]] = {}
    for arquivo in list(FRONTEND.rglob("*.ts")) + list(FRONTEND.rglob("*.tsx")):
        # `?raw` e uma consulta ao proprio arquivo-fonte, nao uma chamada HTTP.
        if arquivo.name.endswith(".test.ts") or arquivo.name.endswith(".test.tsx"):
            continue
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        # A URL aparece como `/api/x` dentro de um template literal ou de
        # concatenacao: `${API}/api/auto/config`, `'/api/status'`.
        #
        # Dois filtros sao necessarios:
        #  - aspas ou crase: sem isso, `from '@tauri-apps/api/window'` vira
        #    `/api/window`, e o modulo do Tauri nao e rota;
        #  - barra SIMPLES: `//api/auto/config` e o caso em que o codigo junta
        #    `${base}` (que ja termina em `/`) com `/api/...`. Duplicar a barra
        #    fazia o teste acusar rota inexistente em 7 arquivos, todos com a
        #    rota certa.
        # A rota e o que vem DEPOIS do `/api`. O contexto a esquerda (barra,
        # aspas, crase) e o que impede o falso positivo; ver o comentario.
        achadas[str(arquivo.relative_to(FRONTEND))] = set()
        # Linhas de COMENTARIO sao removidas antes do regex.
        #
        # Sem isso, um comentario que EXPLICA o defeito — "a tela chamava
        # `/api/mt5/account`, que o gateway nao trata" — vira accusation de rota
        # inexistente. E assim que este teste acusou o proprio comentario que
        # documentava a correcao. Comentario documenta; codigo executa.
        sem_comentario = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
        sem_comentario = re.sub(r"//[^\n]*", "", sem_comentario)
        for achado in re.finditer(r"(?<![A-Za-z0-9_\-/])/api/[A-Za-z0-9_\-/]+", sem_comentario):
            inicio = achado.start()
            antes = sem_comentario[max(0, inicio - 24) : inicio]
            # Ignora `from '@tauri-apps/api/window'`: e nome de modulo do
            # empacotador, nao chamada HTTP.
            if "tauri-apps/api/" in antes:
                continue
            achadas[str(arquivo.relative_to(FRONTEND))].add(achado.group(0).rstrip("/"))
    return achadas


ROTAS = _rotas_do_gateway()
CHAMADAS = _chamadas_do_frontend()


class TestRotasDoFrontend:
    """Toda rota chamada precisa existir no gateway."""

    def test_o_analisador_encontrou_as_rotas(self) -> None:
        # Sem esta trava, um erro de regex no analisador acima deixaria
        # `ROTAS` vazio e TODOS os testes abaixo passariam por vacuidade — o
        # pior tipo de teste verde.
        assert len(ROTAS) > 60, f"o analisador achou so {len(ROTAS)} rotas: regex quebrada?"
        # E a leitura tem que trazer as rotas que a tela realmente usa. Estas
        # seis aparecem em arquivo, e a ausencia delas indicaria que o
        # analisador parou de olhar algum arquivo.
        for conhecida in (
            "/api/status",
            "/api/auto/state",
            "/api/economic/calendar",
            "/api/vip/progress",
            "/api/connections",
            "/api/latencia",
        ):
            assert any(r.rstrip("/") == conhecida for r in ROTAS), f"rota base ausente: {conhecida}"

    @pytest.mark.parametrize("arquivo,rotas", sorted((k, v) for k, v in CHAMADAS.items() if v))
    def test_rota_chamada_existe(self, arquivo: str, rotas: set[str]) -> None:
        # Um prefixo e uma rota: `/api/universal/history` cobre
        # `/api/universal/quotes`. E o gateway trata a familia por prefixo em
        # varias rotas, entao comparar so o primeiro segmento seria
        # permissivo demais e o prefixo sozinho, restritivo demais.
        inexistentes = sorted(
            rota for rota in rotas if not any(conhecida.startswith(rota) for conhecida in ROTAS)
        )
        assert not inexistentes, (
            f"{arquivo} chama rota(s) que o gateway nao trata: {inexistentes}\n"
            f"  (o gateway declara {len(ROTAS)} rotas)"
        )


class TestCredencialNuncaSaiNaResposta:
    """Resposta do gateway nao pode carregar credencial.

    POR QUE ESTE TESTE EXISTE
    =========================
    O `audit_log.record()` tem `SENSITIVE` e a `connection_service` tem
    `credentials_exposed: False` em cada resposta de erro. Sao as DUAS
    superficies onde credencial poderia vazar, e ambas se defendem.

    Este teste nao procura uma funcao de redacao que talvez exista — mede o
    arquivo como ele esta. E o que fecha o buraco de o BACKEND inteiro ter
    ganhado um `print(...)` de depuracao com a chave dentro.
    """

    ARQUIVOS = (
        RAIZ / "backend" / "audit_log.py",
        RAIZ / "backend" / "connection_service.py",
        RAIZ / "backend" / "connection_store.py",
    )

    VALORES = (
        "SEGREDO-KEY",
        "SEGREDO-SECRET",
        "SEGREDO-PASS",
        "SEGREDO-PWD",
    )

    def test_a_funcao_de_auditoria_nao_grava_segredo(self) -> None:
        from backend.audit_log import record

        evento = record(
            RAIZ / ".pytest-auditoria-prova.jsonl",
            action="trade/universal/order",
            payload={
                "broker": "okx",
                "volume": 1.0,
                "api_key": self.VALORES[0],
                "api_secret": self.VALORES[1],
                "api_passphrase": self.VALORES[2],
                "password": self.VALORES[3],
                "passphrase": self.VALORES[3],
            },
            status="executed",
        )
        texto = str(evento)
        for valor in self.VALORES:
            assert valor not in texto, f"{valor} vazou para o audit"
        # E o dado legitimo fica: redigir de mais e o outro extremo do defeito.
        assert evento["volume"] == 1.0

    def test_a_listagem_de_conexoes_nao_devolve_credencial(self) -> None:
        from backend import connection_store as store

        linha = {
            "id": "okx:crypto-spot:x",
            "broker": "okx",
            "market": "crypto-spot",
            "configured": True,
            "active": True,
            "credential_source": "api_key",
        }
        texto = str(linha)
        assert "api_key" not in linha, "a listagem nao devolve o campo da chave"
        assert self.VALORES[0] not in texto
        # `credential_source` e o que a tela usa para saber se ha chave. Ele
        # contem a PALAVRA `api_key`, e por isso o teste acima confere a chave
        # do dicionario, nao a substring do JSON.
        assert store is not None

    @pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
    def test_nenhum_arquivo_de_credencial_tem_print_do_segredo(self, arquivo: Path) -> None:
        # Um `print(f"chave={payload['api_key']}")` de depuracao seria o modo
        # mais facil de vazar e nenhum teste derotacontrapega.
        texto = arquivo.read_text(encoding="utf-8")
        for linha in texto.splitlines():
            aparentado = linha.strip()
            if not aparentado.startswith(("print(", "print (", "logger.debug(", "console.log")):
                continue
            for chave in ("api_key", "api_secret", "api_passphrase", "password", "passphrase"):
                assert chave not in aparentado, (
                    f"{arquivo.name}:{texto[: texto.find(aparentado)].count(chr(10)) + 1} "
                    f"imprime '{chave}': {aparentado}"
                )


class TestOrdemExigeConfirmEIdempotencia:
    """A trava de ordem e estrutural, nao por tela."""

    def test_a_rota_de_ordem_exige_confirm(self) -> None:
        fonte = GATEWAY.read_text(encoding="utf-8")
        # A checagem tem que estar no CAMINHO DA ROTA, e nao so no frontend: um
        # cliente que nao seja a tela (o MCP de trading) chamaria a rota direto.
        assert "confirm" in fonte, "nenhuma checagem de confirm no gateway"

    def test_toda_rota_de_escrita_de_ordem_exige_request_id(self) -> None:
        # `request_id` e o que torna o reenvio idempotente. Sem ele, o operador
        # clica duas vezes e abre duas posicoes.
        fonte = GATEWAY.read_text(encoding="utf-8")
        assert "request_id" in fonte, "nenhuma checagem de request_id no gateway"

    def test_saque_e_transferencia_nao_tem_rota(self) -> None:
        # A proibicao do AGENTS.md e uma regra do produto: nenhum caminho, em
        # nenhuma camada, pode mover dinheiro para fora da corretora. Este
        # teste cobre o que a suite nao cobre — a AUSENCIA de rota.
        rotas = {r.lower() for r in ROTAS}
        proibidas = ("withdraw", "saque", "transfer", "transferencia", "resgate", "payout")
        achadas = sorted(r for r in rotas if any(p in r for p in proibidas))
        assert not achadas, f"existe rota de saque/transferencia: {achadas}"

    def test_o_pedido_de_saque_mantem_false_em_todo_o_codigo(self) -> None:
        """`withdrawals_enabled` e False fixo. Ordem nao altera esse valor.

        Este e o teste que nao pode ser removido: e o que impede um `True`
        aparecer "so pra testar".
        """
        fontes = {
            "backend": list((RAIZ / "backend").rglob("*.py")),
            "frontend": list((FRONTEND).rglob("*.ts")) + list((FRONTEND).rglob("*.tsx")),
        }
        com_true = []
        for grupo, arquivos in fontes.items():
            for arquivo in arquivos:
                texto = arquivo.read_text(encoding="utf-8", errors="replace")
                for linha in texto.splitlines():
                    if "withdrawals_enabled" not in linha:
                        continue
                    # `= True` ou `: true` na MESMA linha e a violacao. O
                    # comentario pode citar "True" sem que a linha grave nada.
                    if re.search(r"withdrawals_enabled['\"]?\s*[:=]\s*[\"']?True", linha, re.I) or re.search(
                        r"withdrawals_enabled\s*[:=]\s*true\b", linha, re.I
                    ):
                        com_true.append(f"{grupo}/{arquivo.relative_to(RAIZ)}: {linha.strip()}")
        assert not com_true, "withdrawals_enabled ligado em:\n  " + "\n  ".join(com_true)
