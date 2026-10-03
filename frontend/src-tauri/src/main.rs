#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::fs;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Mutex, OnceLock};
use std::time::Duration;
use std::time::Instant;

use serde::Serialize;
use tauri::path::BaseDirectory;
use tauri::Manager;

static OWNED_CHILDREN: OnceLock<Mutex<Vec<Child>>> = OnceLock::new();
static GATEWAY_TOKEN: OnceLock<String> = OnceLock::new();

const EXPECTED_GATEWAY_BUILD: &str = "xau-ai-pro-1.2.4-universal-20260928";

fn gateway_token() -> Result<String, String> {
    if let Some(token) = GATEWAY_TOKEN.get() {
        return Ok(token.clone());
    }
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|err| format!("falha ao gerar token da sessao: {}", err))?;
    let token = bytes
        .iter()
        .map(|byte| format!("{:02x}", byte))
        .collect::<String>();
    let _ = GATEWAY_TOKEN.set(token.clone());
    Ok(token)
}

#[tauri::command]
fn gateway_token_command() -> Result<String, String> {
    gateway_token()
}

fn register_child(child: Child) {
    OWNED_CHILDREN
        .get_or_init(|| Mutex::new(Vec::new()))
        .lock()
        .unwrap()
        .push(child);
}

fn shutdown_children() {
    if let Some(children) = OWNED_CHILDREN.get() {
        if let Ok(mut children) = children.lock() {
            for child in children.iter_mut() {
                let _ = child.kill();
            }
            children.clear();
            log_core("processos filhos encerrados com a UI");
        }
    }
}

#[tauri::command]
fn exit_app() {
    shutdown_children();
    std::process::exit(0);
}

#[cfg(target_os = "windows")]
fn acquire_single_instance() -> bool {
    use std::os::windows::ffi::OsStrExt;
    use std::ptr::null_mut;

    extern "system" {
        fn CreateMutexW(attributes: *mut (), initial_owner: i32, name: *const u16) -> *mut ();
        fn GetLastError() -> u32;
    }

    let name: Vec<u16> = std::ffi::OsStr::new("Local\\XAU_AI_PRO_SINGLE_INSTANCE")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    let handle = unsafe { CreateMutexW(null_mut(), 0, name.as_ptr()) };
    if handle.is_null() {
        // Se o Windows bloquear o mutex, nao impedir a inicializacao da UI.
        return true;
    }
    // ERROR_ALREADY_EXISTS: outra instância já detém o mutex.
    unsafe { GetLastError() != 183 }
}

#[cfg(not(target_os = "windows"))]
fn acquire_single_instance() -> bool {
    true
}

fn log_core(msg: &str) {
    if let Some(base) = std::env::var("LOCALAPPDATA").ok().map(PathBuf::from) {
        let dir = base.join("XAU_AI_PRO").join("logs");
        if std::fs::create_dir_all(&dir).is_ok() {
            use std::io::Write;
            if let Ok(mut f) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(dir.join("core_bootstrap.log"))
            {
                let _ = writeln!(f, "{}", msg);
            }
        }
    }
}

#[cfg(target_os = "windows")]
fn ocultar_console(command: &mut Command) {
    use std::os::windows::process::CommandExt;
    command.creation_flags(0x08000000);
}

#[cfg(not(target_os = "windows"))]
fn ocultar_console(_command: &mut Command) {}

/// Diretorio canonico de dados do usuario: %APPDATA%\XAU_AI_PRO (Roaming).
fn dados_dir() -> Result<PathBuf, String> {
    let base = dirs::config_dir().ok_or_else(|| "APPDATA indisponivel".to_string())?;
    Ok(base.join("XAU_AI_PRO"))
}

/// Garante que o diretorio de dados e o config.json canonico existam.
/// Nao migra nem le o legado %LOCALAPPDATA%\XAU_AI_PRO (continha segredos em texto puro).
#[tauri::command]
fn ensure_config() -> Result<String, String> {
    let dir = dados_dir()?;
    fs::create_dir_all(&dir).map_err(|e| format!("falha ao criar diretorio de dados: {}", e))?;
    let arquivo = dir.join("config.json");
    if !arquivo.exists() {
        let vazio = "{}";
        fs::write(&arquivo, vazio).map_err(|e| format!("falha ao criar config.json: {}", e))?;
    }
    Ok(arquivo.to_string_lossy().into_owned())
}

#[derive(Serialize)]
pub struct AppDirs {
    pub data_dir: String,
    pub config_path: String,
    pub auth_path: String,
    pub log_dir: String,
}

