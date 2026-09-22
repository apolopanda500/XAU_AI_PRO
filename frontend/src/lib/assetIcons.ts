export function assetIcon(symbol: string, assetClass?: string): string {
  const clean = String(symbol || '').toUpperCase();
  const text = `${clean} ${assetClass || ''}`.toUpperCase();
  if (/BTC/.test(text)) return 'BTC';
  if (/ETH/.test(text)) return 'ETH';
  if (/SOL/.test(text)) return 'SOL';
  if (/XRP/.test(text)) return 'XRP';
  if (/DOGE/.test(text)) return 'DOGE';
  if (assetClass === 'metal' || /XAU|GOLD/.test(text)) return 'Au';
  if (/XAG|SILVER/.test(text)) return 'Ag';
  if (/XPT|PLATIN/.test(text)) return 'Pt';
  if (assetClass === 'index' || /US30|US500|NAS|SPX|DAX|HK50|USTEC/.test(text)) return 'IDX';
  if (assetClass === 'equity' || /STOCK|SHARES/.test(text)) return 'EQ';
  if (assetClass === 'future' || /FUT/.test(text)) return 'FUT';
  if (assetClass === 'forex' || /^[A-Z]{6}$/.test(clean)) return clean.slice(0, 3);
  if (/USDT|USDC|BNB|ADA|TRX|AVAX|LINK|DOT|MATIC|LTC|BCH|ETC/.test(text)) return 'CRY';
  return clean.slice(0, 3) || 'AST';
}
