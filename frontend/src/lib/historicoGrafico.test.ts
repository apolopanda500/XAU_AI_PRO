import { describe, it, expect } from 'vitest';
import {
  historicoVazio,
  registrar,
  desfazer,
  refazer,
  podeDesfazer,
  podeRefazer,
  rotuloDesfazer,
  rotuloRefazer,
  LIMITE,
} from './historicoGrafico';

/*
  O HISTORICO DO GRAFICO — DESFAZER QUE DESFAZ (06/10/2026)
  ==========================================================
  O dono pediu "desfazer" e "refazer" na barra, como na XM.

  E o defeito medido no MESMO ciclo e a razao deste arquivo existir: o botao EMA
  era decorativo. Ligava, desliga e nao mudava nada, porque o dado que ele
  escrevia morava no pai e o pai nunca era avisado. Um botao de desfazer sem
  HISTORICO e a mesma coisa: um controle que parece funcionar.

  Por isso estes testes medem o EFEITO no estado, e nao que a funcao "chamou".
*/

type Tela = { tipo: 'candles' | 'linha'; rsi: boolean; ema: boolean };

const INICIAL: Tela = { tipo: 'candles', rsi: false, ema: false };
const linha: Tela = { ...INICIAL, tipo: 'linha' };
const linhaComRsi: Tela = { ...linha, rsi: true };
const linhaComRsiEema: Tela = { ...linhaComRsi, ema: true };

describe('historico do grafico — registrar', () => {
  it('comeca vazio e sem estado para desfazer', () => {
    const h = historicoVazio(INICIAL);
    expect(h.atual).toEqual(INICIAL);
    expect(podeDesfazer(h)).toBe(false);
    expect(podeRefazer(h)).toBe(false);
    // E os rotulos sao VAZIOS, e nao um texto que promete acao: um botao
    // desabilitado com "Desfazer" na aria-label diria que ha o que desfazer.
    expect(rotuloDesfazer(h)).toBe('');
    expect(rotuloRefazer(h)).toBe('');
  });

  it('um passo novo guarda o estado de ANTES e o de DEPOIS', () => {
    const h = registrar(historicoVazio(INICIAL), linha, 'tipo de grafico');
    expect(h.atual).toEqual(linha);
    expect(h.passos).toHaveLength(1);
    expect(h.passos[0].antes).toEqual(INICIAL);
    expect(h.passos[0].depois).toEqual(linha);
    expect(h.passos[0].rotulo).toBe('tipo de grafico');
    expect(podeDesfazer(h)).toBe(true);
    expect(rotuloDesfazer(h)).toBe('tipo de grafico');
  });

  it('PROVA NEGATIVA: o MESMO estado nao cria passo', () => {
    // Clicar duas vezes no mesmo botão nao pode encher o historico de passos
    // identicos — e o operador teria de apertar "desfazer" duas vezes para o
    // grafico voltar ao estado anterior.
    const um = registrar(historicoVazio(INICIAL), linha, 'tipo de grafico');
    const dois = registrar(um, linha, 'tipo de grafico');
    expect(dois.passos).toHaveLength(1);
    // E o objeto e o MESMO: nao houve alocacao.
    expect(dois).toBe(um);
  });

  it('PROVA NEGATIVA: objeto IGUAL mas novo nao vira passo', () => {
    /*
    MEDIDO: `Object.is` compara REFERENCIA, e o estado do grafico e um objeto que
    o React recria a cada render. Com `Object.is`, clicar duas vezes no mesmo
    botao criava dois passos de mesmo conteudo — e o operador teria de apertar
    "desfazer" DUAS vezes para o grafico voltar ao estado anterior.
    */
    const mesmaConteudo: Tela = { ...INICIAL };
    const h = registrar(historicoVazio(INICIAL), mesmaConteudo, 'nada');
    expect(h.passos).toHaveLength(0);
    expect(podeDesfazer(h)).toBe(false);
  });

  it('guarda no maximo LIMITE passos, e descarta os mais antigos', () => {
    let h = historicoVazio(INICIAL);
    for (let i = 0; i < LIMITE + 10; i += 1) {
      h = registrar(h, { ...INICIAL, ema: i % 2 === 0 }, `passo ${i}`);
    }
    // Crescer sem parar numa sessao longa nao compra nada: o operador desfaz o
    // que fez nos ultimos segundos.
    expect(h.passos).toHaveLength(LIMITE);
    // E o mais antigo que ficou e o passo LIMITE, nao o zero.
    expect(h.passos[0].rotulo).toBe(`passo ${10}`);
    expect(h.passos[LIMITE - 1].rotulo).toBe(`passo ${LIMITE + 9}`);
  });
});

