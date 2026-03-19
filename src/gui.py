from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .app import AppError, run_app
from .background_library import (
    BackgroundLibraryError,
    create_group,
    delete_background,
    delete_group,
    ensure_library_root,
    import_backgrounds,
    list_backgrounds,
    list_groups,
)
from .device_profiles import DEVICE_PROFILES, get_device_profile
from .gui_settings import load_gui_settings, save_gui_settings
from .models import BackgroundSelection, RenderConfig
from .renderer import MATPLOTLIB_AVAILABLE

SETTINGS_FILE_NAME = ".gui_settings.json"
BACKGROUND_LIBRARY_RELATIVE_DIR = Path("assets") / "backgrounds"
MODE_OPTIONS = ["white", "specific", "random_group", "random_all"]

STRINGS = {
    "zh": {
        "window_title": "DailyTipsApp",
        "language": "语言",
        "source": "来源",
        "local_folder": "本地文件夹",
        "github_repo": "GitHub 公开仓库",
        "local_path": "本地路径",
        "browse": "浏览",
        "github_url": "GitHub 地址",
        "output_dir": "项目输出目录",
        "cloud_dir": "云盘目录",
        "cloud_dir_hint": "可选 iCloud / OneDrive / Dropbox 等同步目录",
        "device_model": "iPhone 型号",
        "custom_size": "自定义尺寸",
        "image_size": "图片尺寸",
        "background_section": "背景图库",
        "background_groups": "分组",
        "background_images": "图片",
        "add_group": "新增分组",
        "delete_group": "删除分组",
        "add_images": "导入图片",
        "delete_image": "删除图片",
        "background_mode": "背景模式",
        "specific_image": "指定图片",
        "random_group": "指定分组随机",
        "random_all": "全部随机",
        "white_mode": "纯白背景",
        "run": "开始运行",
        "ready": "就绪。",
        "running": "运行中...",
        "done": "完成。",
        "failed": "失败。",
        "preparing": "正在准备笔记来源...",
        "invalid_size_title": "尺寸无效",
        "invalid_size_message": "宽度和高度必须是整数。",
        "completed_title": "执行完成",
        "completed_message": "处理完成。",
        "run_failed_title": "运行失败",
        "cloud_missing_title": "云盘目录不存在",
        "cloud_missing_message": "所选云盘目录不存在，是否立即创建？",
        "cloud_create_failed": "创建云盘目录失败。",
        "source_line": "来源: {value}",
        "markdown_files": "扫描到的 Markdown 文件数: {value}",
        "items": "提取到的条目数: {value}",
        "images": "图片总数: {value}",
        "delta": "新建: {created}，更新: {updated}，未变更: {unchanged}，删除: {deleted}",
        "output_line": "项目输出目录: {value}",
        "cloud_line": "云盘目录: {value}",
        "cloud_sync": "云盘复制: 已复制 {copied}，已删除 {deleted}",
        "cloud_skipped": "未设置云盘目录，已跳过复制。",
        "formula_support": "公式渲染: 已启用" if MATPLOTLIB_AVAILABLE else "公式渲染: 未安装 matplotlib，将回退为普通文本显示",
        "group_name_prompt": "输入新分组名称",
        "group_name_title": "新增分组",
        "no_group_selected": "请先选择一个分组。",
        "confirm_delete_group": "确定删除分组“{name}”及其全部图片吗？",
        "confirm_delete_image": "确定删除图片“{name}”吗？",
        "library_error": "背景图库操作失败",
        "background_mode_prompt": "背景模式",
        "no_image_available": "暂无图片",
        "no_group_available": "暂无分组",
    },
    "en": {
        "window_title": "DailyTipsApp",
        "language": "Language",
        "source": "Source",
        "local_folder": "Local folder",
        "github_repo": "GitHub public repo",
        "local_path": "Local path",
        "browse": "Browse",
        "github_url": "GitHub URL",
        "output_dir": "Project output dir",
        "cloud_dir": "Cloud dir",
        "cloud_dir_hint": "Optional iCloud / OneDrive / Dropbox synced folder",
        "device_model": "iPhone model",
        "custom_size": "Custom size",
        "image_size": "Image size",
        "background_section": "Background library",
        "background_groups": "Groups",
        "background_images": "Images",
        "add_group": "Add group",
        "delete_group": "Delete group",
        "add_images": "Import images",
        "delete_image": "Delete image",
        "background_mode": "Background mode",
        "specific_image": "Specific image",
        "random_group": "Random from group",
        "random_all": "Random from all",
        "white_mode": "White background",
        "run": "Run",
        "ready": "Ready.",
        "running": "Running...",
        "done": "Done.",
        "failed": "Failed.",
        "preparing": "Preparing notes source...",
        "invalid_size_title": "Invalid size",
        "invalid_size_message": "Width and height must be integers.",
        "completed_title": "Completed",
        "completed_message": "Processing finished.",
        "run_failed_title": "Run failed",
        "cloud_missing_title": "Cloud directory missing",
        "cloud_missing_message": "The selected cloud directory does not exist. Create it now?",
        "cloud_create_failed": "Failed to create cloud directory.",
        "source_line": "Source: {value}",
        "markdown_files": "Scanned markdown files: {value}",
        "items": "Extracted items: {value}",
        "images": "Generated images: {value}",
        "delta": "Created: {created}, Updated: {updated}, Unchanged: {unchanged}, Deleted: {deleted}",
        "output_line": "Project output dir: {value}",
        "cloud_line": "Cloud dir: {value}",
        "cloud_sync": "Cloud copy: copied {copied}, deleted {deleted}",
        "cloud_skipped": "Cloud directory not set, copy skipped.",
        "formula_support": "Formula rendering: enabled" if MATPLOTLIB_AVAILABLE else "Formula rendering: matplotlib not installed, plain-text fallback will be used",
        "group_name_prompt": "Enter a new group name",
        "group_name_title": "Add group",
        "no_group_selected": "Please select a group first.",
        "confirm_delete_group": "Delete group '{name}' and all its images?",
        "confirm_delete_image": "Delete image '{name}'?",
        "library_error": "Background library action failed",
        "background_mode_prompt": "Background mode",
        "no_image_available": "No images",
        "no_group_available": "No groups",
    },
}


