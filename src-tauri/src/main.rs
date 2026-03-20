use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunPayload {
    command: String,
    payload: Value,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ApiResponse {
    success: bool,
    exit_code: i32,
    stdout: String,
    stderr: String,
    data: Option<Value>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeStatus {
    repo_root: String,
    python_ok: bool,
    python_summary: String,
    tectonic_bundled: bool,
    tectonic_summary: String,
}

#[tauri::command]
fn get_runtime_status() -> Result<RuntimeStatus, String> {
    let repo_root = resolve_repo_root()?;
    let python = find_python_command();
    let python_summary = match &python {
        Some((program, prefix)) => format!("{} {}", program.display(), prefix.join(" ")).trim().to_string(),
        None => "Python not found in PATH or bundled Miniconda".to_string(),
    };
    let tectonic = repo_root.join("vendor").join("tectonic").join("tectonic.exe");
    let tectonic_summary = if tectonic.exists() {
        format!("Bundled Tectonic found at {}", tectonic.display())
    } else {
        "Bundled Tectonic not found yet".to_string()
    };
    Ok(RuntimeStatus {
        repo_root: repo_root.display().to_string(),
        python_ok: python.is_some(),
        python_summary,
        tectonic_bundled: tectonic.exists(),
        tectonic_summary,
    })
}

#[tauri::command]
fn run_python_api(request: RunPayload) -> Result<ApiResponse, String> {
    let repo_root = resolve_repo_root()?;
    let (program, prefix) = find_python_command().ok_or_else(|| "Python executable not found in PATH or bundled Miniconda".to_string())?;
    let mut command = Command::new(program);
    for arg in prefix {
        command.arg(arg);
    }
    command.current_dir(&repo_root);
    command
        .arg("-m")
        .arg("src.desktop_api")
        .arg(request.command)
        .arg("--payload")
        .arg(request.payload.to_string());

    let output = command.output().map_err(|error| error.to_string())?;
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let data = if output.status.success() {
        serde_json::from_str::<Value>(stdout.trim()).ok()
    } else {
        None
    };

    Ok(ApiResponse {
        success: output.status.success(),
        exit_code: output.status.code().unwrap_or(-1),
        stdout,
        stderr,
        data,
    })
}

fn find_python_command() -> Option<(PathBuf, Vec<String>)> {
    let bundled = PathBuf::from(r"D:\Applications\miniconda\python.exe");
    let candidates = [
        (PathBuf::from(r"D:\Applications\miniconda\python.exe"), Vec::<String>::new()),
        (PathBuf::from("python"), Vec::<String>::new()),
        (PathBuf::from("py"), vec!["-3".to_string()]),
    ];

    if bundled.exists() {
        let mut command = Command::new(&bundled);
        let result = command.arg("--version").output();
        if matches!(result, Ok(output) if output.status.success()) {
            return Some((bundled, Vec::new()));
        }
    }

    for (program, prefix) in candidates {
        let mut command = Command::new(&program);
        for arg in &prefix {
            command.arg(arg);
        }
        let result = command.arg("--version").output();
        if matches!(result, Ok(output) if output.status.success()) {
            return Some((program, prefix));
        }
    }
    None
}

fn resolve_repo_root() -> Result<PathBuf, String> {
    let current = std::env::current_dir().map_err(|error| error.to_string())?;
    if current.join("src").join("main.py").exists() {
        return Ok(current);
    }

    let exe_dir = std::env::current_exe()
        .map_err(|error| error.to_string())?
        .parent()
        .map(Path::to_path_buf)
        .ok_or_else(|| "Unable to resolve executable directory".to_string())?;
    if exe_dir.join("src").join("main.py").exists() {
        return Ok(exe_dir);
    }
    if let Some(parent) = exe_dir.parent() {
        if parent.join("src").join("main.py").exists() {
            return Ok(parent.to_path_buf());
        }
    }

    Err("Unable to locate repository root containing src/main.py".to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![get_runtime_status, run_python_api])
        .run(tauri::generate_context!())
        .expect("failed to run DailyTipsApp desktop shell");
}
