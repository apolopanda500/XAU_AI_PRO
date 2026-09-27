# -*- coding: utf-8 -*-
"""Testes do copiloto e do mapa do EA.

O que estes testes impedem que volte:
  - o copiloto inventar um controle de risco que nao existe;
  - ele "responder" com texto generico quando nao sabe;
  - ele prometer previsao de preco, que os numeros do modelo nao sustentam;
  - ele afirmar que escreve MQL5, o que a regra do projeto proibe.
"""
from __future__ import annotations

import pytest

from backend import copilot, ea_map


class TestMapaEA:
    def test_arvore_do_ea_existe(self):
        inv = ea_map.inventario()
        assert inv["ok"] is True, inv.get("error")

    def test_inventario_tem_linhas(self):
        inv = ea_map.inventario()
        assert inv["total_arquivos"] > 50
        assert inv["total_linhas"] > 10_000

    def test_release_nao_conta_como_codigo_vivo(self):
        arv = ea_map._arvore()  # noqa: SLF001
        vivos = [a["arquivo"] for a in arv["arquivos_vivos"]]
        assert not any(a.startswith("Release/") for a in vivos)

    def test_todo_achado_tem_localizacao(self):
        for a in ea_map.TODOS_ACHADOS:
            assert a.arquivo, f"achado {a.id} sem arquivo"
            assert a.linha, f"achado {a.id} sem linha"
            assert a.titulo and a.descricao and a.por_que_importa

    def test_gravidades_validas(self):
        validas = {"CRITICO", "ALTO", "MEDIO", "BAIXO"}
        for a in ea_map.TODOS_ACHADOS:
            assert a.gravidade in validas, f"achado {a.id}: {a.gravidade}"

    def test_ids_unicos(self):
        ids = [a.id for a in ea_map.TODOS_ACHADOS]
        assert len(ids) == len(set(ids)), "ids de achado duplicados"

    def test_ex5_presente_e_nao_suspeito(self):
        ex5 = ea_map.inventario()["ex5"]
        if ex5.get("bytes"):
            assert ex5["suspeito"] is False, (
                f".ex5 com {ex5['bytes']} bytes parece nao corresponder a fonte"
            )


class TestControlesRisco:
    def test_tem_controles_catalogados(self):
        assert len(ea_map.CONTROLES_DE_RISCO) >= 20

    def test_situacoes_validas(self):
        for c in ea_map.CONTROLES_DE_RISCO:
            assert c.situacao in {"ATIVO", "PARCIAL", "INOPERANTE", "STUB"}

    def test_existe_controle_inoperante_conhecido(self):
        """O mapa tem que registrar que o AutoTrade nao protege."""
        inop = {c.nome for c in ea_map.CONTROLES_DE_RISCO if c.situacao == "INOPERANTE"}
        assert any("AutoTrade" in n for n in inop)

    def test_filtro_por_situacao(self):
        ativos = ea_map.controles_risco("ATIVO")
        assert all(c["situacao"] == "ATIVO" for c in ativos)


class TestFluxo:
    def test_fluxo_tem_passos(self):
        assert len(ea_map.FLUXO_ON_TICK) >= 20

    def test_cadeia_de_entrada_documenta_order_send(self):
        locais = " ".join(p["local"] for p in ea_map.CADEIA_DE_ENTRADA)
        assert "OrderRetry" in locais

    def test_manage_positions_fora_dos_returns(self):
        """Achado estrutural: ManagePositions roda fora de todo early-return."""
        passo = next(p for p in ea_map.FLUXO_ON_TICK if "ManagePositions" in p["acao"])
        assert "SEMPRE" in passo["acao"] or "sempre" in passo.get("nota", "").lower()


class TestDeteccaoDeIntent:
    @pytest.mark.parametrize("pergunta,esperado", [
        ("qual o pior problema do meu EA", "achados"),
        ("achado 4", "achado"),
        ("me mostra os controles de risco", "risco"),
        ("como funciona o OnTick", "fluxo"),
        ("o que acontece sem sinal de IA", "ia"),
        ("o que o EA grava nos dados", "dados"),
        ("onde OrderSend e chamado", "codigo"),
        ("quem e voce", "copiloto"),
        ("qual o preco do ouro agora", "mercado"),
        ("minha conta esta em demo", "conta"),
        ("blablabla sem sentido", "geral"),
    ])
    def test_intents(self, pergunta, esperado):
        assert copilot.detectar_intent(pergunta) == esperado

    def test_conta_nao_ganha_de_posicao(self):
        """'conta' e palavra comum; nao pode roubar a intencao de 'posicao'."""
        assert copilot.detectar_intent("minha conta demo") == "conta"
        assert copilot.detectar_intent("minhas posicoes abertas") == "posicao"