#[derive(Serialize, Clone)]
pub struct HardwareTelemetry {
    pub os: String,
    pub architecture: String,
    pub cpu_name: Option<String>,
    pub cpu_cores: u32,
    pub cpu_usage_percent: Option<f64>,
    pub memory_total_gb: Option<f64>,
    pub memory_available_gb: Option<f64>,
    pub disk_total_gb: Option<f64>,
    pub disk_free_gb: Option<f64>,
    pub cpu_temperature_c: Option<f64>,
    pub gpu_name: Option<String>,
    pub gpu_available: bool,
    pub source: String,
}

/// Cache da telemetria.
///
/// POR QUE ISTO EXISTE
/// ===================
/// A leitura do Windows abre um `powershell.exe` e roda cinco consultas CIM.
/// A interface polled a cada 2 s: eram 30 processos por minuto, e o app
/// MORREU — os filhos ficavam orfaos e todas as abas passaram a responder
/// "gateway indisponivel".
///
/// WMI so muda na escala de segundos, entao repetir a leitura varias vezes
/// por segundo nao produz dado mais fresco: produz carga. O cache garante no
/// maximo UMA leitura a cada `TELEMETRY_TTL`, e o comando responde na hora
/// com o ultimo valor.
static TELEMETRY_CACHE: Mutex<Option<(Instant, HardwareTelemetry)>> = Mutex::new(None);

const TELEMETRY_TTL: Duration = Duration::from_secs(8);

fn hardware_telemetry_cached() -> HardwareTelemetry {
    if let Ok(guard) = TELEMETRY_CACHE.lock() {
        if let Some((quando, dados)) = guard.as_ref() {
            if quando.elapsed() < TELEMETRY_TTL {
                return dados.clone();
            }
        }
    }
    let dados = hardware_telemetry_collect();
    if let Ok(mut guard) = TELEMETRY_CACHE.lock() {
        *guard = Some((Instant::now(), dados.clone()));
    }
    dados
}

/// Coleta apenas telemetria local. Nao executa ordens, saques ou alteracoes no MT5.
///
/// Sincrono de proposito. A versao anterior usava
/// `tauri::async_runtime::spawn_blocking`, e o PANICAVA quando o app ainda
/// estava subindo: o processo morria logo depois de "tauri setup executado",
/// deixando tela branca e os filhos orfaos.
///
/// O custo de abertura do powershell ja esta resolvido pelo CACHE de 8s e
/// pelo pre-aquecimento no boot. Aqui o comando so devolve o cache.
#[tauri::command]
fn hardware_telemetry() -> HardwareTelemetry {
    hardware_telemetry_cached()
}

fn hardware_telemetry_collect() -> HardwareTelemetry {
    #[cfg(target_os = "windows")]
    {
        let script = r#"$os=Get-CimInstance Win32_OperatingSystem; $cpu=Get-CimInstance Win32_Processor | Select-Object -First 1; $gpu=Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Where-Object {$_.Name} | Select-Object -First 1; $tz=Get-CimInstance MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -First 1; $disk=Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" | Select-Object -First 1; $load=Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average; [pscustomobject]@{os=$os.Caption; arch=$os.OSArchitecture; cpu_name=$cpu.Name; cores=$cpu.NumberOfLogicalProcessors; usage=if($load.Average -ne $null){[math]::Round($load.Average,1)}else{$null}; mem_total=if($os.TotalVisibleMemorySize){[math]::Round($os.TotalVisibleMemorySize/1MB,2)}else{$null}; mem_free=if($os.FreePhysicalMemory){[math]::Round($os.FreePhysicalMemory/1MB,2)}else{$null}; disk_total=if($disk.Size){[math]::Round($disk.Size/1GB,2)}else{$null}; disk_free=if($disk.FreeSpace){[math]::Round($disk.FreeSpace/1GB,2)}else{$null}; temp=if($tz){[math]::Round(($tz.CurrentTemperature/10)-273.15,1)}else{$null}; gpu=if($gpu){$gpu.Name}else{$null}} | ConvertTo-Json -Compress"#;
        let mut powershell = Command::new("powershell.exe");
        use std::os::windows::process::CommandExt;
        powershell.creation_flags(0x08000000);
        if let Ok(output) = powershell
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ])
            .output()
        {
            if let Ok(value) = serde_json::from_slice::<serde_json::Value>(&output.stdout) {
                let cpu = value.get("cpu").and_then(|v| v.as_f64());
                let gpu_name = value.get("gpu").and_then(|v| v.as_str()).map(str::to_owned);
                return HardwareTelemetry {
                    os: value
                        .get("os")
                        .and_then(|v| v.as_str())
                        .unwrap_or("Windows")
                        .to_string(),
                    architecture: value
                        .get("arch")
                        .and_then(|v| v.as_str())
                        .unwrap_or("desconhecida")
                        .to_string(),
                    cpu_name: value
                        .get("cpu_name")
                        .and_then(|v| v.as_str())
                        .map(str::to_owned),
                    cpu_cores: value.get("cores").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
                    cpu_usage_percent: value.get("usage").and_then(|v| v.as_f64()),
                    memory_total_gb: value.get("mem_total").and_then(|v| v.as_f64()),
                    memory_available_gb: value.get("mem_free").and_then(|v| v.as_f64()),
                    disk_total_gb: value.get("disk_total").and_then(|v| v.as_f64()),
                    disk_free_gb: value.get("disk_free").and_then(|v| v.as_f64()),
                    cpu_temperature_c: cpu,
                    gpu_available: gpu_name.is_some(),
                    gpu_name,
                    source: "Windows WMI".to_string(),
                };
            }
        }
        return HardwareTelemetry {
            os: "Windows".to_string(),
            architecture: "desconhecida".to_string(),
            cpu_name: None,
            cpu_cores: 0,
            cpu_usage_percent: None,
            memory_total_gb: None,
            memory_available_gb: None,
            disk_total_gb: None,
            disk_free_gb: None,
            cpu_temperature_c: None,
            gpu_name: None,
            gpu_available: false,
            source: "Windows WMI indisponivel".to_string(),
        };
    }
    #[cfg(not(target_os = "windows"))]
    HardwareTelemetry {
        os: "desconhecido".to_string(),
        architecture: "desconhecida".to_string(),
        cpu_name: None,
        cpu_cores: 0,
        cpu_usage_percent: None,
        memory_total_gb: None,
        memory_available_gb: None,
        disk_total_gb: None,
        disk_free_gb: None,
        cpu_temperature_c: None,
        gpu_name: None,
        gpu_available: false,
        source: "Telemetria nao suportada neste sistema".to_string(),
    }
}

