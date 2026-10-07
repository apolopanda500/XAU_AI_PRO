# -*- coding: utf-8 -*-
"""Os NOMES de campo que o frontend manda, e os que o backend le.

O QUE ESTE ARQUIVO PROVA
========================
`test_endpoints_e_seguranca.py` garante que a ROTA que a tela chama existe. Nao
diz nada dos NOMES dos campos do corpo. E essa e a lacuna que deixou passar o
defeito de 05/10/2026:

    MEDIDO: `OperacaoAutomatica` tem o botao `Quantidade`, mostra os dois niveis
    derivados do SL e do alvo em dinheiro, e o campo de valor do risco — e
    `ligar()` mandava `sl_preco`/`tp_preco` SEMPRE. O que o operador escrevia em
    dinheiro chegava a lugar nenhum, e o motor recebia precos vazios.

A recusa que o operador veria seria "defina lote, stop loss e take profit", que
aponta para o SERVIDOR. O defeito era do CLIENTE: o nome que ele mandava
(`sl_preco`) era lido, e o que ele devia mandar (`sl_valor`) nunca era
mandado. E o sintoma e "campo faltando" — a armadilha mais cara deste
repositorio (AGENTS.md 5).

COMO ESTE TESTE MEDE
====================
Nao importa o frontend nem executa JavaScript: le o fonte do `.tsx` que monta o
corpo da rota e compara as chaves com os campos que `LimitesAuto` DECLARA. O
`configurar` do motor grava o que veio em `asdict(self.limites)`, entao um nome
que nao existe ali e silenciosamente ignorado — que e o defeito, sem erro em
nenhum lugar.
"""
from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import pytest

from backend.auto_engine import LimitesAuto

RAIZ = Path(__file__).resolve().parent.parent
FRONTEND = RAIZ / "frontend" / "src"

# Campos de `LimitesAuto`: e o que o `configurar` grava, porque grava o que veio
# em `asdict(self.limites)`.
LIMITES = {f.name for f in fields(LimitesAuto)}

# Campos que NAO sao limite, e que o `configurar` le em separado (simbolo,
# timeframe, corretora e mercado sao o QUE OBSERVAR, nao o RISCO).
OBSERVAR = {"simbolo", "timeframe", "broker", "market", "alvos"}

CONHECIDOS = LIMITES | OBSERVAR


def _comentarios_fora(texto: str) -> str:
    """Remove comentario de bloco e de linha.

    Sem isso um comentario que EXPLICA o defeito — "`ligar()` mandava
    `sl_preco`, que e o nome do preco e nao o do dinheiro" — vira acusacao de
    campo inexistente. Comentario documenta; codigo executa. E foi assim que este
    arquivo acusou o proprio comentario que documentava a correcao.
    """
    sem_bloco = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    return re.sub(r"//[^\n]*", "", sem_bloco)


def _chaves_de_corpo(arquivo: Path) -> set[str]:
    """Chaves que o arquivo escreve no corpo do POST, no formato objeto.

    Cobre as duas formas que o codigo usa:
      - `{ lote: loteN, sl_preco: slN }`   (literal de objeto)
      - `corpo.sl_valor = slValorN`        (atribuicao em objeto montado)

    A forma por atribuicao e a que o modo dinheiro usa, porque o corpo muda
    conforme o modo; sem ela o teste leria um corpo so e passaria calado no
    campo que o defeito apagava.
    """
    texto = _comentarios_fora(arquivo.read_text(encoding="utf-8", errors="replace"))
    achadas: set[str] = set()
    # Literal de objeto e atributo: `identificador: expr` e `obj.campo = expr`.
    for nome in re.findall(r"(?<![A-Za-z0-9_\-$])([a-z_][a-z0-9_]*)\s*:", texto):
        achadas.add(nome)
    for nome in re.findall(r"\b[A-Za-z_$][A-Za-z0-9_$]*\.([a-z_][a-z0-9_]*)\s*=", texto):
        achadas.add(nome)
    return achadas


ARQUIVOS = [
    p
    for p in FRONTEND.rglob("*.tsx")
    if not p.name.endswith(".test.tsx") and "/api/auto/config" in p.read_text(encoding="utf-8", errors="replace")
]


