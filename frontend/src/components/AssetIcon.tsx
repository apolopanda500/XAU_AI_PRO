import { assetIcon } from '../lib/assetIcons';

export function AssetIcon({ symbol, broker }: { symbol: string; broker?: string }) {
  return <span className="asset-icon" aria-hidden="true" title={`${broker ?? 'mercado'} ${symbol}`}>{assetIcon(symbol)}</span>;
}
