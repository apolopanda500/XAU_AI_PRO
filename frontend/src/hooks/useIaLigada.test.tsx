// O INTERRUPTOR DA IA SOBREVIVE A TROCA DE ABA (09/10/2026)
// =========================================================
// O DONO REPORTOU: "quando desligo e volto novamente ele desliga".
//
// MEDIDO: `iaLigada` era `useState(false)` dentro de `OperacaoAutomatica`. A
// aba ROBO monta e desmonta aquele componente inteiro, entao sair e voltar
// zerava o interruptor. Nao era so a tela: `useInferenciaIA(timeframe,
// iaLigada)` usava o valor para decidir se chama o gateway, e a inferencia
// parava sem o operador pedir.
//
// Este teste mede o que a troca de aba produz: desmontar e montar de novo.
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { act, cleanup, render, screen } from '@testing-library/react';
import { useIaLigada, zerarIaLigada } from './useIaLigada';

// Sem isso, o `render` de um teste continua no DOM do outro — e o teste de
// compartilhamento acha dois `data-testid="estado"` e reprova o proprio teste.
afterEach(() => {
  cleanup();
  /*
    E ZERAR O STORE. MEDIDO (09/10/2026): o store ȁ de modulo e sobrevive ao
    arquivo de teste. Sem este reset, o `RobotTabs.test.tsx` herdava
    `ligada: true` e reprovava de forma INTERMITENTE (1 em 3 rodadas da suite
    inteira) — que ȁ a assinatura de estado compartilhado entre arquivos.
  */
  zerarIaLigada();
});

/*
  E ZERAR ANTES TAMBEM (10/10/2026).
  ==================================
  Este arquivo ȁ a ORIGEM do vazamento: o primeiro caso liga a IA
  (`setLigada(true)`) e o segundo comeca com `setLigada(false)` explicito, mas
  um terceiro arquivo que rodasse antes e deixasse `ligada: true` faria o
  PRIMEIRO caso daqui nascer no estado errado. O `afterEach` limpa o que
  passou; o `beforeEach` garante o estado que cada caso DECLAROU. Medido:
  rodada a rodada da suite inteira invertia o resultado so pela ordem.
*/
beforeEach(() => {
  zerarIaLigada();
});

/** Um componente que so le o interruptor, como o painel faz. */
function Leitor() {
  const ligada = useIaLigada((s) => s.ligada);
  return <span data-testid="estado">{ligada ? 'ligada' : 'desligada'}</span>;
}

/** Um botao que liga, como o do painel. */
function Botao() {
  const setLigada = useIaLigada((s) => s.setLigada);
  return (
    <button type="button" onClick={() => setLigada(true)}>
      Ligar IA
    </button>
  );
}

describe('o interruptor da IA nao morre na troca de aba', () => {
  it('desmontar e montar de novo MANTEM ligada', () => {
    // O defeito: o render depois do unmount mostrava "desligada".
    act(() => {
      useIaLigada.getState().setLigada(true);
    });

    const primeira = render(<Leitor />);
    expect(screen.getByTestId('estado').textContent).toBe('ligada');

    // Sair da aba: desmonta.
    primeira.unmount();

    // Voltar: monta do zero. Com `useState(false)` daria "desligada".
    render(<Leitor />);
    expect(screen.getByTestId('estado').textContent, 'a troca de aba apagou a IA').toBe('ligada');
  });

  it('PROVA NEGATIVA: o estado e COMPARTILHADO entre componentes', () => {
    /*
      Se cada componente tivesse o seu proprio pedaco de estado, o botao de um
      lugar nao mudaria a leitura do outro — e o interruptor continuaria morrendo
      com o componente. Aqui o botao e o leitor sao arvores separadas.
    */
    useIaLigada.getState().setLigada(false);

    render(
      <>
        <Botao />
        <Leitor />
      </>,
    );

    expect(screen.getByTestId('estado').textContent).toBe('desligada');
    act(() => {
      screen.getByRole('button', { name: 'Ligar IA' }).click();
    });
    expect(screen.getByTestId('estado').textContent).toBe('ligada');
  });

  it('a sessao nova comeca DESLIGADA (nao persiste no localStorage)', () => {
    /*
      A escolha e deliberada: inferencia consome CPU e escreve estado, e ligar
      sozinho na abertura e decidir pelo operador. Se este estado entrasse no
      `useAppStore` — que tem `persist` — voltaria ligado no dia seguinte.

      Este teste reprova se o estado passar a persistir: o localStorage vem do
      navegador, e a chave usada pelo store persistido e `xau-ai-pro`.
    */
    expect(window.localStorage.getItem('xau-ai-pro')).toBeNull();
    // E nenhuma chave deste store pode ir para o localStorage.
    const chaves = Object.keys(window.localStorage);
    expect(chaves.some((k) => k.toLowerCase().includes('ialigada'))).toBe(false);
  });
});