describe('historico do grafico — desfazer e refazer', () => {
  const tresPassos = () => {
    let h = historicoVazio(INICIAL);
    h = registrar(h, linha, 'tipo de grafico');
    h = registrar(h, linhaComRsi, 'ligar RSI');
    h = registrar(h, linhaComRsiEema, 'ligar EMA');
    return h;
  };

  it('desfazer volta ao estado ANTERIOR, nao ao inicial', () => {
    const h = desfazer(tresPassos());
    expect(h.atual).toEqual(linhaComRsi);
    expect(h.atual.rsi).toBe(true);
    expect(h.atual.ema).toBe(false);
  });

  it('desfazer ate o fim volta ao inicial', () => {
    let h = tresPassos();
    h = desfazer(h);
    h = desfazer(h);
    h = desfazer(h);
    expect(h.atual).toEqual(INICIAL);
    expect(podeDesfazer(h)).toBe(false);
  });

  it('refazer volta ao estado DEPOIS, nao repete o ultimo', () => {
    // Refazer repete o ULTIMO passo desfeito. O primeiro desfeito e "ligar EMA",
    // entao o primeiro refazer volta ao estado DEPOIS dele: `linhaComRsiEema`,
    // com `ema:true`. Voltar a `linha` seria pular um passo.
    let h = desfazer(tresPassos());
    expect(h.atual).toEqual(linhaComRsi);
    h = refazer(h);
    expect(h.atual).toEqual(linhaComRsiEema);
    expect(h.atual.ema).toBe(true);
  });

  it('PROVA NEGATIVA: mexer depois de desfazer DESCARTA o refazer', () => {
    // E o que toda ferramenta faz. Sem isso, o "refazer" descreveria um caminho
    // que deixou de existir: o operador desfazia, mudava outra coisa, e o
    // refazer saltava por cima da mudanca nova.
    let h = desfazer(tresPassos());
    expect(podeRefazer(h)).toBe(true);
    h = registrar(h, { ...linha, ema: false }, 'outra coisa');
    expect(podeRefazer(h)).toBe(false);
    expect(rotuloRefazer(h)).toBe('');
  });

  it('PROVA NEGATIVA: desfazer sem nada a desfazer devolve o MESMO estado', () => {
    // O que permite ao botao desabilitar por `disabled={!podeDesfazer(h)}` sem
    // um estado booleano extra: e a propria estrutura que diz. E devolve a MESMA
    // referencia, para o React nao re-renderizar a tela inteira a toa.
    const h = historicoVazio(INICIAL);
    const depois = desfazer(h);
    expect(depois).toBe(h);
    const d2 = refazer(depois);
    expect(d2).toBe(h);
    expect(podeDesfazer(d2)).toBe(false);
    expect(podeRefazer(d2)).toBe(false);
  });

  it('desfazer e refazer em sequencia volta ao estado final, sem passos a mais', () => {
    // A ida e a volta nao pode ACRESCENTAR passo: `passos` mede o que o
    // operador mudou, nao quantas vezes ele apertou o botao.
    const h = tresPassos();
    const volta = refazer(desfazer(h));
    expect(volta.atual).toEqual(h.atual);
    expect(volta.atual).toEqual(linhaComRsiEema);
    expect(volta.passos).toHaveLength(h.passos.length);
  });

  it('o ROTULO diz o que volta, para o botao poder anunciar', () => {
    let h = tresPassos();
    expect(rotuloDesfazer(h)).toBe('ligar EMA');
    h = desfazer(h);
    expect(rotuloDesfazer(h)).toBe('ligar RSI');
    expect(rotuloRefazer(h)).toBe('ligar EMA');
    h = desfazer(h);
    expect(rotuloDesfazer(h)).toBe('tipo de grafico');
  });
});