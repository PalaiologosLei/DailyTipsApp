use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunPayload {
    source_mode: String,
    notes_dir: String,
    github_url: String,
    cloud_dir: String,
    output_dir: String,
    width: i32,
    height: i32,
    formula_renderer: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct RunResponse {
    success: bool,
    exit_code: i32,
    stdout: String,
    stderr: String,
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
        None => "Python not found in PATH".to_string(),
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
fn run_python_job(payload: RunPayload) -> Result<RunResponse, String> {
    let repo_root = resolve_repo_root()?;
    let (program, prefix) = find_python_command().ok_or_else(|| "Python executable not found in PATH".to_string())?;
    let mut command = Command::new(program);
    for arg in prefix {
        command.arg(arg);
    }
    command.current_dir(&repo_root);
    command.arg("-m").arg("src.main");

    if payload.source_mode == "local" {
        let notes_dir = payload.notes_dir.trim();
        if notes_dir.is_empty() {
            return Err("Notes directory is required in local mode".to_string());
        }
        command.arg("--notes-dir").arg(notes_dir);
    } else {
        let github_url = payload.github_url.trim();
        if github_url.is_empty() {
            return Err("GitHub URL is required in GitHub mode".to_string());
        }
        command.arg("--github-url").arg(github_url);
    }

    let cloud_dir = payload.cloud_dir.trim();
    if cloud_dir.is_empty() {
        return Err("Cloud image directory is required".to_string());
    }

    command
        .arg("--cloud-dir").arg(cloud_dir)
        .arg("--output-dir").arg(payload.output_dir.trim())
        .arg("--width").arg(payload.width.to_string())
        .arg("--height").arg(payload.height.to_string())
        .arg("--formula-renderer").arg(payload.formula_renderer.trim());

    let output = command.output().map_err(|error| error.to_string())?;
    Ok(RunResponse {
        success: output.status.success(),
        exit_code: output.status.code().unwrap_or(-1),
        stdout: String::from_utf8_lossy(&output.stdout).to_string(),
        stderr: String::from_utf8_lossy(&output.stderr).to_string(),
    })
}

fn find_python_command() -> Option<(PathBuf, Vec<String>)> {
    let candidates = [
        (PathBuf::from("python"), Vec::<String>::new()),
        (PathBuf::from("py"), vec!["-3".to_string()]),
    ];

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
        .invoke_handler(tauri::generate_handler![get_runtime_status, run_python_job])
        .run(tauri::generate_context!())
        .expect("failed to run DailyTipsApp desktop shell");
}
