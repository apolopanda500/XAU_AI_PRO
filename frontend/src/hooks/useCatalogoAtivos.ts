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
    if (!market) {
      setAtivos([]);
      return undefined;
    }
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
