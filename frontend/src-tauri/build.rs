// A identidade que o bootstrap exige do gateway NAO e escrita a mao.
//
// MEDIDO 22/10/2026: `main.rs` trazia `xau-ai-pro-1.2.4-universal-20260928` e
// `main.tsx` repetia a mesma string. Na 1.2.5 o gateway passou a responder
// `xau-ai-pro-1.2.5-universal-20261022`, os dois compararam com a velha e o
// app abriu em tela preta. Um valor, tres leitores: quem deriva e o gateway
// (`_gateway_build()` em `backend/mt5_gateway.py`), e o Rust recebe o mesmo
// resultado daqui, lendo `Docs/version.json` no build.
//
// `rerun-if-changed` e obrigatorio: sem ele o Cargo reaproveita o `env!` do
// build anterior e a string volta a ficar velha depois de um bump de versao.
use std::path::Path;

fn main() {
    let versao = Path::new("../../Docs/version.json");
    println!("cargo:rerun-if-changed={}", versao.display());
    let texto = std::fs::read_to_string(versao).unwrap_or_default();
    let campo = |nome: &str, padrao: &str| -> String {
        texto
            .split(&format!("\"{}\"", nome))
            .nth(1)
            .and_then(|resto| resto.split('"').nth(1))
            .map(|v| v.trim().to_string())
            .filter(|v| !v.is_empty())
            .unwrap_or_else(|| padrao.to_string())
    };
    let version = campo("version", "1.2.5");
    let suffix = campo("gateway_build_suffix", "universal");
    let updated = campo("updated_at", "").replace('-', "");
    let stamp = if updated.len() == 8 && updated.chars().all(|c| c.is_ascii_digit()) {
        updated
    } else {
        "20260928".to_string()
    };
    println!("cargo:rustc-env=XAU_GATEWAY_BUILD=xau-ai-pro-{version}-{suffix}-{stamp}");
    tauri_build::build()
}
