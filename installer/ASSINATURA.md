# Assinatura do Instalador (XAU_AI_PRO)

## Status atual

| Artefato | Tamanho | Assinatura |
|---|---|---|
| `dist\XAU_AI_PRO.exe` | ~174 MB | ✅ Assinado (Authenticode SHA-256 + timestamp) |
| `installer\XAU_AI_PRO_Setup.exe` | ~173 MB | ✅ Assinado (Authenticode SHA-256 + timestamp) |

Assinatura aplicada com `signtool` (Windows SDK 10.0.26100.0 x64), certificado
`CN=trust_1f236627-5690-4a3e-a0ac-883af776b255` (autoassinado, do store
`CurrentUser\My`), hash SHA-256 e carimbo de tempo DigiCert (RFC3161).

> ⚠️ Tamanhos atualizados em 31/08/2026 — os valores antigos (~91/92 MB) eram
> de um build anterior menor. O EXE atual embute numpy/pandas/sklearn/scipy +
> streamlit/altair/openai/uvicorn (necessário para o dashboard funcionar no
> EXE) e por isso pesa ~174 MB.

## Importante: limitação de confiança

O certificado usado é **autoassinado (self-signed)**. Consequências:

- A assinatura é criptograficamente válida e prova a integridade do arquivo
  (o hash não é adulterável).
- Porém o Windows **não confia** na cadeia em máquinas novas: o SmartScreen /
  UAC exibirá **"Editor desconhecido"** até que a raiz seja instalada como
  confiável ou o binário seja assinado por uma CA comercial.
- A raiz do certificado foi exportada para
  `installer\cert\XAU_AI_PRO_Dev_Root.cer` — ela pode ser instalada em máquinas
  internas (Trusted Root) para reconhecer a assinatura, mas **não** para
  distribuição pública.

## Para distribuição pública (recomendado)

Adquira um certificado de **Code Signing** de uma CA comercial e assine com:

```bat
sign.cmd "C:\certs\meu-cert.pfx" "senha"
```

Opções de CA:
- **Azure Trusted Signing** (moderno, sem hardware token, evita SmartScreen após reputação)
- **DigiCert / Sectigo / SSL.com** (tradicional, requer token USB/HSM na maioria)
- Certificados **OV/EV** eliminam/amenizam o aviso do SmartScreen após reputação

Depois de assinar com a CA, o Status (`Get-AuthenticodeSignature`) passa a ser
`Valid` nas máquinas com a raiz da CA (pré-instalada no Windows para CAs
públicas confiáveis).

## Como assinar / re-assinar

```bat
rem usar melhor certificado do store:
installer\sign.cmd
rem usar certificado real:
installer\sign.cmd "C:\certs\meu-cert.pfx" "minha-senha"
```

O script também roda a verificação (`signtool verify /pa`).

## Build completo automatizado

Use `installer\build_installer.cmd` para gerar EXE + Instalador + assinatura
em um único passo:

```bat
installer\build_installer.cmd            rem sem assinatura
installer\build_installer.cmd SIGN       rem usa melhor certificado do store
installer\build_installer.cmd "C:\certs\meu-cert.pfx" "senha"
```

## Layout do instalador

```
XAU_AI_PRO_Setup.exe
├── XAU_AI_PRO.exe          (CLI one-file ~174 MB: numpy/pandas/sklearn/scipy/sentry/streamlit/uvicorn)
├── Python\*.py             (módulos carregados do disco; SEM models/~2,3 GB e __pycache__)
├── MQL5\Experts|Include|Scripts  (fonte EA + integração)
├── EA\XAU_AI_PRO.ex5
├── assets\ (ícone)
├── XAU_AI_PRO.cmd          (wrapper: define XAU_AI_PRO_ROOT)
└── Docs\CHANGELOG.md
```

> **Nota:** modelos treinados não são embarcados no instalador (2,3 GB).
> Após instalar, rode `XAU_AI_PRO.exe train` para gerar os modelos.

## Correções aplicadas (31/08/2026)

1. **Dashboard quebrava no EXE** (`uvicorn is not installed`): o Streamlit faz
   import lazy de uvicorn via `importlib.util.find_spec()`, invisível à análise
   estática do PyInstaller. `launcher.spec` agora embute `uvicorn` (+ submodulos).
2. **`server.port does not work when global.developmentMode is true`**: no
   bundle onefile o `__file__` não contém `site-packages`, então o Streamlit
   assume `developmentMode=true` por padrão. O launcher agora define
   `STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false` (+ port/address/headless via env).
3. **Build do instalador ~7 h**: `Compression=lzma2/ultra64` trocada por
   `lzma2/normal` (minutos, custo mínimo de tamanho — o EXE já vem compactado
   pelo PyInstaller/UPX).
4. `installer.iss` ganhou metadata de versão (aba Detalhes) e limpeza de
   `__pycache__/*.pyc` em upgrades.