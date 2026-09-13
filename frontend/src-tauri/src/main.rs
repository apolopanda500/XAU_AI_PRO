#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::process::Command;
use std::path::PathBuf;

fn log_core(msg: &str) {
    if let Some(base) = std::env::var("LOCALAPPDATA").ok().map(PathBuf::from) {
        let dir = base.join("XAU_AI_PRO").join("logs");
        if std::fs::create_dir_all(&dir).is_ok() {
            use std::io::Write;
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(dir.join("core_bootstrap.log")) {
                let _ = writeln!(f, "{}", msg);
            }
        }
    }
}

/// Localiza o executavel do core: primeiro como resource empacotado,
/// depois como pasta "core" ao lado do executavel principal.
fn localizar_core(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    if let Some(p) = app.path_resolver().resolve_resource("core/xau-ai-pro-core.exe") {
        if p.exists() {
            return Ok(p);
        }
    }
    let cand = std::env::current_exe().ok()
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
        .invoke_handler(tauri::generate_handler![start_core])
        .run(tauri::generate_context!())
        .expect("erro ao iniciar XAU AI PRO");
}
