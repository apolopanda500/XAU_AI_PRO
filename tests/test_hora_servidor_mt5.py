# -*- coding: utf-8 -*-
"""A HORA DO HISTORICO TEM DE BATER COM O MT5.

MEDIDO em 23/10/2026 nesta maquina (conta XMGlobal-MT5): o tick do EURUSD veio
com `time` = 2026-10-23T23:14:19 e o UTC real era 20:14:19. O servidor esta em
UTC+3 e o `deal.time` do MT5 carrega a hora de PAREDE do servidor codificada
como se fosse UTC.

O gateway publicava so `time` (ISO em UTC); o navegador formatava no fuso da
maquina (UTC-3) e a tela mostrava `17:14:19` para um deal que o MT5 mostra as
`23:14:19`. Seis horas de diferenca e, cruzando a meia-noite, o DIA errado.

A prova positiva e o carimbo; a prova NEGATIVA e que ele NAO coincide com a
formatacao no fuso da maquina — se as duas coincidissem, o teste passaria por
acidente em um servidor que estivesse em UTC.
"""
from __future__ import annotations

import datetime as dt

from backend import mt5_gateway as gw


class TestHoraDoServidor:
    def test_carimbo_no_formato_do_mt5(self):
        # 2026.10.05 01:46:43 (deal 24503922 da captura do dono)
        epoch = 1791164803
        assert gw._mt5_hora_servidor(epoch) == "2026.10.05 01:46:43"

    def test_e_a_hora_de_parede_e_nao_o_fuso_da_maquina(self):
        epoch = 1791164803
        do_servidor = gw._mt5_hora_servidor(epoch)
        local = dt.datetime.fromtimestamp(epoch).strftime("%Y.%m.%d %H:%M:%S")
        # Se a maquina estivesse em UTC os dois coincidiriam e o teste abaixo
        # nao provaria nada; ainda assim o carimbo tem de ser o do MT5.
        assert do_servidor == dt.datetime.utcfromtimestamp(epoch).strftime("%Y.%m.%d %H:%M:%S")
        if dt.datetime.now().astimezone().utcoffset() != dt.timedelta(0):
            assert do_servidor != local

    def test_ausente_nao_inventa_data(self):
        assert gw._mt5_hora_servidor(None) is None
        assert gw._mt5_hora_servidor("nao-e-numero") is None


class TestPayloadDoHistorico:
    def test_os_dois_campos_convivem(self):
        """`time` para ordenar/calcular, `time_server` para exibir."""
        epoch = 1791164803
        iso = gw.timestamp_iso(epoch)
        servidor = gw._mt5_hora_servidor(epoch)
        assert iso and iso.endswith("Z")
        assert servidor and servidor[4] == "." and servidor[10] == " "
        assert iso[:10] == servidor.replace(".", "-")[:10]
