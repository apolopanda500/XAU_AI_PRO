# Assinatura do Instalador (XAU_AI_PRO)

## Registro historico (nao comprova o build atual)

| Artefato | Tamanho | Assinatura |
|---|---|---|
| Build anterior de `XAU_AI_PRO.exe` | ~174 MB | Assinado com certificado de desenvolvimento; nao equivale a confianca publica |
| Build anterior de `XAU_AI_PRO_Setup.exe` | ~173 MB | Assinado com certificado de desenvolvimento; nao equivale a confianca publica |

Assinatura aplicada com `signtool` (Windows SDK 10.0.26100.0 x64), certificado
`CN=trust_1f236627-5690-4a3e-a0ac-883af776b255` (autoassinado, do store
`CurrentUser\My`), hash SHA-256 e carimbo de tempo DigiCert (RFC3161).

> Os tamanhos acima sao historicos (31/08/2026). O spec atual usa onedir,
> e seus arquivos e tamanhos devem ser medidos novamente apos o build.

## Importante: limitação de confiança

O certificado usado é **autoassinado (self-signed)**. Consequências:

- A assinatura permite verificar integridade e origem alegada quando o
  certificado e a cadeia sao confiaveis; publique o SHA-256 separadamente.
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
- **Azure Trusted Signing** (servico de assinatura; nao dispensa reputacao nem scans)
- **DigiCert / Sectigo / SSL.com** (tradicional, requer token USB/HSM na maioria)
- Certificados **OV/EV** nao garantem ausencia de avisos do SmartScreen nem de deteccoes do Defender.
- Verifique assinatura e hashes no artefato exato que sera distribuido.

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

Use `installer\build_installer.cmd` para gerar EXE + instalador e, opcionalmente, assinatura
em um único passo:

```bat
installer\build_installer.cmd            rem sem assinatura
installer\build_installer.cmd SIGN       rem usa melhor certificado do store
installer\build_installer.cmd "C:\certs\meu-cert.pfx" "senha"
```

## Layout do instalador

```
XAU_AI_PRO_Setup_<versao>.exe
├── XAU_AI_PRO.exe + _internal/ (bundle onedir: conferir conteudo do build)
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
   pelo PyInstaller, sem UPX no spec atual).
4. `installer.iss` ganhou metadata de versão (aba Detalhes) e limpeza de
   `__pycache__/*.pyc` em upgrades.