# -*- coding: utf-8 -*-
"""Progressão VIP: a escada e as regras que a corretora aplica.

O backend desta feature (`backend/vip_progress.py`) nasceu sem nenhum teste
Python — a suíte contava 662 e nenhum deles exercitava a lógica de nível. Só
havia 5 testes vitest, que verificam a TELA com resposta mockada: se o
backend devolvesse o nível errado, nenhum deles pegaria.

Estes testes fixam as regras que vieram da pesquisa (PrimeXBT e Interactive
Brokers) e, mais importante, os casos em que a resposta honesta é "zero" ou
"recusa" em vez de um número inventado.
"""
from __future__ import annotations

import json

from backend import vip_progress as vp
from backend.vip_progress import NIVEIS, escada_completa


class TestEscadaCompleta:
    """A escada inteira que a tela precisa, e as regras do rotulo `estado`.

    Antes desta mudanca a tela recebia so o nivel alcancado e o proximo: o
    operador via "falta US$ 10.000" sem enxergar quantos degraus existem nem
    onde ele esta. Um nivel solto nao diz se a meta esta longe ou perto.
    """

    def test_escada_tem_todos_os_degraus_na_ordem(self) -> None:
        escada = escada_completa({"cripto": 0.0, "forex_cfd": 0.0}, "regular")
        assert [d["id"] for d in escada] == [n["id"] for n in NIVEIS]

    def test_exatamente_um_degrau_atual(self) -> None:
        """So o proximo degrau e `atual`. Marcar todos diria que o operador
        precisa trabalhar em cinco metas ao mesmo tempo — o que e falso."""
        escada = escada_completa({"cripto": 5_000.0, "forex_cfd": 50_000.0}, "regular")
        assert sum(1 for d in escada if d["estado"] == "atual") == 1
        assert next(d for d in escada if d["estado"] == "atual")["id"] == "vip1"

    def test_no_topo_nao_ha_degrau_atual(self) -> None:
        escada = escada_completa({"cripto": 99_999_999.0, "forex_cfd": 99_999_999.0}, "vip5")
        assert sum(1 for d in escada if d["estado"] == "atual") == 0

    def test_percentual_usa_o_grupo_mais_atrasado(self) -> None:
        """O nivel so conta quando TODOS os grupos passam. Mostrar o melhor
        grupo daria um percentual maior que a realidade."""
        volumes = {"cripto": 100_000.0, "forex_cfd": 5_000.0}
        linha = next(d for d in escada_completa(volumes, "regular") if d["id"] == "vip1")
        # cripto 100000/10000 = 1000% (teto 100); forex 5000/100000 = 5%.
        # O menor manda: 5%.
        assert linha["percentual"] == 5.0

    def test_percentual_preso_em_100(self) -> None:
        escada = escada_completa({"cripto": 50_000_000.0, "forex_cfd": 500_000_000.0}, "regular")
        assert all(0.0 <= d["percentual"] <= 100.0 for d in escada)

    def test_regular_always_100_porque_limiar_e_zero(self) -> None:
        """Divisao por zero produziria NaN e a tela mostraria 'NaN%'."""
        regular = next(d for d in escada_completa({"cripto": 0.0, "forex_cfd": 0.0}, "regular") if d["id"] == "regular")
        assert regular["percentual"] == 100.0

    def test_progresso_expoe_a_escada_e_o_total(self) -> None:
        resultado = vp.progresso()
        assert resultado["escada"], "a API precisa devolver a escada"
        assert resultado["total_degraus"] == len(NIVEIS)
        for linha in resultado["escada"]:
            assert linha["estado"] in {"alcancado", "atual", "futuro"}

    def test_escada_nao_promete_desconto(self) -> None:
        """A escada mostra limiar, nunca preco. O desconto depende de acordo
        comercial e nao esta no sistema."""
        resultado = vp.progresso()
        texto = json.dumps(resultado, ensure_ascii=False).lower()
        assert "desconto de" not in texto


def escrever_audit(tmp_path, monkeypatch, eventos):
    """Grava um audit.jsonl falso e aponta o modulo para ele."""
    base = tmp_path / "XAU_AI_PRO"
    base.mkdir(parents=True, exist_ok=True)
    (base / "audit.jsonl").write_text(
        "\n".join(json.dumps(e) for e in eventos) + "\n", encoding="utf-8"
    )
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return base


def evento(**kwargs):
    base = {
        "at": "2026-10-01T12:00:00+00:00",
        "action": "trade/universal/order",
        "broker": "mt5",
        "status": "executed",
        "volume": 1000.0,
    }
    base.update(kwargs)
    return base


# --------------------------------------------------------------------------
# Ausencia de dado
# --------------------------------------------------------------------------


