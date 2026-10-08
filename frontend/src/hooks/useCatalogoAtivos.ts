import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { parseAssetCatalog, type AssetRow } from '../lib/brokerCatalog';
import type { Broker } from '../lib/connections';

/*
  O CATALOGO DE ATIVOS DA CORRETORA (05/10/2026)
  ==============================================
  Vive em modulo proprio, e nao dentro do componente que o consome.

  Motivo medido: com o hook dentro de `SeletorModelo.tsx`, o painel do ticket
  precisou importar de um COMPONENTE - e o teste que mocka esse componente
  quebrou, porque o mock de componente nao tem hook dentro. Dependencia de hook
  em componente e camada errada, e o erro apareceu antes de ir para producao.
*/
export function useCatalogoAtivos(broker: Broker, market: string): AssetRow[] {
  const [ativos, setAtivos] = useState<AssetRow[]>([]);
  useEffect(() => {
    // MERCADO VAZIO NAO IMPEDE A CONSULTA.
    //
    // MEDIDO em 07/10/2026, conta 391773676 (XMGlobal-MT5 14), com o motor
    // desligado — que e quando `auto.market` chega vazio:
    //
    //   backend  _universal_assets("mt5", "")        -> 1639 ativos; BTCUSD
    //            class=crypto contract_size=1.0
    //   backend  _universal_candles("mt5","","BTCUSD","M1") -> 20 candles, ok
    //
    // O gateway tem reserva: `mt5_gateway._universal_scope` troca mercado vazio
    // por "other" no MT5 e por "crypto-spot" nas exchanges.
    //
    // Este hook NAO tinha a mesma reserva: com `market === ""` ele fazia
    // `setAtivos([])` sem consultar (linhas 19-22). A cadeia era:
    //
    //   auto.market="" -> catalogo vazio -> fichaDoAtivo=null
    //     -> mercadoDoAtivo(undefined)=null -> market=""
    //     -> getCandles -> normalizeMarketSource("mt5","")=null
    //     -> throw "Identidade de mercado invalida"
    //
    // O throw e no FRONTEND, antes de qualquer chamada ao gateway. O operador
    // lia "Identidade de mercado invalida" e culpava o servidor — que estava
    // respondendo 1639 ativos. E AGENTS.md 5: o defeito estava do lado que
    // produziu a mensagem, e a medicao do backend prova isso.
    const controller = new AbortController();
    const url = `${apiBase()}/api/universal/assets?broker=${encodeURIComponent(
      broker,
    )}&market=${encodeURIComponent(market)}`;
    fetch(url, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : {}))
      .then((payload) => {
        if (controller.signal.aborted) return;
        setAtivos(parseAssetCatalog(payload));
      })
      .catch(() => {
        if (!controller.signal.aborted) setAtivos([]);
      });
    return () => controller.abort();
  }, [broker, market]);
  return ativos;
}
