// BARRA INFERIOR — estilo MT5 (05/10/2026)
//
// O DONO PEDIU
// ============
// "botao de selecionar ms ao vivo latecencias. colocar na barra inferior do app
//  lado direito estilo mt5"
//
// O QUE A BARRA DO MT5 FAZ (pesquisado na documentacao)
// =====================================================
// Da esquerda para a direita, a barra de status do MT5 mostra: dica do comando
// sob o cursor, nome do perfil, data/OHLC/volume do ponto sob o cursor,
// ESTADO DA CONEXÃO com o servidor e o tráfego da sessão.
//
// Duas decisões daqui:
//   - a latência e item de RODAPÉ, não de cabeçalho. No cabeçalho ela competia
//     com o relógio e com o status do EA, e cinco corretoras medindo não cabiam;
//   - a conexão e um item de RODAPÉ. O operador precisa ver se o gateway está
//     vivo sem ir procurar o Diagnóstico.
//
// AJUSTE DE 05/10/2026, A PEDIDO DO DONO
// =======================================
// "barra inferios sem fixo por ativos ou nomes, pesquisar esta melhorias igual
//  a corretora usa, botoes com uso essencial alinhados compactos"
//
// O QUE MUDOU, E POR QUE
// ---------------------
// 1. ATIVO E TIMEFRAME VIRARAM UM ITEM SÓ.
//
//    Havia DOIS botões com rótulo escrito: "Ativo: GOLD" e "TF: H1". O rótulo é
//    redundância — o valor já diz o que é, e o MT5 não escreve "Symbol:" nem
//    "Period:" na barra. E "fixo por ativos ou nomes" não é o mesmo que
//    "sem ativo": um valor que não muda quando o par muda é layout quebrado, não
//    preferência. O item continua lendo o par que o motor está usando.
//
// 2. A TROCA DE ATIVO SAIU DO `window.prompt`.
//
//    O prompt é bloqueante, some atrás da janela do navegador e não aceita
//    colar com o botão direito. Trocar de par é a ação mais frequente da barra,
//    e ela era a única em modal nativo do app. O campo agora fica no TOPO DA
//    MESMA LISTA, que é onde o MT5 e a XM colocam.
//
// 3. "Tempo real" / "Reconectando" VIRARAM UM PONTO.
//
//    Na barra do MT5 o indicador de conexão é um marcador à direita, e não uma
//    frase. A frase continua no `title` e num `sr-only`: perde-se para o olho e
//    não se perde para o leitor de tela.
//
// O QUE FICOU AQUI
// ================
//   ESQUERDA: par + timeframe num botão só, com a lista de timeframes (marcando
//             o que o modelo aceita e o que é só gráfico) e o campo de par.
//   DIREITA: ponto de conexão e latência por corretora (a `LatenciaBar`, que já
//             existia dentro da Mesa e saiu de lá para não duplicar).
//
// O que a barra NÃO tem é tão intencional quanto o que tem: sem nome de
// corretora, sem nome de conta, sem relógio, sem contador de ordem. A pergunta
// é "o sistema está vivo e rápido?", e ponto + latência respondem isso.
//
// O QUE ESTE COMPONENTE NÃO FAZ
// =============================
// Não escolhe corretora. O escopo vem de `escopoAtivo()`, o mesmo do terminal
// e do gráfico: um seletor próprio aqui foi o defeito que fez a ordem ir para a
// corretora errada — a tela afirmava uma e o dinheiro ia para outra.
import { useEffect, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { useAutoState } from '../hooks/queries';
import LatenciaBar from './LatenciaBar';
import '../theme/status-bar.css';

/**
 * Timeframes que o MT5 sabe LER (`_TIMEFRAME_MAP` em `mt5_gateway.py`).
 *
 * O backend recusa qualquer outro com "timeframe MT5 invalido", então a lista
 * aqui é a lista real — não uma lista de botão decorativo.
 */
const MT5_ACEITA = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'] as const;

/**
 * Timeframes que o MODELO aceita (`TIMEFRAMES_VALIDOS` em `ai_inference.py`).
 *
 * SÓ M5, M15, H1 e H4. Escolher D1 aqui deixaria o motor ligado num timeframe
 * que a inferência recusa — o motor ligaria, o gráfico desenharia, e o operador
 * veria "motor ligado" sem nenhuma ordem acontecendo.
 *
 * Por isso os outros três aparecem na lista marcados como GRÁFICO: mudam o que
 * se vê, não o que o modelo decide. Deixar isso explícito é melhor que esconder
 * a opção e o operador achar que o app não tem D1.
 */
const MODELO_ACEITA = new Set(['M5', 'M15', 'H1', 'H4']);

export default function StatusBar() {
  const autoQ = useAutoState();
  const wsConnected = useAppStore((s) => s.wsConnected);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);

  const simbolo = String(autoQ.data?.simbolo || selectedSymbol || '').toUpperCase();
  const timeframe = String(autoQ.data?.timeframe || '').toUpperCase();

  const [listaAberta, setListaAberta] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState('');
  const caixa = useRef<HTMLDivElement>(null);

  // Fecha ao clicar fora e no `Escape`, como a lista de latência. Sem isso a
  // lista ficaria aberta por cima da tela depois que o operador mudou de aba.
  useEffect(() => {
    if (!listaAberta) return undefined;
    const fora = (e: MouseEvent) => {
      if (caixa.current && !caixa.current.contains(e.target as Node)) setListaAberta(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setListaAberta(false);
    };
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', fora);
      document.removeEventListener('keydown', esc);
    };
  }, [listaAberta]);

  /**
   * Trocar o timeframe chama `/api/auto/config` com SÓ o timeframe.
   *
   * `configurar()` no backend mescla campo a campo: o que não vem no payload
   * fica como está. Então enviar apenas `{timeframe}` muda o timeframe do motor
   * e não toca em lote, SL, TP, ativo nem corretora.
   *
   * Isso é o que faz o seletor do rodapé valer para o APP INTEIRO: o gráfico,
   * o motor e a leitura da escada leem o mesmo `timeframe` do estado.
   */
  const escolherTimeframe = async (proximo: string) => {
    setListaAberta(false);
    if (proximo === timeframe) return;
    if (ocupado) return;
    setOcupado(true);
    setErro('');
    try {
      const r = await fetch(`${apiBase()}/api/auto/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timeframe: proximo }),
        signal: AbortSignal.timeout(10_000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      if (!r.ok || d.ok === false) {
        setErro(String(d.error ?? `HTTP ${r.status}`));
        return;
      }
      // O gráfico lê do estado do motor; sem invalidar, ele continuaria
      // desenhando o timeframe anterior e o operador acharia que nada mudou.
      void autoQ.refetch();
    } catch (e) {
      setErro(`Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <footer className="status-bar" aria-label="Barra de status">
      <div className="status-bar-esq">
        {/*
          ATIVO E TIMEFRAME — um item só, como no MT5.

          A versão anterior tinha DOIS botões com rótulo ("Ativo" e "TF"), e o
          dono pediu para não ter nomes fixos: "barra inferios sem fixo por
          ativos ou nomes". O rótulo é redundância — o valor já diz o que é
          (GOLD, H1), e o MT5 não escreve "Symbol:" nem "Period:" na barra.

          Agora é UM botão que abre a lista de timeframes com o ativo no
          cabeçalho, e o clique no próprio símbolo troca o ativo. É o que a
          XM faz: o nome do instrumento é clicável e abre o seletor.
        */}
        <div className="status-tf" ref={caixa}>
          <button
            type="button"
            className="status-item status-simbolo"
            title={`${simbolo || 'Sem par'} · ${timeframe || 'sem timeframe'} — clique para trocar o timeframe`}
            onClick={() => setListaAberta((v) => !v)}
            aria-expanded={listaAberta}
            aria-haspopup="listbox"
          >
            <span className="status-valor">{simbolo || '—'}</span>
            <span className="status-divisor" aria-hidden="true">
              ·
            </span>
            <span className="status-valor status-tf-valor">{timeframe || '—'}</span>
            <span className="status-seta" aria-hidden="true">
              ▾
            </span>
          </button>
          {listaAberta && (
            <div className="status-tf-lista" role="listbox" aria-label="Timeframe">
              {/*
                O ATIVO no topo da lista, com um campo de texto.

                Antes o ativo era um `window.prompt` num botão separado. O prompt
                é bloqueante, some atrás da janela do navegador e não aceita
                colar com o mouse direito. O MT5 e a XM abrem um seletor com o
                campo preenchido e o cursor dentro.

                Aqui a lista é a mesma: o campo fica no topo, o timeframe embaixo.
              */}
              <div className="status-tf-ativo" onClick={(e) => e.stopPropagation()}>
                <label className="status-tf-ativo-rotulo" htmlFor="status-ativo-campo">
                  Ativo
                </label>
                <input
                  id="status-ativo-campo"
                  className="status-tf-ativo-input"
                  defaultValue={simbolo}
                  placeholder="ex.: XAUUSD"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const valor = e.currentTarget.value.trim().toUpperCase();
                      if (valor) setSelectedSymbol(valor);
                      setListaAberta(false);
                    }
                    if (e.key === 'Escape') setListaAberta(false);
                  }}
                  onBlur={(e) => {
                    const valor = e.currentTarget.value.trim().toUpperCase();
                    if (valor) setSelectedSymbol(valor);
                  }}
                />
              </div>
              {MT5_ACEITA.map((tf) => {
                const soGrafico = !MODELO_ACEITA.has(tf);
                return (
                  <button
                    key={tf}
                    type="button"
                    role="option"
                    aria-selected={tf === timeframe}
                    className={`status-tf-item${tf === timeframe ? ' is-ativo' : ''}${
                      soGrafico ? ' so-grafico' : ''
                    }`}
                    onClick={() => void escolherTimeframe(tf)}
                    title={
                      soGrafico
                        ? `${tf}: o MT5 lê, mas o modelo só infere em M5, M15, H1 e H4. Muda o gráfico, não a decisão.`
                        : `${tf}: o MT5 lê e o modelo infere.`
                    }
                  >
                    <span className="status-tf-nome">{tf}</span>
                    <span className="status-tf-marca">{soGrafico ? 'só gráfico' : 'modelo'}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {erro && (
          <span className="status-item status-erro" role="status">
            {erro}
          </span>
        )}
      </div>

      <div className="status-bar-dir">
        {/*
          O PONTO DE CONEXÃO, como no MT5.

          researched: na barra do MT5 o indicador de conexão vem à direita e é um
          MARCADOR, não uma frase. O texto "Tempo real" ocupa 70 px e diz o que
          um ponto colorido já diz; e "Reconectando" é o pior dos dois — é uma
          palavra para ler numa faixa de 24 px.

          Fica o ponto, o título (tooltip) diz a frase, e o ping da latência ao
          lado é a informação que o operador realmente usa.
        */}
        <span
          className={`status-item status-conexao ${wsConnected ? 'is-ok' : 'is-warn'}`}
          title={
            wsConnected
              ? 'Tempo real conectado'
              : 'Reconectando ao fluxo de tempo real — as leituras caem para HTTP'
          }
        >
          <span className="status-ponto" aria-hidden="true" />
          <span className="sr-only">
            {wsConnected ? 'Tempo real conectado' : 'Reconectando'}
          </span>
        </span>
        {/* A latência fica no lado direito, como no MT5: é informação de
            rodapé, e o operador lê sem clicar. */}
        <LatenciaBar />
      </div>
    </footer>
  );
}