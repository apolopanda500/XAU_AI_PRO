# -*- coding: utf-8 -*-
"""O gerador de tokens da Figma produz CSS que serve para alguma coisa.

POR QUE ESTE TESTE EXISTE
=========================
O `sincronizar_figma.py` tem DUAS fontes de erro que nenhuma chamada de rede
pega, porque ele so roda de verdade quando a Figma tem design system
publicado — e esse era o estado medido em 04/10/2026:

1. `cor/dark/bg` produzia `[data-theme="default"] { --dark: ... }`: o nome do
   TEMA virava nome de TOKEN. O CSS gerado era invalido e, pior, era gerado
   sem erro nenhum.
2. `espaco/1` produzia `--1`, que nao e um token usavel.

Ambos sairam de uma geracao com variaveis falsa, sem tocar a Figma nem
gravar arquivo. Este teste fixa o comportamento para o dia em que as variaveis
existirem de verdade.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from sincronizar_figma import gerar_css  # noqa: E402


def cor(hexa: str) -> dict[str, float]:
    return {
        "r": int(hexa[1:3], 16) / 255,
        "g": int(hexa[3:5], 16) / 255,
        "b": int(hexa[5:7], 16) / 255,
        "a": 1,
    }


def variavel(nome: str, **modos) -> dict:
    return {"name": nome, "valuesByMode": modos}


class TestGeraCssUtil:
    def test_tema_vira_data_theme_e_nao_nome_de_token(self):
        """O defeito 1: `cor/dark/bg` nao pode virar `--dark`.

        Verificacao dupla: o valor tem de estar DENTRO do bloco do tema, e
        nao no `:root`. A primeira versao do teste so conferia que `--bg`
        aparecia em algum lugar, e passava mesmo com a regra desligada — que
        e como se descobre que o teste nao prendia nada.
        """
        css = gerar_css({"v": variavel("cor/dark/bg", default=cor("#0f1420"))}, [])
        assert '--bg: #0f1420;' in css, css
        # E o inverso: nenhum token chamado `--dark` pode existir.
        assert "--dark:" not in css, css
        # O valor tem de estar no bloco do tema, e nao no `:root`.
        bloco_tema = css.split('[data-theme="dark"] {', 1)[1].split("}", 1)[0]
        assert "--bg: #0f1420;" in bloco_tema, css
        bloco_root = css.split(":root {", 1)[1].split("}", 1)[0]
        assert "--bg" not in bloco_root, (
            "com o tema no nome, o valor NAO e o padrao global"
        )

    def test_papel_que_comeca_com_digito_ganha_a_familia(self):
        """O defeito 2: `espaco/1` nao pode virar `--1`."""
        css = gerar_css({"v": variavel("espaco/1", default=4)}, [])
        assert "--espaco-1: 4;" in css, css
        assert "--1:" not in css, css

    def test_cada_tema_vai_para_o_seu_data_theme(self):
        css = gerar_css(
            {
                "a": variavel("cor/dark/bg", default=cor("#0f1420")),
                "b": variavel("cor/xau_dark/bg", default=cor("#14100a")),
                "c": variavel("cor/light/bg", default=cor("#f3f5f9")),
            },
            [],
        )
        assert '[data-theme="dark"]' in css
        assert '[data-theme="xau"]' in css, "apelido curto tem de virar xau"
        assert '[data-theme="light"]' in css

    def test_valor_padrao_vai_para_root(self):
        """`default` e o modo padrao: ele vai no `:root`, sem data-theme.

        So quando o nome NAO traz tema — `cor/bg` — o `default` e global.
        Com `cor/dark/bg` o valor pertence ao tema dark e vai para
        `[data-theme="dark"]`: tratar como `:root` faria o tema escuro
        virar a cor de TODOS os temas ate o proximo `data-theme`.
        """
        css = gerar_css({"a": variavel("cor/bg", default=cor("#0f1420"))}, [])
        bloco_root = css.split(":root {", 1)[1].split("}", 1)[0]
        assert "--bg: #0f1420;" in bloco_root, css

    def test_root_e_emitido_mesmo_sem_valor_padrao(self):
        """`cor/dark/bg` nao tem padrao global, mas `:root` precisa existir.

        Sem isso o arquivo gerado perde o fallback do app e uma theme nova
        nao tem cor nenhuma.
        """
        css = gerar_css({"a": variavel("cor/dark/bg", default=cor("#0f1420"))}, [])
        assert ":root {" in css, css

    def test_cor_com_alpha_vira_canal_alpha(self):
        css = gerar_css(
            {"a": variavel("cor/dark/bg", default={**cor("#0f1420"), "a": 0.5})}, []
        )
        assert "#0f1420 / 0.5" in css, css

    def test_estilos_publicados_aparecem_como_referencia(self):
        css = gerar_css({}, [{"name": "Botao/Primario"}, {"name": "Chip/Status"}])
        assert "Botao/Primario" in css
        assert "Chip/Status" in css

    def test_nao_inventa_token_que_a_figma_nao_tem(self):
        """O que a Figma nao define nao aparece: o CSS mao segue valendo."""
        css = gerar_css({"a": variavel("cor/dark/bg", default=cor("#0f1420"))}, [])
        for inventado in ("--panel2", "--primary-contrast", "--danger"):
            assert inventado not in css, f"{inventado} nao foi definido pela Figma"

    def test_arquivo_gerado_avisa_que_nao_e_para_editar_mao(self):
        css = gerar_css({"a": variavel("cor/dark/bg", default=cor("#0f1420"))}, [])
        assert "NAO EDITE COM A MAO" in css