# -*- coding: utf-8 -*-
"""Governanca do MULTI: o que ele pode destravar e o que nunca destrava.

O QUE ESTES TESTES TRAVAM
=========================
O MULTI e o benefit do plano PRO. Tres regras do dono:

1. *"FREE nao pode usar multi"* — o Free nunca destrava, e nao por trust no
   arquivo: o `plan_id` gravado e conferido alem do entitlement.
2. Nenhum modelo destrava **dinheiro real**, saque ou transferencia.
3. Modelo reprovado pelo quality gate **nao entra** como carregavel, e o
   `.meta.json` guarda o motivo.

O terceiro precisa do `.spec` alem do Python: `train_multi` e ferramenta de
treino e roda FORA do app. Quem le os artefatos e `ai_inference`, que e
empacotado — por isso o teste olha os artefatos de verdade, no disco.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.asset_classes import (
    CLASSES_COM_DADO,
    CLASSES_SEM_DADO,
    classe_de,
    nome_do_modelo_multi,
    simbolos_da_classe,
)

MODELOS = Path(__file__).resolve().parents[1] / "frontend" / "src-tauri" / "Python" / "models"


def _meta(classe: str) -> dict:
    caminho = MODELOS / f"{nome_do_modelo_multi(classe)}.meta.json"
    if not caminho.exists():
        pytest.skip(f"artefato ausente (treine a classe {classe}): {caminho.name}")
    return json.loads(caminho.read_text(encoding="utf-8"))


class TestFreeNuncaUsaMulti:
    """Regra 1, com reforco duplo."""

    def test_catalogo_free_tem_multi_model_desligado(self):
        from app.subscriptions import _PLAN_CATALOG

        assert _PLAN_CATALOG["free"]["entitlements"]["multi_model"] is False
        assert _PLAN_CATALOG["free"]["limits"]["multi_models"] == 0

    def test_acesso_bloqueia_multi_no_free(self, monkeypatch):
        """O Free nao usa multi — com o Free injetado, nao com o plano da maquina.

        Este teste JA falhou uma vez por ler o `subscriptions.json` da maquina:
        quem rodou tinha `vips` gravado e recebeu `True`, enquanto o dono
        executando com `free` receberia `False`. Teste que depende do disco
        local nao e teste — e、事故 que so aparece em uma das maquinas.

        Aqui o Free e injetado explicitamente, entao o resultado e o mesmo em
        qualquer maquina e com qualquer assinatura gravada.
        """
        from backend import acesso

        assinatura_free = {
            "plan_id": "free",
            "active": True,
            "entitlements": {"multi_model": False},
            "limits": {"multi_models": 0},
            "degraded": False,
        }
        monkeypatch.setattr(acesso, "plano_atual", lambda user_id=None: assinatura_free)

        assert acesso.pode_usar_multi_modelo() is False
        assert acesso.limite_multi_modelos() == 0

    def test_plano_desconhecido_tambem_bloqueia(self):
        """`plan_id` adulterado no arquivo nao vira topo da escada."""
        from backend.metas_vip import multi_model_liberado

        for plano in ("", "lifetime", "admin", None):
            assert multi_model_liberado(plano) is False, plano


class TestNenhumModeloDestravaDinheiro:
    """Regra 2, medida nos artefatos reais."""

    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_meta_declara_travas(self, classe):
        meta = _meta(classe)
        assert meta["live_execution"] is False
        assert meta["withdrawals_enabled"] is False
        assert meta["transfers_enabled"] is False

    def test_arvore_de_acesso_nao_declara_movimento(self):
        # Alem dos artefatos, a arvore que a tela le tambem declara.
        from backend.acesso import acesso

        arvore = acesso()
        assert arvore["live_execution"] is False
        assert arvore["withdrawals_enabled"] is False


class TestQualidadeDoArtefato:
    """Regra 3 — o gate e o que decide se o modelo entra."""

    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_publicado_requer_edge_estavel(self, classe):
        meta = _meta(classe)
        if not meta["publicable"]:
            # Reprovado e valido desde que o motivo esteja gravado.
            assert meta["publish_reason"], "reprovado sem motivo"
            return
        assert meta["metrics"]["edge_estavel"] is True, (
            "publicado com edge instavel — o gate nao foi respeitado"
        )

    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_reprovado_nao_tem_pkl(self, classe):
        meta = _meta(classe)
        if meta["publicable"]:
            return
        assert not (MODELOS / f"{nome_do_modelo_multi(classe)}.pkl").exists(), (
            "modelo reprovado tem .pkl: a tela o mostraria e o gateway nao "
            "conseguiria carregar"
        )

    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_publicado_tem_pkl(self, classe):
        meta = _meta(classe)
        if not meta["publicable"]:
            pytest.skip(f"{classe} reprovado")
        assert (MODELOS / f"{nome_do_modelo_multi(classe)}.pkl").exists()

    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_folds_expanding_window(self, classe):
        # `train` cresce de fold em fold. Sem isso, o walk-forward estaria
        # testando no passado e o edge medido seria mentira.
        folds = _meta(classe)["metrics"]["folds"]
        for anterior, seguinte in zip(folds, folds[1:]):
            assert seguinte["train"] > anterior["train"]


class TestContratoDoArtefato:
    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_feature_version_estacionaria(self, classe):
        meta = _meta(classe)
        assert meta["feature_version"] == "25F-est-v1"
        assert meta["model_type"] == "multi"

    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_nome_sem_timeframe(self, classe):
        # O dono definiu MULTI sem sufixo: um so artefato opera todos os
        # horarios. Se voltar `MULTI_CRYPTO_H1`, a regra foi quebrada.
        #
        # A regra e sobre o SUFIXO de timeframe, nao sobre o underscore: o
        # proprio nome `MULTI_CRYPTO` tem underscore e esta certo. Verificar
        # `'_' not in nome` reprovaria o nome correto.
        nome = nome_do_modelo_multi(classe)
        sufixos_de_timeframe = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1")
        for sufixo in sufixos_de_timeframe:
            assert not nome.endswith(f"_{sufixo}"), (
                f"{nome} tem sufixo de timeframe: quebraria a regra do MULTI "
                "unico (um artefato para todos os horarios)"
            )
        meta = _meta(classe)
        assert len(meta["timeframes"]) >= 2, "MULTI com um so timeframe nao e multi"

    @pytest.mark.parametrize("classe", CLASSES_COM_DADO)
    def test_simbolos_batem_com_a_classe(self, classe):
        meta = _meta(classe)
        declarados = set(meta["metrics"]["symbols"])
        for simbolo in declarados:
            assert classe_de(simbolo) == classe, (
                f"{simbolo} foi treinado em {classe} mas pertence a "
                f"{classe_de(simbolo)}"
            )
        assert declarados & set(simbolos_da_classe(classe)), (
            f"nenhum simbolo de {classe} no modelo"
        )

    def test_amostragem_declarada(self):
        """Se houve corte, o `.meta.json` diz — a tela le esse arquivo."""
        for classe in CLASSES_COM_DADO:
            m = _meta(classe)["metrics"]
            if m.get("amostra_estratificada"):
                assert m["train_samples"] < m["train_samples_bruto"]
            else:
                assert m["train_samples"] == m["train_samples_bruto"]


class TestClasseSemDado:
    """O plano nao pode prometer o que o dataset nao tem."""

    @pytest.mark.parametrize("classe", CLASSES_SEM_DADO)
    def test_classe_sem_dado_nao_tem_artefato(self, classe):
        caminho = MODELOS / f"{nome_do_modelo_multi(classe)}.meta.json"
        assert not caminho.exists(), (
            f"{classe} foi declarada sem dado mas existe artefato — ou o "
            "dado chegou (atualize CLASSES_COM_DADO) ou o modelo e falso"
        )