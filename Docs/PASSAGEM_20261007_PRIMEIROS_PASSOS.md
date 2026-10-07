# PASSAGEM — 07/10/2026, fechamento para o próximo agente

> **Este é o PRIMEIRO arquivo a ler.** Ele aponta para os outros.
> **Sem data e sem hora de propósito: as regras valem para sempre, os números
> não. Se um número divergir do que o comando medir, o comando vence.**

## 1. ESTADO EM UMA FRASE

O gráfico, o histórico e o ouro foram **corrigidos e validados no código**,
mas **não estão no app instalado** — falta um build. Nada está commitado por
falta; tudo está commitado.

## 2. OS NÚMEROS, MEDIDOS

| | medido em |
|---|---|
| `pytest` | **1271 verdes** |
| `vitest` | **731 verdes**, 51 arquivos |
| `tsc --noEmit` | **limpo** |
| `git status` | **0 pendentes** |
| `preflight` | 2 avisos (disco 6,2 GB · flag de execução), **nenhuma falha** |
| commits desta sessão | `48754ed` `96a684e` `c578f10` `ed2c125` `c352d14` `dc484d7` |

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests -p no:cacheprovider   # 1271
cd frontend
npx tsc --noEmit
npx vitest run                                                      # 731
```

## 3. O PRIMEIRO TRABALHO: BUILD

**O app instalado é o de antes de quatro correções.** Testar agora mostra o
gráfico vazio e o campo SL espremido. `build_app.bat` leva ~8 min.

```powershell
Stop-Process -Id (Get-Process -Name "XAU AI PRO","xau-ai-pro-core" -ErrorAction SilentlyContinue).Id -Force
cmd /c "scripts\build_app.bat"
# desinstalar: "C:\Users\Micro\AppData\Local\XAU AI PRO\uninstall.exe" /S
# instalar:    Temp\cargo-target\release\bundle\nsis\XAU AI PRO_1.2.4_x64-setup.exe /S
# rodar:       "$env:USERPROFILE\Desktop\XAU AI PRO.lnk"
```

**NÃO** rodar `scripts\limpeza_segura.ps1 -BuildArtifacts` antes de instalar: ele
apaga `Temp\cargo-target`, onde está o instalador.

## 4. O QUE FOI CORRIGIDO — E O QUE VERIFICAR NA TELA

| correção | como confirmar na tela |
|---|---|
| **Gráfico carrega** com o motor desligado | escolher `BTCUSD` e ver candles, sem `Identidade de mercado inválida` |
| **O ouro abre pelo nome `GOLD`** | escolher `GOLD` no seletor de par e ver candles |
| **SL e TP lado a lado** | os dois campos com largura de caixa, rótulo em uma linha |
| **Requisito de margem** | `Requisito de margem 0.85 USD` + nocional + `alavancagem 1000:1` |
| **Pontas arrastáveis** | linha de tendência com 2 círculos; arrastar move a linha |
| **Paleta, espessura, trava** | clicar na linha → paleta aparece; `🔒` esconde as pontas |
| **`Ctrl + Z`** | desfaz criação **e** arraste |
| **Histórico não trava mais** | trocar o filtro durante o carregamento e ver o filtro novo |
| **Histórico diz quando o MT5 está fechado** | fechar o terminal e ver "Sem leitura: o MetaTrader 5 está sem sessão" |

## 5. OS DOCUMENTOS, E O QUE CADA UM RESPONDE

| documento | responde |
|---|---|
| **`Docs/PASSAGEM_20261007_FIM_DE_CONEXAO.md`** | o estado desta sessão, item a item |
| `Docs/PASSAGEM_20261006_RECUPERACAO.md` | a corrupção de arquivos e a recuperação |
| `Docs/PASSAGEM_GRAFICO_XM_20261006.md` | o ciclo anterior, com as capturas da XM |
| `Docs/ORDEM_PELO_GRAFICO_20261006.md` | o painel de ordem, os 4 passos |
| **`AGENTS.md` §14** | **arquivo zerado**: como descobrir e onde procurar a cópia boa |
| `AGENTS.md` §4 | a ordem dos gates antes de conta real |

## 6. O QUE ESTÁ ABERTO

### 6.1 A conta real opera com o app DESLIGADO

**Este é o item mais sério em aberto, e não é do app.**

MEDIDO: 8 posições na conta 391773676, com o app em `AUTO NÃO` /
`Motor desligado` / `EA off`. É o EA do MT5, que roda fora do app.

| | |
|---|---|
| perdas | −1,41 · −1,53 · −1,45 · −1,55 — **todas `[sl ...]`, todas ~1,50** |
| resultado | **+0,62** em 8 posições |
| stop | ~200 pontos = **0,23%** do preço |
| alavancagem | **1000:1** |

Com $3,94 de saldo livre, **três stops com a mesma configuração comem 15% da
conta.**

### 6.2 Os dois testes do AGENTS.md §4 já rodaram — em código de SETEMBRO

| teste | resultado | binário |
|---|---|---|
| forward | 4 operações, Lucro −0,74 | **23/09** |
| endurance | **923 operações · PF 0,48 · Sharpe −9,31 · Lucro −334,01** | **23/09** |

Log do Strategy Tester: `GOLD,M5`, 4h26min33s, 15.020.685 ticks.
`.ex5` medido: `Experts\estadoA_8445b74\XAU_AI_PRO\XAU_AI_PRO.ex5` (23/09),
**fora do repositório**. O do repositório é de 07/10 01:08.

**53,20% de acerto com PF 0,48** é a assinatura de stop curto com alvo longo — o
perfil `SL=80 · TP=160` é 1:2.

**Nenhum dos dois mediu o binário de hoje.** Para um backtest que valha
alguma coisa: recompilar do fonte atual no MetaEditor (§7) e rodar `GOLD,M5`.

O log também acusa `[NOTIFY] SendNotification falhou | Erro=4014` e
`Sent=0 | Failed=14394` — **14.394 notificações falhadas.**

### 6.3 Nada mais

A reconciliação do saldo **fecha** (`soma dos 19 deals = +9,56 = balance +
credit`). Indicadores com busca (`rsi` → 3 resultados) é o que falta da XM.

## 7. ARMADILHAS DESTA SESSÃO — CADA UMA CUSTOU UM CICLO

**Arquivo zerado com o MESMO tamanho do original.** `git diff` diz
`Bin 19157 -> 19157 bytes` — parece "arquivo binário". Leia os **bytes**:
zero no primeiro bloco é arquivo destruído. `git checkout` do `HEAD` teria
perdido 24 h de trabalho, porque o `HEAD` era a versão antiga. A cópia boa
estava no **`.map` do `dist`**. Ver `AGENTS.md` §14.

**`git status` com `bad signature 0x00000000`** é o **índice** zerado, não o
repositório: `git read-tree HEAD`. O `refs/stash` zerado **não tem
reconstrução**.

**`?raw` em CSS devolve string VAZIA no vitest.** MEDIDO: `len: 0`. O vitest
troca o módulo de CSS por um stub antes do `?raw` resolver. Um
`expect(length).toBeGreaterThan(0)` teria **passado sem verificar nada** — o
AGENTS.md §6 do avesso. A forma que funciona é `node:fs` por `await import`.

**`minmax(0, …)` num grid colapsa em silêncio.** O grid serve primeiro as
colunas `auto`, que têm conteúdo intrínseco; a de mínimo zero é a única que
colapsa. Foi assim que `Stop Loss` ficou com 10 px.

**Comparar uma soma antiga com um saldo novo.** A conta operava enquanto eu
media. Para conta ativa, a conferência é o **`equity`**. Eu relatei "faltam $5,11
sem deal" com três hipóteses e nenhuma era a resposta.

**Trava textual que proíbe documentar.** O teste *"o código não tem nome de
ativo"* varria o arquivo e reprovou no texto que documenta a medição. É o
AGENTS.md §4e — **o defeito era o teste.**

**Default não é medida.** `escopoAtivo()` devolve `mt5:forex` sem chave
gravada. Usá-lo como mercado de consulta é a presunção que o §3 proíbe.

## 8. REGRAS QUE NÃO SE DESCARTAM

- **Nenhum saque, transferência, resgate ou movimentação para fora da
  corretora.** Trava: `tests/test_movimentacoes.py::TestNadaDeDinheiroForaDaCorretora`.
- **Toda escrita exige `confirm=true` e `request_id` idempotente.** O clique
  arma; só o botão envia.
- **Nenhum símbolo nem corretora pode ser presumido.** A classe vem da
  hierarquia da corretora (`asset_class`), nunca de palavra no nome.
- **Medir antes de dizer que está consertado.** Aconteceu **duas vezes** nesta
  sessão: "o histórico está consertado" e "o gráfico tem as pontas" — ambos
  verdade no código, falsos no binário instalado.
- **Nunca `xfail` onde existe compilador e código.**
- **Um controle que nada lê é pior que a ausência dele.**
- **Não declarar "pronto" sem os números.**

## 9. O COMO DE LER UM `Docs/` DESTE PROJETO

Os documentos mais antigos têm **data no nome** e são de ciclos passados. Para
saber o que é verdade agora:

1. **O `command` vence o número.** Se divergir, o comando está certo.
2. **O documento mais recente manda.** `PASSAGEM_20261007_*` é o estado de
   hoje; `PASSAGEM_GRAFICO_XM_20261006.md` descreve o build anterior.
3. **Item marcado "ABERTO" em um doc antigo pode estar fechado em um novo.**
   Foi assim com a reconciliação do saldo.

**Não declarar nada "pronto" sem rodar o comando e trazer o número.**

## 10. ESTADO DO GIT — MEDIDO

Os **7 commits desta sessão estão nos dois remotos**, com o mesmo SHA:

```
gitlab  097567b   https://gitlab.com/apolopanda500/XAU_AI_PRO.git
github  097567b   https://github.com/apolopanda500/XAU_AI_PRO.git
local   097567b   develop
working tree       0 pendentes
```

```
097567b  docs: o indice para o proximo agente, e a conversa da sessao
dc484d7  ouro: o nome da corretora e o nome do modelo agora se encontram
c352d14  docs: a conta fecha, e o erro foi meu de metodo
ed2c125  grafico e ticket: o que o app instalado mostrou e o CSS que mentia
c578f10  docs: o instalador novo medido, e o motor que perdeu 2,94 na conta
96a684e  margem: o requisito que o painel recusou por engano
48754ed  grafico: as pontas, a paleta, a trava e o Ctrl+Z; historico
540b5b4  (base) robo: tres blocos, sem previsao
```

### 10.1 ARQUIVOS CORROMPIDOS — backup em disco

**Em `C:\Users\Micro\Desktop\XAU_AI_PRO_BACKUP_20261007\`:**

| arquivo | o que é |
|---|---|
| `index_corrompido_105608_bytes.zip` | o `.git/index` **inteiro de `0x00`** |
| `stash_ref_quebrado_41_bytes.txt` | o `refs/stash` com 41 espaços |
| `PriceChart_recuperado_do_sourcemap_71968.tsx` | a versão **boa**, do `.map` |
| `PriceChart_checkpoint_cline_54403.tsx` | a outra cópia boa, do checkpoint |
| `build_app_20261006.log` | o log do build de 06/10 |

**O stash não foi recuperado** — 41 bytes de espaço num arquivo que deveria ter
40 hex + quebra. Está documentado, não escondido.