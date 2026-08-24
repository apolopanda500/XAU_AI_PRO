# Atualizacao de DSN Sentry - XAU AI Pro

## Data: 2026-08-09

## Alteracao Realizada

### DSN Anterior
```
https://c58d3855cb3d89ff2da34aaefc68106a@o4511837787586560.ingest.de.sentry.io/4511882908074064
```

### Novo DSN
```
https://05227ee0f8ff71eb959444ff355ad5f4@o4511837787586560.ingest.de.sentry.io/4511883313545296
```

## Comparacao

| Item | Anterior | Novo |
|------|----------|------|
| Project ID | 4511882908074064 | 4511883313545296 |
| API Key | c58d3855cb3d89ff2da34aaefc68106a | 05227ee0f8ff71eb959444ff355ad5f4 |
| send_default_pii | True | True |

## Arquivos Atualizados

- `.env` - DSN atualizado
- Todos os arquivos de configuracao agora usam o novo DSN

## Teste Realizado

- [x] DSN carregado do .env
- [x] Sentry inicializado
- [x] Evento enviado com sucesso
- [x] Sistema funcionando

## Dashboard

https://henrique-7n.sentry.io/issues/views/28799/

## Aviso de Seguranca

O parametro send_default_pii=True esta configurado.

Isso envia dados pessoais como:
- Enderecos IP
- Headers HTTP
- User-Agent
- Outros dados PII

Para producao, considere alterar para False a menos que necessario.

## Proximos Passos

1. Verifique o dashboard do novo projeto
2. Configure alertas no Sentry
3. Teste em producao

**Atualizacao concluida com sucesso!**