#[tauri::command]
fn get_app_dirs() -> Result<AppDirs, String> {
    let dir = dados_dir()?;
    Ok(AppDirs {
        data_dir: dir.to_string_lossy().into_owned(),
        config_path: dir.join("config.json").to_string_lossy().into_owned(),
        auth_path: dir.join("auth.json").to_string_lossy().into_owned(),
        log_dir: dir.join("logs").to_string_lossy().into_owned(),
    })
}

/// Grava auth.json (hash PBKDF2 gerado no webview — o PIN em claro nunca chega ao Rust).
#[tauri::command]
fn save_auth(payload: serde_json::Value) -> Result<(), String> {
    let dir = dados_dir()?;
    fs::create_dir_all(&dir).map_err(|e| format!("falha ao criar diretorio de dados: {}", e))?;
    let arquivo = dir.join("auth.json");
    fs::write(
        &arquivo,
        serde_json::to_string(&payload).map_err(|e| e.to_string())?,
    )
    .map_err(|e| format!("falha ao gravar auth.json: {}", e))
}

/// Le auth.json; retorna None quando nao ha PIN cadastrado.
#[tauri::command]
fn load_auth() -> Result<Option<serde_json::Value>, String> {
    let arquivo = dados_dir()?.join("auth.json");
    if !arquivo.exists() {
        return Ok(None);
    }
    let conteudo =
        fs::read_to_string(&arquivo).map_err(|e| format!("falha ao ler auth.json: {}", e))?;
    let valor: serde_json::Value =
        serde_json::from_str(&conteudo).map_err(|e| format!("auth.json invalido: {}", e))?;
    Ok(Some(valor))
}

/// Remove auth.json (desativa o PIN).
#[tauri::command]
fn remove_auth() -> Result<(), String> {
    let arquivo = dados_dir()?.join("auth.json");
    if arquivo.exists() {
        fs::remove_file(&arquivo).map_err(|e| format!("falha ao remover auth.json: {}", e))?;
    }
    Ok(())
}

fn localizar_core(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let path = app
        .path()
        .resolve("core/xau-ai-pro-core.exe", BaseDirectory::Resource)
        .map_err(|err| format!("core nao encontrado nos resources: {}", err))?;
    if path.is_file() {
        Ok(path)
    } else {
        Err("core invalido nos resources".to_string())
    }
}

fn localizar_bridge(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let path = app
        .path()
        .resolve("bridge/mt5-gateway.exe", BaseDirectory::Resource)
        .map_err(|err| format!("bridge MT5 nao encontrado nos resources: {}", err))?;
    if path.is_file() {
        Ok(path)
    } else {
        Err("bridge MT5 invalido nos resources".to_string())
    }
}

