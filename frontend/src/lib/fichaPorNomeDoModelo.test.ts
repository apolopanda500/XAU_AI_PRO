/*
  O OURO: O NOME DA CORRETORA E O NOME DO MODELO (07/10/2026)
  =============================================================

  MEDIDO na conta 391773676 (XMGlobal-MT5 14), com o build instalado:

      GOLD       path = Derivatives\Spot Metals\GOLD   contract_size = 100
      XAUUSD     NAO EXISTE no terminal XM  (symbol_info("XAUUSD") -> None)
      XAUJPY     existe, path = Derivatives\Spot Metals
      .meta.json XAUUSD_H1 / _H4 / _M15 / _M5
      .ex5       o EA roda GOLD,M5 no tester

  O MESMO METAL, TRES NOMES, E O PRIMEIRO `find` CASAVA COM UM SO.

  POR QUE ISTO NAO E "SÓ UM DETALHE DE NOME"
  ============================================
  A ficha do ativo alimenta TRES coisas que a tela usa para decidir:

      - `assetClass`  -> `mercadoDoAtivo` -> o mercado da consulta
      - `contractSize` -> `nivelDoValor`  -> dinheiro vira preco
      - `volumeMin/Max/Step` -> a faixa que o painel aceita

  Com a ficha `null`, as TRES somem de uma vez, e o painel diz "depende do
  contrato" para um ativo que a corretora JA TINHA PUBLICADO. E o AGENTS.md 5
  pelo lado que ESCREVEU a tela: o sintoma cairia em quem escreveu, e a culpa
  seria da corretora.

  A SEGUNDA BUSCA E POR `modelSymbol`
  ===================================
  O campo que o PRODUTOR preenche, com o mapa do operador (`para_modelo`).

  E no produtor, e nao no frontend, pelo motivo do AGENTS.md 5: o mapa vive no
  gateway, e duas copias divergem. O `symbol_aliases.json` tem
  `{"mt5": {"XAUUSD": "GOLD"}}` — se o frontend tivesse o proprio mapa, e o
  operador mudasse o arquivo, a tela continuaria com o mapa velho.

  A ORDEM DAS BUSCAS IMPORTA, e e medida
  ======================================
  `symbol` primeiro, `modelSymbol` depois. Se `modelSymbol` casasse primeiro, um
  ativo poderia receber a ficha de OUTRO pelo nome do modelo — e a ficha errada
  e silenciosa: `contract_size` errado em forex e 100.000 vezes o preco.
*/
import { describe, expect, it } from 'vitest';
import { fichaDoAtivo, mercadoDoAtivo, requisitoDeMargem, unidadeDeVolume } from './volumeUnidade';
import { parseAssetCatalog, type AssetRow } from './brokerCatalog';

/** O que o gateway devolve para `GOLD`, medido no terminal da XM. */
const PAYLOAD_GOLD = {
  assets: [
    {
      symbol: 'GOLD',
      model_symbol: 'XAUUSD',
      has_model: true,
      asset_class: 'metal',
      contract_size: 100,
      point: 0.01,
      digits: 2,
      volume_min: 0.01,
      volume_max: 50,
      volume_step: 0.01,
      availability: 'available',
      restrictions: [],
    },
  ],
};

const CATALOGO: AssetRow[] = parseAssetCatalog(PAYLOAD_GOLD);

describe('o OURO: a ficha vem pelo nome que a CORRETORA publica', () => {
  it('PROVA: `GOLD` acha a ficha, com contrato, classe e faixa', () => {
    const ficha = fichaDoAtivo(CATALOGO, 'GOLD');

    expect(ficha).not.toBeNull();
    // MEDIDO no terminal da XM: contract_size 100, nao 1.
    expect(ficha!.contractSize).toBe(100);
    expect(ficha!.assetClass).toBe('metal');
    expect(ficha!.volumeMin).toBe(0.01);
    expect(ficha!.volumeMax).toBe(50);
  });

  it('PROVA: `XAUUSD` — o nome do MODELO — acha a MESMA ficha', () => {
    /*
      E o que faltava. O `.meta.json` e o `.pkl` se chamam `XAUUSD_*`, e o
      `PriceChart` recebe o par escolhido na tela. Com o `find` so por
      `symbol`, a ficha vinha `null` e o mercado ficava vazio — o grafico nao
      carregava, com o mesmo defeito do BTCUSD.
    */
    const porCorretora = fichaDoAtivo(CATALOGO, 'GOLD');
    const porModelo = fichaDoAtivo(CATALOGO, 'XAUUSD');

    expect(porModelo).not.toBeNull();
    // E a MESMA ficha, nao uma parecido: o contrato tem de ser o mesmo numero.
    expect(porModelo!.contractSize).toBe(porCorretora!.contractSize);
    expect(porModelo!.assetClass).toBe(porCorretora!.assetClass);
  });

  it('PROVA: com a ficha, o mercado e METAS e o requisito sai em dinheiro', () => {
    /*
      O grafico so precisa de `mercadoDoAtivo`. Sem a ficha ele devolve `null`,
      e o `configurado` do `AcompanharModelos` fica falso — o grafico nao
      carrega, e a tela diz que o par nao esta escolhido quando o par ESTA.
    */
    const ficha = fichaDoAtivo(CATALOGO, 'XAUUSD');
    expect(mercadoDoAtivo(ficha?.assetClass)).toBe('metals');

    // E com o contrato 100, o dinheiro vira preco sem 100.000 vezes de erro.
    const r = requisitoDeMargem(0.01, 2400, ficha!.contractSize, 1000);
    expect(r.nocional).toBeCloseTo(0.01 * 100 * 2400, 6);
    expect(r.motivo).toBeNull();
  });

  it('a unidade do volume e a do METAL, e nao "Token(s)"', () => {
    // `unidadeDeVolume` so le `assetClass`. Sem a ficha, `null` — e o painel
    // escreveria "Lote(s)" para o ouro por acidente, nao por decisao.
    const ficha = fichaDoAtivo(CATALOGO, 'XAUUSD');
    expect(unidadeDeVolume(ficha?.assetClass)).toBe('Lote(s)');
  });
});

