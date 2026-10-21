/**
 * TRADUÇÃO DOS EVENTOS DO CALENDÁRIO ECONÔMICO (05/10/2026)
 * ========================================================
 *
 * O DONO PEDIU: "aba calendario traduzir eventos em portugues".
 *
 * POR QUE TRADUZIR AQUI, E NÃO NO BACKEND
 * ========================================
 * O feed público (`nfs.faireconomy.media`) entrega o título em inglês e não
 * oferece tradução. Mas o app JÁ tem o nome do país em português em
 * `types.ts` (`PAISES_SUPORTADOS`), e a tabela de países é consumida aqui.
 *
 * Se a tradução ficasse no backend, o mesmo evento chegaria em português pelo
 * gateway e em inglês pelo cache antigo — e o operador veria os dois idiomas
 * conforme o caminho do dado. Uma tradução por CONSUMIDOR é o que garante que
 * a tela fale uma língua só.
 *
 * TRÊS CAMADAS, NA ORDEM
 * ======================
 * 1. DICIONÁRIO EXATO dos eventos de alta frequência. Saída limpa, porque são
 *    os que o operador vê toda semana.
 * 2. DICIONÁRIO DE FRASES e depois DE PALAVRAS, sobre o título que sobrou.
 *    É o que cobre os eventos raros: os títulos do ForexFactory são compostos
 *    ("German Ifo Business Climate" = "Alemanha" + "Ifo" + "Clima de Negócios"),
 *    então a maioria sobrevive à troca palavra a palavra.
 * 3. TÍTULO ORIGINAL, se nenhuma das duas acertou.
 *
 * POR QUE A CAMADA 3 EXISTE E NÃO SE ESCONDE
 * ===========================================
 * Um evento não traduzido NÃO pode virar string vazia: o operador precisa saber
 * qual é o evento, mesmo sem entender o inglês. Por isso `traduzirEvento`
 * devolve o original e `eventoTraduzido` diz se houve tradução — a interface usa
 * isso para marcar a linha, e um teste trava o comportamento.
 *
 * SOBRE INVENTAR TRADUÇÃO
 * =======================
 * Não há "tradução inteligente" aqui: não há modelo, não há API. Um dicionário
 * escrito à mão é verificável — dá para ler o que ele afirma. Um título errado
 * seria pior que um título em inglês, porque o operador confia no que lê.
 */

/**
 * Dicionário exato, em ordem de aplicação.
 *
 * A chave é o título do feed com espaços normalizados e SEM o parêntese do mês
 * ("Retail Sales (Dec)" e "Retail Sales (Jan)" caem na mesma chave).
 *
 * Siglas ficam como siglas: MoM, QoQ, YoY, CPI, PPI, PMI, GDP, FOMC e ECB são
 * abreviações de uso corrente em português e traduzi-las tornaria o texto MENOS
 * reconheçível para quem lê calendário todo dia.
 */