fn request_json(port: u16, path: &str, token: &str) -> Result<serde_json::Value, String> {
    let address = format!("127.0.0.1:{}", port);
    let mut stream =
        TcpStream::connect_timeout(&address.parse().unwrap(), Duration::from_millis(300))
            .map_err(|err| err.to_string())?;
    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(300)));
    let request = format!(
        "GET {} HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nAuthorization: Bearer {}\r\nConnection: close\r\n\r\n",
        path, port, token
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|err| err.to_string())?;
    let mut response = String::new();
    stream
        .take(128 * 1024)
        .read_to_string(&mut response)
        .map_err(|err| err.to_string())?;
    if !response.starts_with("HTTP/1.1 200") && !response.starts_with("HTTP/1.0 200") {
        return Err("healthcheck sem HTTP 200".to_string());
    }
    let body = response
        .split_once("\r\n\r\n")
        .map(|(_, body)| body)
        .ok_or_else(|| "healthcheck sem corpo".to_string())?;
    serde_json::from_str(body).map_err(|err| err.to_string())
}

fn bridge_atual_ativo() -> bool {
    let Ok(token) = gateway_token() else {
        return false;
    };
    let Ok(payload) = request_json(9001, "/api/health", &token) else {
        return false;
    };
    payload.get("ok").and_then(serde_json::Value::as_bool) == Some(true)
        && payload.get("source").and_then(serde_json::Value::as_str) == Some("mt5_gateway")
        && payload
            .get("gateway_build")
            .and_then(serde_json::Value::as_str)
            == Some(EXPECTED_GATEWAY_BUILD)
}

fn core_atual_ativo() -> bool {
    let Ok(token) = gateway_token() else {
        return false;
    };
    let Ok(payload) = request_json(9003, "/health", &token) else {
        return false;
    };
    payload.get("ok").and_then(serde_json::Value::as_bool) == Some(true)
        && payload.get("service").and_then(serde_json::Value::as_str) == Some("xau-ai-pro-core")
        && payload
            .get("core_version")
            .and_then(serde_json::Value::as_str)
            == Some(env!("CARGO_PKG_VERSION"))
}

/// Le uma flag de execucao do AMBIENTE, com padrao fail-closed.
///
/// Ate 2026-09-29 o `.env("XAU_ENABLE_REAL_ORDERS", "1")` estava fixo em
/// codigo compilado: dinheiro real ligado dentro do binario, sem forma de o
/// operador desligar, e em conflito com o documento que dizia `0`. A decisao
/// passa a ser do ambiente e auditavel. Saque e transferencia nao entram aqui:
/// nenhuma flag os habilita, e o gateway mantem `withdrawals_enabled` e
/// `transfers` em `false`.
fn flag(nome: &str, padrao: &str) -> String {
    std::env::var(nome).unwrap_or_else(|_| padrao.to_string())
}

// ---------------------------------------------------------------- supervisao
//
// O QUE EXISTIA ANTES
// ==================
// O `setup()` subia bridge e core uma vez e nunca mais olhava para eles. O
// `log_core("core spawnado com sucesso")` era escrito no instante do
// `Command::spawn()`, que so prova que o Windows ACEITOU criar o processo — nao
// que ele continuou de pe. Na sessao de 29->30/2026 o `mt5-gateway` morreu
// duas vezes e o log seguiu afirmando sucesso ate o fim.
//
// O `spawn_core()` tambem guardava o `Child` em `OWNED_CHILDREN` e nunca
// chamava `try_wait()`: o handle ficava la para sempre, sem ninguem perguntar
// se o processo ainda existia. Nao havia forma de o app descobrir que perdera
// o proprio gateway.
//
// O QUE ESTA FAZ
// ===============
// Uma thread de supervisao que, a cada intervalo:
//   1. pergunta aos filhos se eles SAUDES (HTTP autenticado, nao so vivo);
//   2. recolhe (`try_wait`) os que ja morreram, para o log dizer a verdade;
//   3. reinicia o que caiu, com espera entre tentativas;
//   4. desiste apos varias falhas seguidas e DIZ que desistiu.
//
// Sem o passo 4, um binario que falha em loop cria centenas de processos por
// minuto e enche o disco — o mesmo tipo de dano que o ciclo de telemetria ja
// causou (ver o comentario de TELEMETRY_CACHE acima).
//
// DECISAO DE PRODUTO
// ==================
// O supervisor nao envia ordem, nao toca em saldo e nao escreve no MT5. Ele
// cuida so do processo local que serve as rotas. `XAU_ENABLE_REAL_ORDERS`
// continua lendo do ambiente com padrao `0`, e nenhuma flag habilita saque.

/// Intervalo entre checagens de saude dos filhos.
const INTERVALO_SUPERVISAO: Duration = Duration::from_secs(15);