def _e_o_painel_do_modo_dinheiro(arquivo: Path) -> bool:
    """Este arquivo e o painel que OFERECE a protecao em dinheiro?

    Identificado pelo ROTULO que o dono le na tela — "Valor do stop loss" — e
    nao por `sl_valor`. Se o campo mudar de nome no codigo, o painel continua
    sendo o mesmo arquivo e este teste nao para de acha-lo.

    Outros arquivos chamam `/api/auto/config` legitimamente sem os dois modos:
    `StatusBar` e `ListaModelos` mandam so o que observam (simbolo e periodo),
    porque observar nao arrisca dinheiro. Aplicar a exigencia dos dois modos a
    eles seria exigir um campo de risco de uma tela que nao opera.
    """
    texto = _comentarios_fora(arquivo.read_text(encoding="utf-8", errors="replace"))
    return "Valor do stop loss" in texto


PAINEL = [p for p in ARQUIVOS if _e_o_painel_do_modo_dinheiro(p)]


class TestNomeDeCampoDoPainelParaOMotor:
    """Todo campo que a tela manda para `/api/auto/config` existe no motor."""

    def test_o_analisador_achou_o_arquivo_do_painel(self) -> None:
        # Sem esta trava, um erro de caminho deixaria `ARQUIVOS` vazio e TODOS os
        # testes abaixo passariam por vacuidade — o pior teste verde.
        assert ARQUIVOS, "nenhum arquivo do frontend monta corpo de /api/auto/config"
        assert any("OperacaoAutomatica" in p.name for p in ARQUIVOS), (
            "o painel de operacao automatica nao foi analisado: o teste pode "
            "estar lendo o arquivo errado"
        )

    def test_limites_tem_os_cinco_campos_de_protecao(self) -> None:
        # O que o painel oferece tem que existir no motor. Sem este teste, um
        # campo REMOVIDO de `LimitesAuto` deixaria o painel oferecer algo que
        # o motor ignora em silencio.
        for nome in ("lote", "sl_preco", "tp_preco", "sl_valor", "tp_valor"):
            assert nome in LIMITES, f"`{nome}` nao existe em LimitesAuto"

    @pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda p: p.name)
    def test_nenhum_campo_mandado_e_desconhecido(self, arquivo: Path) -> None:
        # Um nome fora de `LimitesAuto` e fora de OBSERVAR e IGNORADO pelo
        # `configurar`: ele so grava o que bate com um campo declarado. O
        # sintoma e o campo "nao existe", com o defeito no cliente.
        #
        # A lista e测量 de verdade: o painel tem muitas chaves locais (state,
        # rotulos, css) que nao vao no corpo. Por isso a checagem e o par
        # (chave desconhecida que ESTA no corpo da rota), e nao a lista toda.
        corpo = _corpo_da_rota(arquivo)
        desconhecidas = sorted(k for k in corpo if k not in CONHECIDOS)
        assert not desconhecidas, (
            f"{arquivo.name} manda para /api/auto/config campo(s) que o motor "
            f"nao le: {desconhecidas}\n"
            f"  (o motor grava so os {len(LIMITES)} campos de LimitesAuto; "
            f"o resto e ignorado em silencio)"
        )

    @pytest.mark.parametrize("arquivo", PAINEL, ids=lambda p: p.name)
    def test_o_painel_manda_os_dois_modos(self, arquivo: Path) -> None:
        """O painel tem que mandar preco E dinheiro.

        MEDIDO (05/10/2026): mandava so `sl_preco`/`tp_preco`. O campo de valor
        aparecia na tela, o operador preenchia, e o valor nao chegava ao motor —
        que recebia precos vazios e recusava com um motivo que aponta para o
        servidor. Este teste e o que impede o modo dinheiro de voltar a ser
        decorativo.
        """
        texto = _comentarios_fora(arquivo.read_text(encoding="utf-8", errors="replace"))
        for nome in ("sl_preco", "tp_preco", "sl_valor", "tp_valor"):
            assert re.search(rf"\b{nome}\b", texto), (
                f"{arquivo.name} nao menciona `{nome}`: um dos dois modos de "
                f"protecao nao chega ao motor"
            )

    def test_so_um_painel_oferece_o_modo_dinheiro(self) -> None:
        # Se dois arquivos oferecessem o modo dinheiro, o operador veria o mesmo
        # campo em duas telas com nomes diferentes — e uma das duas ia mandar
        # o campo errado. E o sintoma de nome que este arquivo existe para pegar.
        assert len(PAINEL) == 1, f"painel de dinheiro em mais de um arquivo: {[p.name for p in PAINEL]}"

    @pytest.mark.parametrize("arquivo", PAINEL, ids=lambda p: p.name)
    def test_o_motor_aceita_o_nome_do_dinheiro(self, arquivo: Path) -> None:
        """Prova pelo lado que CONSOME: o `configurar` grava e valida.

        Nao basta o nome existir no fonte do painel: tem que ser o nome que o
        `LimitesAuto` declara, porque e por ele que o `configurar` escreve.
        """
        from backend.auto_engine import MotorAuto

        motor = MotorAuto()
        resposta = motor.configurar(
            {"lote": 0.01, "sl_valor": 3.5, "tp_valor": 7.0, "simbolo": "BTCUSD", "timeframe": "H1"}
        )
        assert resposta["ok"], resposta.get("error")
        assert motor.limites.sl_valor == 3.5
        assert motor.limites.tp_valor == 7.0
        # E o preco NAO foi inventado a partir do dinheiro: quem deriva o nivel
        # e o motor, no ciclo, com o lado e o preco reais.
        assert motor.limites.sl_preco == 0.0
        assert motor.limites.tp_preco == 0.0
        # Com so dinheiro, o preco nao tem prioridade — `modo_preco_do_lote` e
        # o que decide, e ele tem de ser FALSO aqui. Se virasse verdadeiro, o
        # motor usaria preco vazio e o dinheiro seria decorativo de novo.
        assert motor.modo_preco_do_lote(vars(motor.limites)) is False

    def test_preco_prevale_sobre_dinheiro_quando_os_dois_vem(self) -> None:
        """Com os dois preenchidos, o PRECO vence — e isso tem de continuar.

        `modo_preco_do_lote` existe por um motivo medido: com os dois modos
        preenchidos o operador escolheu o nivel, e derivar de dinheiro ignoraria
        a escolha dele.
        """
        from backend.auto_engine import MotorAuto

        motor = MotorAuto()
        limites = {"lote": 0.01, "sl_preco": 4130.0, "tp_preco": 4150.0, "sl_valor": 3.5, "tp_valor": 7.0}
        assert motor.modo_preco_do_lote(limites) is True


