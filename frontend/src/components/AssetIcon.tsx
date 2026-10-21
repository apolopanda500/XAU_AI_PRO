import { assetIcon } from '../lib/assetIcons';

/**
 * O selo do ativo na lista — OPCIONAL, como o dono decidiu em 09/10/2026:
 * "deixar o catalogo sem icone apenas lista opcional".
 *
 * A sigla vem SOMENTE da classe que a corretora publica. Sem classe, este
 * componente devolve `null`: nada e desenhado, e a lista fica so com o par.
 *
 * MEDIDO: antes havia uma lista de nomes no codigo (`BTC`, `SOL`, `GOLD`...) que
 * adivinhava a sigla pelo simbolo — e o AGENTS.md §3 tem o caso medido disso:
 * `SOL` casa dentro de `SOLVAR`. A assinatura agora recebe a classe, nao o
 * simbolo, e por isso nao consegue adivinhar por nome.
 */
export function AssetIcon({
  symbol,
  assetClass,
}: {
  symbol: string;
  assetClass?: string | null;
}) {
  const sigla = assetIcon(assetClass ?? undefined);

  // Sem sigla, sem selo. Um selo vazio ocupa espaco e nao informa nada.
  if (!sigla) return null;

  return (
    <span className="asset-icon" aria-hidden="true" title={symbol}>
      {sigla}
    </span>
  );
}
