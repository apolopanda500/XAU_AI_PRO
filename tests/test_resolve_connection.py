# -*- coding: utf-8 -*-
"""resolve_connection: SESSAO ignora o mercado gravado; API key filtra.

O QUE FOI MEDIDO (22/10/2026, maquina real)
===========================================
Duas conexoes MT5 ativas em `connections.dpapi.json`, AMBAS gravadas como
`market=forex` — a tela pede um mercado ao cadastrar e o operador escolhe
forex. XAUUSD e `metal` na hierarquia que a corretora publica, entao o motor
chamava `resolve_connection("", "mt5", "metals")` e levava 0 matches:

    LookupError: conexão ativa não encontrada

...para uma conta que existia, estava logada e ativa. O motor morria antes de
enviar; o operador via sintoma de CONTA e o defeito era do FILTRO (AGENTS.md 5).

A REGRA NOVA
============
Credencial de SESSAO (MT5) e o terminal logado, que serve TODOS os mercados
da corretora — o `market` gravado na conexao e rotulo do cadastro, nao filtro
de acesso. Credencial de API KEY (binance/mexc/bybit/okx) CONTINUA filtrando:
spot e futuros sao endpoints diferentes, com permissoes e riscos diferentes.

PROVAS NEGATIVAS
================
Toda correcao aqui vem com o caso que teria de reprovar: o filtro de mercado
da API key nao pode ter morrido junto, e conta inativa nao pode voltar a
resolver.

O store e gravado num `tmp_path` (APPDATA isolado): nenhum arquivo do
operador e lido nem alterado, e nenhum DPAPI e usado (o JSON e escrito
direto — resolve so LE).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.connection_store import resolve_connection

#: Duas contas de sessao ativas, ambas rotuladas como forex — o estado
#: MEDIDO da maquina do dono (XMGlobal real + MetaQuotes-Demo).
SESSAO_XM = {
    "broker": "mt5", "market": "forex", "active": True,
    "credential_source": "session",
}
SESSAO_DEMO = {
    "broker": "mt5", "market": "forex", "active": True,
    "credential_source": "session",
}


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """APPDATA isolado: o resolve lê o store deste tmp, nunca o do operador."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def gravar(dados: dict, tmp_path: Path) -> None:
    pasta = tmp_path / "XAU AI PRO"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "connections.dpapi.json").write_text(
        json.dumps(dados, ensure_ascii=False), encoding="utf-8"
    )


class TestSessaoIgnoraOMercadoGravado:
    """O rotulo do cadastro nao pode barrar o terminal logado."""

    def test_xauusd_metals_acha_a_conta_gravada_como_forex(self, store):
        """A PROVA do defeito medido: metals resolve a conexao rotulada forex.

        Com o filtro antigo este era o 0 matches que derrubava o ciclo do
        motor em toda iteracao.
        """
        gravar({"mt5:forex:XMGlobal": SESSAO_XM}, store)
        conta = resolve_connection("", "mt5", "metals")
        assert conta["id"] == "mt5:forex:XMGlobal"

    def test_pedido_com_a_conta_escolhida_tambem_ignora_o_rotulo(self, store):
        """O caminho do motor com account_id escolhido: id + mercado do ativo."""
        gravar({"mt5:forex:XMGlobal": SESSAO_XM}, store)
        conta = resolve_connection("mt5:forex:XMGlobal", "mt5", "metals")
        assert conta["id"] == "mt5:forex:XMGlobal"

    def test_outro_broker_de_sessao_nao_casa(self, store):
        """Ignorar MERCADO nao e ignorar CORRETORA: broker continua exigido."""
        gravar({"mt5:forex:XMGlobal": SESSAO_XM}, store)
        with pytest.raises(LookupError):
            resolve_connection("", "outro-broker", "metals")


class TestApiKeyContinuaFiltrandoPorMercado:
    """PROVA NEGATIVA: spot e futuros sao mundos diferentes, e continuam sendo.

    Se a correcao da sessao tivesse afrouxado o filtro TODO, uma conta
    spot resolveria como futuros — permissao e risco trocados em silencio.
    """

    MEXC_SPOT = {
        "broker": "mexc", "market": "crypto-spot", "active": True,
        "credential_source": "api_key",
    }

    def test_spot_nao_resolve_como_futures(self, store):
        gravar({"mexc:crypto-spot:principal": self.MEXC_SPOT}, store)
        with pytest.raises(LookupError, match="não encontrada"):
            resolve_connection("", "mexc", "crypto-futures")

    def test_spot_resolve_no_seu_proprio_mercado(self, store):
        """O filtro nao quebrou para o lado certo: o match legitimo continua."""
        gravar({"mexc:crypto-spot:principal": self.MEXC_SPOT}, store)
        conta = resolve_connection("", "mexc", "crypto-spot")
        assert conta["id"] == "mexc:crypto-spot:principal"

    def test_conta_escolhida_nao_vence_o_filtro_de_mercado(self, store):
        """Escolher o ID explicitamente nao pode furar o filtro da API key."""
        gravar({"mexc:crypto-spot:principal": self.MEXC_SPOT}, store)
        with pytest.raises(LookupError, match="incompatível"):
            resolve_connection("mexc:crypto-spot:principal", "mexc", "crypto-futures")


class TestDuasContasExigemEscolhaDoOperador:
    """A recusa multiple e por design: escolher entre contas e decisao humana."""

    def test_sem_account_id_recusa_com_o_motivo_certo(self, store):
        gravar({
            "mt5:forex:XMGlobal": SESSAO_XM,
            "mt5:forex:Demo": SESSAO_DEMO,
        }, store)
        with pytest.raises(LookupError, match="account_id"):
            resolve_connection("", "mt5", "metals")

    def test_com_account_id_devolve_exatamente_a_escolhida(self, store):
        """A escolha que o painel manda via /api/auto/config chega inteira."""
        gravar({
            "mt5:forex:XMGlobal": SESSAO_XM,
            "mt5:forex:Demo": SESSAO_DEMO,
        }, store)
        conta = resolve_connection("mt5:forex:Demo", "mt5", "metals")
        assert conta["id"] == "mt5:forex:Demo"

    def test_conta_desativada_nao_resolve_nem_com_o_id_na_mao(self, store):
        """PROVA NEGATIVA: `active: false` continua barrando — a correcao do
        rotulo nao pode ter virado porta aberta para conta desligada."""
        morta = dict(SESSAO_DEMO, active=False)
        gravar({"mt5:forex:Demo": morta}, store)
        with pytest.raises(LookupError):
            resolve_connection("mt5:forex:Demo", "mt5", "forex")

    def test_uma_unica_conta_continua_resolvendo_sozinha(self, store):
        """Sem escolha multipla o motor continua decidindo so — sem account_id."""
        gravar({"mt5:forex:XMGlobal": SESSAO_XM}, store)
        conta = resolve_connection("", "mt5", "forex")
        assert conta["id"] == "mt5:forex:XMGlobal"
