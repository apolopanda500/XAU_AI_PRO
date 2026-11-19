// ===========================================================================
//  SELETOR DE ATIVOS (18/11/2026)
// ===========================================================================
//  A LISTA VEM DO CATALOGO DA CORRETORA — NUNCA DE UMA LISTA FIXA.
//
//  AGENTS.md §3: "Uma lista fixa de ativos contra os milhares que a corretora
//  oferece e exatamente essa presuncao." Por isso este componente NAO tem
//  `DEFAULT_ASSETS`: sem catalogo ele mostra o motivo da ausencia, e o
//  placeholder de busca nao cita nenhum simbolo (a trava
//  `ativoPresumido.test.ts` reprova nome de ativo no codigo, inclusive em
//  placeholder).
//
//  As classes usadas como filtro tambem vem do dado (`assetClass` que a
//  corretora publicou). Nenhuma classe e traduzida nem adivinhada pelo nome
//  do simbolo.
import { useMemo, useState } from 'react';

export interface AtivoDoCatalogo {
  symbol: string;
  assetClass?: string;
  description?: string;
}

export interface AssetSymbolPickerProps {
  ativos: AtivoDoCatalogo[];
  selecionado: string;
  onSelect: (symbol: string) => void;
  carregando?: boolean;
}

export default function AssetSymbolPicker({
  ativos,
  selecionado,
  onSelect,
  carregando = false,
}: AssetSymbolPickerProps) {
  const [busca, setBusca] = useState('');
  const [classe, setClasse] = useState<string>('TODAS');

  const classes = useMemo(() => {
    const vistas = new Set<string>();
    ativos.forEach((a) => {
      const c = String(a.assetClass ?? '').trim().toLowerCase();
      if (c) vistas.add(c);
    });
    return Array.from(vistas).sort();
  }, [ativos]);

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    return ativos.filter((a) => {
      const classeDoAtivo = String(a.assetClass ?? '').trim().toLowerCase();
      if (classe !== 'TODAS' && classeDoAtivo !== classe) return false;
      if (!termo) return true;
      return (
        a.symbol.toLowerCase().includes(termo) ||
        String(a.description ?? '').toLowerCase().includes(termo)
      );
    });
  }, [ativos, busca, classe]);

  return (
    <div className="seletor-ativos">
      <div className="seletor-ativos-filtros">
        <input
          type="search"
          className="seletor-ativos-busca"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar no catalogo da corretora..."
          aria-label="Buscar ativo no catalogo"
        />
        {classes.length > 0 && (
          <div className="seletor-ativos-classes" role="group" aria-label="Classes de ativo">
            <button
              type="button"
              className={`seletor-ativos-classe ${classe === 'TODAS' ? 'ativa' : ''}`}
              aria-pressed={classe === 'TODAS'}
              onClick={() => setClasse('TODAS')}
            >
              TODAS
            </button>
            {classes.map((c) => (
              <button
                key={c}
                type="button"
                className={`seletor-ativos-classe ${classe === c ? 'ativa' : ''}`}
                aria-pressed={classe === c}
                onClick={() => setClasse(c)}
              >
                {c.toUpperCase()}
              </button>
            ))}
          </div>
        )}
      </div>

      {carregando ? (
        <p className="seletor-ativos-vazio">Carregando o catalogo da corretora...</p>
      ) : ativos.length === 0 ? (
        <p className="seletor-ativos-vazio">
          Sem catalogo: escolha a corretora e o mercado na barra inferior. Nenhum ativo e
          presumido.
        </p>
      ) : filtrados.length === 0 ? (
        <p className="seletor-ativos-vazio">Nenhum ativo do catalogo casa com a busca.</p>
      ) : (
        <div className="seletor-ativos-lista" role="listbox" aria-label="Ativos do catalogo">
          {filtrados.slice(0, 200).map((a) => {
            const ativo = a.symbol === selecionado;
            return (
              <button
                key={a.symbol}
                type="button"
                role="option"
                aria-selected={ativo}
                className={`seletor-ativos-item ${ativo ? 'ativo' : ''}`}
                onClick={() => onSelect(a.symbol)}
              >
                <span className="seletor-ativos-simbolo">{a.symbol}</span>
                {a.assetClass ? (
                  <span className="seletor-ativos-classe-tag">{a.assetClass}</span>
                ) : null}
              </button>
            );
          })}
        </div>
      )}
      {filtrados.length > 200 ? (
        <p className="seletor-ativos-vazio">
          Mostrando 200 de {filtrados.length}. Refine a busca para ver os demais.
        </p>
      ) : null}
    </div>
  );
}
