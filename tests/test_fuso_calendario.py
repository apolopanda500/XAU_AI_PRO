"""FUSO HORARIO DO CALENDARIO — O QUE O SERVIDOR REALMENTE LE (05/10/2026)
==========================================================================

MEDIDO na captura da XM (21:01): o dono escolhe uma CIDADE, o rodape mostra
`UTC-3`, e trocar o fuso redesenha o grafico. O cliente passou a mandar a zona
IANA da cidade escolhida.

O teste que motivou tudo: `convert_to_tz` fazia
`_TZ_OFFSETS.get(tz, 0)`. Fuso desconhecido virava **UTC sem erro**. Mandar
`America/Sao_Paulo` devolvia agenda 3 horas errada e nenhuma pista — a
divergencia silenciosa entre dois lados que discordam do nome.

E a tabela de offset fixo nao representa o que a XM mostra: `Europe/London` e
UTC+0 em janeiro e UTC+1 em outubro, e so havia uma linha para ele.
"""

from __future__ import annotations

import datetime as dt

import pytest

from backend.planos.economic_calendar import (
    _TZ_OFFSETS,
    convert_to_tz,
    tz_desconhecida,
    tz_list,
    upcoming_events,
)


class TestFusoDesconhecidoNaoViraUtc:
    """O defeito medido: fuso errado virava resposta plausivel e errada."""

    def test_zona_iana_valida_nao_e_desconhecida(self):
        assert tz_desconhecida("Europe/London") is False
        assert tz_desconhecida("America/Sao_Paulo") is False
        assert tz_desconhecida("Asia/Kolkata") is False

    def test_inventado_e_desconhecido(self):
        assert tz_desconhecida("Brasil/Inventado") is True
        assert tz_desconhecida("casa") is True

    def test_vazio_e_utc_nao_sao_desconhecidos(self):
        assert tz_desconhecida("") is False
        assert tz_desconhecida("UTC") is False

    def test_as_chaves_curtas_antigas_continuam_valendo(self):
        for chave in _TZ_OFFSETS:
            assert tz_desconhecida(chave) is False, chave


