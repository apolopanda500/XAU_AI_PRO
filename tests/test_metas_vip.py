# -*- coding: utf-8 -*-
"""Metas e travas do VIP: compra OU volume, e Free nunca usa multi.

Cada teste aqui trava uma regra do `backend/metas_vip.py`. As regras que
tem prova automatizada sao as que o dono definiu — *"FREE nao pode usar
multi"*, *"operou x volume OU comprou 100$"* — e a regra que resolve a
duplicata: **volume nao compra plano**.
"""
from __future__ import annotations

import pytest

from backend.metas_vip import (
    METAS,
    PRECO_PRO_USD,
    avaliar,
    multi_model_liberado,
)

ZERO = {"cripto": 0.0, "forex_cfd": 0.0}
# Volume que cumpre a meta PRO (10k cripto, 100k forex).
PRO_CUMPRIDO = {"cripto": 10_000.0, "forex_cfd": 100_000.0}
ALTO = {"cripto": 500_000.0, "forex_cfd": 5_000_000.0}


class TestFreeNuncaUsaMulti:
    """Regra do dono, com reforco contra arquivo adulterado."""

    def test_free_sem_volume(self):
        assert multi_model_liberado("free", ZERO) is False

    def test_free_com_volume_que_cumpre_pro(self):
        # O caso que o plano tem que fechar: mesmo com o volume batendo,
        # o Free nao abre. Se um dia isto virar True, o Free destrava multi.
        assert multi_model_liberado("free", PRO_CUMPRIDO) is False

    def test_free_com_volume_absurdo(self):
        assert multi_model_liberado("free", {"cripto": 9e12, "forex_cfd": 9e12}) is False

    def test_plano_gratuito_desconhecido_nao_libera(self):
        # `subscriptions.json` editado a mao: um id inventado nao pode virar
        # topo da escada. Fail-closed.
        assert multi_model_liberado("lifetime", PRO_CUMPRIDO) is False
        assert multi_model_liberado("", PRO_CUMPRIDO) is False
        assert multi_model_liberado(None, PRO_CUMPRIDO) is False


class TestOsDoisCaminhos:
    """Compra OU volume — nunca os dois."""

    def test_plano_pago_destrava_sem_volume(self):
        assert multi_model_liberado("vip", ZERO) is True
        assert multi_model_liberado("vips", ZERO) is True

    def test_volume_alto_com_plano_pago(self):
        assert multi_model_liberado("vip", ALTO) is True


class TestVolumeNaoCompraPlano:
    """A regra que resolve a duplicata reportada pelo dono."""

    def test_volume_alto_no_free_nao_destrava(self):
        assert multi_model_liberado("free", ALTO) is False

    def test_meta_pro_ficou_no_catalogo_com_os_dois_caminhos(self):
        meta = next(m for m in METAS if m.libera == "multi_model")
        assert meta.plano_por_compra, "meta precisa de um caminho por compra"
        assert meta.minimo_por_grupo, "meta precisa de um caminho por volume"


class TestEscada:
    def test_todos_os_degraus_aparecem(self):
        # Um degrau futuro mostra o limiar; esconder seria promessa de
        # desconto que o sistema nao pode cumprir.
        assert len(avaliar("free", ZERO)["escada"]) == len(METAS)

    def test_compra_marca_a_meta_como_alcancada(self):
        escada = avaliar("vip", ZERO)["escada"]
        por_id = {d["id"]: d["estado"] for d in escada}
        assert por_id["livre"] == "alcancado"
        assert por_id["pro"] == "alcancado"

    def test_proxima_meta_e_unica(self):
        assert avaliar("vip", ZERO)["proxima"]["id"] == "vip"

    def test_degraus_futuros_vem_antes_do_atual_na_ordem(self):
        estados = [d["estado"] for d in avaliar("free", ZERO)["escada"]]
        assert estados == ["alcancado", "atual", "futuro"]


class TestPercentual:
    def test_usa_o_grupo_mais_atrasado(self):
        # Cripto 100% (10k/10k) e forex 0% => a PRO fica em 0%. Mostrar 100%
        # aqui seria dizer "cumprida" enquanto ainda falta 100k no forex.
        # Este e o caso que a regra do PrimeXBT protege.
        so_cripto = {"cripto": 10_000.0, "forex_cfd": 0.0}
        assert avaliar("free", so_cripto)["escada"][1]["percentual"] == 0.0

    def test_dos_grupos_no_limiar_marca_cem(self):
        # PRO_CUMPRIDO tem os dois grupos no limiar: 100% e 100%.
        assert avaliar("free", PRO_CUMPRIDO)["escada"][1]["percentual"] == 100.0

    def test_50_por_cento_nos_dois_grupos(self):
        volume = {"cripto": 5_000.0, "forex_cfd": 50_000.0}
        assert avaliar("free", volume)["escada"][1]["percentual"] == 50.0

    def test_volume_completo_marca_cem(self):
        assert avaliar("free", PRO_CUMPRIDO)["escada"][1]["percentual"] == 100.0

    def test_falta_e_informada_por_grupo_na_meta_atual(self):
        # Free sem nada: PRO e o proximo alvo, e a falta vem por grupo.
        falta = avaliar("free", ZERO)["proxima"]["falta_por_grupo"]
        assert falta["cripto"] == 10_000.0
        assert falta["forex_cfd"] == 100_000.0

    def test_cumprida_por_volume_marca_a_meta(self):
        assert avaliar("free", PRO_CUMPRIDO)["escada"][1]["estado"] == "alcancado"
        assert avaliar("free", PRO_CUMPRIDO)["metas_alcancadas"][0]["caminhos"] == ["volume"]

    def test_proxima_passa_a_ser_a_meta_vip_apos_cumprir_pro(self):
        # Cumprir PRO por volume tira PRO do alvo; o proximo vira VIP, e a
        # falta passa a ser a DA VIP (90k / 900k), nao mais 0 / 100k.
        proxima = avaliar("free", PRO_CUMPRIDO)["proxima"]
        assert proxima["id"] == "vip"
        assert proxima["falta_por_grupo"] == {"cripto": 90_000.0, "forex_cfd": 900_000.0}


class TestNenhumaMetaDestravaDinheiro:
    def test_avaliacao_nunca_declara_movimento_de_dinheiro(self):
        for plano in ("free", "vip", "vips"):
            for volume in (ZERO, PRO_CUMPRIDO, ALTO):
                estado = avaliar(plano, volume)
                assert estado["live_execution"] is False
                assert estado["withdrawals_enabled"] is False

    def test_preco_de_referencia_declarado(self):
        assert PRECO_PRO_USD == 100.0
        meta = next(m for m in METAS if m.libera == "multi_model")
        assert meta.preco_usd == PRECO_PRO_USD


def test_catalogo_nao_declara_saque_em_nenhuma_meta():
    # Trava dupla: a string nao aparece no modulo inteiro.
    fonte = (__import__("pathlib").Path(__file__).resolve().parents[1]
             / "backend" / "metas_vip.py").read_text(encoding="utf-8")
    assert '"withdrawals_enabled": True' not in fonte
    assert "'withdrawals_enabled': True" not in fonte