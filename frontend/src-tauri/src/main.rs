#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::fs;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Mutex, OnceLock};
use std::time::Duration;

use serde::Serialize;
use tauri::path::BaseDirectory;
use tauri::Manager;

static OWNED_CHILDREN: OnceLock<Mutex<Vec<Child>>> = OnceLock::new();
static GATEWAY_TOKEN: OnceLock<String> = OnceLock::new();

const EXPECTED_GATEWAY_BUILD: &str = "xau-ai-pro-1.2.3-universal-20260918";

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

#[derive(Serialize)]
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

/// Coleta apenas telemetria local. Nao executa ordens, saques ou alteracoes no MT5.
#[tauri::command]
fn hardware_telemetry() -> HardwareTelemetry {
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
        .env("XAU_ENABLE_DEMO_ORDERS", "1")
        .env("XAU_ENABLE_REAL_ORDERS", "0")
        .spawn()
        .map(|child| {
            register_child(child);
            log_core("bridge MT5 spawnado com sucesso");
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
    command.env("XAU_CORE_HEALTH_TOKEN", token);
    if let Some(config) = config_path {
        command.env("XAU_AI_PRO_CONFIG", config);
    }
    command
        .current_dir(working_dir)
        .spawn()
        .map(|child| {
            register_child(child);
            log_core("core spawnado com sucesso");
        })
        .map_err(|e| {
            let m = format!("falha ao spawnar core: {}", e);
            log_core(&m);
            m
        })
}

#[tauri::command]
fn start_core(app: tauri::AppHandle) -> Result<(), String> {
    spawn_core(&app)
}

fn main() {
    if !acquire_single_instance() {
        return;
    }
    log_core("tauri app inicializando");
    tauri::Builder::default()
        .setup(|app| {
            log_core("tauri setup executado");
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
                }
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
