#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::fs;
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::Command;
use std::time::Duration;

use serde::Serialize;

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
        let script = r#"$tz=Get-CimInstance MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -First 1; $gpu=Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Where-Object {$_.Name} | Select-Object -First 1; [pscustomobject]@{cpu=if($tz){[math]::Round(($tz.CurrentTemperature/10)-273.15,1)}else{$null}; gpu=if($gpu){$gpu.Name}else{$null}} | ConvertTo-Json -Compress"#;
        if let Ok(output) = Command::new("powershell.exe")
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
                    cpu_temperature_c: cpu,
                    gpu_available: gpu_name.is_some(),
                    gpu_name,
                    source: "Windows WMI".to_string(),
                };
            }
        }
        return HardwareTelemetry {
            cpu_temperature_c: None,
            gpu_name: None,
            gpu_available: false,
            source: "Windows WMI indisponivel".to_string(),
        };
    }
    #[cfg(not(target_os = "windows"))]
    HardwareTelemetry {
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

/// Localiza o executavel do core: primeiro como resource empacotado,
/// depois como pasta "core" ao lado do executavel principal.
fn localizar_core(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    if let Some(p) = app
        .path_resolver()
        .resolve_resource("core/xau-ai-pro-core.exe")
    {
        if p.exists() {
            return Ok(p);
        }
    }
    let cand = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .map(|d| d.join("core").join("xau-ai-pro-core.exe"))
        .filter(|c| c.exists());
    cand.ok_or_else(|| "core nao encontrado (resource e exe_dir)".to_string())
}

fn localizar_bridge(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    if let Some(p) = app
        .path_resolver()
        .resolve_resource("bridge/mt5-gateway.exe")
    {
        if p.exists() {
            return Ok(p);
        }
    }
    let cand = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .map(|d| d.join("bridge").join("mt5-gateway.exe"))
        .filter(|c| c.exists());
    cand.ok_or_else(|| "bridge MT5 nao encontrado".to_string())
}

fn spawn_bridge(app: &tauri::AppHandle) -> Result<(), String> {
    if TcpStream::connect_timeout(
        &"127.0.0.1:9001".parse().unwrap(),
        Duration::from_millis(300),
    )
    .is_ok()
    {
        return Ok(());
    }
    let path = localizar_bridge(app)?;
    let mut command = Command::new(&path);
    ocultar_console(&mut command);
    command
        .current_dir(path.parent().unwrap())
        .spawn()
        .map(|_| log_core("bridge MT5 spawnado com sucesso"))
        .map_err(|e| format!("falha ao iniciar bridge MT5: {}", e))
}

fn aguardar_bridge() {
    for _ in 0..30 {
        if TcpStream::connect_timeout(
            &"127.0.0.1:9001".parse().unwrap(),
            Duration::from_millis(300),
        )
        .is_ok()
        {
            log_core("bridge MT5 pronto antes do Core");
            return;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    log_core("bridge MT5 nao respondeu no prazo; Core sera iniciado em modo sem MT5");
}

/// Inicia o core em processo separado (idempotente: ignora se ja houver um).
fn spawn_core(app: &tauri::AppHandle) -> Result<(), String> {
    // O Core sobrevive ao fechamento da UI; nunca iniciar uma segunda cópia.
    for port in [9002_u16, 9003_u16] {
        if TcpStream::connect_timeout(
            &format!("127.0.0.1:{port}").parse().unwrap(),
            Duration::from_millis(300),
        )
        .is_ok()
        {
            log_core("core ja esta ativo; spawn ignorado");
            return Ok(());
        }
    }
    let path = localizar_core(app)?;
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
    if let Some(config) = config_path {
        command.env("XAU_AI_PRO_CONFIG", config);
    }
    command
        .current_dir(working_dir)
        .spawn()
        .map(|_| {
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
                aguardar_bridge();
                if let Err(e) = spawn_core(&handle) {
                    log_core(&format!("setup: {}", e));
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            start_core,
            ensure_config,
            get_app_dirs,
            save_auth,
            load_auth,
            remove_auth,
            hardware_telemetry
        ])
        .run(tauri::generate_context!())
        .unwrap_or_else(|e| log_core(&format!("erro ao iniciar XAU AI PRO: {}", e)));
}