def test_sem_arquivo_de_auditoria_devolve_zero(tmp_path, monkeypatch):
    """Zero volume e resposta honesta; inventar numero seria tela mentindo."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "vazio"))
    assert vp.volume_por_grupo() == {"cripto": 0.0, "forex_cfd": 0.0}


def test_linha_corrompida_nao_derruba_a_leitura(tmp_path, monkeypatch):
    """Queda de energia deixa linha truncada. Uma linha ruim nao pode
    invalidar as milhares de boas que vem depois dela."""
    base = escrever_audit(tmp_path, monkeypatch, [evento(volume=500.0)])
    caminho = base / "audit.jsonl"
    caminho.write_text(
        '{"quebrado\n' + caminho.read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert vp.volume_por_grupo()["forex_cfd"] == 500.0


# --------------------------------------------------------------------------
# O que conta e o que nao conta
# --------------------------------------------------------------------------


def test_ordem_nao_executada_nao_conta(tmp_path, monkeypatch):
    """Cancelada e recusada nao movimentaram dinheiro."""
    escrever_audit(tmp_path, monkeypatch, [
        evento(volume=999.0, status="failed"),
        evento(volume=888.0, status="pending"),
    ])
    assert vp.volume_por_grupo()["forex_cfd"] == 0.0


def test_ato_sem_volume_nao_conta(tmp_path, monkeypatch):
    """`cancel` nao tem volume; contar seria somar ordem nao executada."""
    escrever_audit(tmp_path, monkeypatch, [
        evento(action="trade/universal/cancel", volume=500.0),
    ])
    assert vp.volume_por_grupo()["forex_cfd"] == 0.0


def test_fora_da_janela_nao_conta(tmp_path, monkeypatch):
    """O que e da janela e o que conta, como na IBKR."""
    escrever_audit(tmp_path, monkeypatch, [
        evento(at="2026-01-01T12:00:00+00:00", volume=10000.0),
        evento(at="2026-10-01T12:00:00+00:00", volume=100.0),
    ])
    assert vp.volume_por_grupo()["forex_cfd"] == 100.0


def test_cripto_e_forex_sao_contados_separadamente(tmp_path, monkeypatch):
    """Limiar muda por grupo. Somar tudo daria nivel errado nos dois."""
    escrever_audit(tmp_path, monkeypatch, [
        evento(broker="binance", volume=6000.0),
        evento(broker="mt5", volume=4000.0),
    ])
    volumes = vp.volume_por_grupo()
    assert volumes["cripto"] == 6000.0
    assert volumes["forex_cfd"] == 4000.0



# --------------------------------------------------------------------------
# A escada
# --------------------------------------------------------------------------


def test_nivel_exige_que_TODOS_os_grupos_passem():
    """Regressao de regra: com cripto alto e forex baixo, o nivel NAO sobe.

    Sem esta exigencia, quem tivesse 500.000 em cripto e 20.000 em forex
    subiria olhando so para o cripto — e perderia o desconto do grupo que
    nao atingiu.
    """
    resultado = vp.nivel_por_volume({"cripto": 500_000.0, "forex_cfd": 20_000.0})
    assert resultado["nivel"] == "regular"


def test_escada_sobe_na_ordem_dos_limiares():
    for cripto, forex, esperado in [
        (0, 0, "regular"),
        (12_000, 150_000, "vip1"),
        (150_000, 2_000_000, "vip2"),
        (30_000_000, 95_000_000, "vip5"),
    ]:
        r = vp.nivel_por_volume({"cripto": float(cripto), "forex_cfd": float(forex)})
        assert r["nivel"] == esperado, f"{cripto}/{forex} deveria ser {esperado}"


def test_proximo_e_o_primeiro_nao_alcancado():
    """Regressao real: a primeira versao apontava o proximo como o primeiro
    da lista e mostrava "falta 0" para quem ja tinha passado dele."""
    r = vp.nivel_por_volume({"cripto": 12_000.0, "forex_cfd": 150_000.0})
    assert r["proximo"]["nome"] == "VIP 2"
    assert r["proximo"]["falta_por_grupo"]["cripto"] == 88_000.0


def test_no_maximo_nao_ha_proximo():
    r = vp.nivel_por_volume({"cripto": 1e9, "forex_cfd": 1e9})
    assert r["nivel"] == "vip5"
    assert r["proximo"] is None


# --------------------------------------------------------------------------
# Regras da pesquisa e travas
# --------------------------------------------------------------------------


def test_promocao_nao_e_imediata():
    """Regra da IBKR: o nivel novo vale no dia seguinte, nao no instante.

    Sem isto, o operador opera no ultimo minuto achando que o desconto ja
    vale.
    """
    assert vp.DIAS_ATE_PROMOCAO == 1
    assert vp.progresso()["dias_ate_promocao"] == 1


def test_nivel_alcancado_trava_por_30_dias():
    """Regra del PrimeXBT: sem a trava, um mes fraco tiraria o cliente do
    nivel no meio do ciclo."""
    assert vp.JANELA_DIAS == 30
    assert vp.progresso()["trava_dias"] == 30


def test_progressao_nao_habilita_dinheiro_real():
    """A trava e declarada no payload: um cliente que acredite ter liberado
    saque por subir de nivel e o pior desfecho possivel."""
    resultado = vp.progresso()
    assert resultado["withdrawals_enabled"] is False
    assert resultado["live_execution"] is False


def test_catalogo_nao_expoe_saque():
    """Nenhum nivel pode ter entitlement de saque ou transferencia."""
    proibidos = {"saque", "withdrawal", "transfer", "transferencia", "resgate"}
    for nivel in vp.NIVEIS:
        beneficios = {b.lower() for b in nivel["beneficios"]}
        assert not (beneficios & proibidos), f"{nivel['id']} expoe {beneficios & proibidos}"


def test_limiares_sao_crescentes():
    """Um nivel mais alto com limiar menor faria a escada voltar atras."""
    for anterior, atual in zip(vp.NIVEIS, vp.NIVEIS[1:]):
        for grupo, minimo in atual["minimo_por_grupo"].items():
            assert minimo >= anterior["minimo_por_grupo"][grupo], (
                f"{atual['id']} tem limiar menor que {anterior['id']} em {grupo}"
            )