def launch_gui() -> None:
    root = tk.Tk()
    root.geometry("1100x860")
    root.minsize(980, 760)

    repo_dir = Path(__file__).resolve().parent.parent
    background_library_dir = repo_dir / BACKGROUND_LIBRARY_RELATIVE_DIR
    ensure_library_root(background_library_dir)
    settings_path = repo_dir / SETTINGS_FILE_NAME
    saved = load_gui_settings(settings_path)

    language = tk.StringVar(value=str(saved["language"]))
    source_mode = tk.StringVar(value=str(saved["source_mode"]))
    local_path = tk.StringVar(value=str(saved["local_path"]))
    github_url = tk.StringVar(value=str(saved["github_url"]))
    output_dir = tk.StringVar(value=str(saved["output_dir"]))
    cloud_dir = tk.StringVar(value=str(saved["cloud_dir"]))
    device_model = tk.StringVar(value=str(saved["device_model"]))
    width_var = tk.StringVar(value=str(saved["width"]))
    height_var = tk.StringVar(value=str(saved["height"]))
    background_mode = tk.StringVar(value=str(saved["background_mode"]))
    background_group = tk.StringVar(value=str(saved["background_group"]))
    background_image_id = tk.StringVar(value=str(saved["background_image_id"]))
    status_var = tk.StringVar(value=STRINGS[language.get()]["ready"])

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=3)
    frame.columnconfigure(1, weight=2)
    frame.rowconfigure(1, weight=1)
    frame.rowconfigure(2, weight=1)

    widgets: dict[str, object] = {}

    top = ttk.Frame(frame)
    top.grid(row=0, column=0, columnspan=2, sticky="ew")
    top.columnconfigure(1, weight=1)
    top.columnconfigure(3, weight=1)

    widgets["language_label"] = ttk.Label(top)
    widgets["language_label"].grid(row=0, column=0, sticky="w")
    language_box = ttk.Combobox(top, state="readonly", values=["中文", "English"], width=12)
    language_box.grid(row=0, column=1, sticky="w", padx=(8, 24), pady=(0, 12))
    language_box.set("中文" if language.get() == "zh" else "English")

    widgets["device_label"] = ttk.Label(top)
    widgets["device_label"].grid(row=0, column=2, sticky="w")
    device_box = ttk.Combobox(top, state="readonly", width=28)
    device_box.grid(row=0, column=3, sticky="w", padx=(8, 0), pady=(0, 12))

    left = ttk.LabelFrame(frame, padding=12)
    left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
    left.columnconfigure(1, weight=1)
    left.rowconfigure(8, weight=1)

    widgets["source_label"] = ttk.Label(left)
    widgets["source_label"].grid(row=0, column=0, sticky="w")
    source_row = ttk.Frame(left)
    source_row.grid(row=0, column=1, sticky="ew", pady=(0, 12))
    widgets["local_radio"] = ttk.Radiobutton(source_row, value="local", variable=source_mode)
    widgets["local_radio"].pack(side="left")
    widgets["github_radio"] = ttk.Radiobutton(source_row, value="github", variable=source_mode)
    widgets["github_radio"].pack(side="left", padx=(16, 0))

    widgets["local_path_label"] = ttk.Label(left)
    widgets["local_path_label"].grid(row=1, column=0, sticky="w")
    local_row = ttk.Frame(left)
    local_row.grid(row=1, column=1, sticky="ew", pady=(0, 12))
    local_row.columnconfigure(0, weight=1)
    ttk.Entry(local_row, textvariable=local_path).grid(row=0, column=0, sticky="ew")
    widgets["browse_local_button"] = ttk.Button(local_row, command=lambda: _pick_directory(local_path))
    widgets["browse_local_button"].grid(row=0, column=1, padx=(8, 0))

    widgets["github_label"] = ttk.Label(left)
    widgets["github_label"].grid(row=2, column=0, sticky="w")
    ttk.Entry(left, textvariable=github_url).grid(row=2, column=1, sticky="ew", pady=(0, 12))

    widgets["output_label"] = ttk.Label(left)
    widgets["output_label"].grid(row=3, column=0, sticky="w")
    ttk.Entry(left, textvariable=output_dir).grid(row=3, column=1, sticky="ew", pady=(0, 12))

    widgets["cloud_label"] = ttk.Label(left)
    widgets["cloud_label"].grid(row=4, column=0, sticky="w")
    cloud_row = ttk.Frame(left)
    cloud_row.grid(row=4, column=1, sticky="ew", pady=(0, 4))
    cloud_row.columnconfigure(0, weight=1)
    ttk.Entry(cloud_row, textvariable=cloud_dir).grid(row=0, column=0, sticky="ew")
    widgets["browse_cloud_button"] = ttk.Button(cloud_row, command=lambda: _pick_directory(cloud_dir))
    widgets["browse_cloud_button"].grid(row=0, column=1, padx=(8, 0))
    widgets["cloud_hint_label"] = ttk.Label(left)
    widgets["cloud_hint_label"].grid(row=5, column=1, sticky="w", pady=(0, 12))

    widgets["size_label"] = ttk.Label(left)
    widgets["size_label"].grid(row=6, column=0, sticky="w")
    size_row = ttk.Frame(left)
    size_row.grid(row=6, column=1, sticky="w", pady=(0, 12))
    ttk.Entry(size_row, width=10, textvariable=width_var).pack(side="left")
    ttk.Label(size_row, text="x").pack(side="left", padx=8)
    ttk.Entry(size_row, width=10, textvariable=height_var).pack(side="left")

    widgets["bg_mode_label"] = ttk.Label(left)
    widgets["bg_mode_label"].grid(row=7, column=0, sticky="w")
    bg_mode_box = ttk.Combobox(left, state="readonly")
    bg_mode_box.grid(row=7, column=1, sticky="ew", pady=(0, 12))

    widgets["specific_image_label"] = ttk.Label(left)
    widgets["specific_image_label"].grid(row=8, column=0, sticky="nw")
    selection_frame = ttk.Frame(left)
    selection_frame.grid(row=8, column=1, sticky="nsew")
    selection_frame.columnconfigure(0, weight=1)
    image_choice_box = ttk.Combobox(selection_frame, state="readonly")
    image_choice_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    group_choice_box = ttk.Combobox(selection_frame, state="readonly")
    group_choice_box.grid(row=1, column=0, sticky="ew")

    right = ttk.LabelFrame(frame, padding=12)
    right.grid(row=1, column=1, rowspan=2, sticky="nsew")
    right.columnconfigure(0, weight=1)
    right.columnconfigure(1, weight=1)
    right.rowconfigure(1, weight=1)

    widgets["library_label"] = ttk.Label(right)
    widgets["library_label"].grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    widgets["groups_label"] = ttk.Label(right)
    widgets["groups_label"].grid(row=1, column=0, sticky="nw")
    widgets["images_label"] = ttk.Label(right)
    widgets["images_label"].grid(row=1, column=1, sticky="nw")

    group_list = tk.Listbox(right, exportselection=False, height=14)
    group_list.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
    image_list = tk.Listbox(right, exportselection=False, height=14)
    image_list.grid(row=2, column=1, sticky="nsew")
    right.rowconfigure(2, weight=1)

    group_button_row = ttk.Frame(right)
    group_button_row.grid(row=3, column=0, sticky="ew", pady=(8, 0), padx=(0, 8))
    widgets["add_group_button"] = ttk.Button(group_button_row)
    widgets["add_group_button"].pack(side="left")
    widgets["delete_group_button"] = ttk.Button(group_button_row)
    widgets["delete_group_button"].pack(side="left", padx=(8, 0))

    image_button_row = ttk.Frame(right)
    image_button_row.grid(row=3, column=1, sticky="ew", pady=(8, 0))
    widgets["add_images_button"] = ttk.Button(image_button_row)
    widgets["add_images_button"].pack(side="left")
    widgets["delete_image_button"] = ttk.Button(image_button_row)
    widgets["delete_image_button"].pack(side="left", padx=(8, 0))

    bottom = ttk.Frame(frame)
    bottom.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
    bottom.columnconfigure(0, weight=1)
    bottom.rowconfigure(0, weight=1)
    log_box = tk.Text(bottom, height=12, wrap="word")
    log_box.grid(row=0, column=0, sticky="nsew", pady=(8, 12))
    action_row = ttk.Frame(bottom)
    action_row.grid(row=1, column=0, sticky="ew")
    action_row.columnconfigure(0, weight=1)
    ttk.Label(action_row, textvariable=status_var).grid(row=0, column=0, sticky="w")
    widgets["run_button"] = ttk.Button(action_row)
    widgets["run_button"].grid(row=0, column=1, sticky="e")

    device_label_to_key = {profile.label: profile.key for profile in DEVICE_PROFILES}
    device_box["values"] = [profile.label for profile in DEVICE_PROFILES]
    current_device = get_device_profile(device_model.get())
    device_box.set(current_device.label)

    def tr(key: str, **kwargs: object) -> str:
        return STRINGS[language.get()][key].format(**kwargs)

    def mode_label(mode: str) -> str:
        mapping = {
            "white": tr("white_mode"),
            "specific": tr("specific_image"),
            "random_group": tr("random_group"),
            "random_all": tr("random_all"),
        }
        return mapping[mode]

    def mode_from_label(label: str) -> str:
        for mode in MODE_OPTIONS:
            if mode_label(mode) == label:
                return mode
        return "white"

    def current_settings() -> dict[str, object]:
        return {
            "language": language.get(),
            "source_mode": source_mode.get(),
            "local_path": local_path.get(),
            "github_url": github_url.get(),
            "output_dir": output_dir.get(),
            "cloud_dir": cloud_dir.get(),
            "device_model": device_model.get(),
            "width": width_var.get(),
            "height": height_var.get(),
            "background_mode": background_mode.get(),
            "background_group": background_group.get(),
            "background_image_id": background_image_id.get(),
        }

    def persist_settings() -> None:
        save_gui_settings(settings_path, current_settings())

    def append_log(message: str) -> None:
        log_box.insert("end", message + "\n")
        log_box.see("end")
        root.update_idletasks()

    def refresh_group_list() -> None:
        groups = list_groups(background_library_dir)
        group_list.delete(0, "end")
        for group_name in groups:
            group_list.insert("end", group_name)
        if groups:
            if background_group.get() not in groups:
                background_group.set(groups[0])
            try:
                index = groups.index(background_group.get())
                group_list.selection_clear(0, "end")
                group_list.selection_set(index)
            except ValueError:
                pass
        else:
            background_group.set("")
        refresh_image_list()
        refresh_background_choices()

    def refresh_image_list() -> None:
        image_list.delete(0, "end")
        group_name = background_group.get()
        images = list_backgrounds(background_library_dir, group_name if group_name else None)
        names = []
        for image in images:
            names.append(image.id)
            image_list.insert("end", image.name)
        if names:
            if background_image_id.get() not in names:
                background_image_id.set(names[0])
            try:
                index = names.index(background_image_id.get())
                image_list.selection_clear(0, "end")
                image_list.selection_set(index)
            except ValueError:
                pass
        else:
            background_image_id.set("")
        refresh_background_choices()

    def refresh_background_choices() -> None:
        groups = list_groups(background_library_dir)
        images = list_backgrounds(background_library_dir)
        group_choice_box["values"] = groups if groups else [tr("no_group_available")]
        image_choice_box["values"] = [image.id for image in images] if images else [tr("no_image_available")]
        if groups:
            if background_group.get() not in groups:
                background_group.set(groups[0])
            group_choice_box.set(background_group.get())
        else:
            group_choice_box.set(tr("no_group_available"))
        if images:
            image_ids = [image.id for image in images]
            if background_image_id.get() not in image_ids:
                background_image_id.set(image_ids[0])
            image_choice_box.set(background_image_id.get())
        else:
            image_choice_box.set(tr("no_image_available"))

    def sync_device_fields() -> None:
        profile = get_device_profile(device_model.get())
        is_custom = profile.key == "custom"
        if not is_custom:
            width_var.set(str(profile.width))
            height_var.set(str(profile.height))
        state = "normal" if is_custom else "disabled"
        for child in size_row.winfo_children():
            if isinstance(child, ttk.Entry):
                child.configure(state=state)

    def apply_language() -> None:
        root.title(tr("window_title"))
        widgets["language_label"].configure(text=tr("language"))
        widgets["device_label"].configure(text=tr("device_model"))
        widgets["source_label"].configure(text=tr("source"))
        widgets["local_radio"].configure(text=tr("local_folder"))
        widgets["github_radio"].configure(text=tr("github_repo"))
        widgets["local_path_label"].configure(text=tr("local_path"))
        widgets["browse_local_button"].configure(text=tr("browse"))
        widgets["github_label"].configure(text=tr("github_url"))
        widgets["output_label"].configure(text=tr("output_dir"))
        widgets["cloud_label"].configure(text=tr("cloud_dir"))
        widgets["browse_cloud_button"].configure(text=tr("browse"))
        widgets["cloud_hint_label"].configure(text=tr("cloud_dir_hint"))
        widgets["size_label"].configure(text=tr("image_size"))
        widgets["bg_mode_label"].configure(text=tr("background_mode"))
        widgets["specific_image_label"].configure(text=tr("specific_image"))
        widgets["library_label"].configure(text=tr("background_section"))
        widgets["groups_label"].configure(text=tr("background_groups"))
        widgets["images_label"].configure(text=tr("background_images"))
        widgets["add_group_button"].configure(text=tr("add_group"))
        widgets["delete_group_button"].configure(text=tr("delete_group"))
        widgets["add_images_button"].configure(text=tr("add_images"))
        widgets["delete_image_button"].configure(text=tr("delete_image"))
        widgets["run_button"].configure(text=tr("run"))
        bg_mode_box["values"] = [mode_label(mode) for mode in MODE_OPTIONS]
        bg_mode_box.set(mode_label(background_mode.get()))
        if status_var.get() in {STRINGS["zh"]["ready"], STRINGS["en"]["ready"]}:
            status_var.set(tr("ready"))
        refresh_background_choices()

    def ensure_cloud_dir_exists() -> Path | None:
        raw = cloud_dir.get().strip()
        if not raw:
            return None
        chosen_cloud_dir = Path(raw).expanduser()
        if chosen_cloud_dir.exists():
            return chosen_cloud_dir
        if messagebox.askyesno(tr("cloud_missing_title"), tr("cloud_missing_message")):
            try:
                chosen_cloud_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                messagebox.showerror(tr("cloud_missing_title"), tr("cloud_create_failed"))
                return None
            return chosen_cloud_dir
        return None

    def handle_add_group() -> None:
        name = simpledialog.askstring(tr("group_name_title"), tr("group_name_prompt"), parent=root)
        if not name:
            return
        try:
            group_path = create_group(background_library_dir, name)
        except BackgroundLibraryError as error:
            messagebox.showerror(tr("library_error"), str(error))
            return
        background_group.set(group_path.name)
        refresh_group_list()
        persist_settings()

    def handle_delete_group() -> None:
        selected = _selected_group_name(group_list)
        if not selected:
            messagebox.showinfo(tr("background_section"), tr("no_group_selected"))
            return
        if not messagebox.askyesno(tr("delete_group"), tr("confirm_delete_group", name=selected)):
            return
        delete_group(background_library_dir, selected)
        refresh_group_list()
        persist_settings()

    def handle_add_images() -> None:
        target_group = background_group.get() or _selected_group_name(group_list)
        if not target_group:
            messagebox.showinfo(tr("background_section"), tr("no_group_selected"))
            return
        paths = filedialog.askopenfilenames(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if not paths:
            return
        try:
            import_backgrounds(background_library_dir, target_group, [Path(path) for path in paths])
        except BackgroundLibraryError as error:
            messagebox.showerror(tr("library_error"), str(error))
            return
        refresh_group_list()
        persist_settings()

    def handle_delete_image() -> None:
        selected_id = background_image_id.get()
        if not selected_id:
            return
        name = selected_id.split("/", 1)[-1]
        if not messagebox.askyesno(tr("delete_image"), tr("confirm_delete_image", name=name)):
            return
        delete_background(background_library_dir, selected_id)
        refresh_group_list()
        persist_settings()

    def on_group_select(_: object = None) -> None:
        selected = _selected_group_name(group_list)
        if selected:
            background_group.set(selected)
            refresh_image_list()
            persist_settings()

    def on_image_select(_: object = None) -> None:
        selected = _selected_image_id(image_list, background_group.get(), background_library_dir)
        if selected:
            background_image_id.set(selected)
            image_choice_box.set(selected)
            persist_settings()

    def on_device_change(_: object = None) -> None:
        device_model.set(device_label_to_key.get(device_box.get(), "iphone_15_pro"))
        sync_device_fields()
        persist_settings()

    def on_mode_change(_: object = None) -> None:
        background_mode.set(mode_from_label(bg_mode_box.get()))
        persist_settings()

    def on_language_change(_: object = None) -> None:
        language.set("zh" if language_box.get() == "中文" else "en")
        apply_language()
        persist_settings()

    def on_group_choice_change(_: object = None) -> None:
        value = group_choice_box.get()
        if value and value != tr("no_group_available"):
            background_group.set(value)
            refresh_group_list()
            persist_settings()

    def on_image_choice_change(_: object = None) -> None:
        value = image_choice_box.get()
        if value and value != tr("no_image_available"):
            background_image_id.set(value)
            persist_settings()

    def run_clicked() -> None:
        log_box.delete("1.0", "end")
        status_var.set(tr("running"))

        try:
            width = int(width_var.get().strip())
            height = int(height_var.get().strip())
        except ValueError:
            messagebox.showerror(tr("invalid_size_title"), tr("invalid_size_message"))
            status_var.set(tr("ready"))
            return

        selected_mode = source_mode.get()
        chosen_local = Path(local_path.get().strip()).expanduser().resolve() if local_path.get().strip() else None
        chosen_github = github_url.get().strip() or None
        chosen_cloud_dir = ensure_cloud_dir_exists()
        if cloud_dir.get().strip() and chosen_cloud_dir is None:
            status_var.set(tr("ready"))
            return

        render_config = RenderConfig(
            width=width,
            height=height,
            background_selection=BackgroundSelection(
                mode=background_mode.get(),
                image_id=background_image_id.get(),
                group_name=background_group.get(),
            ),
            background_library_dir=background_library_dir,
        )

        persist_settings()
        append_log(tr("formula_support"))
        append_log(tr("preparing"))

        try:
            summary = run_app(
                repo_dir=repo_dir,
                notes_dir=chosen_local if selected_mode == "local" else None,
                github_url=chosen_github if selected_mode == "github" else None,
                output_dir_arg=output_dir.get().strip() or "output/images",
                cloud_dir=chosen_cloud_dir,
                render_config=render_config,
            )
        except AppError as error:
            append_log(str(error))
            messagebox.showerror(tr("run_failed_title"), str(error))
            status_var.set(tr("failed"))
            return

        append_log(tr("source_line", value=summary.source_description))
        append_log(tr("markdown_files", value=summary.markdown_file_count))
        append_log(tr("items", value=summary.item_count))
        append_log(tr("images", value=summary.image_count))
        append_log(tr("delta", created=summary.created_count, updated=summary.updated_count, unchanged=summary.unchanged_count, deleted=summary.deleted_count))
        append_log(tr("output_line", value=summary.output_dir))
        if summary.cloud_dir is not None:
            append_log(tr("cloud_line", value=summary.cloud_dir))
            append_log(tr("cloud_sync", copied=summary.cloud_copied_count, deleted=summary.cloud_deleted_count))
        else:
            append_log(tr("cloud_skipped"))

        status_var.set(tr("done"))
        persist_settings()
        messagebox.showinfo(tr("completed_title"), tr("completed_message"))

    def on_close() -> None:
        persist_settings()
        root.destroy()

    widgets["add_group_button"].configure(command=handle_add_group)
    widgets["delete_group_button"].configure(command=handle_delete_group)
    widgets["add_images_button"].configure(command=handle_add_images)
    widgets["delete_image_button"].configure(command=handle_delete_image)
    widgets["run_button"].configure(command=run_clicked)

    language_box.bind("<<ComboboxSelected>>", on_language_change)
    device_box.bind("<<ComboboxSelected>>", on_device_change)
    bg_mode_box.bind("<<ComboboxSelected>>", on_mode_change)
    group_choice_box.bind("<<ComboboxSelected>>", on_group_choice_change)
    image_choice_box.bind("<<ComboboxSelected>>", on_image_choice_change)
    group_list.bind("<<ListboxSelect>>", on_group_select)
    image_list.bind("<<ListboxSelect>>", on_image_select)

    sync_device_fields()
    refresh_group_list()
    apply_language()
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def _pick_directory(target: tk.StringVar) -> None:
    chosen = filedialog.askdirectory()
    if chosen:
        target.set(chosen)


def _selected_group_name(group_list: tk.Listbox) -> str:
    selection = group_list.curselection()
    if not selection:
        return ""
    return str(group_list.get(selection[0]))


def _selected_image_id(image_list: tk.Listbox, group_name: str, library_root: Path) -> str:
    selection = image_list.curselection()
    if not selection:
        return ""
    index = selection[0]
    images = list_backgrounds(library_root, group_name if group_name else None)
    if 0 <= index < len(images):
        return images[index].id
    return ""