/// Quantas falhas CONSECUTIVAS de um mesmo filho autorizam um reinicio.
///
/// Um por ciclo seria sensivel demais: uma checagem de 300 ms que esbarra num
/// pico de CPU ja contaria como queda. Tres falhas seguidas, com o intervalo de
/// 15 s, dao 45 s de evidencia continua antes de agir.
const FALHAS_ANTES_DE_REINICIAR: u32 = 3;

/// Quantas tentativas de reinicio o supervisor faz antes de parar.
///
/// Acima disso o problema NAO e do supervisor: e o binario que falha em loop,
/// ou uma dependencia ausente. Tentar mais so cria processo morto em disco.
const TENTATIVAS_MAXIMAS: u32 = 5;

/// O que o supervisor faz com um filho neste ciclo.
#[derive(Debug, PartialEq, Eq)]
enum Decisao {
    /// Respondeu: nada a fazer.
    Saudavel,
    /// Falhou, mas ainda nao ha evidencia suficiente para agir.
    Aguardar,
    /// Falhou o suficiente: reiniciar.
    Reiniciar,
    /// Falhou demais: parar de tentar e avisar o operador.
    Desistir,
}

/// Estado de supervisao de um processo filho.
struct EstadoFilho {
    /// Nome usado no log ("bridge MT5" / "core").
    nome: &'static str,
    /// Falhas de saude consecutivas, zeradas quando o filho responde.
    falhas: u32,
    /// Quantas vezes o supervisor ja tentou reiniciar este filho.
    reinicios: u32,
}

impl EstadoFilho {
    fn novo(nome: &'static str) -> Self {
        Self {
            nome,
            falhas: 0,
            reinicios: 0,
        }
    }

    /// Um ciclo de checagem: decide o que fazer com a resposta de saude.
    ///
    /// Fica separado do laco de I/O para poder ser testado sem abrir socket
    /// nem criar processo. As regras que importam:
    ///
    /// - filho saudavel zera as falhas (uma volta ao normal apaga o historico);
    /// - `reinicios >= TENTATIVAS_MAXIMAS` nao tenta mais, para nao gerar
    ///   processos mortos em laco;
    /// - a partir de `FALHAS_ANTES_DE_REINICIAR` falhas, manda reiniciar.
    fn ciclo(&mut self, saudavel: bool) -> Decisao {
        if saudavel {
            self.falhas = 0;
            return Decisao::Saudavel;
        }
        self.falhas = self.falhas.saturating_add(1);
        if self.reinicios >= TENTATIVAS_MAXIMAS {
            return Decisao::Desistir;
        }
        if self.falhas >= FALHAS_ANTES_DE_REINICIAR {
            self.reinicios = self.reinicios.saturating_add(1);
            self.falhas = 0;
            return Decisao::Reiniciar;
        }
        Decisao::Aguardar
    }
}

/// Recolhe os filhos que ja terminaram.
///
/// `Child::try_wait` nao bloqueia e devolve `Some(status)` quando o processo ja
/// saiu. Sem esta chamada, `OWNED_CHILDREN` cresce a cada reinicio e o app
/// perde a memoria de quem morreu — e o log continua mentindo.
fn recolher_mortos() -> Vec<String> {
    let mut mortos = Vec::new();
    if let Some(children) = OWNED_CHILDREN.get() {
        if let Ok(mut children) = children.lock() {
            children.retain_mut(|child| match child.try_wait() {
                Ok(Some(status)) => {
                    mortos.push(format!("pid {} saiu com {}", child.id(), status));
                    false
                }
                _ => true,
            });
        }
    }
    mortos
}

/// Trata um ciclo de um filho: registra a decisao e age.
///
/// Separate do laco para que a politica (quando agir, quando desistir) fique
/// em um unico lugar, e para que o laco nao precise repetir o mesmo `match`
/// para bridge e core.
fn tratar_ciclo(
    estado: &mut EstadoFilho,
    saudavel: bool,
    reiniciar: impl FnOnce() -> Result<(), String>,
) {
    match estado.ciclo(saudavel) {
        Decisao::Saudavel | Decisao::Aguardar => {}
        Decisao::Reiniciar => {
            log_core(&format!(
                "{} sem resposta em {} ciclos; reiniciando (tentativa {}/{})",
                estado.nome, FALHAS_ANTES_DE_REINICIAR, estado.reinicios, TENTATIVAS_MAXIMAS
            ));
            if let Err(e) = reiniciar() {
                log_core(&format!("reinicio do {} falhou: {}", estado.nome, e));
            }
        }
        Decisao::Desistir => log_core(&format!(
            "{} continua sem resposta apos {} tentativas; PARANDO de reiniciar. \
             Verifique o binario e o espaco em disco antes de insistir.",
            estado.nome, TENTATIVAS_MAXIMAS
        )),
    }
}