class TestCopilotoResponde:
    def test_pergunta_vazia_nao_quebra(self):
        r = copilot.perguntar("")
        assert r["ok"] is False
        assert r["resposta"]

    def test_achado_por_numero_traz_localizacao(self):
        r = copilot.perguntar("achado 1")
        assert r["ok"] is True
        assert r["intent"] == "achado"
        assert r["achado"]["arquivo"] == "Enterprise/OrderRetry.mqh"
        assert "606" in r["achado"]["linha"]

    def test_achado_inexistente_nao_inventa(self):
        r = copilot.perguntar("achado 9999")
        assert r["ok"] is True
        assert r.get("achado") is None

    def test_resposta_sem_achado_nao_esta_vazia(self):
        for p in ("qual o pior problema", "me mostra os controles de risco",
                  "como funciona o OnTick", "o que acontece sem sinal de IA",
                  "o que o EA grava nos dados", "quem e voce"):
            r = copilot.perguntar(p)
            assert r["ok"] is True
            assert len(r["resposta"]) > 80, f"resposta curta demais para: {p}"

    def test_resposta_menciona_arquivo_e_linha(self):
        """Toda resposta sobre o EA tem de ser citavel."""
        r = copilot.perguntar("me mostra os controles de risco")
        assert ".mqh" in r["resposta"] or ".mq5" in r["resposta"]

    def test_resposta_nao_promete_escrita_de_codigo(self):
        for p in ("quem e voce", "onde OrderSend e chamado", "qual o pior problema"):
            r = copilot.perguntar(p)
            proibido = ("vou corrigir o codigo", "editei o arquivo",
                        "corrigi o OrderRetry", "escrevi no mq5")
            baixo = r["resposta"].lower()
            for frase in proibido:
                assert frase not in baixo, f"copiloto prometeu escrever: {p}"


class TestCopilotoHonesto:
    def test_recusa_previsao_com_justificativa(self):
        r = copilot.perguntar("me inventa uma previsao de direcao")
        baixo = r["resposta"].lower()
        assert "nao faco" in baixo or "não faço" in baixo
        # E tem de trazer o numero que justifica a recusa.
        assert "0,11" in r["resposta"] or "0.11" in r["resposta"]

    def test_nao_diz_que_esta_ok_quando_nao_sabe(self):
        r = copilot.perguntar("xyzzy plugh")
        baixo = r["resposta"].lower()
        assert "nao sei" in baixo or "não sei" in baixo

    def test_declara_limitacao_sobre_mql5(self):
        r = copilot.perguntar("quem e voce")
        baixo = r["resposta"].lower()
        assert "nao escrevo" in baixo or "não escrevo" in baixo
        assert "metatrader" in baixo or "metaeditor" in baixo

    def test_nao_promete_ganho(self):
        """Nenhuma resposta pode conter promessa de retorno."""
        for p in ("qual o pior problema", "o que acontece sem sinal de IA",
                  "qual o preco do ouro agora", "me inventa uma previsao"):
            baixo = copilot.perguntar(p)["resposta"].lower()
            for frase in ("vai render", "garanto lucro", "lucro garantido",
                          "vai subir", "vai cair", "sera lucrativo"):
                assert frase not in baixo, f"promessa de retorno em: {p}"


class TestContextoCopiloto:
    def test_contexto_descreve_o_que_sabe(self):
        ctx = copilot.contexto()
        assert ctx["ok"] is True
        assert ctx["achados_total"] == len(ea_map.TODOS_ACHADOS)
        assert ctx["escreve_codigo"] is False
        assert ctx["previsao_mercado"] is False

    def test_contexto_conta_controles(self):
        ctrl = copilot.contexto()["controles"]
        assert ctrl["total"] == len(ea_map.CONTROLES_DE_RISCO)
        assert ctrl["inoperantes"] >= 1

    def test_cotacao_ausente_nao_quebra(self):
        """Gateway fora do ar nao pode derrubar o copiloto."""
        ctx = copilot.Contexto()
        r = copilot.perguntar("qual o preco do ouro", ctx)
        assert r["ok"] is True
        assert "sem cotacoes" in r["resposta"].lower() or "preco" in r["resposta"].lower()

    def test_gateway_que_lanca_nao_derruba(self):
        def _lanca():
            raise RuntimeError("gateway fora")
        ctx = copilot.Contexto(agora=_lanca)
        r = copilot.perguntar("qual o preco do ouro", ctx)
        assert r["ok"] is True
