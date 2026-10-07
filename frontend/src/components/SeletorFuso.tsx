import { useEffect, useMemo, useRef, useState } from 'react';
import { listaOrdenada, rotuloOffset, offsetMinutos, fusoAutomatico } from '../lib/fuso';
import { useFuso, zonaAtual } from '../hooks/useFuso';

/*
  O SELETOR DE FUSO (05/10/2026)
  ==============================
  MEDIDO na captura da XM, 21:01: lista de CIDADES com o offset entre parenteses,
  `(UTC-3) Sao Paulo` com tick, e `auto` em AZUL como padrao.

  Duas coisas que a tela da XM faz e que aqui estao explicitas:

  1. `auto` e o PADRAO. Comecar apontando para uma cidade seria inventar o fuso
     do operador. O item `auto` fica no TOPO, separado da lista, e mostra a
     propria deteccao do navegador: "auto · (UTC-3) America/Sao_Paulo".

  2. A lista e ORDENADA por offset corrente. Ordenar pela zona seria ordenar
     alfabeticamente, e nao ajuda ninguem a achar o proprio fuso.

  O offset ao lado e calculado na hora da renderizacao, e por isso a lista
  reconstroi a cada minuto: um operador que deixa a tela aberta na virada do
  horario de verao ve o rotulo antigo ate recarregar.
*/
export function SeletorFuso({ onEscolher }: { onEscolher?: (zona: string) => void }) {
  const { auto, zona, usarAuto, escolher } = useFuso();
  const [aberto, setAberto] = useState(false);
  const [agora, setAgora] = useState(() => new Date());
  const raizRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setInterval(() => setAgora(new Date()), 60_000);
    return () => clearInterval(t);
  }, []);

  // Fecha com Escape e com clique fora: um menu que so fecha no proprio botao
  // deixa o operador preso nele.
  useEffect(() => {
    if (!aberto) return undefined;
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setAberto(false);
    };
    const aoClicar = (e: MouseEvent) => {
      if (!raizRef.current?.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener('keydown', aoTeclar);
    document.addEventListener('mousedown', aoClicar);
    return () => {
      document.removeEventListener('keydown', aoTeclar);
      document.removeEventListener('mousedown', aoClicar);
    };
  }, [aberto]);

  const lista = useMemo(() => listaOrdenada(agora), [agora]);
  const deteccao = fusoAutomatico();
  const atual = zonaAtual();

  const escolherZona = (nova: string) => {
    if (nova === '__auto__') usarAuto();
    else escolher(nova);
    setAberto(false);
    onEscolher?.(nova);
  };

  return (
    <div className="fuso" ref={raizRef}>
      <button
        type="button"
        className="fuso-btn"
        aria-haspopup="listbox"
        aria-expanded={aberto}
        title={`Fuso: ${auto ? 'automatico' : zona} (${rotuloOffset(offsetMinutos(atual, agora))})`}
        onClick={() => setAberto((v) => !v)}
      >
        <span className="mono">{rotuloOffset(offsetMinutos(atual, agora))}</span>
        <span className="fuso-modo">{auto ? 'auto' : 'manual'}</span>
      </button>

      {aberto && (
        <div className="fuso-menu" role="listbox" aria-label="Fuso horario">
          {/*
            `auto` SEPARADO no topo. Itens que podem ser escolhidos ficam com
            `role="option"`: misturar um item de acao com itens de escolha e o
            que faz leitor de tela announcing "opcao" para algo que nao escolhe
            fuso nenhum.
          */}
          <button
            type="button"
            role="option"
            aria-selected={auto}
            className={`fuso-item fuso-item-auto${auto ? ' ativo' : ''}`}
            onClick={() => escolherZona('__auto__')}
          >
            <span className="fuso-tick">{auto ? '\u2713' : ''}</span>
            <span className="fuso-nome">auto</span>
            <span className="muted mono">
              {rotuloOffset(offsetMinutos(deteccao, agora))} {deteccao}
            </span>
          </button>

          <div className="fuso-divisor" role="separator" />

          {lista.map((c) => {
            const escolhido = !auto && zona === c.zona;
            return (
              <button
                key={c.zona}
                type="button"
                role="option"
                aria-selected={escolhido}
                className={`fuso-item${escolhido ? ' ativo' : ''}`}
                onClick={() => escolherZona(c.zona)}
              >
                <span className="fuso-tick">{escolhido ? '\u2713' : ''}</span>
                <span className="fuso-nome">{c.cidade}</span>
                <span className="muted mono">{rotuloOffset(offsetMinutos(c.zona, agora))}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default SeletorFuso;