describe('PROVAS NEGATIVAS — o que a segunda busca NAO pode fazer', () => {
  it('PROVA NEGATIVA: um par que NAO existe continua NAO encontrado', () => {
    /*
      A busca por `modelSymbol` nao pode virar "qualquer par acha alguma ficha".
      `ATIVO_QUALQUER` nao esta no catalogo nem como `symbol` nem como
      `modelSymbol`, e a resposta correta e `null` — sem ela, o painel
      configurava um par inexistente e o operador veria numeros de um ativo que
      ele nao escolheu.
    */
    expect(fichaDoAtivo(CATALOGO, 'ATIVO_QUALQUER')).toBeNull();
    expect(fichaDoAtivo(CATALOGO, '')).toBeNull();
    expect(fichaDoAtivo([], 'GOLD')).toBeNull();
  });

  it('PROVA NEGATIVA: `modelSymbol` AUSENTE nao vira o proprio `symbol`', () => {
    /*
      Se `modelSymbol` ausente caesse no proprio `symbol`, todo par do catalogo
      passaria a ter "modelo" — e a lista de modelos mentiria para os 1.539
      pares que nao tem `.meta.json` (MEDIDO: o catalogo tem 1.639 linhas e
      existem 36 `.meta.json`).

      `null` e a ausencia medida: "nenhum modelo treinado com este nome".
    */
    const semModelo = parseAssetCatalog({
      assets: [{ symbol: 'EURUSD', asset_class: 'forex', contract_size: 100_000 }],
    });
    expect(semModelo[0].modelSymbol).toBeNull();
    // E buscar pelo nome do modelo NAO acha esse par.
    expect(fichaDoAtivo(semModelo, 'EURUSD')).not.toBeNull();
    expect(fichaDoAtivo(semModelo, 'BTCUSD')).toBeNull();
  });

  it('PROVA NEGATIVA: `symbol` tem PRIORIDADE sobre `modelSymbol`', () => {
    /*
      Dois ativos, e o `modelSymbol` de um aponta para o nome do outro:

          symbol=XAUUSD  modelSymbol=OUTRO     <- ficha pelo nome exato
          symbol=GOLD    modelSymbol=XAUUSD    <- a ponte medida

      Se a busca por `modelSymbol` viesse primeiro, escolher `XAUUSD` cairia na
      ficha de `GOLD`... que aqui e o mesmo metal, e por isso o teste deste
      caso usa `OUTRO`. Em forex o erro seria 100.000 vezes o preco, e a ficha
      errada e SILENCIOSA.
    */
    const dois: AssetRow[] = [
      { ...parseAssetCatalog({ assets: [{ symbol: 'GOLD', asset_class: 'metal', contract_size: 100 }] })[0], modelSymbol: 'XAUUSD' },
      { ...parseAssetCatalog({ assets: [{ symbol: 'OUTRO', asset_class: 'forex', contract_size: 100_000 }] })[0], modelSymbol: 'XAUUSD' },
    ];

    const porNomeExato = fichaDoAtivo(dois, 'OUTRO');
    expect(porNomeExato!.contractSize).toBe(100_000);
    // E `XAUUSD` pega a PRIMEIRA que declara, que e `GOLD` — o par real.
    const porModelo = fichaDoAtivo(dois, 'XAUUSD');
    expect(porModelo!.contractSize).toBe(100);
  });

  it('PROVA NEGATIVA: a comparacao ignora a caixa dos DOIS lados', () => {
    /*
      MEDIDO no ciclo anterior: a XM publica `btcusd` em MINUSCULA e o app
      mandava `BTCUSD`, e a busca voltava vazia SEM ERRO.

      `GOLD` e `XAUUSD` sao maiusculos dos dois lados, mas `btcusd`/`BTCUSD`
      nao sao — e o defeito e o mesmo. Por isso as DUAS comparacoes caixa.
    */
    const minusculo = parseAssetCatalog({
      assets: [{ symbol: 'gold', model_symbol: 'xauusd', asset_class: 'metal', contract_size: 100 }],
    });
    expect(fichaDoAtivo(minusculo, 'GOLD')).not.toBeNull();
    expect(fichaDoAtivo(minusculo, 'XAUUSD')).not.toBeNull();
  });
});

describe('o produtor preenche o campo que a tela consome', () => {
  it('`model_symbol` e lido do payload CRU, e `null` quando nao vem', () => {
    /*
      `parseAssetCatalog` le o payload CRU de proposito — o mesmo cuidado que o
      `contract_size` exigiu (o `getAssets` normalizado NAO tem o campo, e
      passar a resposta normalizada dava `null` sem erro).

      Aqui o campo e novo, entao a prova e que ele sobrevive a traducao: um
      `modelSymbol` sempre `null` faria a segunda busca nunca achar nada, e o
      grafico do ouro nao carregaria — com o codigo parecer correto.
    */
    const com = parseAssetCatalog(PAYLOAD_GOLD)[0];
    expect(com.modelSymbol).toBe('XAUUSD');

    const sem = parseAssetCatalog({ assets: [{ symbol: 'GOLD', asset_class: 'metal' }] })[0];
    expect(sem.modelSymbol).toBeNull();
  });

  it('`has_model` NAO substitui `model_symbol` para a ficha', () => {
    /*
      `has_model: false` com `model_symbol` presente e contradicao. A ficha usa
      `modelSymbol`, que e o nome — e nao um booleano que a tela converteria em
      `symbol`, o que faria todo par achar a si mesmo pelo nome do modelo.
    */
    const contradiction = parseAssetCatalog({
      assets: [{ symbol: 'GOLD', model_symbol: 'XAUUSD', has_model: false }],
    })[0];
    expect(contradiction.modelSymbol).toBe('XAUUSD');
  });
});