const EXATOS: Record<string, string> = {
  // ---Política monetária dos EUA ---
  'fed interest rate decision': 'Decisão de juros do Fed',
  'fed rate decision': 'Decisão de juros do Fed',
  'fomc statement': 'Comunicado do FOMC',
  'fomc press conference': 'Coletiva de imprensa do FOMC',
  'fomc meeting minutes': 'Ata da reunião do FOMC',
  'fomc economic projections': 'Projeções econômicas do FOMC',
  'fed chair powell speaks': 'Fed: Powell fala',
  'fed chair speech': 'Discurso do presidente do Fed',
  'fed vice chair speaks': 'Fed: vice-presidente fala',
  'fed official speaks': 'Dirigente do Fed fala',
  'fed balance sheet': 'Balanço do Fed',
  'fed interest rate decision statement': 'Comunicado da decisão de juros do Fed',
  'speculator positions': 'Posições especulativas',

  // ---Mercado de trabalho dos EUA ---
  'non-farm employment change': 'Variação do emprego não agrícola',
  'nonfarm payrolls': 'Folha de pagamento não agrícola',
  'non-farm payrolls': 'Folha de pagamento não agrícola',
  'unemployment rate': 'Taxa de desemprego',
  'initial jobless claims': 'Pedidos iniciais de auxílio-desemprego',
  'continuing jobless claims': 'Pedidos continuados de auxílio-desemprego',
  'average hourly earnings': 'Salário médio por hora',
  'average weekly jobless claims': 'Pedidos semanais médios de auxílio',
  'employment change': 'Variação do emprego',
  'nonfarm employment change': 'Variação do emprego não agrícola',

  // ---Inflação dos EUA ---
  cpi: 'IPC',
  'core cpi': 'Núcleo do IPC',
  ppi: 'IPP',
  'core ppi': 'Núcleo do IPP',
  'pce price index': 'Índice de preços do gasto pessoal',
  'core pce price index': 'Núcleo do índice de preços do gasto pessoal',
  'consumer price index': 'Índice de preços ao consumidor',
  'producer price index': 'Índice de preços ao produtor',

  // ---Atividade dos EUA ---
  'retail sales': 'Vendas no varejo',
  'industrial production': 'Produção industrial',
  'building permits': 'Alvarás de construção',
  'housing starts': 'Início de obras',
  'housing permits': 'Alvarás residenciais',
  'new home sales': 'Vendas de casas novas',
  'existing home sales': 'Vendas de casas usadas',
  'pending home sales': 'Vendas de casas pendentes',
  'durable goods orders': 'Pedidos de bens de consumo duráveis',
  gdp: 'PIB',
  'trade balance': 'Balança comercial',
  'current account': 'Conta corrente',
  'consumer confidence': 'Confiança do consumidor',
  'consumer sentiment': 'Sentimento do consumidor',
  'business confidence': 'Confiança empresarial',
  'manufacturing pmi': 'PMI industrial',
  'services pmi': 'PMI de serviços',
  'composite pmi': 'PMI composto',
  'ism manufacturing pmi': 'ISM industrial',
  'ism services pmi': 'ISM de serviços',
  'ism manufacturing': 'ISM industrial',
  'ism services': 'ISM de serviços',
  's&p global manufacturing pmi': 'PMI industrial S&P Global',
  's&p global services pmi': 'PMI de serviços S&P Global',
  's&p global composite pmi': 'PMI composto S&P Global',

  // ---Banco central do Reino Unido ---
  'boe interest rate decision': 'Decisão de juros do Banco da Inglaterra',
  'boe official bank rate': 'Taxa oficial do Banco da Inglaterra',
  'boe monetary policy report': 'Relatório de política monetária do Banco da Inglaterra',
  'boe governor bailey speaks': 'Banco da Inglaterra: Bailey fala',
  'boe gov bailey speaks': 'Banco da Inglaterra: Bailey fala',
  'boe mpc member speak': 'Banco da Inglaterra: membro fala',

  // ---Banco central do Japão ---
  'boj interest rate decision': 'Decisão de juros do Banco do Japão',
  'boj statement on monetary policy': 'Comunicado de política monetária do Banco do Japão',
  'boj governor speech': 'Banco do Japão: governador fala',

  // ---Zona do euro ---
  'ecb interest rate decision': 'Decisão de juros do BCE',
  'ecb press conference': 'Coletiva de imprensa do BCE',
  'ecb economic bulletin': 'Boletim econômico do BCE',
  'ecb monetary policy accounts': 'Contas de política monetária do BCE',
  'ecb lagged accounts': 'Contas de política monetária do BCE',
  'ecb rate decision': 'Decisão de juros do BCE',
  'german ifo business climate': 'Clima de negócios Ifo da Alemanha',
  'german ifo business climate index': 'Índice de clima de negócios Ifo da Alemanha',
  'german ifo expectations': 'Expectativas Ifo da Alemanha',
  'german zew economic sentiment': 'Sentimento econômico ZEW da Alemanha',
  'german zew current conditions': 'Condições atuais ZEW da Alemanha',
  'german zew economic expectations': 'Expectativas econômicas ZEW da Alemanha',
  'german unemployment rate': 'Taxa de desemprego da Alemanha',
  'german industrial production': 'Produção industrial da Alemanha',
  'german trade balance': 'Balança comercial da Alemanha',
  'german retail sales': 'Vendas no varejo da Alemanha',
  'german cpi': 'IPC da Alemanha',
  'french business confidence': 'Confiança empresarial da França',
  'french manufacturing pmi': 'PMI industrial da França',
  'french services pmi': 'PMI de serviços da França',
  'french consumer confidence': 'Confiança do consumidor da França',
  'french cpi': 'IPC da França',
  'french unemployment rate': 'Taxa de desemprego da França',
  'eurozone industrial production': 'Produção industrial da Zona do Euro',
  'eurozone gdp': 'PIB da Zona do Euro',
  'eurozone zew economic sentiment': 'Sentimento econômico ZEW da Zona do Euro',
  'eurozone consumer confidence': 'Confiança do consumidor da Zona do Euro',
  'eurozone trade balance': 'Balança comercial da Zona do Euro',
  'euro area gdp': 'PIB da Zona do Euro',
  'spanish gdp': 'PIB da Espanha',
  'spanish industrial production': 'Produção industrial da Espanha',
  'italian gdp': 'PIB da Itália',
  'italian industrial production': 'Produção industrial da Itália',

  // ---Canadá, Austrália e Nova Zelândia ---
  'canadian gdp': 'PIB do Canadá',
  'canadian jobs report': 'Relatório de emprego do Canadá',
  'canadian employment change': 'Variação do emprego no Canadá',
  'canadian unemployment rate': 'Taxa de desemprego do Canadá',
  'canadian retail sales': 'Vendas no varejo do Canadá',
  'canadian trade balance': 'Balança comercial do Canadá',
  'canadian ivey pmi': 'PMI Ivey do Canadá',
  'australian employment change': 'Variação do emprego na Austrália',
  'australian unemployment rate': 'Taxa de desbloqueio na Austrália',
  'australian retail sales': 'Vendas no varejo na Austrália',
  'australian trade balance': 'Balança comercial da Austrália',
  'australian consumer confidence': 'Confiança do consumidor na Austrália',
  'australian business confidence': 'Confiança empresarial na Austrália',
  'rba interest rate decision': 'Decisão de juros do RBA',
  'rba statement on monetary policy': 'Comunicado de política monetária do RBA',
  'rba governor lowe speaks': 'RBA: Lowe fala',
  'new zealand gdp': 'PIB da Nova Zelândia',
  'new zealand cpi': 'IPC da Nova Zelândia',
  'new zealand unemployment rate': 'Taxa de desemprego da Nova Zelândia',
  'new zealand employment change': 'Variação do emprego na Nova Zelândia',
  'new zealand retail sales': 'Vendas no varejo na Nova Zelândia',
  'new zealand trade balance': 'Balança comercial da Nova Zelândia',
  'rbnz interest rate decision': 'Decisão de juros do RBNZ',
  'rbnz monetary policy statement': 'Comunicado de política monetária do RBNZ',

  // ---Brasil e América Latina ---
  'bcb interest rate decision': 'Decisão de juros do Banco Central do Brasil',
  'bcb selic rate decision': 'Decisão da taxa Selic',
  'copom rate decision': 'Decisão do Copom',
  bcb: 'Banco Central do Brasil',

  // ---China ---
  'china nbs manufacturing pmi': 'PMI industrial NBS da China',
  'china caixin manufacturing pmi': 'PMI industrial Caixin da China',
  'china nbs non-manufacturing pmi': 'PMI não industrial NBS da China',
  'china cpi': 'IPC da China',
  'china ppi': 'IPP da China',
  'pboc interest rate decision': 'Decisão de juros do Banco Popular da China',
  'lpr rate decision': 'Decisão da taxa LPR',
  'lpr': 'Taxa LPR',

  // ---Outros bancos centrais ---
  'snb interest rate decision': 'Decisão de juros do SNB',
  'rbi interest rate decision': 'Decisão de juros do Banco Central da Índia',
  'banxico interest rate decision': 'Decisão de juros do Banxico',

  // ---Petróleo, metais e energia ---
  'crude oil inventories': 'Inventário de petróleo bruto',
  'api crude oil inventories': 'Inventário de petróleo bruto (API)',
  'eia crude oil inventories': 'Inventário de petróleo bruto (EIA)',
  'natural gas storage': 'Estoque de gás natural',
  'eia natural gas storage': 'Estoque de gás natural (EIA)',
  'opec monthly oil market report': 'Relatório mensal de petróleo da OPEP',
  'opec+ meeting': 'Reunião da OPEP+',
  'opec meeting': 'Reunião da OPEP',
  'api crude oil inventory change': 'Variação do inventário de petróleo bruto (API)',

  // ---Índice de preços dosipayos ---
  'south africa cpi': 'IPC da África do Sul',
  'south africa unemployment rate': 'Taxa de desemprego da África do Sul',
  'turkey cpi': 'IPC da Turquia',
  'india cpi': 'IPC da Índia',
  'indonesia gdp': 'PIB da Indonésia',
  'south korea cpi': 'IPC da Coreia do Sul',
  'singapore cpi': 'IPC de Singapura',

  // ---Índices regionais dos EUA ---
  'philadelphia fed manufacturing index': 'Índice industrial da Fed de Filadélfia',
  'dallas fed manufacturing index': 'Índice industrial da Fed de Dallas',
  'richmond fed manufacturing index': 'Índice industrial da Fed de Richmond',
  'new york fed manufacturing index': 'Índice industrial da Fed de Nova York',
  'kansas city fed manufacturing index': 'Índice industrial da Fed de Kansas City',
  'atlanta fed gdp nowcast': 'Estimativa do PIB da Fed de Atlanta',
  'cleveland fed inflation nowcasting': 'Estimativa de inflação da Fed de Cleveland',
  'empire state manufacturing index': 'Índice industrial do Empire State',
  'gdp price index': 'Índice de preços do PIB',
  'real gdp': 'PIB real',
  'core real gdp': 'PIB real do núcleo',
  'unit labor costs': 'Custo do trabalho por unidade',
  'corporate profits': 'Lucros das empresas',
};