class TestConversaoComZonaIana:
    """`naive` = UTC, e o resultado nao pode depender da maquina."""

    # 2026: outubro e inverno no norte, e o Brasil NAO tem horario de verao
    # desde 2019 — Sao Paulo e UTC-3 nos dois meses.
    OUTUBRO = dt.datetime(2026, 10, 7, 12, 0)
    JANEIRO = dt.datetime(2026, 1, 14, 12, 0)

    @pytest.mark.parametrize(
        "zona,outubro,janeiro",
        [
            ("Europe/London", 13.0, 12.0),      # BST em outubro, GMT em janeiro
            ("America/Sao_Paulo", 9.0, 9.0),    # UTC-3 o ano inteiro
            ("Europe/Amsterdam", 14.0, 13.0),   # CEST em outubro, CET em janeiro
            ("Asia/Kolkata", 17.5, 17.5),       # meia hora
            ("UTC", 12.0, 12.0),
        ],
    )
    def test_offset_por_mes(self, zona, outubro, janeiro):
        def horas(d):
            r = convert_to_tz(d, zona)
            return r.hour + r.minute / 60

        assert horas(self.OUTUBRO) == pytest.approx(outubro)
        assert horas(self.JANEIRO) == pytest.approx(janeiro)

    def test_londres_muda_entre_os_dois_meses(self):
        # ESTE e o motivo da zona IANA: uma tabela de offset fixo tem uma linha
        # so para Londres, e ela estaria errada em um dos dois meses o ano
        # inteiro. O codigo anterior nao tinha London: caia em UTC.
        assert convert_to_tz(self.OUTUBRO, "Europe/London").hour == 13
        assert convert_to_tz(self.JANEIRO, "Europe/London").hour == 12

    def test_meia_hora_nao_e_arredondada_para_hora(self):
        # Kolkata e +5:30. Arredondar para +5 seria uma hora errada de mercado.
        assert convert_to_tz(self.OUTUBRO, "Asia/Kolkata").minute == 30

    def test_chaves_curtas_preservam_o_comportamento_antigo(self):
        assert convert_to_tz(self.OUTUBRO, "BRT").hour == 9
        assert convert_to_tz(self.OUTUBRO, "JST").hour == 21
        assert convert_to_tz(self.OUTUBRO, "utc").hour == 12

    def test_resultado_nao_tem_tzinfo(self):
        # O formato antigo e `%d/%m %H:%M`, sem offset. Um datetime com tzinfo
        # no meio quebra a formatacao em outro lugar.
        assert convert_to_tz(self.OUTUBRO, "America/Sao_Paulo").tzinfo is None

    def test_naive_entra_como_UTC_e_nao_como_hora_do_sistema(self):
        """
        O CONTRATO, sem depender da maquina.

        PROVA NEGATIVA, e o motivo de este teste ter sido reescrito: a versao
        anterior fazia `monkeypatch.setenv("TZ", ...)` e conferia que o resultado
        nao mudava. MEDIDO: isso NAO funciona no Windows — nao existe
        `time.tzset()`, entao a variavel de ambiente nao troca o fuso do processo.
        O teste passava COM O BUG DE VOLTA nesta maquina, porque esta maquina e
        `America/Sao_Paulo`: o caminho errado (`dt.astimezone(zona)`) devolvia
        12:00 para 12:00 UTC, certo por acidente.

        Teste que passa com o defeito e teste decorativo. Este verifica a
        propriedade que o parametro acima ja mede, e nao tenta fingir que mede
        outra coisa.

        O detector de verdade do bug e `test_offset_por_mes`, que fixa os
        numeros esperados e por isso reprova quando o `tzinfo` some.
        """
        # 12:00 UTC e, no contrato, 12:00 UTC.
        assert convert_to_tz(self.OUTUBRO, "UTC") == self.OUTUBRO
        # 12:00 UTC sao 21:00 em Toquio (UTC+9, sem horario de verao).
        assert convert_to_tz(self.OUTUBRO, "Asia/Tokyo").hour == 21
        # 12:00 UTC sao 07:00 em Nova York em JANEIRO (EST, UTC-5).
        assert convert_to_tz(self.JANEIRO, "America/New_York").hour == 7


class TestAgendaUsaOFusoEscolhido:
    def test_eventos_mudam_de_hora_quando_o_fuso_muda(self):
        a = upcoming_events(limit=5, days=7, tz="UTC")
        b = upcoming_events(limit=5, days=7, tz="America/Sao_Paulo")
        assert len(a) == len(b)
        # mesma agenda, outra hora: os eventos sao os mesmos, deslocados
        assert [e["currency"] for e in a] == [e["currency"] for e in b]
        assert a[0]["when"] != b[0]["when"]

    def test_zona_inventada_nao_derruba_a_agenda(self):
        # `convert_to_tz` mantem o comportamento antigo em vez de estourar: quem
        # chama decide se recusa, usando `tz_desconhecida`.
        eventos = upcoming_events(limit=3, days=7, tz="Brasil/Inventado")
        assert len(eventos) == 3


class TestCatalogoDeFusos:
    def test_tz_list_continua_ordenado_por_offset(self):
        lista = tz_list()
        assert lista == sorted(_TZ_OFFSETS, key=lambda k: (_TZ_OFFSETS[k], k))
        assert "BRT" in lista

    def test_a_tabela_curta_nao_pode_ser_tratada_como_catalogo_de_cidades(self):
        """
        `tz_list()` devolve CHAVES CURTAS (BRT, JST), nao cidades.

        A tela precisa de cidade + zona IANA, porque a escolha e por cidade (foi
        o que a XM mostrou). Reusar esta lista na interface daria "BRT" como se
        fosse um lugar, e o operador escolheria um rotulo no escuro.
        """
        assert all("/" not in c for c in tz_list())
        assert "America/Sao_Paulo" not in tz_list()