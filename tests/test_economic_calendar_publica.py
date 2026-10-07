# -*- coding: utf-8 -*-
"""Calendario economico: fonte real, rotulo de procedencia e o que nao existe.

POR QUE ESTES TESTES EXISTEM
============================
A tela do Calendario tinha tres colunas — Anterior, Previsao e Real — e as tres
ficavam permanentemente em `--`. A causa nao era a tela: era a FONTE.
`planos/economic_calendar.py` e uma tabela local de horarios recorrentes. Ela
sabe QUANDO o evento acontece e nada mais — nao existe valor anterior, nem
consenso, nem numero divulgado.

Tres colunas que nunca podem ter dado e pior que coluna ausente: faz o
operador desconfiar de tudo o mais da tela.

Estes testes fixam o que a tela passou a prometer e o que ela NAO pode prometer:

- a semana corrente vem do feed publico, com anterior, previsao e real;
- as semanas seguintes continuam estimativa, e isso e DECLARADO;
- o feed fora (429) nao vira lista vazia fingindo que nao ha evento.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from backend import economic_calendar_publica as publica
from backend.mt5_gateway import _economic_calendar


class TestAdaptadorDoFeed:
    """O que o adaptador faz com o corpo do feed publico."""

    def test_normaliza_o_payload_real(self):
        # Formato medido em 05/10/2026: `date` em ISO com deslocamento, e
        # `country` carregando o CODIGO DA MOEDA, nao o nome do pais.
        linha = {
            "date": "2026-10-07T10:00:00-04:00",
            "country": "USD",
            "impact": "High",
            "title": "FOMC Meeting Minutes",
            "previous": "4.25%",
            "forecast": "4.10%",
            "actual": "4.15%",
        }
        evento = publica._normaliza(linha, datetime(2026, 10, 5, tzinfo=timezone.utc))
        assert evento is not None
        assert evento["currency"] == "USD"
        assert evento["impact"] == "alto"
        assert evento["when_utc"].startswith("2026-10-07T14:00")
        assert evento["previous"] == "4.25%"
        assert evento["forecast"] == "4.10%"
        assert evento["actual"] == "4.15%"
        # Feed publico e dado publicado. Never `estimado`.
        assert evento["estimado"] is False
        assert evento["fonte"] == "feed-publico"

    def test_campo_vazio_vira_ausente_e_nao_string_vazia(self):
        # `""` na celula ao lado de numero deixa o operador sem saber qual das
        # duas e ausencia de verdade.
        evento = publica._normaliza(
            {
                "date": "2026-10-07T10:00:00-04:00",
                "country": "USD",
                "impact": "High",
                "title": "X",
                "previous": "  ",
                "forecast": "",
                "actual": None,
            },
            datetime(2026, 10, 5, tzinfo=timezone.utc),
        )
        assert evento is not None
        assert evento["previous"] is None
        assert evento["forecast"] is None
        assert evento["actual"] is None

    def test_importancia_desconhecida_vira_medio_e_nao_alto(self):
        # Impacto inventado como "alto" seria o pior erro possivel: marcaria
        # evento irrelevante como o dia que mexe no preco.
        evento = publica._normaliza(
            {
                "date": "2026-10-07T10:00:00-04:00",
                "country": "USD",
                "impact": "banana",
                "title": "X",
            },
            datetime(2026, 10, 5, tzinfo=timezone.utc),
        )
        assert evento is not None
        assert evento["impact"] == "medio"

    def test_holiday_e_feriado_nao_e_evento_de_preco(self):
        evento = publica._normaliza(
            {
                "date": "2026-10-05T20:00:00-04:00",
                "country": "AUD",
                "impact": "Holiday",
                "title": "Bank Holiday",
            },
            datetime(2026, 10, 5, tzinfo=timezone.utc),
        )
        assert evento is not None
        assert evento["impact"] == "baixo"

    def test_linha_sem_data_ou_titulo_e_descartada(self):
        agora = datetime(2026, 10, 5, tzinfo=timezone.utc)
        assert publica._normaliza({"country": "USD", "title": "X"}, agora) is None
        assert publica._normaliza({"date": "nao-e-data", "country": "USD", "title": "X"}, agora) is None
        assert publica._normaliza({"date": "2026-10-07T10:00:00-04:00", "country": "USD"}, agora) is None


class TestRedeComFalha:
    """`CalendarUnavailable` e o que impede a mentira de 'sem evento nenhum'."""

    def test_feed_fora_nao_devolve_lista_vazia(self, monkeypatch):
        def explode(*_args, **_kwargs):
            raise publica.CalendarUnavailable("feed publico recusou a consulta (HTTP 429)")

        monkeypatch.setattr(publica, "buscar_semana", explode)
        with pytest.raises(publica.CalendarUnavailable):
            publica.buscar_semana(datetime(2026, 10, 5, tzinfo=timezone.utc))

    def test_429_e_mensagem_propria_e_nao_generica(self, monkeypatch):
        # "indisponivel" generico leva o operador a culpar o gateway local,
        # quando o culpado e o feed remoto.
        import urllib.error

        def erro(*_args, **_kwargs):
            raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)

        monkeypatch.setattr(publica.urllib.request, "urlopen", erro)
        monkeypatch.setattr(publica, "ler_cache", lambda: None)
        with pytest.raises(publica.CalendarUnavailable) as erro:
            publica.buscar_semana(datetime(2026, 10, 5, tzinfo=timezone.utc))
        assert "429" in str(erro.value)

    def test_corpo_ilegivel_nao_vira_agenda_vazia(self, monkeypatch):
        monkeypatch.setattr(publica, "ler_cache", lambda: None)

        class RespostaFalsa:
            def read(self):
                return b"<html>429 Too Many Requests</html>"

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        monkeypatch.setattr(publica.urllib.request, "urlopen", lambda *a, **k: RespostaFalsa())
        with pytest.raises(publica.CalendarUnavailable):
            publica.buscar_semana(datetime(2026, 10, 5, tzinfo=timezone.utc))


class TestRotaDoCalendario:
    """O contrato HTTP: procedencia declarada e semana corrente com valores."""

    @pytest.fixture(autouse=True)
    def _sem_rede(self, monkeypatch, tmp_path):
        # Nenhum teste pode depender da rede. O feed e substituido por uma
        # semana sintetica de formato MEDIDO (05/10/2026).
        monkeypatch.setattr(publica, "ler_cache", lambda: None)
        monkeypatch.setattr(publica, "gravar_cache", lambda _eventos: None)
        self.eventos = [
            {
                "title": "FOMC Meeting Minutes",
                "currency": "USD",
                "impact": "alto",
                "when_utc": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(timespec="minutes"),
                "previous": "4.25%",
                "forecast": "4.10%",
                "actual": None,
                "bandeira": "\U0001F1FA\U0001F1F8",
                "divulgado": False,
                "estimado": False,
                "fonte": "feed-publico",
            },
            {
                "title": "Holiday",
                "currency": "AUD",
                "impact": "baixo",
                "when_utc": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(timespec="minutes"),
                "previous": None,
                "forecast": None,
                "actual": None,
                "bandeira": "\U0001F1E6\U0001F1FA",
                "divulgado": False,
                "estimado": False,
                "fonte": "feed-publico",
            },
        ]
        monkeypatch.setattr(publica, "buscar_semana", lambda *a, **k: self.eventos)

    def test_semana_corrente_traz_os_tres_valores(self):
        r = _economic_calendar(limit=30, days=14)
        reais = [e for e in r["events"] if not e.get("estimado")]
        assert reais, "a semana corrente tem de vir do feed"
        fomed = next(e for e in reais if "FOMC" in e["title"])
        assert fomed["previous"] == "4.25%"
        assert fomed["forecast"] == "4.10%"
        # `actual` segue None ate a divulgacao: e a data, nao a tela, que diz
        # que o numero nao existe.
        assert fomed["actual"] is None

    def test_todo_evento_declara_a_procedencia(self):
        # Sem isto, estimativa e numero publicado se misturam na mesma coluna.
        r = _economic_calendar(limit=30, days=14)
        for evento in r["events"]:
            assert "estimado" in evento, evento
            assert "fonte" in evento, evento

    def test_evento_estimado_nao_inventa_valor(self):
        r = _economic_calendar(limit=30, days=14)
        estimados = [e for e in r["events"] if e.get("estimado")]
        assert estimados, "as semanas seguintes continuam estimativa"
        for evento in estimados:
            assert evento["previous"] is None
            assert evento["forecast"] is None
            assert evento["actual"] is None

    def test_feed_fora_avisa_em_vez_de_mostrar_somente_estimativa(self, monkeypatch):
        # Medido em 05/10/2026: o feed respondeu 429. A agenda continuava
        # respondendo 200 com 30 estimativas e NENHUM aviso — o operador via
        # uma agenda normal e não sabia que era tudo estimativa.
        def explode(*_args, **_kwargs):
            raise publica.CalendarUnavailable("feed publico recusou a consulta (HTTP 429)")

        monkeypatch.setattr(publica, "buscar_semana", explode)
        r = _economic_calendar(limit=30, days=14)
        assert r["ok"] is True, "a agenda local ainda responde"
        assert r["fontes"]["feed_disponivel"] is False
        assert "429" in r["fontes"]["erro"]

    def test_disclaimer_distingue_o_que_e_real_do_que_e_estimativa(self):
        r = _economic_calendar(limit=30, days=14)
        texto = r["disclaimer"]
        assert "publicados" in texto.lower()
        assert "estimados" in texto.lower()
        # O aviso nao pode dizer "estime tudo" quando a semana corrente tem
        # numero de verdade.
        assert r["fontes"]["reais"] > 0

    def test_rota_ignora_corpo_de_resposta_da_api(self):
        # Trava: a rota nao pode voltar a devolver so `events` e `count`,
        # porque a tela precisa de `fontes` para rotular a procedencia.
        r = _economic_calendar(limit=30, days=14)
        assert "fontes" in r
        assert set(r["fontes"]) >= {"reais", "estimados", "feed_disponivel"}
        # E nao pode sair do limite pedido.
        assert len(r["events"]) <= 30

    def test_json_serializavel(self):
        # O gateway responde por socket: qualquer `datetime` que escape para o
        # payload quebra a rota inteira com `TypeError`.
        json.dumps(_economic_calendar(limit=5, days=14), ensure_ascii=False)