/**
 * Países: ADJETIVO e NOME.
 *
 * Os dois são necessários porque o feed escreve as duas formas. "Swedish Trade
 * Balance" e "Sweden Trade Balance" são o mesmo evento, e o feed traz as duas em
 * semanas diferentes. Traduzir só o substantivo deixaria metade da semana em
 * inglês — e foi assim que o teste pegou o defeito.
 */
const PAISES: Array<[string, string]> = [
  ['united states', 'Estados Unidos'],
  ['united kingdom', 'Reino Unido'],
  ['united', 'Unidos'],
  ['kingdom', 'Reino'],
  ['states', 'Estados'],
  ['america', 'América'],
  ['american', 'americano'],
  ['britain', 'Reino Unido'],
  ['british', 'britânico'],
  ['england', 'Inglaterra'],
  ['england\u2019s', 'da Inglaterra'],
  ['ireland', 'Irlanda'],
  ['irish', 'Irlanda'],
  ['scotland', 'Escócia'],
  ['wales', 'País de Gales'],
  ['germany', 'Alemanha'],
  ['german', 'Alemanha'],
  ['france', 'França'],
  ['french', 'França'],
  ['spain', 'Espanha'],
  ['spanish', 'Espanha'],
  ['italy', 'Itália'],
  ['italian', 'Itália'],
  ['portugal', 'Portugal'],
  ['greece', 'Grécia'],
  ['greek', 'Grécia'],
  ['netherlands', 'Holanda'],
  ['dutch', 'Holanda'],
  ['belgium', 'Bélgica'],
  ['switzerland', 'Suíça'],
  ['swiss', 'Suíça'],
  ['austria', 'Áustria'],
  ['poland', 'Polônia'],
  ['polish', 'Polônia'],
  ['sweden', 'Suécia'],
  ['swedish', 'Suécia'],
  ['norway', 'Noruega'],
  ['norwegian', 'Noruega'],
  ['denmark', 'Dinamarca'],
  ['danish', 'Dinamarca'],
  ['finland', 'Finlândia'],
  ['finnish', 'Finlândia'],
  ['canada', 'Canadá'],
  ['canadian', 'Canadá'],
  ['australia', 'Austrália'],
  ['australian', 'Austrália'],
  ['new zealand', 'Nova Zelândia'],
  ['japan', 'Japão'],
  ['japanese', 'Japão'],
  ['china', 'China'],
  ['chinese', 'China'],
  ['hong kong', 'Hong Kong'],
  ['korea', 'Coreia'],
  ['south korea', 'Coreia do Sul'],
  ['korean', 'Coreia'],
  ['india', 'Índia'],
  ['indian', 'Índia'],
  ['indonesia', 'Indonésia'],
  ['indonesian', 'Indonésia'],
  ['malaysia', 'Malásia'],
  ['thailand', 'Tailândia'],
  ['vietnam', 'Vietnã'],
  ['philippines', 'Filipinas'],
  ['singapore', 'Singapura'],
  ['brazil', 'Brasil'],
  ['brazilian', 'brasileiro'],
  ['mexico', 'México'],
  ['mexican', 'México'],
  ['chile', 'Chile'],
  ['colombia', 'Colômbia'],
  ['argentina', 'Argentina'],
  ['peru', 'Peru'],
  ['south africa', 'África do Sul'],
  ['turkey', 'Turquia'],
  ['turkish', 'Turquia'],
  ['egypt', 'Egito'],
  ['nigeria', 'Nigéria'],
  ['saudi', 'Arábia Saudita'],
  ['israel', 'Israel'],
  ['russia', 'Rússia'],
  ['ukraine', 'Ucrânia'],
  ['eurozone', 'Zona do Euro'],
  ['euro zone', 'Zona do Euro'],
  ['euro area', 'Zona do Euro'],
];

