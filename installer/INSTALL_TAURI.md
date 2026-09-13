# Instalação
## Requisitos
- Windows 10/11 x64
- WebView2 (pré-instalado no Win10/11 atualizados)

## Instalador NSIS (recomendado)
- Instalação por usuário (não exige admin)
- `XAU AI PRO_0.1.0_x64-setup.exe`

## Instalador MSI (corporativo)
- Instalação por máquina (exige admin)
- `XAU AI PRO_0.1.0_x64_en-US.msi`

## Pós-instalação
O instalador entrega:
- `XAU AI PRO.exe` — shell Tauri com React embutido
- `core\xau-ai-pro-core.exe` — motor Rust (WS 9002 / HTTP 9003)

O Core é iniciado automaticamente pelo shell Tauri (thread no `setup`).
Log de bootstrap: `%LOCALAPPDATA%\XAU_AI_PRO\logs\core_bootstrap.log`

## Desinstalação
- NSIS: `uninstall.exe` na pasta de instalação
- MSI: "Adicionar ou Remover Programas"
