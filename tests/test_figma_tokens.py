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

import re
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

# =====================================================================
#  TEMA COMPLETO POR PAPEL  (medido em 04/10/2026)
# =====================================================================
# `ok`, `warn` e `danger` so eram declarados no tema `light`. Os outros 7
# pegavam estes tres do `:root` sem ninguem ter escolhido — funciona por
# acaso, porque todo tema novo nasce com o verde calibrado para o `dark`.
# E a mesma classe de defeito do `DEFAULT_TIMEFRAME = "M5"`: um valor que
# ninguem escolheu decidindo por todos.
#
# Nenhum teste de frontend pega isso: o CSS compila sem uma variavel e a tela
# abre normalmente.

CSS = Path(__file__).resolve().parent.parent / "frontend" / "src" / "theme" / "global.css"
USE_THEME = Path(__file__).resolve().parent.parent / "frontend" / "src" / "hooks" / "useTheme.ts"

# `primary-contrast` entra porque texto sobre `primary` sem ele fica ilegivel.
PAPEIS = ("bg", "panel", "panel2", "border", "text", "muted",
          "primary", "primary-contrast", "ok", "warn", "danger")


def _temas_do_css() -> dict[str, dict[str, str]]:
    """Mapa seletor -> variaveis, contando o nivel de chaves.

    Um `.*?` nao aninhado para no `}` errado quando o bloco tem chave interna,
    e o tema seguinte desaparece do mapa sem erro. Foi assim que `xau_dark` e
    `btc_dark` sairam da folha de estilos com "-" sendo que o CSS estava certo.
    """
    texto = CSS.read_text(encoding="utf-8")
    achados: dict[str, dict[str, str]] = {}
    padrao = r"((?:\[data-theme='[a-z_]+'\]\s*,\s*)*\[data-theme='[a-z_]+'\])\s*\{"
    for m in re.finditer(padrao, texto):
        nomes = re.findall(r"\[data-theme='([a-z_]+)'\]", m.group(1))
        i, nivel = m.end(), 1
        while i < len(texto) and nivel:
            if texto[i] == "{":
                nivel += 1
            elif texto[i] == "}":
                nivel -= 1
            i += 1
        variaveis = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", texto[m.end():i]))
        for nome in nomes:
            achados.setdefault(nome, {}).update(variaveis)
    return achados


# Os 8 temas reais. Um `re.findall` solto sobre o `useTheme.ts` tambem pega
# `react` e `undefined` do codigo vizinho, e o teste passa a acusar tema que
# nao existe. A lista e explicita porque ela E o contrato: um tema novo
# entra aqui e no CSS, nunca so num dos dois.
TEMAS = ("dark", "xau_dark", "btc_dark", "light", "ocean_dark",
         "emerald_dark", "rose_dark", "violet_dark")


def _temas_oferecidos() -> set[str]:
    return set(TEMAS)


class TestCadaTemaTemTodosOsPapeis:
    def test_nenhum_tema_fica_sem_um_papel(self):
        css = _temas_do_css()
        faltando = []
        for tema in sorted(_temas_oferecidos()):
            if tema not in css:
                faltando.append(f"{tema}: sem bloco no CSS")
                continue
            for papel in PAPEIS:
                if papel not in css[tema]:
                    faltando.append(f"{tema}: sem --{papel}")
        assert not faltando, "tema incompleto: " + "; ".join(faltando)

    def test_estados_nao_dependem_do_root(self):
        """`ok`/`warn`/`danger` por tema, nunca herdados do `:root`."""
        css = _temas_do_css()
        for tema, variaveis in sorted(css.items()):
            for papel in ("ok", "warn", "danger"):
                assert papel in variaveis, f"[{tema}] herdaria --{papel} do :root"

    def test_o_css_tem_as_chaves_balanceadas(self):
        """Um bloco de tema sem `}` engole o CSS seguinte em silencio.

        Foi assim que os blocos chegaram a sumir: o `/* Utilitarios */` ficou
        dentro do `[data-theme=...]`, as variaveis daquele tema nunca
        existiram, o build passou e a tela herdou o tema anterior.
        """
        texto = CSS.read_text(encoding="utf-8")
        assert texto.count("{") == texto.count("}"), (
            f"chaves desbalanceadas: {texto.count('{')} abre / {texto.count('}')} fecha")