/**
 * Variação temporal no fim do título.
 *
 * ForexFactory escreve o sufixo no MEIO da string — "GDP YoY", "Retail Sales
 * MoM" — mas ele é sempre a ÚLTIMA palavra. Sem tirar o sufixo antes de buscar
 * no dicionário, "GDP YoY" não casa com a entrada "gdp" e o evento mais
 * watched do calendário fica em inglês.
 */
const VARIACOES = ['mom', 'yoy', 'qoq', 'm/m', 'q/q', 'y/y', 'q3', 'q4'];

/**
 * OS 61 TITULOS QUE O FEED REAL DEU E O DICIONARIO NAO COBRIA (05/10/2026).
 *
 * MEDIDO, nao estimado: `ff_calendar_thisweek.json` devolveu **82 eventos**, e
 * **61 titulos distintos (69 ocorrencias) cafram fora** das 162 entradas que
 * eu tinha escrito a mao. Ou seja, **84% do calendario aparecia em ingles ou em
 * portugues pela metade** — que e exatamente a "poluicao" e o "outros PT BR" que
 * o dono apontou.
 *
 * Conclusao honesta: um dicionario escrito de memoria nao cobre o feed. Ele
 * cobre o que eu imaginei que viria. A lista abaixo vem do DADO, nao da
 * suposicao.
 *
 * As entradas sao as do feed com a traducao. Um titulo novo nao entra aqui por
 * palpite: entra quando o feed o traz, e a tela marca `en` ate la chegar.
 */
