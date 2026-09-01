; XAU_AI_PRO - Instalador oficial (Inno Setup 6)
; Compilacao: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; (ou use installer\build_installer.cmd para o build completo automatizado)
;
; Conteudo instalado (enxuto - SEM modelos treinados / backups / pycache):
;   - XAU_AI_PRO.exe        (CLI launcher one-file enxuto: numpy/pandas/sklearn/joblib/sentry/uvicorn)
;   - Python\               (modulos .py do projeto carregados do disco; SEM models\ e __pycache__)
;   - MQL5\                 (fonte EA + include + scripts de integracao)
;   - EA  XAU_AI_PRO.ex5    (copiado para {app}\EA)
;   - assets\               (icone/recursos)
;   - XAU_AI_PRO.cmd        (wrapper que define XAU_AI_PRO_ROOT e roda o EXE)
;
; Nota: modelos treinados (Python\models, ~2.3 GB) NAO sao embarcados.
;       Execute "XAU_AI_PRO.exe train" apos instalar para gerar os modelos.
;
; Compressao: lzma2/ultra64 em EXE de ~170 MB tornava o build ~7h.
;             lzma2/normal reduz para poucos minutos com custo minimo
;             de tamanho (o EXE ja vem compactado pelo PyInstaller/UPX).

#define MyAppName "XAU AI PRO"
#define MyAppVersion "1.3.2"
#define MyAppPublisher "XAU AI PRO"
#define MyAppExeName "XAU_AI_PRO.exe"
#define MyRoot "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO"

[Setup]
AppId={{8A1F2E34-9C57-4E6B-9A2D-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=XAU_AI_PRO_Setup
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
SetupIconFile={#MyRoot}\app\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Metadata do Setup.exe (aba Detalhes no Explorer / UAC)
VersionInfoVersion={#MyAppVersion}.0
VersionInfoDescription=XAU AI PRO - Instalador
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 XAU AI PRO
VersionInfoCompany={#MyAppPublisher}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Limpa bytecode/__pycache__ antigos em upgrades (evita .pyc obsoletos)
Type: files; Name: "{app}\Python\*.pyc"
Type: files; Name: "{app}\Python\*\*.pyc"
Type: filesandordirs; Name: "{app}\Python\__pycache__"
Type: filesandordirs; Name: "{app}\Python\*\__pycache__"

[Files]
; EXE principal (CLI launcher one-file)
Source: "{#MyRoot}\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Modulos do projeto (o launcher importa do disco) - apenas .py, sem models/pycache
Source: "{#MyRoot}\Python\*.py"; DestDir: "{app}\Python"; Flags: ignoreversion; Excludes: "test_*.py"
Source: "{#MyRoot}\Python\ai\*.py"; DestDir: "{app}\Python\ai"; Flags: ignoreversion
Source: "{#MyRoot}\Python\data\*.py"; DestDir: "{app}\Python\data"; Flags: ignoreversion
Source: "{#MyRoot}\Python\risk\*.py"; DestDir: "{app}\Python\risk"; Flags: ignoreversion
Source: "{#MyRoot}\Python\decision\*.py"; DestDir: "{app}\Python\decision"; Flags: ignoreversion
Source: "{#MyRoot}\Python\entry\*.py"; DestDir: "{app}\Python\entry"; Flags: ignoreversion
Source: "{#MyRoot}\Python\backtest\*.py"; DestDir: "{app}\Python\backtest"; Flags: ignoreversion
Source: "{#MyRoot}\Python\core\*.py"; DestDir: "{app}\Python\core"; Flags: ignoreversion
; Painel web (Streamlit) e backend local - obrigatorios p/ comando dashboard
Source: "{#MyRoot}\Python\dashboard\*.py"; DestDir: "{app}\Python\dashboard"; Flags: ignoreversion
Source: "{#MyRoot}\Python\dashboard\.streamlit\config.toml"; DestDir: "{app}\Python\dashboard\.streamlit"; Flags: ignoreversion
Source: "{#MyRoot}\Python\backend\*.py"; DestDir: "{app}\Python\backend"; Flags: ignoreversion
; INTERFACE NATIVA (Tkinter) - app/ desktop (Trading Desk com abas)
Source: "{#MyRoot}\app\*.py"; DestDir: "{app}\app"; Flags: ignoreversion
Source: "{#MyRoot}\app\components\*.py"; DestDir: "{app}\app\components"; Flags: ignoreversion
Source: "{#MyRoot}\app\tabs\*.py"; DestDir: "{app}\app\tabs"; Flags: ignoreversion
Source: "{#MyRoot}\app\theme\*.py"; DestDir: "{app}\app\theme"; Flags: ignoreversion
Source: "{#MyRoot}\app\utils\*.py"; DestDir: "{app}\app\utils"; Flags: ignoreversion
Source: "{#MyRoot}\app\data\config.json"; DestDir: "{app}\app\data"; Flags: ignoreversion
; Integracao com a plataforma MQL5 (somente fonte/EA/include/scripts, sem lixo de runtime)
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\*.mq5"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\*.ex5"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Include\*"; DestDir: "{app}\MQL5\Include"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyRoot}\MQL5\Scripts\*.ex5"; DestDir: "{app}\MQL5\Scripts"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Scripts\*.mq5"; DestDir: "{app}\MQL5\Scripts"; Flags: ignoreversion
; EA compilado (copiado tambem para {app}\EA)
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.ex5"; DestDir: "{app}\EA"; Flags: ignoreversion
; Assets/icone
Source: "{#MyRoot}\app\assets\*.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
; Wrapper que define XAU_AI_PRO_ROOT (Start In = {app})
Source: "XAU_AI_PRO.cmd"; DestDir: "{app}"; Flags: ignoreversion
; Docs
Source: "{#MyRoot}\CHANGELOG.md"; DestDir: "{app}\Docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\XAU_AI_PRO.cmd"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\XAU_AI_PRO.cmd"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\XAU_AI_PRO.cmd"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent