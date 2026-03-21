use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use tauri::Manager;
use std::collections::{BTreeMap, BTreeSet};
use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const SETTINGS_FILE_NAME: &str = ".gui_settings.json";
const BACKGROUND_LIBRARY_RELATIVE_DIR: &str = "assets/backgrounds";
const DEFAULT_GROUP: &str = "default";
const VALID_IMAGE_SUFFIXES: &[&str] = &["png", "jpg", "jpeg", "webp", "bmp"];
const IMAGE_INDEX_NAME: &str = "images_index.json";
const MANIFEST_NAME: &str = ".manifest.json";
const RENDER_STATE_NAME: &str = "render_state.json";
const RENDERER_VERSION: &str = "7";
const DEFAULT_TEXT_COLOR: &str = "#000000";
const DEFAULT_TOP_BLANK_RATIO: f64 = 1.0 / 3.0;

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

#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
struct RuntimeStatus {
    repo_root: String,
    python_ok: bool,
    python_summary: String,
    tectonic_bundled: bool,
    tectonic_summary: String,
    formula_support: String,
    formula_backend_requested: String,
    formula_backend_effective: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct OptionItem {
    key: String,
    label: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct DeviceProfile {
    key: String,
    label: String,
    width: i32,
    height: i32,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackgroundImageInfo {
    id: String,
    group_name: String,
    name: String,
    path: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackgroundLibraryState {
    groups: Vec<String>,
    images: Vec<BackgroundImageInfo>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct BootstrapState {
    settings: Value,
    devices: Vec<DeviceProfile>,
    text_fonts: Vec<OptionItem>,
    math_fonts: Vec<OptionItem>,
    formula_renderers: Vec<OptionItem>,
    background_library: BackgroundLibraryState,
    runtime: RuntimeStatus,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct SaveSettingsResponse {
    settings: Value,
    runtime: RuntimeStatus,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct NamedPayload {
    name: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GroupPayload {
    group_name: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ImagePayload {
    image_id: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ImportPayload {
    group_name: String,
    paths: Vec<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ClearGeneratedSummary {
    removed_metadata_count: usize,
    removed_cloud_count: usize,
    removed_index_count: usize,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct CloudIndexSummary {
    target_dir: String,
    image_count: usize,
    index_path: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct RenderMetadataSummary {
    metadata_dir: String,
    manifest_exists: bool,
    render_state_exists: bool,
    item_count: usize,
    renderer_version: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct LocalScanPayload {
    notes_dir: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ParsedItemPreview {
    title: String,
    body: String,
    note_count: usize,
    notes: Vec<String>,
    source_path: String,
    source_line: usize,
    item_hash: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct LocalScanSummary {
    markdown_file_count: usize,
    item_count: usize,
    items: Vec<ParsedItemPreview>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct PipelineSummary {
    summary: Value,
    runtime: RuntimeStatus,
    background_library: BackgroundLibraryState,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct InstallSelfCheck {
    repo_root: String,
    resource_root: Option<String>,
    desktop_api_path: String,
    desktop_api_exists: bool,
    bundled_python_path: Option<String>,
    bundled_python_exists: bool,
    selected_python_command: Option<String>,
    tectonic_path: Option<String>,
    tectonic_exists: bool,
    default_background_path: String,
    default_background_exists: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ManifestEntry {
    file: String,
    hash: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct PreparedRenderItem {
    title: String,
    body: String,
    notes: Vec<String>,
    source_path: String,
    source_line: usize,
    output_file: String,
}

#[derive(Debug)]
struct RenderPlan {
    render_queue: Vec<PreparedRenderItem>,
    current_entries: BTreeMap<String, ManifestEntry>,
    stale_files: Vec<PathBuf>,
    render_state: Value,
    created_count: usize,
    updated_count: usize,
    unchanged_count: usize,
}

#[tauri::command]
fn get_runtime_status(app: tauri::AppHandle) -> Result<RuntimeStatus, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    Ok(runtime_status_for_renderer(&repo_root, resource_root_for_app(Some(&app)).as_deref(), "auto"))
}

#[tauri::command]
fn bootstrap_app_state(app: tauri::AppHandle) -> Result<BootstrapState, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let resource_root = resource_root_for_app(Some(&app));
    ensure_library_root(&background_library_dir(&repo_root))?;
    let settings = load_gui_settings(&repo_root)?;
    let renderer = settings
        .get("formula_renderer")
        .and_then(Value::as_str)
        .unwrap_or("auto")
        .to_string();
    Ok(BootstrapState {
        settings,
        devices: device_profiles(),
        text_fonts: text_font_choices(),
        math_fonts: math_font_choices(),
        formula_renderers: formula_renderer_choices(),
        background_library: list_background_library(&repo_root)?,
        runtime: runtime_status_for_renderer(&repo_root, resource_root.as_deref(), &renderer),
    })
}

#[tauri::command]
fn save_app_settings(app: tauri::AppHandle, settings: Value) -> Result<SaveSettingsResponse, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let resource_root = resource_root_for_app(Some(&app));
    let stored = save_gui_settings(&repo_root, settings)?;
    let renderer = stored
        .get("formula_renderer")
        .and_then(Value::as_str)
        .unwrap_or("auto")
        .to_string();
    Ok(SaveSettingsResponse {
        settings: stored,
        runtime: runtime_status_for_renderer(&repo_root, resource_root.as_deref(), &renderer),
    })
}

#[tauri::command]
fn create_background_group(app: tauri::AppHandle, payload: NamedPayload) -> Result<BackgroundLibraryState, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let group_name = normalize_group_name(&payload.name)?;
    let group_path = background_library_dir(&repo_root).join(group_name);
    fs::create_dir_all(group_path).map_err(|error| error.to_string())?;
    list_background_library(&repo_root)
}

#[tauri::command]
fn delete_background_group(app: tauri::AppHandle, payload: GroupPayload) -> Result<BackgroundLibraryState, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let group_name = normalize_group_name(&payload.group_name)?;
    let group_path = background_library_dir(&repo_root).join(group_name);
    if group_path.exists() {
        fs::remove_dir_all(group_path).map_err(|error| error.to_string())?;
    }
    ensure_default_group(&background_library_dir(&repo_root))?;
    list_background_library(&repo_root)
}

#[tauri::command]
fn delete_background_image(app: tauri::AppHandle, payload: ImagePayload) -> Result<BackgroundLibraryState, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let image_path = resolve_image_id(&background_library_dir(&repo_root), &payload.image_id)?;
    if image_path.exists() {
        fs::remove_file(image_path).map_err(|error| error.to_string())?;
    }
    list_background_library(&repo_root)
}

#[tauri::command]
fn import_background_images(app: tauri::AppHandle, payload: ImportPayload) -> Result<BackgroundLibraryState, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let group_name = normalize_group_name(&payload.group_name)?;
    let group_path = background_library_dir(&repo_root).join(group_name);
    fs::create_dir_all(&group_path).map_err(|error| error.to_string())?;
    for raw_path in payload.paths {
        let source = PathBuf::from(raw_path);
        validate_image_file(&source)?;
        let target_name = dedupe_name(
            &group_path,
            source
                .file_name()
                .and_then(OsStr::to_str)
                .ok_or_else(|| "无法读取图片文件名".to_string())?,
        );
        let target_path = group_path.join(target_name);
        fs::copy(&source, &target_path).map_err(|error| error.to_string())?;
    }
    list_background_library(&repo_root)
}

#[tauri::command]
fn clear_background_library(app: tauri::AppHandle) -> Result<BackgroundLibraryState, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let library_root = background_library_dir(&repo_root);
    ensure_library_root(&library_root)?;
    for entry in fs::read_dir(&library_root).map_err(|error| error.to_string())? {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        if path.file_name() == Some(OsStr::new(DEFAULT_GROUP)) {
            for file in fs::read_dir(&path).map_err(|error| error.to_string())? {
                let file = file.map_err(|error| error.to_string())?;
                let file_path = file.path();
                if file_path.is_file() && file_path.file_name() != Some(OsStr::new(".gitkeep")) {
                    fs::remove_file(file_path).map_err(|error| error.to_string())?;
                }
            }
        } else {
            fs::remove_dir_all(path).map_err(|error| error.to_string())?;
        }
    }
    ensure_default_group(&library_root)?;
    list_background_library(&repo_root)
}


#[tauri::command]
fn clear_generated_outputs_in_rust(app: tauri::AppHandle, settings: Value) -> Result<ClearGeneratedSummary, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let merged = merge_settings(default_settings(), settings);

    let output_dir_arg = merged
        .get("output_dir")
        .and_then(Value::as_str)
        .unwrap_or(".dailytipsapp")
        .trim();
    let metadata_dir = repo_root.join(output_dir_arg);

    let cloud_dir = merged
        .get("cloud_dir")
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);

    let mut removed_metadata_count = 0usize;
    if metadata_dir.exists() && metadata_dir.is_dir() {
        for entry in fs::read_dir(&metadata_dir).map_err(|error| error.to_string())? {
            let entry = entry.map_err(|error| error.to_string())?;
            let path = entry.path();
            if path.is_file() {
                fs::remove_file(path).map_err(|error| error.to_string())?;
                removed_metadata_count += 1;
            }
        }
    }

    let mut removed_cloud_count = 0usize;
    let mut removed_index_count = 0usize;
    if let Some(cloud_dir) = cloud_dir {
        if cloud_dir.exists() && cloud_dir.is_dir() {
            for entry in fs::read_dir(&cloud_dir).map_err(|error| error.to_string())? {
                let entry = entry.map_err(|error| error.to_string())?;
                let path = entry.path();
                if path.is_file() {
                    let is_png = path
                        .extension()
                        .and_then(OsStr::to_str)
                        .map(|value| value.eq_ignore_ascii_case("png"))
                        .unwrap_or(false);
                    if is_png {
                        fs::remove_file(path).map_err(|error| error.to_string())?;
                        removed_cloud_count += 1;
                    }
                }
            }
            let index_path = cloud_dir.join(IMAGE_INDEX_NAME);
            if index_path.exists() {
                fs::remove_file(index_path).map_err(|error| error.to_string())?;
                removed_index_count = 1;
            }
        }
    }

    Ok(ClearGeneratedSummary {
        removed_metadata_count,
        removed_cloud_count,
        removed_index_count,
    })
}

#[tauri::command]
fn rebuild_cloud_image_index_in_rust(cloud_dir: String) -> Result<CloudIndexSummary, String> {
    let target_dir = PathBuf::from(cloud_dir.trim());
    if !target_dir.exists() || !target_dir.is_dir() {
        return Err(format!("Cloud image directory does not exist: {}", target_dir.display()));
    }

    let mut names = Vec::new();
    for entry in fs::read_dir(&target_dir).map_err(|error| error.to_string())? {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        if path.is_file() {
            let is_png = path
                .extension()
                .and_then(OsStr::to_str)
                .map(|value| value.eq_ignore_ascii_case("png"))
                .unwrap_or(false);
            if is_png {
                names.push(entry.file_name().to_string_lossy().to_string());
            }
        }
    }
    names.sort();
    let payload = json!({ "images": names, "count": names.len() });
    let index_path = target_dir.join(IMAGE_INDEX_NAME);
    let serialized = serde_json::to_string_pretty(&payload).map_err(|error| error.to_string())?;
    fs::write(&index_path, serialized).map_err(|error| error.to_string())?;
    Ok(CloudIndexSummary {
        target_dir: target_dir.display().to_string(),
        image_count: payload["count"].as_u64().unwrap_or(0) as usize,
        index_path: index_path.display().to_string(),
    })
}

#[tauri::command]
fn inspect_render_metadata_in_rust(app: tauri::AppHandle, output_dir: String) -> Result<RenderMetadataSummary, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let metadata_dir = repo_root.join(output_dir.trim());
    let manifest_path = metadata_dir.join(MANIFEST_NAME);
    let render_state_path = metadata_dir.join(RENDER_STATE_NAME);

    let manifest_exists = manifest_path.exists();
    let render_state_exists = render_state_path.exists();
    let mut item_count = 0usize;
    let mut renderer_version = String::new();

    if manifest_exists {
        let raw = fs::read_to_string(&manifest_path).map_err(|error| error.to_string())?;
        let manifest: Value = serde_json::from_str(&raw).unwrap_or_else(|_| json!({}));
        item_count = manifest
            .get("items")
            .and_then(Value::as_object)
            .map(|items| items.len())
            .unwrap_or(0);
        renderer_version = manifest
            .get("version")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string();
    }

    Ok(RenderMetadataSummary {
        metadata_dir: metadata_dir.display().to_string(),
        manifest_exists,
        render_state_exists,
        item_count,
        renderer_version,
    })
}

#[tauri::command]
fn scan_local_markdown(payload: LocalScanPayload) -> Result<LocalScanSummary, String> {
    scan_local_markdown_summary(Path::new(payload.notes_dir.trim()))
}

#[tauri::command]
fn run_generation_pipeline(app: tauri::AppHandle, settings: Value) -> Result<PipelineSummary, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let resource_root = resource_root_for_app(Some(&app));
    let merged = merge_settings(default_settings(), settings);
    let notes_dir = merged
        .get("local_path")
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "请先选择本地 Markdown 目录".to_string())?;

    let prepared = scan_local_markdown_summary(Path::new(notes_dir))?;
    let runtime = runtime_status_for_renderer(
        &repo_root,
        resource_root.as_deref(),
        merged.get("formula_renderer").and_then(Value::as_str).unwrap_or("auto"),
    );
    let plan = build_render_plan(&repo_root, &merged, &runtime, &prepared.items)?;

    if !plan.render_queue.is_empty() {
        let payload = json!({
            "settings": merged.clone(),
            "items": plan.render_queue,
        });
        let data = execute_python_api(&repo_root, resource_root.as_deref(), "render-prepared", payload)?;
        if !data.success {
            return Err(
                data.stderr
                    .trim()
                    .to_string()
                    .if_empty_then(data.stdout.trim().to_string())
                    .if_empty_then(format!("Python pipeline failed with exit code {}", data.exit_code)),
            );
        }
    }

    for stale_path in &plan.stale_files {
        if stale_path.exists() {
            fs::remove_file(stale_path).map_err(|error| error.to_string())?;
        }
    }

    persist_render_outputs(&repo_root, &merged, &plan)?;
    let background_library = list_background_library(&repo_root)?;
    let metadata_dir = metadata_dir_for_settings(&repo_root, &merged);
    let cloud_dir = cloud_dir_for_settings(&merged)?;
    let summary = json!({
        "source_description": format!("本地笔记目录：{}", notes_dir),
        "markdown_file_count": prepared.markdown_file_count,
        "item_count": prepared.item_count,
        "image_count": plan.current_entries.len(),
        "data_dir": metadata_dir.display().to_string(),
        "cloud_dir": cloud_dir.display().to_string(),
        "index_path": cloud_dir.join(IMAGE_INDEX_NAME).display().to_string(),
        "created_count": plan.created_count,
        "updated_count": plan.updated_count,
        "unchanged_count": plan.unchanged_count,
        "deleted_count": plan.stale_files.len(),
    });

    Ok(PipelineSummary {
        summary,
        runtime,
        background_library,
    })
}

#[tauri::command]
fn run_python_api(app: tauri::AppHandle, request: RunPayload) -> Result<ApiResponse, String> {
    let repo_root = resolve_repo_root(Some(&app))?;
    let resource_root = resource_root_for_app(Some(&app));
    execute_python_api(&repo_root, resource_root.as_deref(), &request.command, request.payload)
}

#[tauri::command]
fn installation_self_check(app: tauri::AppHandle) -> Result<InstallSelfCheck, String> {
    let resource_root = resource_root_for_app(Some(&app));
    let repo_root = resolve_repo_root(Some(&app))?;
    let desktop_api_path = repo_root.join("src").join("desktop_api.py");
    let bundled_python_root = python_runtime_root(&repo_root, resource_root.as_deref());
    let bundled_python_path = bundled_python_root
        .as_ref()
        .map(|root| root.join("python.exe"))
        .filter(|path| path.exists());
    let selected_python_command = find_python_command(&repo_root, resource_root.as_deref()).map(|(program, prefix)| {
        let mut parts = vec![program.display().to_string()];
        parts.extend(prefix);
        parts.join(" ")
    });
    let tectonic_path = resolve_tectonic_executable(&repo_root, resource_root.as_deref());
    let default_background_path = repo_root
        .join("assets")
        .join("backgrounds")
        .join("default")
        .join("CBD.jpg");

    Ok(InstallSelfCheck {
        repo_root: repo_root.display().to_string(),
        resource_root: resource_root.map(|path| path.display().to_string()),
        desktop_api_path: desktop_api_path.display().to_string(),
        desktop_api_exists: desktop_api_path.exists(),
        bundled_python_path: bundled_python_path.as_ref().map(|path| path.display().to_string()),
        bundled_python_exists: bundled_python_path.is_some(),
        selected_python_command,
        tectonic_path: tectonic_path.as_ref().map(|path| path.display().to_string()),
        tectonic_exists: tectonic_path.is_some(),
        default_background_path: default_background_path.display().to_string(),
        default_background_exists: default_background_path.exists(),
    })
}

fn runtime_status_for_renderer(repo_root: &Path, resource_root: Option<&Path>, requested: &str) -> RuntimeStatus {
    let python = find_python_command(repo_root, resource_root);
    let python_summary = match &python {
        Some((program, prefix)) => format!("{} {}", program.display(), prefix.join(" "))
            .trim()
            .to_string(),
        None => "未找到可用的 Python 解释器".to_string(),
    };

    let tectonic = resolve_tectonic_executable(repo_root, resource_root);
    let tectonic_exists = tectonic.is_some();
    let tectonic_summary = if let Some(path) = &tectonic {
        format!("已检测到 Tectonic：{}", path.display())
    } else {
        "未检测到 Tectonic 可执行文件".to_string()
    };

    let requested_key = match requested {
        "tectonic" | "matplotlib" | "auto" => requested.to_string(),
        _ => "auto".to_string(),
    };

    let (effective, support) = match requested_key.as_str() {
        "tectonic" if tectonic_exists => ("tectonic".to_string(), "当前使用 Tectonic LaTeX".to_string()),
        "tectonic" => ("plain".to_string(), "未找到 Tectonic，暂时回退到纯文本模式".to_string()),
        "matplotlib" => ("matplotlib".to_string(), "当前使用 Matplotlib MathText".to_string()),
        _ if tectonic_exists => ("tectonic".to_string(), "自动选择 Tectonic LaTeX".to_string()),
        _ => ("matplotlib".to_string(), "自动回退到 Matplotlib MathText".to_string()),
    };

    RuntimeStatus {
        repo_root: repo_root.display().to_string(),
        python_ok: python.is_some(),
        python_summary,
        tectonic_bundled: tectonic_exists,
        tectonic_summary,
        formula_support: support,
        formula_backend_requested: requested_key,
        formula_backend_effective: effective,
    }
}

fn device_profiles() -> Vec<DeviceProfile> {
    vec![
        DeviceProfile { key: "iphone_17".into(), label: "iPhone 17".into(), width: 1206, height: 2622 },
        DeviceProfile { key: "iphone_17_air".into(), label: "iPhone 17 Air".into(), width: 1260, height: 2736 },
        DeviceProfile { key: "iphone_17_pro".into(), label: "iPhone 17 Pro".into(), width: 1206, height: 2622 },
        DeviceProfile { key: "iphone_17_pro_max".into(), label: "iPhone 17 Pro Max".into(), width: 1320, height: 2868 },
        DeviceProfile { key: "iphone_17e".into(), label: "iPhone 17e".into(), width: 1170, height: 2532 },
        DeviceProfile { key: "iphone_16".into(), label: "iPhone 16".into(), width: 1179, height: 2556 },
        DeviceProfile { key: "iphone_16_plus".into(), label: "iPhone 16 Plus".into(), width: 1290, height: 2796 },
        DeviceProfile { key: "iphone_16_pro".into(), label: "iPhone 16 Pro".into(), width: 1206, height: 2622 },
        DeviceProfile { key: "iphone_16_pro_max".into(), label: "iPhone 16 Pro Max".into(), width: 1320, height: 2868 },
        DeviceProfile { key: "iphone_15_pro".into(), label: "iPhone 15 Pro".into(), width: 1179, height: 2556 },
        DeviceProfile { key: "iphone_15_pro_max".into(), label: "iPhone 15 Pro Max".into(), width: 1290, height: 2796 },
        DeviceProfile { key: "iphone_14".into(), label: "iPhone 14 / 13 / 12".into(), width: 1170, height: 2532 },
        DeviceProfile { key: "iphone_14_plus".into(), label: "iPhone 14 Plus / 13 Pro Max / 12 Pro Max".into(), width: 1284, height: 2778 },
        DeviceProfile { key: "iphone_se".into(), label: "iPhone SE / 8 / 7 / 6".into(), width: 750, height: 1334 },
        DeviceProfile { key: "custom".into(), label: "自定义".into(), width: 1179, height: 2556 },
    ]
}

fn text_font_choices() -> Vec<OptionItem> {
    vec![
        OptionItem { key: "microsoft_yahei".into(), label: "Microsoft YaHei".into() },
        OptionItem { key: "simhei".into(), label: "SimHei".into() },
        OptionItem { key: "simsun".into(), label: "SimSun".into() },
    ]
}

fn math_font_choices() -> Vec<OptionItem> {
    vec![
        OptionItem { key: "dejavusans".into(), label: "DejaVu Sans".into() },
        OptionItem { key: "stixsans".into(), label: "STIX Sans".into() },
        OptionItem { key: "dejavuserif".into(), label: "DejaVu Serif".into() },
        OptionItem { key: "stix".into(), label: "STIX".into() },
        OptionItem { key: "cm".into(), label: "Computer Modern".into() },
    ]
}

fn formula_renderer_choices() -> Vec<OptionItem> {
    vec![
        OptionItem { key: "auto".into(), label: "自动（推荐）".into() },
        OptionItem { key: "tectonic".into(), label: "Tectonic LaTeX".into() },
        OptionItem { key: "matplotlib".into(), label: "Matplotlib MathText".into() },
    ]
}

fn default_settings() -> Value {
    json!({
        "local_path": "",
        "output_dir": ".dailytipsapp",
        "cloud_dir": "C:/Users/lky14/iCloudDrive/DailyTips",
        "device_model": "iphone_17_pro",
        "width": "1206",
        "height": "2622",
        "background_mode": "white",
        "background_group": "",
        "background_image_id": "",
        "show_content_panel": true,
        "panel_opacity": 212,
        "text_font_family": "microsoft_yahei",
        "math_font_family": "dejavusans",
        "formula_renderer": "auto",
        "text_color": "#000000",
        "math_color": "#000000"
    })
}

fn load_gui_settings(repo_root: &Path) -> Result<Value, String> {
    let path = repo_root.join(SETTINGS_FILE_NAME);
    let defaults = default_settings();
    if !path.exists() {
        return Ok(defaults);
    }
    let raw = fs::read_to_string(path).map_err(|error| error.to_string())?;
    let loaded: Value = serde_json::from_str(&raw).unwrap_or_else(|_| json!({}));
    Ok(merge_settings(defaults, loaded))
}

fn save_gui_settings(repo_root: &Path, settings: Value) -> Result<Value, String> {
    let path = repo_root.join(SETTINGS_FILE_NAME);
    let merged = merge_settings(default_settings(), settings);
    let serialized = serde_json::to_string_pretty(&merged).map_err(|error| error.to_string())?;
    fs::write(path, serialized).map_err(|error| error.to_string())?;
    Ok(merged)
}

fn merge_settings(defaults: Value, loaded: Value) -> Value {
    let mut merged = match defaults {
        Value::Object(map) => map,
        _ => Map::new(),
    };
    if let Value::Object(loaded_map) = loaded {
        for (key, value) in loaded_map {
            if merged.contains_key(&key) {
                merged.insert(key, value);
            }
        }
    }
    Value::Object(merged)
}

fn list_background_library(repo_root: &Path) -> Result<BackgroundLibraryState, String> {
    let library_root = background_library_dir(repo_root);
    ensure_library_root(&library_root)?;
    let mut groups = Vec::new();
    let mut images = Vec::new();

    for entry in fs::read_dir(&library_root).map_err(|error| error.to_string())? {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let group_name = entry.file_name().to_string_lossy().to_string();
        groups.push(group_name.clone());
        for image_entry in fs::read_dir(&path).map_err(|error| error.to_string())? {
            let image_entry = image_entry.map_err(|error| error.to_string())?;
            let image_path = image_entry.path();
            if !image_path.is_file() || !has_valid_image_suffix(&image_path) {
                continue;
            }
            let image_name = image_entry.file_name().to_string_lossy().to_string();
            images.push(BackgroundImageInfo {
                id: format!("{group_name}/{image_name}"),
                group_name: group_name.clone(),
                name: image_name,
                path: image_path.display().to_string(),
            });
        }
    }

    groups.sort();
    images.sort_by(|a, b| a.id.cmp(&b.id));
    Ok(BackgroundLibraryState { groups, images })
}

fn ensure_library_root(path: &Path) -> Result<(), String> {
    fs::create_dir_all(path).map_err(|error| error.to_string())?;
    ensure_default_group(path)
}

fn ensure_default_group(library_root: &Path) -> Result<(), String> {
    let default_group = library_root.join(DEFAULT_GROUP);
    fs::create_dir_all(&default_group).map_err(|error| error.to_string())?;
    let gitkeep = default_group.join(".gitkeep");
    if !gitkeep.exists() {
        fs::write(gitkeep, "").map_err(|error| error.to_string())?;
    }
    Ok(())
}

fn background_library_dir(repo_root: &Path) -> PathBuf {
    repo_root.join(BACKGROUND_LIBRARY_RELATIVE_DIR)
}

fn normalize_group_name(group_name: &str) -> Result<String, String> {
    let normalized = group_name.trim().replace('\\', "_").replace('/', "_");
    if normalized.is_empty() {
        return Err("分组名称不能为空".to_string());
    }
    Ok(normalized)
}

fn resolve_image_id(library_root: &Path, image_id: &str) -> Result<PathBuf, String> {
    let Some((group_name, name)) = image_id.split_once('/') else {
        return Err("无效的图片 ID".to_string());
    };
    Ok(library_root.join(group_name).join(name))
}

fn validate_image_file(path: &Path) -> Result<(), String> {
    if !path.exists() || !path.is_file() {
        return Err(format!("图片文件不存在：{}", path.display()));
    }
    if !has_valid_image_suffix(path) {
        return Err(format!("文件不是支持的图片格式：{}", path.display()));
    }
    Ok(())
}

fn has_valid_image_suffix(path: &Path) -> bool {
    path.extension()
        .and_then(OsStr::to_str)
        .map(|suffix| VALID_IMAGE_SUFFIXES.iter().any(|valid| suffix.eq_ignore_ascii_case(valid)))
        .unwrap_or(false)
}

fn dedupe_name(group_path: &Path, original_name: &str) -> String {
    let original = Path::new(original_name);
    let stem = original.file_stem().and_then(OsStr::to_str).unwrap_or("image");
    let suffix = original
        .extension()
        .and_then(OsStr::to_str)
        .map(|value| format!(".{value}"))
        .unwrap_or_default();
    let mut candidate = original_name.to_string();
    let mut index = 1;
    while group_path.join(&candidate).exists() {
        candidate = format!("{stem}_{index}{suffix}");
        index += 1;
    }
    candidate
}

fn scan_local_markdown_summary(notes_dir: &Path) -> Result<LocalScanSummary, String> {
    if !notes_dir.exists() {
        return Err(format!("Notes directory does not exist: {}", notes_dir.display()));
    }
    if !notes_dir.is_dir() {
        return Err(format!("Notes directory is not a directory: {}", notes_dir.display()));
    }

    let mut markdown_files = Vec::new();
    collect_markdown_files(notes_dir, &mut markdown_files)?;
    markdown_files.sort();

    let mut items = Vec::new();
    for file in &markdown_files {
        let text = fs::read_to_string(file).map_err(|error| error.to_string())?;
        items.extend(parse_markdown_text(&text, file));
    }

    let item_count = items.len();
    Ok(LocalScanSummary {
        markdown_file_count: markdown_files.len(),
        item_count,
        items,
    })
}

fn metadata_dir_for_settings(repo_root: &Path, settings: &Value) -> PathBuf {
    let output_dir = settings
        .get("output_dir")
        .and_then(Value::as_str)
        .unwrap_or(".dailytipsapp")
        .trim();
    repo_root.join(output_dir)
}

fn cloud_dir_for_settings(settings: &Value) -> Result<PathBuf, String> {
    settings
        .get("cloud_dir")
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .ok_or_else(|| "Cloud image directory is required.".to_string())
}

fn load_manifest_entries(manifest_path: &Path) -> BTreeMap<String, ManifestEntry> {
    if !manifest_path.exists() {
        return BTreeMap::new();
    }
    let Ok(raw) = fs::read_to_string(manifest_path) else {
        return BTreeMap::new();
    };
    let Ok(loaded) = serde_json::from_str::<Value>(&raw) else {
        return BTreeMap::new();
    };
    let Some(items) = loaded.get("items").and_then(Value::as_object) else {
        return BTreeMap::new();
    };
    let mut result = BTreeMap::new();
    for (key, value) in items {
        let Some(file) = value.get("file").and_then(Value::as_str) else {
            continue;
        };
        let Some(hash) = value.get("hash").and_then(Value::as_str) else {
            continue;
        };
        result.insert(
            key.clone(),
            ManifestEntry {
                file: file.to_string(),
                hash: hash.to_string(),
            },
        );
    }
    result
}

fn load_render_state_value(state_path: &Path) -> Value {
    if !state_path.exists() {
        return json!({});
    }
    let Ok(raw) = fs::read_to_string(state_path) else {
        return json!({});
    };
    serde_json::from_str::<Value>(&raw).unwrap_or_else(|_| json!({}))
}

fn normalize_color_value(raw: Option<&str>) -> String {
    let value = raw.unwrap_or(DEFAULT_TEXT_COLOR).trim();
    if value.is_empty() {
        DEFAULT_TEXT_COLOR.to_string()
    } else {
        value.to_string()
    }
}

fn clamped_panel_opacity(settings: &Value) -> i64 {
    settings
        .get("panel_opacity")
        .and_then(Value::as_i64)
        .unwrap_or(212)
        .clamp(0, 255)
}

fn build_render_state_value(settings: &Value, runtime: &RuntimeStatus) -> Value {
    json!({
        "renderer_version": RENDERER_VERSION,
        "width": settings.get("width").and_then(Value::as_str).and_then(|v| v.trim().parse::<i64>().ok()).unwrap_or(1179),
        "height": settings.get("height").and_then(Value::as_str).and_then(|v| v.trim().parse::<i64>().ok()).unwrap_or(2556),
        "top_blank_ratio": DEFAULT_TOP_BLANK_RATIO,
        "background_mode": settings.get("background_mode").and_then(Value::as_str).unwrap_or("white"),
        "background_image_id": settings.get("background_image_id").and_then(Value::as_str).unwrap_or(""),
        "background_group_name": settings.get("background_group").and_then(Value::as_str).unwrap_or(""),
        "show_content_panel": settings.get("show_content_panel").and_then(Value::as_bool).unwrap_or(true),
        "panel_opacity": clamped_panel_opacity(settings),
        "text_font_family": settings.get("text_font_family").and_then(Value::as_str).unwrap_or("microsoft_yahei"),
        "math_font_family": settings.get("math_font_family").and_then(Value::as_str).unwrap_or("dejavusans"),
        "text_color": normalize_color_value(settings.get("text_color").and_then(Value::as_str)),
        "math_color": normalize_color_value(settings.get("math_color").and_then(Value::as_str)),
        "formula_renderer": settings.get("formula_renderer").and_then(Value::as_str).unwrap_or("auto"),
        "formula_renderer_effective": runtime.formula_backend_effective,
    })
}

fn item_key_for_preview(item: &ParsedItemPreview) -> String {
    format!(
        "{}:{}:{}",
        item.source_path.replace('\\', "/"),
        item.source_line,
        item.title
    )
}

fn build_output_filename(item: &ParsedItemPreview, previous: Option<&ManifestEntry>) -> String {
    if let Some(previous) = previous {
        if !previous.file.trim().is_empty() {
            return previous.file.clone();
        }
    }
    let safe_title: String = item
        .title
        .chars()
        .map(|ch| match ch {
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*' => '_',
            ' ' => '_',
            _ => ch,
        })
        .collect::<String>()
        .trim()
        .chars()
        .take(40)
        .collect();
    let base = if safe_title.is_empty() { "item".to_string() } else { safe_title };
    let digest_source = format!("{}:{}:{}", item.source_path.replace('\\', "/"), item.source_line, item.title);
    let digest = format!("{:x}", Sha256::digest(digest_source.as_bytes()));
    format!("{}_{}.png", base, &digest[..8])
}

fn list_background_candidates(repo_root: &Path, group_name: Option<&str>) -> Vec<(String, PathBuf)> {
    let library_root = background_library_dir(repo_root);
    let mut groups = Vec::new();
    if let Some(group_name) = group_name {
        groups.push(library_root.join(group_name));
    } else if let Ok(entries) = fs::read_dir(&library_root) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                groups.push(path);
            }
        }
    }
    groups.sort();

    let mut images = Vec::new();
    for group_path in groups {
        let group_name = group_path.file_name().and_then(OsStr::to_str).unwrap_or_default().to_string();
        if let Ok(entries) = fs::read_dir(&group_path) {
            for entry in entries.flatten() {
                let path = entry.path();
                if !path.is_file() || !has_valid_image_suffix(&path) {
                    continue;
                }
                let name = entry.file_name().to_string_lossy().to_string();
                images.push((format!("{}/{}", group_name, name), path));
            }
        }
    }
    images.sort_by(|a, b| a.0.cmp(&b.0));
    images
}

fn choose_background_path_for_item(repo_root: &Path, settings: &Value, item_key: &str) -> Option<PathBuf> {
    let mode = settings.get("background_mode").and_then(Value::as_str).unwrap_or("white");
    match mode {
        "white" => None,
        "specific" => {
            let image_id = settings.get("background_image_id").and_then(Value::as_str).unwrap_or("");
            if image_id.is_empty() {
                return None;
            }
            resolve_image_id(&background_library_dir(repo_root), image_id).ok().filter(|path| path.exists())
        }
        "random_group" => {
            let group_name = settings.get("background_group").and_then(Value::as_str).unwrap_or("");
            choose_random_background(list_background_candidates(repo_root, Some(group_name)), mode, group_name, item_key)
        }
        "random_all" => choose_random_background(list_background_candidates(repo_root, None), mode, "", item_key),
        _ => None,
    }
}

fn choose_random_background(
    candidates: Vec<(String, PathBuf)>,
    mode: &str,
    group_name: &str,
    item_key: &str,
) -> Option<PathBuf> {
    if candidates.is_empty() {
        return None;
    }
    let joined = candidates.iter().map(|(id, _)| id.clone()).collect::<Vec<_>>().join("|");
    let seed = format!("{}|{}|{}|{}", mode, group_name, item_key, joined);
    let digest = format!("{:x}", Sha256::digest(seed.as_bytes()));
    let index = usize::from_str_radix(&digest[..8], 16).ok()? % candidates.len();
    Some(candidates[index].1.clone())
}

fn background_stamp(path: Option<&PathBuf>) -> String {
    let Some(path) = path else {
        return "white".to_string();
    };
    let Ok(metadata) = path.metadata() else {
        return "white".to_string();
    };
    let modified = metadata
        .modified()
        .ok()
        .and_then(|time| time.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|duration| duration.as_nanos())
        .unwrap_or(0);
    format!("{}|{}|{}", path.display().to_string().replace('\\', "/"), modified, metadata.len())
}

fn build_content_hash(item: &ParsedItemPreview, settings: &Value, background_stamp: &str, runtime: &RuntimeStatus) -> String {
    let mut payload = BTreeMap::<String, Value>::new();
    payload.insert("background_group_name".to_string(), json!(settings.get("background_group").and_then(Value::as_str).unwrap_or("")));
    payload.insert("background_image_id".to_string(), json!(settings.get("background_image_id").and_then(Value::as_str).unwrap_or("")));
    payload.insert("background_mode".to_string(), json!(settings.get("background_mode").and_then(Value::as_str).unwrap_or("white")));
    payload.insert("background_stamp".to_string(), json!(background_stamp));
    payload.insert("body".to_string(), json!(item.body));
    payload.insert("formula_renderer".to_string(), json!(settings.get("formula_renderer").and_then(Value::as_str).unwrap_or("auto")));
    payload.insert("formula_renderer_effective".to_string(), json!(runtime.formula_backend_effective));
    payload.insert("height".to_string(), json!(settings.get("height").and_then(Value::as_str).and_then(|v| v.trim().parse::<i64>().ok()).unwrap_or(2556)));
    payload.insert("math_color".to_string(), json!(normalize_color_value(settings.get("math_color").and_then(Value::as_str))));
    payload.insert("math_font_family".to_string(), json!(settings.get("math_font_family").and_then(Value::as_str).unwrap_or("dejavusans")));
    payload.insert("notes".to_string(), json!(item.notes));
    payload.insert("panel_opacity".to_string(), json!(clamped_panel_opacity(settings)));
    payload.insert("renderer_version".to_string(), json!(RENDERER_VERSION));
    payload.insert("show_content_panel".to_string(), json!(settings.get("show_content_panel").and_then(Value::as_bool).unwrap_or(true)));
    payload.insert("text_color".to_string(), json!(normalize_color_value(settings.get("text_color").and_then(Value::as_str))));
    payload.insert("text_font_family".to_string(), json!(settings.get("text_font_family").and_then(Value::as_str).unwrap_or("microsoft_yahei")));
    payload.insert("title".to_string(), json!(item.title));
    payload.insert("top_blank_ratio".to_string(), json!(DEFAULT_TOP_BLANK_RATIO));
    payload.insert("width".to_string(), json!(settings.get("width").and_then(Value::as_str).and_then(|v| v.trim().parse::<i64>().ok()).unwrap_or(1179)));
    let serialized = serde_json::to_string(&payload).unwrap_or_default();
    format!("{:x}", Sha256::digest(serialized.as_bytes()))
}

fn build_render_plan(
    repo_root: &Path,
    settings: &Value,
    runtime: &RuntimeStatus,
    items: &[ParsedItemPreview],
) -> Result<RenderPlan, String> {
    let metadata_dir = metadata_dir_for_settings(repo_root, settings);
    let cloud_dir = cloud_dir_for_settings(settings)?;
    let previous_entries = load_manifest_entries(&metadata_dir.join(MANIFEST_NAME));
    let previous_state = load_render_state_value(&metadata_dir.join(RENDER_STATE_NAME));
    let render_state = build_render_state_value(settings, runtime);
    let force_regenerate = previous_state != render_state;

    let mut current_entries = BTreeMap::new();
    let mut render_queue = Vec::new();
    let mut created_count = 0usize;
    let mut updated_count = 0usize;
    let mut unchanged_count = 0usize;

    for item in items {
        let item_key = item_key_for_preview(item);
        let previous = previous_entries.get(&item_key);
        let output_file = build_output_filename(item, previous);
        let image_path = cloud_dir.join(&output_file);
        let bg_path = choose_background_path_for_item(repo_root, settings, &item_key);
        let bg_stamp = background_stamp(bg_path.as_ref());
        let content_hash = build_content_hash(item, settings, &bg_stamp, runtime);

        let unchanged = !force_regenerate
            && previous.map(|entry| entry.hash == content_hash).unwrap_or(false)
            && image_path.exists();

        if unchanged {
            unchanged_count += 1;
        } else {
            if previous.is_some() || image_path.exists() {
                updated_count += 1;
            } else {
                created_count += 1;
            }
            render_queue.push(PreparedRenderItem {
                title: item.title.clone(),
                body: item.body.clone(),
                notes: item.notes.clone(),
                source_path: item.source_path.clone(),
                source_line: item.source_line,
                output_file: output_file.clone(),
            });
        }

        current_entries.insert(
            item_key,
            ManifestEntry {
                file: output_file,
                hash: content_hash,
            },
        );
    }

    let current_files = current_entries
        .values()
        .map(|entry| entry.file.clone())
        .collect::<BTreeSet<_>>();
    let stale_files = previous_entries
        .values()
        .filter(|entry| !current_files.contains(&entry.file))
        .map(|entry| cloud_dir.join(&entry.file))
        .collect::<Vec<_>>();

    Ok(RenderPlan {
        render_queue,
        current_entries,
        stale_files,
        render_state,
        created_count,
        updated_count,
        unchanged_count,
    })
}

fn persist_render_outputs(repo_root: &Path, settings: &Value, plan: &RenderPlan) -> Result<(), String> {
    let metadata_dir = metadata_dir_for_settings(repo_root, settings);
    let cloud_dir = cloud_dir_for_settings(settings)?;
    fs::create_dir_all(&metadata_dir).map_err(|error| error.to_string())?;
    fs::create_dir_all(&cloud_dir).map_err(|error| error.to_string())?;

    let manifest = json!({
        "version": RENDERER_VERSION,
        "items": plan.current_entries,
    });
    let manifest_path = metadata_dir.join(MANIFEST_NAME);
    let manifest_serialized = serde_json::to_string_pretty(&manifest).map_err(|error| error.to_string())?;
    fs::write(&manifest_path, manifest_serialized).map_err(|error| error.to_string())?;

    let render_state_path = metadata_dir.join(RENDER_STATE_NAME);
    let render_state_serialized = serde_json::to_string_pretty(&plan.render_state).map_err(|error| error.to_string())?;
    fs::write(&render_state_path, render_state_serialized).map_err(|error| error.to_string())?;

    let mut images = plan
        .current_entries
        .values()
        .map(|entry| entry.file.clone())
        .filter(|file| cloud_dir.join(file).exists())
        .collect::<Vec<_>>();
    images.sort();
    let index_payload = json!({ "images": images, "count": images.len() });
    let index_path = cloud_dir.join(IMAGE_INDEX_NAME);
    let index_serialized = serde_json::to_string_pretty(&index_payload).map_err(|error| error.to_string())?;
    fs::write(index_path, index_serialized).map_err(|error| error.to_string())?;

    Ok(())
}

fn execute_python_api(
    repo_root: &Path,
    resource_root: Option<&Path>,
    command_name: &str,
    payload: Value,
) -> Result<ApiResponse, String> {
    let (program, prefix) = find_python_command(repo_root, resource_root)
        .ok_or_else(|| "Python executable not found in bundled resources or PATH".to_string())?;
    let mut command = Command::new(program);
    for arg in prefix {
        command.arg(arg);
    }
    command.current_dir(repo_root);
    command.env("PYTHONUTF8", "1");
    command.env("DAILYTIPS_RESOURCE_ROOT", repo_root);

    if let Some(tectonic_path) = resolve_tectonic_executable(repo_root, resource_root) {
        command.env("DAILYTIPS_TECTONIC", tectonic_path);
    }

    if let Some(runtime_root) = python_runtime_root(repo_root, resource_root) {
        let mut path_entries = vec![
            runtime_root.clone(),
            runtime_root.join("DLLs"),
            runtime_root.join("Library").join("bin"),
            runtime_root.join("Scripts"),
        ];
        if let Some(existing_path) = std::env::var_os("PATH") {
            path_entries.extend(std::env::split_paths(&existing_path));
        }
        if let Ok(joined_path) = std::env::join_paths(path_entries.iter()) {
            command.env("PATH", joined_path);
        }
    }

    let payload_string = payload.to_string();
    let payload_file = write_payload_file(&payload_string)?;

    command
        .arg("-m")
        .arg("src.desktop_api")
        .arg(command_name)
        .arg("--payload-file")
        .arg(&payload_file);

    let output = command.output().map_err(|error| error.to_string())?;
    let _ = fs::remove_file(&payload_file);
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

fn write_payload_file(payload: &str) -> Result<PathBuf, String> {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_nanos();
    let digest = format!("{:x}", Sha256::digest(format!("{}:{}:{}", std::process::id(), timestamp, payload.len()).as_bytes()));
    let path = std::env::temp_dir().join(format!("dailytipsapp_payload_{}.json", &digest[..16]));
    fs::write(&path, payload).map_err(|error| error.to_string())?;
    Ok(path)
}

trait IfEmptyThen {
    fn if_empty_then(self, fallback: String) -> String;
}

impl IfEmptyThen for String {
    fn if_empty_then(self, fallback: String) -> String {
        if self.is_empty() {
            fallback
        } else {
            self
        }
    }
}

fn collect_markdown_files(dir: &Path, files: &mut Vec<PathBuf>) -> Result<(), String> {
    for entry in fs::read_dir(dir).map_err(|error| error.to_string())? {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        if path.is_dir() {
            collect_markdown_files(&path, files)?;
        } else if path.is_file() {
            let is_md = path
                .extension()
                .and_then(OsStr::to_str)
                .map(|value| value.eq_ignore_ascii_case("md"))
                .unwrap_or(false);
            if is_md {
                files.push(path);
            }
        }
    }
    Ok(())
}

fn parse_markdown_text(text: &str, source_path: &Path) -> Vec<ParsedItemPreview> {
    let lines: Vec<&str> = text.lines().collect();
    let mut items = Vec::new();

    for (index, raw_line) in lines.iter().enumerate() {
        let Some((indent, content)) = parse_line(raw_line) else {
            continue;
        };
        let Some(title) = extract_title(&content) else {
            continue;
        };
        let child_lines = collect_direct_children(&lines, index + 1, indent);
        if child_lines.is_empty() {
            continue;
        }
        let body = child_lines[0].1.trim().to_string();
        if body.is_empty() {
            continue;
        }
        let notes: Vec<String> = child_lines
            .iter()
            .skip(1)
            .map(|(_, value)| value.trim().to_string())
            .filter(|value| !value.is_empty())
            .collect();
        items.push(ParsedItemPreview {
            item_hash: build_item_hash(&title, &body, &notes),
            title,
            body,
            note_count: notes.len(),
            notes,
            source_path: source_path.display().to_string(),
            source_line: index + 1,
        });
    }

    items
}

fn parse_line(raw_line: &str) -> Option<(usize, String)> {
    if raw_line.trim().is_empty() {
        return None;
    }
    let expanded = raw_line.replace('\t', "    ");
    let indent = expanded.len() - expanded.trim_start_matches(' ').len();
    let content = expanded.trim_start_matches(' ');
    let content = strip_list_marker(content).trim().to_string();
    if content.is_empty() {
        return None;
    }
    Some((indent, content))
}

fn strip_list_marker(content: &str) -> &str {
    let mut chars = content.chars();
    let first = chars.next();
    let second = chars.next();
    match (first, second) {
        (Some('-' | '*' | '+'), Some(' ')) => chars.as_str(),
        _ => content,
    }
}

fn extract_title(content: &str) -> Option<String> {
    let start = content.find('【')?;
    let end = content[start + '【'.len_utf8()..].find('】')? + start + '【'.len_utf8();
    let title = content[start + '【'.len_utf8()..end].trim().to_string();
    if title.is_empty() {
        None
    } else {
        Some(title)
    }
}

fn collect_direct_children(lines: &[&str], start_index: usize, parent_indent: usize) -> Vec<(usize, String)> {
    let mut candidate_lines = Vec::new();
    let mut child_indent: Option<usize> = None;
    let mut index = start_index;

    while index < lines.len() {
        let Some((indent, content)) = parse_line(lines[index]) else {
            index += 1;
            continue;
        };
        if indent <= parent_indent {
            break;
        }
        if child_indent.is_none() {
            child_indent = Some(indent);
        }
        if Some(indent) == child_indent && !content.trim().is_empty() {
            candidate_lines.push((index + 1, content));
        }
        index += 1;
    }

    candidate_lines
}

fn build_item_hash(title: &str, body: &str, notes: &[String]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(title.as_bytes());
    hasher.update(b"\n");
    hasher.update(body.as_bytes());
    hasher.update(b"\n");
    for note in notes {
        hasher.update(note.as_bytes());
        hasher.update(b"\n");
    }
    format!("{:x}", hasher.finalize())
}

fn find_python_command(repo_root: &Path, resource_root: Option<&Path>) -> Option<(PathBuf, Vec<String>)> {
    if let Ok(explicit) = std::env::var("DAILYTIPS_PYTHON_EXE") {
        let explicit_path = PathBuf::from(explicit);
        if python_command_ok(&explicit_path, &[]) {
            return Some((explicit_path, Vec::new()));
        }
    }

    if let Some(runtime_root) = python_runtime_root(repo_root, resource_root) {
        let bundled_python = runtime_root.join("python.exe");
        if python_command_ok(&bundled_python, &[]) {
            return Some((bundled_python, Vec::new()));
        }
    }

    let candidates = [
        (PathBuf::from(r"D:\Applications\miniconda\python.exe"), Vec::<String>::new()),
        (PathBuf::from("python"), Vec::<String>::new()),
        (PathBuf::from("py"), vec!["-3".to_string()]),
    ];

    for (program, prefix) in candidates {
        if python_command_ok(&program, &prefix) {
            return Some((program, prefix));
        }
    }
    None
}

fn python_command_ok(program: &Path, prefix: &[String]) -> bool {
    let mut command = Command::new(program);
    for arg in prefix {
        command.arg(arg);
    }
    matches!(command.arg("--version").output(), Ok(output) if output.status.success())
}

fn resolve_repo_root(app: Option<&tauri::AppHandle>) -> Result<PathBuf, String> {
    if let Some(resource_root) = resource_root_for_app(app) {
        if resource_root.join("src").join("desktop_api.py").exists() {
            return Ok(resource_root);
        }
    }

    if let Ok(current) = std::env::current_dir() {
        if let Some(found) = find_repo_root_from(&current) {
            return Ok(found);
        }
    }

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            let sibling_resource_candidates = [
                exe_dir.join("resources"),
                exe_dir.join("Resources"),
                exe_dir.join("_up_").join("resources"),
                exe_dir.join("_up_").join("Resources"),
            ];
            for candidate in sibling_resource_candidates {
                if candidate.join("src").join("desktop_api.py").exists() {
                    return Ok(candidate);
                }
            }
            if let Some(found) = find_repo_root_from(exe_dir) {
                return Ok(found);
            }
        }
    }

    Err("Unable to locate repository root containing src/desktop_api.py".to_string())
}

fn resource_root_for_app(app: Option<&tauri::AppHandle>) -> Option<PathBuf> {
    app.and_then(|handle| handle.path().resource_dir().ok())
}

fn python_runtime_root(repo_root: &Path, resource_root: Option<&Path>) -> Option<PathBuf> {
    let mut candidates = Vec::new();
    if let Some(resource_root) = resource_root {
        candidates.push(resource_root.join("python-runtime"));
    }
    candidates.push(repo_root.join("python-runtime"));
    candidates.push(repo_root.join("src-tauri").join("resources").join("python-runtime"));

    candidates.into_iter().find(|path| path.join("python.exe").exists())
}

fn resolve_tectonic_executable(repo_root: &Path, resource_root: Option<&Path>) -> Option<PathBuf> {
    if let Ok(explicit) = std::env::var("DAILYTIPS_TECTONIC") {
        let path = PathBuf::from(explicit);
        if path.exists() {
            return Some(path);
        }
    }

    let mut candidates = Vec::new();
    if let Some(resource_root) = resource_root {
        candidates.push(resource_root.join("vendor").join("tectonic").join("tectonic.exe"));
        candidates.push(resource_root.join("vendor").join("tectonic").join("tectonic"));
    }
    candidates.push(repo_root.join("vendor").join("tectonic").join("tectonic.exe"));
    candidates.push(repo_root.join("vendor").join("tectonic").join("tectonic"));
    candidates.push(repo_root.join("src-tauri").join("resources").join("vendor").join("tectonic").join("tectonic.exe"));
    candidates.push(repo_root.join("src-tauri").join("resources").join("vendor").join("tectonic").join("tectonic"));

    candidates.into_iter().find(|path| path.exists())
}

fn find_repo_root_from(start: &Path) -> Option<PathBuf> {
    for candidate in start.ancestors() {
        if candidate.join("src").join("desktop_api.py").exists() {
            return Some(candidate.to_path_buf());
        }
    }
    None
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            get_runtime_status,
            bootstrap_app_state,
            save_app_settings,
            create_background_group,
            delete_background_group,
            delete_background_image,
            import_background_images,
            clear_background_library,
            clear_generated_outputs_in_rust,
            rebuild_cloud_image_index_in_rust,
            inspect_render_metadata_in_rust,
            scan_local_markdown,
            run_generation_pipeline,
            run_python_api,
            installation_self_check
        ])
        .run(tauri::generate_context!())
        .expect("failed to run DailyTipsApp desktop shell");
}