const DO_FEED: Record<string, string> = {
  // --- Agenda e feriados ---
  'bank holiday': 'Feriado bancário',
  'opec-jmmc meetings': 'Reunião da OPEP+ (JMMC)',
  'ecofin meetings': 'Reunião do ECOFIN',
  'eurogroup meetings': 'Reunião do Eurogrupo',
  'ecb monetary policy meeting accounts': 'Contas da reunião de política monetária do BCE',

  // --- Serviços e atividade ---
  'final services pmi': 'PMI de serviços (final)',
  'construction pmi': 'PMI da construção',
  'ivey pmi': 'PMI Ivey',
  'spanish services pmi': 'PMI de serviços da Espanha',
  'italian services pmi': 'PMI de serviços da Itália',
  'french final services pmi': 'PMI de serviços da França (final)',
  'german final services pmi': 'PMI de serviços da Alemanha (final)',

  // --- Encomendas e producao ---
  'german factory orders m/m': 'Encomendas da indústria da Alemanha (m/m)',
  'french industrial production m/m': 'Produção industrial da França (m/m)',
  'italian industrial production m/m': 'Produção industrial da Itália (m/m)',
  'german industrial production m/m': 'Produção industrial da Alemanha (m/m)',
  'final wholesale inventories m/m': 'Estoques no atacado (final, m/m)',
  'prelim machine tool orders y/y': 'Encomendas de máquinas-ferramenta (preliminar, a/a)',
  'housing equity withdrawal q/q': 'Retirada de capital próprio do imóvel (t/t)',
  'leading indicators': 'Indicadores líderes',

  // --- Emprego e salários ---
  'adp weekly employment change': 'Variação do emprego semanal ADP',
  'average cash earnings y/y': 'Ganhos em dinheiro médios (a/a)',
  'anz job advertisements m/m': 'Anúncios de emprego (m/m)',
  'unemployment claims': 'Pedidos de auxílio-desemprego',

  // --- Inflacao e precos ---
  'ppi m/m': 'IPP (m/m)',
  'mi inflation gauge m/m': 'Medidor de inflação da Agency (m/m)',
  'mi inflation expectations': 'Expectativas de inflação da Agency',
  'rcm/tipp economic optimism': 'Otimismo econômico RCM/TIPP',
  'gdt price index': 'Índice de preços GDT',
  'anz commodity prices m/m': 'Preços das matérias-primas ANZ (m/m)',
  'prelim uom inflation expectations': 'Expectativas de inflação da Universidade de Michigan (UoM, preliminar)',
  'seco consumer climate': 'Clima do consumidor SECO',
  'prelim uom consumer sentiment': 'Sentimento do consumidor da Universidade de Michigan (UoM, preliminar)',

  // --- Confianca e sentiment ---
  'sentix investor confidence': 'Confiança do investidor Sentix',
  'nzier business confidence': 'Confiança empresarial NZIER',
  'westpac consumer sentiment': 'Sentimento do consumidor Westpac',
  'economy watchers sentiment': 'Sentimento dos inspetores econômicos',
  'eco watchers sentiment': 'Sentimento dos inspetores econômicos',
  'lloyds hpi m/m': 'Índice de preços imobiliários Lloyds (HPI, m/m)',
  'rics house price balance': 'Saldo do índice de preços imobiliários RICS',
  'boe credit conditions survey': 'Pesquisa de condições de crédito do Banco da Inglaterra',
  'german buba president nagel speaks': 'Bundesbank: Nagel fala',

  // --- Bonds e medidas ---
  '10-y bond auction': 'Leilão de títulos de 10 anos',
  '30-y bond auction': 'Leilão de títulos de 30 anos',
  'foreign currency reserves': 'Reservas cambiais',
  'consumer credit m/m': 'Crédito ao consumidor (m/m)',

  // ---_discursos de bancos centrais ---
  'fomc member bowman speaks': 'FOMC: Bowman fala',
  'fomc member schmid speaks': 'FOMC: Schmid fala',
  'fomc member waller speaks': 'FOMC: Waller fala',
  'fomc member musalem speaks': 'FOMC: Musalem fala',
  'fomc member collins speaks': 'FOMC: Collins fala',
  'boj gov ueda speaks': 'BOJ: Ueda fala',
  'gov board member martin speaks': 'Conselho: Martin fala',
  'mpc member mann speaks': 'MPC: Mann fala',
  'mpc member greene speaks': 'MPC: Greene fala',
  'mpc member pill speaks': 'MPC: Pill fala',
  'mpc member lombardelli speaks': 'MPC: Lombardelli fala',

  // --- Outros ---
  'french gov budget balance': 'Saldo orçamentário do governo francês',
  'french trade balance': 'Balança comercial da França',
  'retail sales m/m': 'Vendas no varejo (m/m)',
  'household spending y/y': 'Gastos das famílias (a/a)',
  'api weekly statistical bulletin': 'Boletim semanal de estatísticas (API)',
};

/** Frases de duas ou mais palavras.
 *
 * Aplicadas ANTES das palavras, e da mais longa para a mais curta: traduzir
 * "Business" e "Climate" separadamente daria "Clima de Negócios" — que está
 * certo — mas traduzir "Retail" antes de "Retail Sales" quebraria a expressão
 * em duas metades sem sentido.
 */
const FRASES: Array<[string, string]> = [
  ['business climate', 'clima de negócios'],
  ['economic sentiment', 'sentimento econômico'],
  ['business sentiment', 'sentimento empresarial'],
  ['inflation expectations', 'expectativas de inflação'],
  ['interest rate decision', 'decisão de juros'],
  ['rate decision', 'decisão de juros'],
  ['official bank rate', 'taxa oficial do banco'],
  ['policy rate', 'taxa de política monetária'],
  ['monetary policy', 'política monetária'],
  ['statement on monetary', 'comunicado de política monetária'],
  ['press conference', 'coletiva de imprensa'],
  ['meeting minutes', 'ata da reunião'],
  ['economic projections', 'projeções econômicas'],
  ['economic bulletin', 'boletim econômico'],
  ['retail sales', 'vendas no varejo'],
  ['industrial production', 'produção industrial'],
  ['consumer confidence', 'confiança do consumidor'],
  ['business confidence', 'confiança empresarial'],
  ['current conditions', 'condições atuais'],
  ['current account', 'conta corrente'],
  ['trade balance', 'balança comercial'],
  ['unemployment rate', 'taxa de desemprego'],
  ['employment change', 'variação do emprego'],
  ['jobless claims', 'pedidos de auxílio-desemprego'],
  ['average hourly earnings', 'salário médio por hora'],
  ['housing starts', 'início de obras'],
  ['new home sales', 'vendas de casas novas'],
  ['existing home sales', 'vendas de casas usadas'],
  ['pending home sales', 'vendas de casas pendentes'],
  ['building permits', 'alvarás de construção'],
  ['durable goods', 'bens de consumo duráveis'],
  ['crude oil', 'petróleo bruto'],
  ['natural gas', 'gás natural'],
  ['central bank', 'banco central'],
  ['manufacturing pmi', 'PMI industrial'],
  ['services pmi', 'PMI de serviços'],
  ['composite pmi', 'PMI composto'],
  ['market pmi', 'PMI de mercado'],
  ['unit labor costs', 'custo do trabalho por unidade'],
  ['job market', 'mercado de trabalho'],
  ['government bonds', 'títulos públicos'],
  ['investment flows', 'fluxos de investimento'],
];

