# XAU_AI_PRO — Publicar no Streamlit in Snowflake (SiS)

Pacote de deploy para rodar o painel no **Snowflake** (conta `grhcwrg`, database
`USER$`, schema `PUBLIC`, worksheet `DEFAULT$`).

## O que foi adaptado

| Recurso | Versão local | Versão Snowflake |
|---|---|---|
| Métricas (dataset/predições/feedback/retreino) | Arquivos locais + SQLite | Tabelas `USER$.PUBLIC.XAU_AI_PRO_*` (criadas no setup.sql); mostram 0 se não existirem |
| Chat IA | LiteLLM em `localhost:4000` | Snowflake Cortex (`snowflake-arctic`) — se disponível na conta; aviso amigável caso contrário |
| Acesso ao disco / MetaTrader 5 | Sim | **Não** (indisponível no SiS) |

## Arquivos

```
snowflake_deploy/
├── app.py            # painel adaptado para o SiS (main_file)
├── environment.yml   # dependências Python (channel snowflake + conda-forge)
├── setup.sql         # cria stage, tabelas e o app Streamlit
└── README_SNOWFLAKE.md
```

## Passo a passo

1. **Instale o snowsql** (CLI do Snowflake):
   <https://docs.snowflake.com/en/user-guide/snowsql-install-config>
   E configure as credenciais:
   ```
   snowsql -a grhcwrg.qc73957 -u SEU_USUARIO
   ```
   (O usará o padrão `USER$` como database se você estiver no contexto.)

2. **Configure o warehouse** no `setup.sql` — substitua `TU_WAREHOUSE` pelo nome
   real (ex.: `COMPUTE_WH`, `XAU_WH`).

3. **Execute o setup** no worksheet Snowsight (ou snowsql), em ordem:
   ```sql
   -- cria stage
   CREATE OR REPLACE STAGE xau_ai_pro_stage;
   -- cria tabelas
   CREATE OR REPLACE TABLE USER$.PUBLIC.XAU_AI_PRO_DATASET (...);  -- conforme setup.sql
   ...
   ```

4. **Suba os arquivos** para o stage (via snowsql):
   ```sql
   PUT file://C:/Users/Micro/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/XAU_AI_PRO/snowflake_deploy/app.py @xau_ai_pro_stage;
   PUT file://C:/Users/Micro/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/XAU_AI_PRO/snowflake_deploy/environment.yml @xau_ai_pro_stage;
   ```

5. **Crie o app Streamlit**:
   ```sql
   CREATE STREAMLIT xau_ai_pro_dashboard
       ROOT_LOCATION = '@xau_ai_pro_stage'
       MAIN_FILE = 'app.py'
       QUERY_WAREHOUSE = 'TU_WAREHOUSE';
   ```

6. **Abra**: em Snowsight → **Apps** → **Streamlit** → `xau_ai_pro_dashboard`.

## Dicas

- Verifique se o **Streamlit in Snowflake** está habilitado na sua conta/região
  (recurso geralmente disponível; em contas enterprise/startup pode precisar de
  enrollment em *Apps*). Se o `CREATE STREAMLIT` falhar com *operation not
  supported*, ative o recurso ou use o Community Cloud (GitHub).
- Para o **chat Cortex**, sua conta precisa de acesso ao modelo `snowflake-arctic`
  (região com Cortex habilitado).
- Para popular as tabelas: ou insira dados manualmente no worksheet, ou faça um
  job/script que leia `MQL5/Files/Data/*` do seu projeto local e rode
  `INSERT INTO USER$.PUBLIC.XAU_AI_PRO_* ... SELECT ...`.

## Alternativa (sem Snowflake): Streamlit Community Cloud

Se preferir o Cloud público gratuito (sem Cortex), suba o repositório para o
GitHub e use o botão Deploy — o app usará arquivos locais do repo, não tabelas.
Nesse caso, use o `Python/dashboard/app.py` original (precisa só de um
`requirements.txt` com streamlit/pandas/openai) em vez do `snowflake_deploy/app.py`.