def _corpo_da_rota(arquivo: Path) -> set[str]:
    """Chaves do corpo do POST para `/api/auto/config`, e nada mais.

    Filtra pelo que esta perto da rota, porque um componente tem dezenas de
    chaves de estado, rotulo e classe que NAO vao no corpo. Sem o filtro, o
    teste acusaria `mode`, `label`, `title` e reprovaria por coisa que nao e
    defeito — e um teste que acusa o irrelevante e um teste que o dono desliga.

    O recorte e do `body: JSON.stringify(` ate o fechamento do `)` correspondente,
    mais as atribuicoes em `corpo.<campo> =` que aparecem no mesmo trecho.
    """
    texto = arquivo.read_text(encoding="utf-8", errors="replace")
    achadas: set[str] = set()
    for achado in re.finditer(r"/api/auto/config", texto):
        trecho = texto[max(0, achado.start() - 1200) : achado.start()]
        # `corpo.<campo> =` e a forma do corpo montado por modo; conta quando
        # aparece antes da rota.
        achadas.update(re.findall(r"\bcorpo\.([a-z_][a-z0-9_]*)\s*=", trecho))
    # O literal de objeto do `JSON.stringify({ ... })` que antecede a rota.
    blocos = re.findall(r"JSON\.stringify\(\s*\{(.*?)\}\s*\)", texto, flags=re.S)
    for bloco in blocos:
        achadas.update(re.findall(r"(?<![A-Za-z0-9_\-$])([a-z_][a-z0-9_]*)\s*:", bloco))
    # `corpo.sl_valor = ...` no trecho do POST, que vem DEPOIS da rota.
    for achado in re.finditer(r"/api/auto/config", texto):
        depois = texto[achado.start() : achado.start() + 2000]
        achadas.update(re.findall(r"\bcorpo\.([a-z_][a-z0-9_]*)\s*=", depois))
    return achadas