/**
 * Palavras isoladas.
 *
 * Só entram aqui termos que sozinhos traduzem sem ambiguirdade. Sigla de banco
 * central (FOMC, ECB, BOE, BOJ, RBA, RBNZ, SNB, BOC, PIMCO) NÃO entra: em
 * português ela continua a sigla.
 */
const PALAVRAS: Array<[string, string]> = [
  ['german', 'Alemanha'],
  ['germany', 'Alemanha'],
  ['french', 'França'],
  ['france', 'França'],
  ['spanish', 'Espanha'],
  ['spain', 'Espanha'],
  ['italian', 'Itália'],
  ['italy', 'Itália'],
  ['canadian', 'Canadá'],
  ['canada', 'Canadá'],
  ['australian', 'Austrália'],
  ['australia', 'Austrália'],
  ['brazilian', 'brasileiro'],
  ['brazil', 'Brasil'],
  ['chinese', 'chinês'],
  ['china', 'China'],
  ['japanese', 'japonês'],
  ['japan', 'Japão'],
  ['british', 'britânico'],
  ['eurozone', 'Zona do Euro'],
  ['euro zone', 'Zona do Euro'],
  ['euro area', 'Zona do Euro'],
  ['new zealand', 'Nova Zelândia'],
  ['south africa', 'África do Sul'],
  ['south korea', 'Coreia do Sul'],
  ['korea', 'Coreia'],
  ['turkey', 'Turquia'],
  ['india', 'Índia'],
  ['indonesia', 'Indonésia'],
  ['singapore', 'Singapura'],
  ['mexico', 'México'],
  ['sweden', 'Suécia'],
  ['norway', 'Noruega'],
  ['denmark', 'Dinamarca'],
  ['switzerland', 'Suíça'],
  ['poland', 'Polônia'],
  ['greece', 'Grécia'],
  ['portugal', 'Portugal'],
  ['ireland', 'Irlanda'],
  ['austria', 'Áustria'],
  ['belgium', 'Bélgica'],
  ['finland', 'Finlândia'],
  ['netherlands', 'Holanda'],
  ['united', 'Unidos'],
  ['kingdom', 'Reino'],
  ['states', 'Estados'],
  ['american', 'americano'],
  ['corporate', 'corporativo'],
  ['business', 'negócios'],
  ['manufacturing', 'industrial'],
  ['services', 'serviços'],
  ['service', 'serviço'],
  ['production', 'produção'],
  ['producer', 'produtor'],
  ['consumer', 'do consumidor'],
  ['customers', 'clientes'],
  ['inflation', 'inflação'],
  ['price', 'de preços'],
  ['prices', 'de preços'],
  ['index', 'índice'],
  ['employment', 'emprego'],
  ['unemployment', 'desemprego'],
  ['payrolls', 'folha de pagamento'],
  ['payroll', 'folha de pagamento'],
  ['farm', 'agrícola'],
  ['non-farm', 'não agrícola'],
  ['nonfarm', 'não agrícola'],
  ['wages', 'salários'],
  ['earnings', 'ganhos'],
  ['hourly', 'por hora'],
  ['average', 'médio'],
  ['weekly', 'semanal'],
  ['initial', 'inicial'],
  ['continuing', 'continuado'],
  ['claims', 'pedidos'],
  ['jobless', 'auxílio-desemprego'],
  ['housing', 'residencial'],
  ['home', 'casa'],
  ['houses', 'casas'],
  ['building', 'construção'],
  ['permits', 'alvarás'],
  ['starts', 'início de obras'],
  ['sales', 'vendas'],
  ['retail', 'varejo'],
  ['orders', 'pedidos'],
  ['goods', 'bens'],
  ['durable', 'duráveis'],
  ['capital', 'capital'],
  ['trade', 'comercial'],
  ['balance', 'balança'],
  ['current', 'atual'],
  ['account', 'conta'],
  ['budget', 'orçamento'],
  ['deficit', 'déficit'],
  ['surplus', 'superávit'],
  ['revisions', 'revisões'],
  ['final', 'final'],
  ['preliminary', 'preliminar'],
  ['flash', 'estimativa rápida'],
  ['inventory', 'inventário'],
  ['inventories', 'inventário'],
  ['storage', 'estoque'],
  ['crude', 'bruto'],
  ['oil', 'petróleo'],
  ['gas', 'gás'],
  ['gold', 'ouro'],
  ['silver', 'prata'],
  ['copper', 'cobre'],
  ['meeting', 'reunião'],
  ['minutes', 'ata'],
  ['statement', 'comunicado'],
  ['speaks', 'fala'],
  ['speech', 'discurso'],
  ['remarks', 'declarações'],
  ['press', 'imprensa'],
  ['conference', 'coletiva'],
  ['forecast', 'previsão'],
  ['rate', 'taxa'],
  ['rates', 'taxas'],
  ['decision', 'decisão'],
  ['decision', 'decisão'],
  ['official', 'oficial'],
  ['governor', 'governador'],
  ['chair', 'presidente'],
  ['vice chair', 'vice-presidente'],
  ['officer', 'dirigente'],
  ['member', 'membro'],
  ['revised', 'revisado'],
  ['revised from', 'revisado de'],
  ['expected', 'previsto'],
  ['actual', 'real'],
  ['previous', 'anterior'],
  ['forecast', 'previsão'],
];

