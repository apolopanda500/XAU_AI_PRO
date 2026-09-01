; ============================================================
; XAU_AI_PRO - Instalador profissional (Inno Setup 6)
; ------------------------------------------------------------
; Instala DENTRO da pasta de dados do MetaTrader 5:
;   {userappdata}\MetaQuotes\Terminal\{ID_DO_TERMINAL}\MQL5\Files\XAU_AI_PRO
;
; O ID do terminal e DETECTADO DINAMICAMENTE no [Code] (varre APPDATA),
; pois cada instalacao do MT5 gera um ID de 32 caracteres diferente.
;
; Modelos de IA (Python/models, ~2,3 GB) NAO sao embutidos:
; o app baixa sob demanda na 1a execucao (botao "Baixar modelos"
; na aba de Treinamento) ou via URL configurada em XAU_AI_PRO_MODELS_URL.
;
; Compilacao: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; ============================================================
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
; O diretorio default (pasta de dados do MT5) e resolvido em tempo real
; no InitializeSetup. Aqui usamos apenas um placeholder seguro.
DefaultDirName={userappdata}\MetaQuotes\Terminal\_XAU_AI_PRO_PLACEHOLDER
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=XAU_AI_PRO_Setup
; Compressao normal: lzma2/ultra64 no EXE de ~175MB levaria ~7h de build.
; lzma2/normal leva poucos minutos (o EXE ja vem compactado pelo PyInstaller/UPX).
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Nao exige admin: instala em APPDATA (sem UAC), como o MT5 padrao.
PrivilegesRequired=lowest
SetupIconFile={#MyRoot}\app\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Metadata do Setup.exe (aba Detalhes / UAC)
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
Name: "autostart"; Description: "Iniciar o XAU AI PRO automaticamente ao ligar o Windows"; GroupDescription: "Inicializacao:"; Flags: unchecked

[InstallDelete]
; Limpa bytecode/__pycache__ antigos em upgrades (evita .pyc obsoletos)
Type: files; Name: "{app}\Python\*.pyc"
Type: files; Name: "{app}\Python\*\*.pyc"
Type: filesandordirs; Name: "{app}\Python\__pycache__"
Type: filesandordirs; Name: "{app}\Python\*\__pycache__"
Type: filesandordirs; Name: "{app}\app\__pycache__"
Type: filesandordirs; Name: "{app}\app\*\__pycache__"

[Files]
; ============================================================
; 1) EXE principal (CLI launcher one-file)
; ============================================================
Source: "{#MyRoot}\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; ============================================================
; 2) Codigo Python (modulos carregados do disco). Excluimos
;    models/, __pycache__/ e testes; incluimos todos os .py,
;    dashboard, backend e o model_manager (download sob demanda).
; ============================================================
Source: "{#MyRoot}\Python\*.py"; DestDir: "{app}\Python"; Flags: ignoreversion; Excludes: "test_*.py,*__pycache__*,models,*\.pkl,*.joblib"
Source: "{#MyRoot}\Python\ai\*.py"; DestDir: "{app}\Python\ai"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\data\*.py"; DestDir: "{app}\Python\data"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\risk\*.py"; DestDir: "{app}\Python\risk"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\decision\*.py"; DestDir: "{app}\Python\decision"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\entry\*.py"; DestDir: "{app}\Python\entry"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\backtest\*.py"; DestDir: "{app}\Python\backtest"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\core\*.py"; DestDir: "{app}\Python\core"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\dashboard\*.py"; DestDir: "{app}\Python\dashboard"; Flags: ignoreversion; Excludes: "*__pycache__*"
Source: "{#MyRoot}\Python\dashboard\.streamlit\*"; DestDir: "{app}\Python\dashboard\.streamlit"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyRoot}\Python\backend\*.py"; DestDir: "{app}\Python\backend"; Flags: ignoreversion; Excludes: "*__pycache__*"
; ============================================================
; 3) Interface nativa (Tkinter) - app/ desktop
; ============================================================
Source: "{#MyRoot}\app\*.py"; DestDir: "{app}\app"; Flags: ignoreversion; Excludes: "*__pycache__*,*.pyc"
Source: "{#MyRoot}\app\components\*.py"; DestDir: "{app}\app\components"; Flags: ignoreversion; Excludes: "*__pycache__*,*.pyc"
Source: "{#MyRoot}\app\tabs\*.py"; DestDir: "{app}\app\tabs"; Flags: ignoreversion; Excludes: "*__pycache__*,*.pyc"
Source: "{#MyRoot}\app\theme\*.py"; DestDir: "{app}\app\theme"; Flags: ignoreversion; Excludes: "*__pycache__*,*.pyc"
Source: "{#MyRoot}\app\utils\*.py"; DestDir: "{app}\app\utils"; Flags: ignoreversion; Excludes: "*__pycache__*,*.pyc"
Source: "{#MyRoot}\app\data\config.json"; DestDir: "{app}\app\data"; Flags: ignoreversion

