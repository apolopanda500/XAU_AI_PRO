// ===========================================================================
//  MESA INSTITUCIONAL (18/11/2026)
// ===========================================================================
//  O painel que o dono pediu: "minimizar por dentro barras, grades, listas" e
//  "tudo atualizado em tempo real", com boleta que respeita o RiskGate.
//
//  TUDO AQUI LE DE UMA FONTE SO
//  ============================
//  * conta/posicoes/ordens/cotacao -> `useRealtimeLiveStore` (que por sua vez
//    le `useAppStore`, alimentado pelo Core e pelo WebSocket);
//  * catalogo -> `useCatalogoAtivos`, o mesmo hook que a operacao automatica
//    usa. Sem corretora escolhida, o catalogo e vazio e a tela diz o motivo;
//  * contrato -> `fichaDoAtivo`, a ficha que a corretora publicou.
//
//  O QUE ESTE PAINEL NAO FAZ
//  =========================
//  Nao envia ordem (a build nao tem executor autorizado), nao liga motor, nao
//  altera limite de risco e nao ativa plano. "Planos e assinatura" e um atalho
//  para `SettingsCore`, onde `PlanoConfig` ja vive — duplicar ali seria o §5
//  outra vez.
import { useMemo } from 'react';
import { useAppStore } from '../hooks/useAppStore';
import { useRealtimeLiveStore } from '../hooks/useRealtimeLiveStore';
import { useCatalogoAtivos } from '../hooks/useCatalogoAtivos';
import { escopoAtivo } from '../lib/escopoAtivo';
import { fichaDoAtivo } from '../lib/volumeUnidade';
import type { Broker } from '../lib/connections';
import CollapsibleSection from './CollapsibleSection';
import ReadingModeBar from './ReadingModeBar';
import AssetSymbolPicker from './AssetSymbolPicker';
import { BankrollPanel, OrdersPanel } from './BankrollAndOrdersPanel';
import OrderTicketPro from './OrderTicketPro';

export default function InstitutionalDesk() {
  const { estado, ressincronizar } = useRealtimeLiveStore();
  const simbolo = useAppStore((s) => s.selectedSymbol);
  const definirSimbolo = useAppStore((s) => s.setSelectedSymbol);
  const setActiveTab = useAppStore((s) => s.setActiveTab);

  const escopo = escopoAtivo();
  const catalogo = useCatalogoAtivos(
    escopo.broker as Broker,
    String(escopo.market || '').toLowerCase(),
  );

  const ficha = useMemo(() => fichaDoAtivo(catalogo, simbolo), [catalogo, simbolo]);

  const ativos = useMemo(
    () =>
      catalogo.map((a) => ({
        symbol: a.symbol,
        assetClass: a.assetClass ?? undefined,
        description: a.displayName ?? undefined,
      })),
    [catalogo],
  );

  const digits = estado.cotacao?.digits ?? ficha?.digits ?? 2;
  const point = estado.cotacao?.point ?? ficha?.point ?? 0;
  const bid = estado.cotacao?.bid ?? 0;
  const ask = estado.cotacao?.ask ?? 0;

  // ZERO MARCAS EXTERNAS: o app usa seu próprio gráfico nativo (sub-aba
  // Operação). Nenhum link para plataforma de terceiro é gerado aqui.

  return (
    <div className="mesa-institucional">
      <ReadingModeBar
        websocket={estado.websocket}
        atualizadoEm={estado.ultimaSincronizacao}
        onRessincronizar={ressincronizar}
      />

      <CollapsibleSection
        id="mesa_ativo"
        title="Ativo e catalogo"
        badge={simbolo || 'sem ativo'}
      >
        {escopo.broker ? (
          <AssetSymbolPicker
            ativos={ativos}
            selecionado={simbolo}
            onSelect={definirSimbolo}
            carregando={ativos.length === 0}
          />
        ) : (
          <p className="seletor-ativos-vazio">
            Sem corretora escolhida na barra inferior. O catalogo nao e presumido: escolha a
            conta para listar os ativos.
          </p>
        )}
      </CollapsibleSection>

      <CollapsibleSection
        id="mesa_banca"
        title="Banca e noticias"
        badge={`${estado.posicoes.length} posicoes`}
      >
        <BankrollPanel
          saldo={estado.saldo}
          patrimonio={estado.patrimonio}
          flutuante={estado.flutuante}
          margemLivre={estado.margemLivre}
          atualizadoEm={estado.ultimaSincronizacao}
        />
        {!estado.temConta ? (
          <p className="seletor-ativos-vazio">
            Sem conta lida do gateway. Os numeros acima ficam em zero ate a leitura chegar.
          </p>
        ) : null}
      </CollapsibleSection>

      <CollapsibleSection
        id="mesa_ordens"
        title="Posicoes e ordens"
        badge={`${estado.ordens.length} pendentes`}
        defaultOpen={false}
      >
        <OrdersPanel ordens={estado.ordens} posicoes={estado.posicoes} />
      </CollapsibleSection>

      <CollapsibleSection id="mesa_boleta" title="Boleta de execucao" badge="RiskGate">
        <OrderTicketPro
          symbol={simbolo}
          bid={bid}
          ask={ask}
          digits={digits}
          point={point}
          ficha={ficha}
          balance={estado.saldo}
          somenteLeitura
        />
      </CollapsibleSection>

      <p className="mesa-rodape">
        Planos, assinatura e limites de risco ficam em{' '}
        <button type="button" className="mesa-link-botao" onClick={() => setActiveTab('settings')}>
          Configuracoes
        </button>
        . Esta mesa nao altera limite de risco nem liga motor.
      </p>
    </div>
  );
}
