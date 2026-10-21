import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { fusoAutomatico, ehConhecida } from '../lib/fuso';

/*
  O FUSO QUE O DONO ESCOLHEU (05/10/2026)
  =======================================
  MEDIDO na XM: `auto` em azul = modo automatico e o PADRAO, e a lista de
  cidades e a excecao. Por isso `auto` comeca `true` aqui tambem — comecar
  apontando para uma cidade seria inventar o fuso do operador.

  A zona so e aceita se estiver no catalogo de cidades que a XM oferece. Uma
  zona gravada no localStorage que nao exista mais (ou que tenha sido digitada)
  cai para `auto` em vez de virar relogio errado silencioso.

  O que este store NAO faz: decidir o fuso do grafico. `lightweight-charts`
  4.2.3 desenha o eixo no fuso do BROWSER e nao aceita troca; exibir outro fuso
  ali e conversao de timestamp, ou seja, mudanca de dado.
*/

type EstadoFuso = {
  auto: boolean;
  zona: string;
  usarAuto: () => void;
  escolher: (zona: string) => void;
};

const PADRAO = { auto: true, zona: '' };

export const useFuso = create<EstadoFuso>()(
  persist(
    (set) => ({
      auto: true,
      zona: '',
      /*
        Voltar para `auto` LIMPA a zona manual.

        MEDIDO (05/10/2026): a primeira versao fazia so `set({ auto: true })` e
        deixava `zona` com a cidade anterior. O comportamento na tela estava
        certo — `zonaAtual()` ignora `zona` quando `auto` —, mas o estado
        PERSISTIDO ficava `auto: true, zona: 'Europe/London'`, que e uma
        contradicao. Qualquer consumidor que leia `zona` direto, em vez de
        `zonaAtual()`, opera em Londres com o relogio marcando Sao Paulo.
      */
      usarAuto: () => set({ auto: true, zona: '' }),
      escolher: (zona) => {
        if (!ehConhecida(zona)) {
          // Zona fora do catalogo: `auto` e a resposta honesta.
          set({ auto: true, zona: '' });
          return;
        }
        set({ auto: false, zona });
      },
    }),
    {
      name: 'xau_ai_pro_fuso',
      version: 1,
      migrate: (estado) => {
        // Sem migracao: o formato nunca mudou. `merge` normaliza o que veio do
        // localStorage, porque esse dado e de versao antiga e nao tem nada a
        // ver com o que o usuario escolheu agora.
        const e = (estado ?? {}) as Partial<EstadoFuso>;
        if (e.auto === false && ehConhecida(String(e.zona))) return e as EstadoFuso;
        return PADRAO;
      },
    },
  ),
);

/**
 * A zona que a tela usa AGORA.
 *
 * `auto` devolve o fuso que o navegador resolveu — e nao `UTC`, que seria a
 * resposta sem informacao.
 */
export function zonaAtual(): string {
  const { auto, zona } = useFuso.getState();
  if (!auto && ehConhecida(zona)) return zona;
  return fusoAutomatico();
}

/** O rotulo da escolha atual: `auto` ou o nome da cidade. */
export function rotuloEscolha(): string {
  const { auto, zona } = useFuso.getState();
  if (auto || !ehConhecida(zona)) return 'auto';
  return zona;
}

export default useFuso;