; ============================================================
; 4) EA MQL5 + includes + presets (estrutura COMPLETA do EA)
;    copiada de Experts\XAU_AI_PRO (raiz atual de producao).
; ============================================================
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\*.mq5"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\*.ex5"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\*.mqproj"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\AI\*.mqh"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\AI"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Core\*.mqh"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Core"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Enterprise\*.mqh"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Enterprise"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Filters\*.mqh"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Filters"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Indicators\*.mqh"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Indicators"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Management\*.mqh"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Management"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Monitoring\*.mqh"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Monitoring"; Flags: ignoreversion

; ============================================================
; 5) Include compartilhado (KCI) e Scripts de integracao
; ============================================================
Source: "{#MyRoot}\MQL5\Include\KCI\*.mqh"; DestDir: "{app}\MQL5\Include\KCI"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyRoot}\MQL5\Scripts\*.ex5"; DestDir: "{app}\MQL5\Scripts"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Scripts\*.mq5"; DestDir: "{app}\MQL5\Scripts"; Flags: ignoreversion

; ============================================================
; 6) Presets de configuracao (.set) do EA
; ============================================================
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Release\v1.2.0\Config\XAU_AI_PRO.AUTOTRADE_ON.set"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Release\v1.2.0\Config"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Release\v1.2.0\Config\XAU_AI_PRO.PRO.set"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Release\v1.2.0\Config"; Flags: ignoreversion
Source: "{#MyRoot}\MQL5\Experts\XAU_AI_PRO\Release\v1.2.0\Config\XAU_AI_PRO.QUALITY.set"; DestDir: "{app}\MQL5\Experts\XAU_AI_PRO\Release\v1.2.0\Config"; Flags: ignoreversion

; ============================================================
; 7) Assets / icone / docs
; ============================================================
Source: "{#MyRoot}\app\assets\*.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "{#MyRoot}\CHANGELOG.md"; DestDir: "{app}\Docs"; Flags: ignoreversion
Source: "{#MyRoot}\README.md"; DestDir: "{app}\Docs"; Flags: ignoreversion

; ============================================================
; 8) Wrapper que define XAU_AI_PRO_ROOT (Start In = {app})
; ============================================================
Source: "XAU_AI_PRO.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\XAU_AI_PRO.cmd"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\XAU_AI_PRO.cmd"; IconFilename: "{app}\assets\icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\XAU_AI_PRO.cmd"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\XAU_AI_PRO.cmd"; Description: "Iniciar XAU AI PRO automaticamente"; Flags: nowait postinstall skipifsilent; Tasks: autostart

[Code]
// ============================================================
// DETECCAO DINAMICA DO DIRETORIO DE DADOS DO MetaTrader 5
// ============================================================
// O ID do terminal tem 32 caracteres e fica em:
//   {userappdata}\MetaQuotes\Terminal\{ID}\MQL5\Files
// Cada instalacao do MT5 gera um ID diferente. Este codigo localiza o
// diretorio que contem uma pasta MQL5\Files (assinatura do terminal real).

const
  MT5Marker = 'MQL5\Files';

var
  DetectedMT5: String;

function FindTerminalDataPath(): String;
var
  base, sub, probe: String;
  rec: TFindRec;
begin
  Result := '';
  base := ExpandConstant('{userappdata}\MetaQuotes\Terminal');
  if not DirExists(base) then Exit;
  if FindFirst(base + '\*', rec) then
  begin
    try
      repeat
        if (rec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
        begin
          sub := rec.Name;
          probe := base + '\' + sub + '\' + MT5Marker;
          if DirExists(probe) then
          begin
            Result := base + '\' + sub;
            Exit;
          end;
        end;
      until not FindNext(rec);
    finally
      FindClose(rec);
    end;
  end;
end;

procedure InitializeWizard;
begin
  DetectedMT5 := FindTerminalDataPath();
  if DetectedMT5 <> '' then
    WizardForm.DirEdit.Text := DetectedMT5 + '\MQL5\Files\XAU_AI_PRO';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if DetectedMT5 = '' then
      MsgBox('Nao foi possivel localizar uma instalacao do MetaTrader 5.' + #13#10 +
             'O XAU AI PRO foi instalado em {app}.' + #13#10 +
             'Abra o MetaTrader 5 e carregue o EA manualmente, se aplicavel.',
             mbInformation, MB_OK);
  end;
end;