/// Loop de supervisao dos processos filhos.
///
/// Nao termina sozinho: o un jeito de sair e o processo do app encerrar, e a
/// thread e daemon. Encerrar a UI chama `shutdown_children()` antes.
fn supervisionar(app: &tauri::AppHandle) {
    let mut bridge = EstadoFilho::novo("bridge MT5");
    let mut core = EstadoFilho::novo("core");
    loop {
        std::thread::sleep(INTERVALO_SUPERVISAO);

        for morto in recolher_mortos() {
            log_core(&format!("filho encerrado sem aviso: {}", morto));
        }

        // O bridge vem primeiro: sem ele nao ha rota nenhuma, e o core depende
        // dele para o WebSocket 9002.
        let bridge_ok = bridge_atual_ativo();
        tratar_ciclo(&mut bridge, bridge_ok, || spawn_bridge(&app).map(|_| ()));

        let core_ok = core_atual_ativo();
        tratar_ciclo(&mut core, core_ok, || spawn_core(&app).map(|_| ()));
    }
}

fn spawn_bridge(app: &tauri::AppHandle) -> Result<(), String> {
    if bridge_atual_ativo() {
        return Ok(());
    }
    let path = localizar_bridge(app)?;
    let token = gateway_token()?;
    let mut command = Command::new(&path);
    ocultar_console(&mut command);
    command
        .current_dir(path.parent().unwrap())
        .env("XAU_GATEWAY_TOKEN", token)
        .env("XAU_EXPECTED_GATEWAY_BUILD", EXPECTED_GATEWAY_BUILD)
        .env(
            "XAU_ENABLE_DEMO_ORDERS",
            &flag("XAU_ENABLE_DEMO_ORDERS", "1"),
        )
        .env(
            "XAU_ENABLE_REAL_ORDERS",
            &flag("XAU_ENABLE_REAL_ORDERS", "0"),
        )
        .spawn()
        .map(|child| {
            let pid = child.id();
            register_child(child);
            // Mesmo cuidado do core: "criado" nao e "saudavel". Quem confirma
            // e `aguardar_bridge`, e depois o supervisor, a cada ciclo.
            if flag("XAU_ENABLE_REAL_ORDERS", "0") == "1" {
                // Fica no log porque e a unica diferenca entre operar em conta
                // de teste e operar com dinheiro do cliente.
                log_core(&format!(
                    "ATENCAO: XAU_ENABLE_REAL_ORDERS=1 - ordens reais habilitadas \
                     (bridge criado, pid {})",
                    pid
                ));
            } else {
                log_core(&format!(
                    "bridge MT5 criado (pid {}) com ordens reais DESLIGADAS",
                    pid
                ));
            }
        })
        .map_err(|e| format!("falha ao iniciar bridge MT5: {}", e))
}

