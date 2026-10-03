# XAU AI PRO — Estado do projeto e pendências

**Última atualização:** 2026-09-27
**Branch:** `develop` · **Commits:** `c5dad9e`, `592a301`
**Objetivo:** trading desk para operadores avançados, com dados reais, robô automático
assistindo ao operador manual, e modelos treinados com dados atuais.

---

## 1. O QUE ESTÁ PRONTO E VERIFICADO

| Componente | Estado |
|---|---|
| Python | **588 passed** |
| Frontend | **159 passed**, tsc 0 |
| Core Rust | **38 passed**, `cargo fmt` limpo |
| Backend hospedado (Nitro/Vercel) | lint e build ok |
| Instalador | NSIS 147,6 MB · MSI 209,2 MB |
| Instalação | `%LOCALAPPDATA%\Programs\XAU AI PRO` — 5136 arquivos, 528 MB |

**Conta conectada:** login 111194406 · MetaQuotes-Demo · US$ 150,87 · XAUUSD 4.291,11/4.291,51

---

## 2. BUGS REAIS ENCONTRADOS E CORRIGIDOS

Estes não eram polished: cada um derrubava uma aba inteira.

### Dados
| Bug | Efeito |
|---|---|
| `_universal_history` usava `mt5` sem definir | `NameError` em **toda** chamada — Histórico morto |
| Risco usava pico de patrimônio de sessão antiga (24/09, saldo 1000) | drawdown fantasma de **84,9%** bloqueando toda ordem |
| Candles do MT5 serializavam `numpy.int64` | `object of type int64 is not json serializable` |
| `_ai_predict_sync` passava a resposta inteira ao `DataFrame` | `All arrays must be of the same length` |
| Inferência usava coluna `time`, features esperavam `Time` | `None of ['Time'] are in the columns` — **previsão real quebrada** |
| `resample` sem `DatetimeIndex` | `Only valid with DatetimeIndex` |
| `intento` `mercado` com pipe duplo `suporte\|\|tendencia` | alternativa vazia capturava **toda** pergunta do copiloto |
| `copilot_data.py` sem `import os` | 8 respostas do copiloto quebravam |
| `mt5-gateway.spec` sem modelos | `models: []` — "Nenhum modelo carregável" no app instalado |

### Segurança
| Bug | Correção |
|---|---|
| Gateway **fail-open** (`if API_TOKEN:`) | **fail-closed**: sem token, recusa tudo |
| Token errado devolvia **500** com traceback | 401 limpo |
| `remote_auth.authenticate` estourava `sqlite3.OperationalError` | falha de armazenamento vira 401 |
| `/api/chat` na Vercel era proxy **aberto** para `AI_GATEWAY_API_KEY` paga | exige `CHAT_API_KEY`, falha fechado com 503 |
| Calendário chamava **LLM externo** na Vercel | usa copiloto local |

### Estabilidade
| Bug | Impacto |
|---|---|
| **Aba Sistema abria `powershell.exe` a cada 2s** | 30 processos/min — **o app MORREU** (filhos órfãos, todas as abas "gateway indisponível") |
| `tauri.conf.json` gravado com **BOM** | build do Tauri falhava: `unable to parse JSON` |
| `RobotAssetTable` offered Bybit/OKX que retornavam `corretora não suportada` | opção quebrada na UI — liberadas no backend |

---

## 3. ARQUITETURA DE SEGURANÇA (estado atual)

```
Vercel (xau-ai-pro-api)     rotas: /, /api, /api/_diag, /api/chat, /api/health, /api/workflows/*
                            SEM rota de ordem, posição, saldo ou saque
                            → NÃO alcança o broker

Gateway local (127.0.0.1:9001)
                            token por sessão do Tauri
                            fail-closed
                            XAU_ENABLE_DEMO_ORDERS=1
                            XAU_ENABLE_REAL_ORDERS=0
                            XAU_MCP_TRADING=0
                            → único caminho que alcança o MT5

MQL5/Experts               INTOCÁVEL (AGENTS.md)
```

**Nenhum segredo rastreado no git.** `.env*` e `.vercel` ignorados.

---

## 4. ABAS (12 → 6)

```
Patrimônio · Robô · Histórico · Calendário · Sistema · Configuração
```

**Robô** na ordem de uso: Modelo → Operação automática → Execução → Risco →
Guardian · EA → Copiloto → **Mini Terminal (no fim, é conferência)**

---

## 5. PENDÊNCIAS — o que falta

### Bloqueadores para o que você pediu

| # | Pendência | Estado |
|---|---|---|
| 1 | **SL/TP e aumento de posição por linha** | Backend tem `modify-position`, `partial-close`, `breakeven`. **UI só expõe Fechar** |
| 2 | **Treinar modelos novos com dados de hoje** | Só H1 existe e é de treino antigo. H4/M15/M5 reprovados |
| 3 | **2 modelos por tipo de ativo** | Existe 1 (XAUUSD H1). Falta a variedade |
| 4 | **Endurance test no MT5** | Nunca executado. Nenhuma ordem real de teste rodada |
| 5 | **Modo mercado real** | Ver seção 6 |
| 6 | **Conectar mais corretoras** | Bybit/OKX/MEXC precisam de credencial configurada |
| 7 | **Revalidar abas após o crash** | Sistema, Histórico, Calendário e Robô precisam de teste seu |