/** Abreviação de mês do feed ("Dec", "Jan") para português. */
const MESES: Array<[string, string]> = [
  ['jan', 'jan'],
  ['feb', 'fev'],
  ['mar', 'mar'],
  ['apr', 'abr'],
  ['may', 'mai'],
  ['jun', 'jun'],
  ['jul', 'jul'],
  ['aug', 'ago'],
  ['sep', 'set'],
  ['oct', 'out'],
  ['nov', 'nov'],
  ['dec', 'dez'],
];

/**
 * Normaliza para busca: espaços colapsados, sem caixa.
 *
 * O feed manda "Retail Sales (Dec)" numa semana e "Retail Sales (Jan)" na
 * seguinte. O parêntese do mês não pode entrar na chave, senão o dicionário
 * precisaria de uma entrada por mês — treze entradas para a mesma frase.
 */
function chave(titulo: string): string {
  return titulo.replace(/\s+/g, ' ').trim().toLowerCase();
}

/**
 * Separa o título do parêntese de mês/ano e devolve as duas partes.
 *
 * "Non-Farm Employment Change (Dec)" → ["non-farm employment change", "(dec)"]
 */
function separarParenthese(titulo: string): [string, string] {
  const m = titulo.match(/^(.*?)\s*(\([^)]*\))?\s*$/);
  const base = (m?.[1] ?? titulo).trim();
  const resto = m?.[2] ?? '';
  return [base, resto];
}

