#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::fs;
use std::path::PathBuf;
use std::process::Command;

use serde::Serialize;

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
    fs::write(&arquivo, serde_json::to_string(&payload).map_err(|e| e.to_string())?)
        .map_err(|e| format!("falha ao gravar auth.json: {}", e))
}

/// Le auth.json; retorna None quando nao ha PIN cadastrado.
#[tauri::command]
fn load_auth() -> Result<Option<serde_json::Value>, String> {
    let arquivo = dados_dir()?.join("auth.json");
    if !arquivo.exists() {
        return Ok(None);
    }
    let conteudo = fs::read_to_string(&arquivo)
        .map_err(|e| format!("falha ao ler auth.json: {}", e))?;
    let valor: serde_json::Value = serde_json::from_str(&conteudo)
        .map_err(|e| format!("auth.json invalido: {}", e))?;
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

/// Inicia o core em processo separado (idempotente: ignora se ja houver um).
fn spawn_core(app: &tauri::AppHandle) -> Result<(), String> {
    let path = localizar_core(app)?;
    log_core(&format!("iniciando core: {}", path.display()));
    Command::new(&path)
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
    log_core("tauri app inicializando");
    tauri::Builder::default()
        .setup(|app| {
            log_core("tauri setup executado");
            // Inicia o core automaticamente em thread separada (nao bloqueia a UI
            // nem depende da execucao do JavaScript no webview).
            let handle = app.handle().clone();
            std::thread::spawn(move || {
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
            remove_auth
        ])
        .run(tauri::generate_context!())
        .expect("erro ao iniciar XAU AI PRO");
}