### Antes de confiar no robô automático
- [ ] Forward test em demo por no mínimo uma semana
- [ ] Teste de rejeição: ordem bloqueada quando limite estourar
- [ ] Verificar kill switch derruba e retoma
- [ ] Auditar os 42 achados do EA (4 críticos: retry inoperante, ATR/RSI trocados, staleness inoperante, AutoTrade não bloqueia)

---

## 6. MODO MERCADO REAL — o que é preciso

Você pediu "autorizar gateway, modo mercado real 10/10". Isto é o que existe:

**Hoje:** `XAU_ENABLE_REAL_ORDERS=0`. Toda ordem vai para conta **de teste**.

**Para conta real, três coisas diferentes:**
1. `XAU_ENABLE_REAL_ORDERS=1` no `main.rs`
2. Credencial de corretora **real** (hoje é MetaQuotes-Demo)
3. Etapa explícita e separada de validação — o AGENTS.md exige isso

**O que continua existindo, ligado ou desligado:**
- O gate de conta (`trade_mode`) **não é removível** — é o que impede conta real de receber ordem por engano
- `confirm_demo: true` no payload — exigência do gateway
- O kill switch
- A tela de Risco com os limites do `risk_gate`

**Minha recomendação honesta:** rodar endurance em **demo** primeiro, porque é onde você descobre problema sem custo. A diferença entre demo e real, para o robô, é só o dinheiro — a lógica é idêntica. Se o robô erra em demo, ele erra em real.

---

## 7. FORMATOS DE ARQUIVO — o que a pesquisa mostrou

Você mencionou BIN, DAT, PAK, SET, TPL, CHR, WND, INI, WELCOME, HCC. Verifiquei contra a documentação do MetaTrader 5:

| Formato | É de quê | Serve para nós? |
|---|---|---|
| `.chr` | **MT5** — descrição de gráfico em `MQL5/Profiles/Charts` | **Já usamos** — anexar EA ao gráfico |
| `.wnd` | **MT5** — ordem de janelas (`order.wnd`) | Não ainda. Controla o layout de janelas do terminal |
| `.tpl` | **MT5** — template de gráfico (`MQL5/Profiles/Templates`) | **Sim, útil** — salvar/recuperar layouts de gráfico com o EA anexado |
| `.set` | **MT5** — parâmetros do EA no Strategy Tester (`Profiles/Tester`) | **Sim, útil** —这里是 o input do EA no backtest |
| `.ini` | **MT5** — configuração do terminal | Parcial. Já existe config do app, mas não do terminal |
| `.hcc` | **MT5** — bars de 1 minuto por ano, formato **intermediário** | **Não usar.** A doc é explícita: "não sont destined à leitura direta" |
| `.dat` | **MT5** — `ticks.dat`, ticks por símbolo | Só leitura. Nenhum ganho: usamos a API ao vivo |
| `WELCOME` | **MT5** — página de boas-vindas | Não |
| `.bin` / `.pak` | **Motores de jogo** (Unreal, Source/Valve) | **Não tem relação com trading.** Nãomisturar |

**Conclusão:** os formatos úteis (`.chr`, `.tpl`, `.set`) são todos do próprio MT5 e o projeto **já usa `.chr`**. `.tpl` e `.set` seriam os próximos de maior retorno: salvar o gráfico com o EA e os parâmetros, e recuperar depois. `.hcc` e `.dat` são isca — a documentação do próprio MT5 diz que `.hcc` não é para leitura direta.

**O que outros apps de trading fazem de fato:** engines próprios, não formatos. O ganho real aqui é mais sobre **estado**: o robô precisa persistir decisão, razão, limite e resultado de cada ciclo — e isso é melhor num banco (SQLite) do que em arquivo binário. Já temos `strategy.db`.

---

## 8. COMO CONTINUAR

```powershell
# Python
.\.venv\Scripts\python.exe -m pytest -q tests

# Frontend
cd frontend
npx tsc --noEmit
npm test
npm run tauri build

# Gateway (OBRIGATÓRIO após mexer em Python)
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean mt5-gateway.spec
Remove-Item frontend\src-tauri\bridge -Recurse -Force
Copy-Item dist\mt5-gateway frontend\src-tauri\bridge -Recurse -Force
```

**Regra que já custou tempo:** se você mudar Python e rodar só `tauri build`, o
app instalado roda o código antigo. O `mt5-gateway.exe` é compilado à parte.

**Nunca:** escrever em `MQL5/Experts`. Exceção única e já autorizada: anexar EA
em `MQL5/Profiles/Charts/*.chr`, com `XAU_ALLOW_CHART_WRITE=1` e terminal fechado.

---

## 9. O QUE NÃO FUNCIONA (e é limitação de ambiente, não do código)

| Item | Motivo |
|---|---|
| **API pública da Binance** | `api.binance.com` não resolve nesta rede (restrição regional). MEXC, Bybit e OKX funcionam |
| Mercado fechado | Domingos e feriados. MT5 responde `10018 Market closed` |
| Compra/fechar de ponta a ponta | Precisa de mercado aberto para validar |

---

## 10. NOTA SOBRE MCP

O MCP `xau-trading` está ligado e é útil — mas **recebe 401** do gateway local,
porque o token é gerado por sessão do Tauri e o MCP roda fora dele. **Isso é o
comportamento correto** (fail-closed). Para o MCP operar, seria preciso um
escopo próprio, e isso é decisão de arquitetura, não coisa para fazer no
meio.
