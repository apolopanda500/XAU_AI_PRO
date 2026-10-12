/**
 * A SIGLA do ativo, decidida SOMENTE pela classe que a corretora publica.
 *
 * A DECISAO DO DONO (09/10/2026)
 * ==============================
 * "deixar o catalogo sem icone apenas lista opcional".
 *
 * Atendendo a decisao, este arquivo PERDEU tudo que decidia por nome:
 *
 *   - a lista de metais por prefixo (`XAU`, `GOLD`, `PLATIN`...);
 *   - a lista de tokens de cripto (`BTC`, `SOL`, `DOGE`...);
 *   - a lista de moedas de cotacao (`USDT`, `USD`, `BRL`...) usada para ADIVINHAR
 *     onde o ativo terminava e a moeda comecava;
 *   - o palpite de par de forex por comprimento (`6 LETRAS = PAR`);
 *   - o recorte de tres letras que vazava `SOL` para `SOLVAR`.
 *
 * POR QUE A FUNCAO NAO RECEBE MAIS O SIMBOLO
 * ==========================================
 * A assinatura era `assetIcon(symbol, assetClass)`. Mesmo com a classe tendo
 * prioridade, a funcao podia ler o nome quando a classe faltava — e foi isso que
 * o AGENTS.md §3 mediu como defeito: "sem fronteira de palavra, `SOL` casa
 * dentro de 'Solvar'". Um parametro que se pode ignorar e um parametro que alguem
 * vai usar.
 *
 * Agora a funcao recebe APENAS a classe. Ela nao tem como adivinhar pelo nome,
 * porque nao recebe o nome. Quem quiser um icone precisa antes saber a classe, e
 * quem sabe a classe e a corretora — pelo catalogo.
 *
 * O QUE ACONTECE SEM CLASSE
 * ==========================
 * Devolve string vazia: NENHUMA sigla. Isso e a decisao do dono — o catalogo
 * fica sem icone, e a lista manda. Antes devolvia `AST`, uma sigla inventada que
 * o operador lia como se fosse informacao.
 *
 * Nada aqui e perdido: quem chamava `assetIcon(x)` sem classe e hoje nao recebe
 * sigla nenhuma, e a coluna do par continua la.
 */

/**
 * As classes, e o que cada uma quer dizer.
 *
 * A chave e a que o gateway manda em `asset_class`. Este mapa e de TRADUCAO de
 * rotulo, e nao de decisao de mercado: nenhuma regra aqui filtra o ativo, todas
 * devolvem a sigla que o operador le.
 *
 * Classe nova entra aqui COM O NOME QUE A CORRETORA ESCREVE — nao adivinhada
 * pelo simbolo. Sem entrada, sem sigla: o icone e opcional.
 */
const SIGLA_POR_CLASSE: Record<string, string> = {
  metal: 'MET',
  crypto: 'CRY',
  forex: 'FX',
  index: 'IDX',
  equity: 'EQ',
  future: 'FUT',
  option: 'OPT',
  bond: 'OND',
  energy: 'ENE',
  commodity: 'COM',
};

/** O icon que nao existe. Devolvido quando a corretora nao contou a classe. */
export const SEM_ICONE = '';

/**
 * A sigla que o operador le, de UM campo: a classe.
 *
 * @param assetClass  a classe que a CORRETORA publica (`metal`, `crypto`,
 *   `forex`...). Vem de `asset_registry`; e a hierarquia, e manda.
 *
 * @returns a sigla da classe, ou `''` quando a classe nao e conhecida.
 */
export function assetIcon(assetClass?: string): string {
  const classe = String(assetClass ?? '')
    .trim()
    .toLowerCase();
  return SIGLA_POR_CLASSE[classe] ?? SEM_ICONE;
}
