# Benchmark de plataformas de trading — 2026

Data da coleta: **2026-09-25**
Autor: sessão de manutenção XAU AI PRO
Estado do produto medido: `develop` @ `777fc12`, working tree com 107 arquivos alterados ainda **não commitados**.

## Limitações deste documento — ler antes de usar

1. Isto **não é benchmark de performance**. Nenhuma latência, throughput ou vazão foi medida. Não há número de ticks/segundo, tempo de ordem ou consumo de memória comparado.
2. A coluna do XAU AI PRO vem de **inspeção do código e execução da suíte de testes** neste ambiente. As colunas dos concorrentes vêm de **páginas oficiais e fontes secundárias**, não de instalação local.
3. As features do XAU AI PRO marcadas como existentes são as que **existem em código**. Features que dependem de MT5 real, conta de corretora ou capital **não foram exercitadas** e estão marcadas como `código, não validado`.
4. Nenhuma comparação de interface foi feita por screenshot.
5. Preços dos concorrentes são os publicados nas fontes citadas e **mudam com frequência**.

## Fontes

| Fonte | URL | Data da fonte |
| --- | --- | --- |
| TradingView — features | `tradingview.com/features` | consultada 2026-09-25 |
| TradingView — Pine Script v6 | `tradingview.com/pine-script-docs/welcome/` | v6, consultada 2026-09-25 |
| TradingView — Google Play | `play.google.com/store/apps/details?id=com.tradingview.tradingviewapp` | atualizado 03/08/2026 |
| NinjaTrader 8 — help | `ninjatrader.com/support/helpGuides/nt8` | consultada 2026-09-25 |
| NinjaTrader vs Sierra vs Tradovate | `proptradingvibes.com/blog/ninjatrader-vs-sierra-vs-tradovate` | atualizado 20/07/2026 |
| Sierra Chart — features | `sierrachart.com/index.php?page=doc/Features.php` | consultada 2026-09-25 |
| Sierra Chart — backtesting | `sierrachart.com/index.php?page=doc/Backtesting.php` | consultada 2026-09-25 |
| Sierra Chart vs Bookmap | `sierrachart.com/blogs/news/bookmap-vs-sierra-chart` | 18/08/2026 |
| Sierra Chart vs NinjaTrader | `rizetrade.com/brokers/sierra-chart-vs-ninjatrader` | 03/08/2026 |
| QuantConnect review | `quantt.co.uk/resources/quantconnect-review` | 10/06/2026 |
| Backtesting platforms | `quantt.co.uk/resources/backtesting-platforms-comparison` | 08/06/2026 |

## Perfil das plataformas de referência

### TradingView
Plataforma cloud e social. Linguagem **Pine Script v6**, executada nos servidores da TradingView. Mais de **150.000 Community Scripts** publicados, metade open source. **100+ corretoras** com integração direta. Paper trading com simulação de corretora. Apps desktop e mobile nativos. Credenciais de corretora ficam no navegador, nunca nos servidores deles. Preço por assinatura (planos Pro/Max).