fn aguardar_bridge() -> bool {
    for _ in 0..60 {
        if bridge_atual_ativo() {
            log_core("bridge MT5 autenticado e pronto antes do Core");
            return true;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    log_core("bridge MT5 nao respondeu com identidade esperada");
    false
}

/// Inicia o core em processo separado (idempotente: ignora se ja houver um).
fn spawn_core(app: &tauri::AppHandle) -> Result<(), String> {
    if core_atual_ativo() {
        log_core("core autenticado ja esta ativo; spawn ignorado");
        return Ok(());
    }
    let path = localizar_core(app)?;
    let token = gateway_token()?;
    log_core(&format!("iniciando core: {}", path.display()));
    let working_dir = path
        .parent()
        .ok_or_else(|| "diretorio do core invalido".to_string())?;
    let config_path = std::env::var_os("APPDATA")
        .map(PathBuf::from)
        .map(|base| base.join("XAU_AI_PRO").join("config.json"));
    let mut command = Command::new(&path);
    ocultar_console(&mut command);
    command.current_dir(working_dir);
    command.env("XAU_CORE_HEALTH_TOKEN", &token);
    // O core fala com o gateway Python (core/src/bridge/mod.rs). Sem este token
    // toda chamada autenticada volta 401 e o bridge nunca conecta, o que deixava
    // o WebSocket 9002 sem entregar cotacao nenhuma. O token e o mesmo
    // gerado por sessao que o bridge recebe.
    command.env("XAU_GATEWAY_TOKEN", &token);
    if let Some(config) = config_path {
        command.env("XAU_AI_PRO_CONFIG", config);
    }
    command
        .current_dir(working_dir)
        .spawn()
        .map(|child| {
            let pid = child.id();
            register_child(child);
            // "criado" e nao "saudavel": `Command::spawn` so prova que o
            // Windows ACEITOU criar o processo. Ate 2026-09-30 esta linha dizia
            // "spawnado com sucesso" e era o que o log afirmava mesmo depois
            // de o core ter morrido. Quem confirma a saude e `aguardar_core`,
            // e depois o supervisor, a cada ciclo.
            log_core(&format!("core criado (pid {}); confirmando saude", pid));
        })
        .map_err(|e| {
            let m = format!("falha ao spawnar core: {}", e);
            log_core(&m);
            m
        })
}

/// Espera o core responder autenticado, e so entao chama o que importa.
///
/// Sem esta espera, o log de `spawn_core` e o unico registro de que o core
/// existe — e ele e escrito antes de qualquer verificacao. Aqui a frase
/// "pronto" so aparece depois de um HTTP 200 com a versao esperada.
fn aguardar_core() -> bool {
    for _ in 0..60 {
        if core_atual_ativo() {
            log_core("core autenticado e respondendo na versao esperada");
            return true;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    log_core("core nao respondeu com identidade esperada apos 30 s");
    false
}

#[tauri::command]
fn start_core(app: tauri::AppHandle) -> Result<(), String> {
    spawn_core(&app)
}

#[cfg(test)]
mod testes {
    use super::*;

    fn motor() -> EstadoFilho {
        EstadoFilho::novo("bridge MT5")
    }

    // ---------------------------------------------------------- EstadoFilho

    #[test]
    fn filho_saudavel_nao_aciona_nada() {
        let mut e = motor();
        assert_eq!(e.ciclo(true), Decisao::Saudavel);
        assert_eq!(e.reinicios, 0);
    }

    #[test]
    fn falha_isolada_nao_reinicia() {
        // Um pico de CPU nao pode custar um reinicio de processo.
        let mut e = motor();
        assert_eq!(e.ciclo(false), Decisao::Aguardar);
        assert_eq!(e.ciclo(true), Decisao::Saudavel);
        assert_eq!(e.falhas, 0, "voltou ao normal: o historico tem de zerar");
    }

    #[test]
    fn falhas_consecutivas_atingem_o_limite_e_reiniciam() {
        let mut e = motor();
        for _ in 0..FALHAS_ANTES_DE_REINICIAR - 1 {
            assert_eq!(e.ciclo(false), Decisao::Aguardar);
        }
        assert_eq!(e.ciclo(false), Decisao::Reiniciar);
        assert_eq!(e.reinicios, 1);
        assert_eq!(e.falhas, 0, "o contador reinicia apos agir");
    }

    #[test]
    fn falha_intercalada_nao_soma_contagem() {
        // Alterna falha/saude: nunca chega ao limite. E o cenario de rede
        // oscilante, que nao e queda de processo.
        let mut e = motor();
        for _ in 0..10 {
            e.ciclo(false);
            e.ciclo(true);
        }
        assert_eq!(e.reinicios, 0);
    }

    #[test]
    fn desiste_apos_o_teto_de_tentativas() {
        // Sem isto, um binario que falha em loop cria centenas de processos
        // por minuto e enche o disco — o mesmo dano do ciclo de telemetria.
        //
        // A sequencia e deterministica: cada reinicio consome
        // FALHAS_ANTES_DE_REINICIAR ciclos, e a desistencia vem no ciclo
        // SEGUINTE ao ultimo reinicio. Com 3 falhas e 5 tentativas:
        // 3*5 = 15 ciclos de reinicio + 1 de desistencia = 16.
        let mut e = motor();
        let mut acoes: Vec<Decisao> = Vec::new();
        let total = FALHAS_ANTES_DE_REINICIAR * TENTATIVAS_MAXIMAS + FALHAS_ANTES_DE_REINICIAR;
        for _ in 0..total {
            acoes.push(e.ciclo(false));
        }
        let reinicios = acoes.iter().filter(|a| **a == Decisao::Reiniciar).count();
        assert_eq!(
            reinicios, TENTATIVAS_MAXIMAS as usize,
            "reiniciou alem do teto"
        );
        assert_eq!(e.reinicios, TENTATIVAS_MAXIMAS);
        assert_eq!(
            acoes.last(),
            Some(&Decisao::Desistir),
            "apos o teto de reinicios o supervisor precisa desistir e dizer que desistiu"
        );
    }

    #[test]
    fn desistido_continua_desistindo() {
        // Se voltasse a tentar depois de desistir, o laco de processo morto
        // voltaria — e sem log novo, que e como o defeito de 29/09 ficou
        // invisivel.
        let mut e = motor();
        for _ in 0..(FALHAS_ANTES_DE_REINICIAR * TENTATIVAS_MAXIMAS + 2) {
            e.ciclo(false);
        }
        for _ in 0..10 {
            assert_eq!(e.ciclo(false), Decisao::Desistir);
        }
        assert_eq!(
            e.reinicios, TENTATIVAS_MAXIMAS,
            "nenhum reinicio novo apos desistir"
        );
    }

    #[test]
    fn desistencia_volta_ao_aguardo_se_o_filho_se_recuperar() {
        let mut e = motor();
        for _ in 0..TENTATIVAS_MAXIMAS + 2 {
            e.ciclo(false);
        }
        assert_eq!(e.ciclo(true), Decisao::Saudavel);
        // Recuperar limpa o historico; o proximo episodeio recomeca do zero.
        assert_eq!(e.falhas, 0);
    }

    #[test]
    fn intervalo_e_teto_sao_valores_que_fazem_sentido() {
        assert!(
            INTERVALO_SUPERVISAO.as_secs() >= 10,
            "10 s ou mais: polling curto pesa"
        );
        assert!(
            FALHAS_ANTES_DE_REINICIAR >= 2,
            "uma falha unica nunca reinicia"
        );
        assert!(TENTATIVAS_MAXIMAS >= 2 && TENTATIVAS_MAXIMAS <= 10);
    }

    // ------------------------------------------------- politica de ambiente

    #[test]
    fn dinheiro_real_e_fail_closed_por_padrao() {
        // Sem `XAU_ENABLE_REAL_ORDERS` no ambiente, o padrao tem de ser "0".
        // Um "1" aqui ligaria ordem real dentro do binario — o defeito
        // corrigido em 30/09/2026.
        assert_eq!(flag("XAU_ENABLE_REAL_ORDERS", "0"), "0");
        assert_eq!(flag("XAU_GATEWAY_TOKEN_INEXISTENTE_12345", "1"), "1");
    }

    #[test]
    fn supervisor_nao_conhece_ordem_ou_saque() {
        // O supervisor cuida de processo local. Se algum dia ele passar a
        // enviar ordem, ler saldo ou tocar saque, este teste acusa.
        let fonte = include_str!("main.rs");
        let trecho: String = fonte
            .lines()
            .skip_while(|l| !l.contains("fn supervisionar"))
            .take_while(|l| !l.contains("fn main()"))
            .collect::<Vec<_>>()
            .join("\n")
            .to_lowercase();
        for proibido in ["withdraw", "transfer", "trade_order", "order/send"] {
            assert!(
                !trecho.contains(proibido),
                "supervisor fala de {proibido:?}: ele cuida so de processo"
            );
        }
    }

    // -------------------------------------------------------- recolher_mortos

    #[test]
    fn recolher_mortos_nao_panca_sem_filhos() {
        // `OWNED_CHILDREN` e um `OnceLock` de processo. Chamar antes de
        // qualquer `register_child` precisa devolver lista vazia, sem panic.
        assert_eq!(recolher_mortos().len(), 0);
    }
}

fn main() {
    if !acquire_single_instance() {
        return;
    }
    log_core("tauri app inicializando");
    tauri::Builder::default()
        .setup(|app| {
            log_core("tauri setup executado");
            // Pre-aquece a telemetria em background: a aba Sistema nunca paga o custo
            // de abrir o powershell.exe no primeiro clique.
            std::thread::spawn(|| {
                let _ = hardware_telemetry_collect();
            });
            // Inicia o core automaticamente em thread separada (nao bloqueia a UI
            // nem depende da execucao do JavaScript no webview).
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                if let Err(e) = spawn_bridge(&handle) {
                    log_core(&format!("setup bridge: {}", e));
                }
                if !aguardar_bridge() {
                    return;
                }
                if let Err(e) = spawn_core(&handle) {
                    log_core(&format!("setup: {}", e));
                } else if !aguardar_core() {
                    // Antes o `setup` terminava aqui sem registrar nada: o log
                    // parava em "core spawnado com sucesso" e o app seguia
                    // aberto sem core. Agora a falha fica escrita.
                    log_core("setup: core nao ficou pronto; supervisor assume");
                }
                // A supervisao sobe MESMO se o boot acima falhar. E ela quem
                // recolhe o filho caido e tenta trazelo de volta — que e
                // exatamente o caso que nao tinha tratamento antes.
                supervisionar(&handle);
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_core,
            gateway_token_command,
            ensure_config,
            get_app_dirs,
            save_auth,
            load_auth,
            remove_auth,
            hardware_telemetry,
            exit_app
        ])
        .on_window_event(|_, event| {
            if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
                shutdown_children();
            }
        })
        .run(tauri::generate_context!())
        .unwrap_or_else(|e| log_core(&format!("erro ao iniciar XAU AI PRO: {}", e)));
}