/** Aplica as camadas 2 e 3: frases e depois palavras. */
function traduzirPorPalavras(titulo: string): string {
  let saida = titulo;

  // PAÍSES primeiro: "United Kingdom" precisa virar uma coisa só, senão
  // "United" e "Kingdom" viram traduções separadas e sobra "Unidos Reino".
  for (const [de, para] of [...PAISES].sort((a, b) => b[0].length - a[0].length)) {
    saida = saida.replace(new RegExp(`\\b${de.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi'), para);
  }

  // Frases depois, e da mais longa para a mais curta: "central bank" tem de
  // ser traduzido antes de "bank" existir como palavra solta.
  for (const [de, para] of [...FRASES].sort((a, b) => b[0].length - a[0].length)) {
    saida = saida.replace(new RegExp(`\\b${de.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi'), para);
  }
  for (const [de, para] of [...PALAVRAS].sort((a, b) => b[0].length - a[0].length)) {
    saida = saida.replace(new RegExp(`\\b${de.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi'), para);
  }

  // Espaços duplos e antes de parêntese.
  saida = saida
    .replace(/\s{2,}/g, ' ')
    .replace(/\s+\(/g, ' (')
    .replace(/\(\s+/g, '(')
    .trim();

  return saida;
}

/** O título cita algum país (nome ou adjetivo)? */
function citaPais(titulo: string): boolean {
  const t = titulo.toLowerCase();
  return PAISES.some(([de]) => new RegExp(`\\b${de.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`).test(t));
}

/**
 * Tira o sufixo de variação e devolve `[base, sufixo]`.
 *
 * "GDP YoY" → ["gdp", "YoY"]. O sufixo é devolvido COMO O FEED ESCREVEU
 * ("YoY", "MoM", "m/m") porque é assim que o operador reconhece no calendário
 * da corretora, e normalizar para português tornaria a comparação mais difícil.
 */
function separarVariacao(titulo: string): [string, string] {
  const partes = titulo.trim().split(/\s+/);
  if (partes.length < 2) return [titulo.trim(), ''];
  const ultimo = partes[partes.length - 1].toLowerCase();
  if (!VARIACOES.includes(ultimo)) return [titulo.trim(), ''];
  return [partes.slice(0, -1).join(' '), partes[partes.length - 1]];
}

/** Traduz o mês dentro do parêntese, se houver. */
function traduzirParenthese(resto: string): string {
  if (!resto) return '';
  let saida = resto;
  for (const [de, para] of MESES) {
    saida = saida.replace(new RegExp(`\\b${de}\\b`, 'gi'), para);
  }
  return saida;
}

/** Primeira letra maiúscula, sem mexer nas siglas. */
function capitalizar(texto: string): string {
  if (!texto) return texto;
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/**
 * Traduz um título de evento para português.
 *
 * Devolve o TÍTULO ORIGINAL quando não reconhece o evento — nunca string vazia
 * e nunca um título inventado. Use `eventoTraduzido` para saber qual dos dois
 * aconteceu.
 */
export function traduzirEvento(titulo: string): string {
  const original = titulo.replace(/\s+/g, ' ').trim();
  if (!original) return original;

  const [baseCrua, restoCru] = separarParenthese(original);
  const [baseSemSufixo, sufixo] = separarVariacao(baseCrua);
  const cauda = sufixo ? ` ${sufixo}` : '';
  const resto = traduzirParenthese(restoCru);

  /*
    Nao duplicar o sufixo.

    MEDIDO (05/10/2026): o dicionário escrito a mao tem duas formas de chave —
    `'ppi'` (o sufixo é anexado) e `'anz commodity prices m/m'` (o sufixo já
    está escrito). Anexar sem olhar produzia "Preços das matérias-primas (m/m)
    m/m" na tela.

    A guarda resolve as DUAS formas de uma vez: se a tradução já termina com o
    sufixo, ele não é anexado. Chave curta continua anexando, e chave longa
    continua sem repetir.
  */
  const anexar = (texto: string): string => {
    if (!sufixo) return texto;
    /*
      Testa `includes`, e nao termina-com.

      A traducao deste feed escreve o sufixo DENTRO de parenteses — "Precos das
      materias-primas (m/m)" — e um teste de fim de string nunca casa com `)`
      depois. Foi assim que a duplicacao "… (m/m) m/m" passou: a guarda existia,
      testava `$`, e nao fazia nada.
    */
    if (texto.toLowerCase().includes(sufixo.toLowerCase())) return texto;
    return `${texto}${cauda}`;
  };

  // CAMADA 1 — dicionário exato.
  //
  // `DO_FEED` entra JUNTO de `EXATOS`: são as traduções tiradas do feed real
  // medido, e o lookup é o mesmo. Se ficassem em dois mapas, a camada 1
  // escolheria um e o outro nunca seria lido.
  //
  // A ORDEM DA BUSCA IMPORTA, e já foi defeito duas vezes:
  //
  //  1. `separarVariacao` tira o sufixo ANTES da busca, então uma chave
  //     escrita COM sufixo — `'ppi m/m'`, `'retail sales m/m'`, 10 dos 61
  //     títulos medidos — nunca era encontrada;
  //  2. corrigindo isso, a busca "inteira" usava `baseSemSufixo`, que JÁ VINHA
  //     sem o sufixo: o mesmo defeito, com outro nome.
  //
  // Por isso a chave INTEIRA vem de `baseCrua`, antes de qualquer separação, e
  // a sem-sufixo é derivada dela. As duas formas de escrever a chave funcionam.
  const baseInteira = chave(baseCrua);
  const baseSemVariacao = sufixo
    ? chave(baseCrua.replace(new RegExp(`\\s+${sufixo}$`, 'i'), ''))
    : baseInteira;
  const exato =
    EXATOS[baseInteira] ??
    DO_FEED[baseInteira] ??
    EXATOS[baseSemVariacao] ??
    DO_FEED[baseSemVariacao];
  if (exato) return capitalizar(anexar(exato)) + (resto ? ` ${resto}` : '');

  // CAMADA 2 — frases e palavras, MAS SÓ QUANDO O TÍTULO CITA UM PAÍS.
  //
  // A condição não é cosmeticamente restritiva: ela é o que impede a camada de
  // traduzir título que ela não conhece. "Zorkian Widget Index Release" tem
  // "Index" e "Release" na lista de palavras, e viraria "Zorkian Widget índice
  // divulgação" — metade em português, metade em inglês, e com CAIXA errada no
  // meio. Pior que deixar em inglês, porque parece traduzido.
  //
  // Já "Swedish Trade Balance" cita um país, e traduzir por palavra é
  // exatamente o que serve ali.
  if (citaPais(baseSemSufixo)) {
    const porPalavras = traduzirPorPalavras(baseSemSufixo);
    if (porPalavras.toLowerCase() !== chave(baseSemSufixo)) {
      return capitalizar(anexar(porPalavras)) + (resto ? ` ${resto}` : '');
    }
  }

  // CAMADA 3 — original.
  return original;
}

/**
 * O título foi de fato traduzido?
 *
 * Serve para a interface marcar a linha como "ainda em inglês" e para o teste
 * distinguir "traduzido" de "devolvido igual".
 */
export function eventoTraduzido(titulo: string): boolean {
  const original = titulo.replace(/\s+/g, ' ').trim();
  if (!original) return false;
  return traduzirEvento(original) !== original;
}

/**
 * Categorias de evento, para o operador achar rápido o que importa.
 *
 * Serve para a-bandeira-e-título na linha: o operador lê "juros", "inflação",
 * "emprego" antes de ler o nome do evento.
 */
export function categoriaEvento(titulo: string): string {
  const t = titulo.toLowerCase();
  if (/fomc|fed |interest rate|rate decision|monetary policy|selic|copom|lpr|pboc|ecb |boe |boj |rba |rbnz|snb|boc |banxico|central bank/.test(t)) {
    return 'Juros';
  }
  if (/cpi|ppi|inflation|pce|price index|deflator/.test(t)) return 'Inflação';
  if (/employment|unemployment|payroll|jobless|wages|earnings|jobs report|labor/.test(t)) return 'Emprego';
  /*
    `\bindex\b` NÃO entra: é genérico demais. Qualquer título desconhecido que
    tenha "Index" receberia "Atividade", e aí a categoria pararia de dizer o que
    o evento é. `ifo` e `zew` são específicos o bastante.
  */
  if (/gdp|pmi|industrial production|retail sales|orders|trade balance|consumer confidence|business confidence|sentiment|\bifo\b|\bzew\b|\brank\b/.test(t)) {
    return 'Atividade';
  }
  if (/inventor|storage|crude|oil|opec|gas/.test(t)) return 'Energia';
  return '';
}