### NinjaTrader 8
Desktop Windows. **NinjaScript (C#)** para estratégia, indicador e backtest. Backtesting multi-ano em **dados tick de futuros** dentro da mesma plataforma. ATM module para OCO brackets, breakeven e trailing stop. Sem app mobile nativo. Licença vitalícia em torno de **US$ 1.099–1.499** (fonte de junho/2026). Order flow via add-ons pagos. A própria documentação do NinjaTrader avisa que resultado real e backtest **divergem** em certos tipos de barra.

### Sierra Chart
Desktop Windows apenas. **ACSIL (C++)** — curva de aprendizado íngreme. Packages de **US$ 26 a US$ 56/mês**; Denali feed a partir de ~US$ 11/mês. Numbers Bars é uma implementação completa de footprint (bid/ask split, delta, imbalance, diagonal ratios). Market Depth Historical Graph e, no package MBO, market by order. Backtesting em modo bar-based e **replay** automático e manual. Recomendam no mínimo 6 núcleos.

### QuantConnect / Lean
Motor **C#** com wrapper Python. Engine **Lean** é open source e auto-hospedável. Dados incluídos mesmo no free tier: equities US desde 1998, options desde 2010, futuros CME desde 2009, Forex desde 2010, crypto (Coinbase, Binance, Bitfinex). Integrações de live: **Interactive Brokers, Tradier, OANDA, Bitfinex, Coinbase, Binance**. Live e backtest usam os mesmos code paths. **Não** é otimizado para baixa latência. Free tier: 2 algos em research, 1 em paper, 4 GB RAM.

## Matriz de features

Legenda de status: `OK` = existe e foi exercitado neste ambiente · `código` = existe em código, não exercitado · `ausente` = não existe.

| Capacidade | XAU AI PRO | TradingView | NinjaTrader 8 | Sierra Chart | QuantConnect/Lean |
| --- | --- | --- | --- | --- | --- |
| Corretoras conectadas | **5** (MT5, Binance, Bybit, MEXC, OKX) — `OK` | 100+ | OK (via NinjaTrader Brokerage + vários) | OK | 6+ diretas |
| Classes de ativo | forex, cripto, índices — `código` | ações, cripto, forex, índices, futuros, opções, commodities | futuros, forex, ações | futuros, forex, opções | ações, futuros, opções, forex, cripto |
| Execução em demo/paper | `OK` | `OK` | `OK` | `OK` | `OK` |
| Execução real liberada | **não, travada por design** | `OK` | `OK` | `OK` | `OK` |
| Linguagem de estratégia | Python + Rust | Pine Script v6 | NinjaScript (C#) | ACSIL (C++) | C# e Python |
| Ecossistema de scripts públicos | **ausente** | 150.000+ | marketplace próprio | ACSIL compartilhado | Algorithms Library |
| Backtest com dados históricos reais | `código` (paper-only; bloqueado por falha de candles MT5 no último registro) | `OK` | `OK` tick de futuros | `OK` bar e replay | `OK` decades |
| Walk-forward | `OK` (`core` tem teste) | `ausente` nativo | `ausente` nativo | `ausente` nativo | `OK` |
| Footprint / order flow | **ausente** | `ausente` | add-on pago | `OK` Numbers Bars | `ausente` |
| Profundidade de mercado (DOM/book) | `OK` (`OrderBookPanel`, `/depth`) | `OK` | `OK` | `OK` MBO | `ausente` |
| Alertas | `OK` (econômico 6h, 1x por evento) | `OK` 13 condições | `OK` | `OK` | `OK` |
| Backoffice de risco e gate | **`OK` e diferencial** — `risk_gate`, kill switch, `intent_log`, `reconciliation` | `ausente` | `ausente` | `ausente` | parcial |
| Trilha de auditoria | `OK` `audit_log.py` | `ausente` | `ausente` | `ausente` | `ausente` |
| Idempotência e reconciliação | `OK` `intent_log`, `reconciliation`, fila persistente | `ausente` | `ausente` | `ausente` | parcial |
| App desktop Windows | `OK` Tauri, assinado, instalador MSI e NSIS | `OK` | `OK` | `OK` | `ausente` (cloud) |
| App mobile nativo | APK `aarch64` **gerado e assinado, não testado em aparelho** | `OK` app completo | **ausente** | **ausente** | `ausente` |
| Rede social / comunidade | `ausente` | `OK` (~100M usuários, rede social) | `ausente` | `ausente` | Alpha Stream |
| Deploy em cloud | `ausente` | `OK` | `OK` | `OK` | `OK` |
| Open source | `ausente` (repo privado) | não (Pine é proprietário, Lean é open) | não | não | **parcial** (Lean open) |
| Preço | ainda não definido | assinatura | ~US$ 1.099–1.499 vitalícia | US$ 26–56/mês | US$ 20–1.000+/mês para live |

## Evidência do XAU AI PRO (verificada neste ambiente)

| Métrica | Valor | Como foi verificado |
| --- | --- | --- |
| Testes Python | **267 passed** | `pytest -q tests`, 2026-09-25 |
| Testes frontend | **35 passed** em 5 arquivos | `vitest run` |
| Testes Rust (core) | **38 passed** | `cargo test --locked` |
| Testes Rust (Tauri) | 0 casos | `cargo test --locked` — crate sem testes unitários |
| Rotas do gateway | **105** | parsing de `@app.get/post` em `backend/fastapi_gateway.py` |
| Módulos backend | 29 arquivos `.py` | listagem de `backend/` |
| Adaptadores de corretora | 5 clientes + 5 de execução | `*_client.py` e `*_execution.py` |
| Componentes frontend | 97 arquivos `.tsx` | listagem de `frontend/src/components` |
| Pylint | **10.00/10** em 11 arquivos | `pylint`, 2026-09-25 |
| TypeScript | sem erros | `tsc --noEmit` |
| Artefatos Windows | 7, todos assinados e `found no threats` | ver manifesto `release/1.2.3/release-manifest.json` |

## Leitura honesta

**Onde o XAU AI PRO é mais forte:** não é gráfico, não é backtest, não é comunidade. É a camada de **governança de execução** — risk gate com fail-closed, kill switch, log de intenções idempotente, reconciliação, trilha de auditoria e trava explícita de dinheiro real. Nenhuma das quatro plataformas de referência trata isso como produto; elas tratam como responsabilidade do usuário. Para uso metal/XAU com múltiplas corretoras e exigência de auditoria, isso é um nicho real.

**Onde o XAU AI PRO está muito atrás:** catálogo de dados, ecossistema de scripting, order flow, experiência de uso e maturidade mobile. Comparado a TradingView, NinjaTrader ou Sierra Chart em qualquer eixo de charting ou backtest, o produto **não está na mesma categoria** e não deve ser apresentado como se estivesse.

**Conclusão:** a alegação de "Mercado 10/10" **não se sustenta** e não deve ser usada. O posicionamento defensável é: "terminal de execução com governança de risco para metal e múltiplas corretoras, com paper/demo e dinheiro real travado por design". Qualquer comparação de mercado precisa qualificar qual eixo.

## O que falta para um benchmark de verdade

1. Ambiente limpo e isolado para instalar cada concorrente e medir a mesma tarefa.
2. Métrica definida: latência p50/p95 de leitura de quote, de envio de ordem e de fill.
3. Volume de dados: número de barras e ticks disponíveis para backtest.
4. Repetibilidade: mesmo script de teste nos quatro produtos, com captura de tela e log.
5. Até que isso seja feito, este documento é **comparação de escopo declarada**, não benchmark medido.
