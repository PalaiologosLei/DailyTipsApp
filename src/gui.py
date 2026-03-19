from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .app import AppError, run_app
from .gui_settings import load_gui_settings, save_gui_settings
from .renderer import DEFAULT_HEIGHT, DEFAULT_WIDTH, MATPLOTLIB_AVAILABLE

SETTINGS_FILE_NAME = ".gui_settings.json"

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
        "output_dir": "输出目录",
        "image_size": "图片尺寸",
        "commit_msg": "提交信息",
        "skip_git": "跳过 git add / commit / push",
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
        "source_line": "来源: {value}",
        "markdown_files": "扫描到的 Markdown 文件数: {value}",
        "items": "提取到的条目数: {value}",
        "images": "图片总数: {value}",
        "delta": "新建: {created}，更新: {updated}，未变更: {unchanged}，删除: {deleted}",
        "output_line": "输出目录: {value}",
        "git_skipped": "已跳过 Git 同步。",
        "git_done": "Git 同步完成。",
        "git_no_changes": "没有检测到 Git 变更。",
        "formula_support": "公式渲染: 已启用" if MATPLOTLIB_AVAILABLE else "公式渲染: 未安装 matplotlib，将回退为普通文本显示",
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
        "output_dir": "Output dir",
        "image_size": "Image size",
        "commit_msg": "Commit message",
        "skip_git": "Skip git add / commit / push",
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
        "source_line": "Source: {value}",
        "markdown_files": "Scanned markdown files: {value}",
        "items": "Extracted items: {value}",
        "images": "Generated images: {value}",
        "delta": "Created: {created}, Updated: {updated}, Unchanged: {unchanged}, Deleted: {deleted}",
        "output_line": "Output directory: {value}",
        "git_skipped": "Git sync skipped.",
        "git_done": "Git sync completed.",
        "git_no_changes": "No git changes detected.",
        "formula_support": "Formula rendering: enabled" if MATPLOTLIB_AVAILABLE else "Formula rendering: matplotlib not installed, plain-text fallback will be used",
    },
}


def launch_gui() -> None:
    root = tk.Tk()
    root.geometry("780x560")
    root.minsize(720, 520)

    repo_dir = Path(__file__).resolve().parent.parent
    settings_path = repo_dir / SETTINGS_FILE_NAME
    saved = load_gui_settings(settings_path)

    language = tk.StringVar(value=str(saved["language"]))
    source_mode = tk.StringVar(value=str(saved["source_mode"]))
    local_path = tk.StringVar(value=str(saved["local_path"]))
    github_url = tk.StringVar(value=str(saved["github_url"]))
    output_dir = tk.StringVar(value=str(saved["output_dir"]))
    width_var = tk.StringVar(value=str(saved["width"]))
    height_var = tk.StringVar(value=str(saved["height"]))
    commit_var = tk.StringVar(value=str(saved["commit_message"]))
    skip_git_var = tk.BooleanVar(value=bool(saved["skip_git"]))
    status_var = tk.StringVar(value=STRINGS[language.get()]["ready"])

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(8, weight=1)

    widgets: dict[str, object] = {}

    widgets["language_label"] = ttk.Label(frame)
    widgets["language_label"].grid(row=0, column=0, sticky="w")
    language_box = ttk.Combobox(frame, state="readonly", values=["中文", "English"], width=12)
    language_box.grid(row=0, column=1, sticky="w", pady=(0, 12))
    language_box.set("中文" if language.get() == "zh" else "English")

    widgets["source_label"] = ttk.Label(frame)
    widgets["source_label"].grid(row=1, column=0, sticky="w")
    source_row = ttk.Frame(frame)
    source_row.grid(row=1, column=1, sticky="ew", pady=(0, 12))
    widgets["local_radio"] = ttk.Radiobutton(source_row, value="local", variable=source_mode)
    widgets["local_radio"].pack(side="left")
    widgets["github_radio"] = ttk.Radiobutton(source_row, value="github", variable=source_mode)
    widgets["github_radio"].pack(side="left", padx=(16, 0))

    widgets["local_path_label"] = ttk.Label(frame)
    widgets["local_path_label"].grid(row=2, column=0, sticky="w")
    local_row = ttk.Frame(frame)
    local_row.grid(row=2, column=1, sticky="ew", pady=(0, 12))
    local_row.columnconfigure(0, weight=1)
    ttk.Entry(local_row, textvariable=local_path).grid(row=0, column=0, sticky="ew")
    widgets["browse_button"] = ttk.Button(local_row, command=lambda: _pick_directory(local_path))
    widgets["browse_button"].grid(row=0, column=1, padx=(8, 0))

    widgets["github_label"] = ttk.Label(frame)
    widgets["github_label"].grid(row=3, column=0, sticky="w")
    ttk.Entry(frame, textvariable=github_url).grid(row=3, column=1, sticky="ew", pady=(0, 12))

    widgets["output_label"] = ttk.Label(frame)
    widgets["output_label"].grid(row=4, column=0, sticky="w")
    ttk.Entry(frame, textvariable=output_dir).grid(row=4, column=1, sticky="ew", pady=(0, 12))

    widgets["size_label"] = ttk.Label(frame)
    widgets["size_label"].grid(row=5, column=0, sticky="w")
    size_row = ttk.Frame(frame)
    size_row.grid(row=5, column=1, sticky="w", pady=(0, 12))
    ttk.Entry(size_row, width=10, textvariable=width_var).pack(side="left")
    ttk.Label(size_row, text="x").pack(side="left", padx=8)
    ttk.Entry(size_row, width=10, textvariable=height_var).pack(side="left")

    widgets["commit_label"] = ttk.Label(frame)
    widgets["commit_label"].grid(row=6, column=0, sticky="w")
    ttk.Entry(frame, textvariable=commit_var).grid(row=6, column=1, sticky="ew", pady=(0, 12))

    widgets["skip_check"] = ttk.Checkbutton(frame, variable=skip_git_var)
    widgets["skip_check"].grid(row=7, column=1, sticky="w", pady=(0, 12))

    log_box = tk.Text(frame, height=12, wrap="word")
    log_box.grid(row=8, column=0, columnspan=2, sticky="nsew", pady=(8, 12))

    action_row = ttk.Frame(frame)
    action_row.grid(row=9, column=0, columnspan=2, sticky="ew")
    action_row.columnconfigure(0, weight=1)
    ttk.Label(action_row, textvariable=status_var).grid(row=0, column=0, sticky="w")
    widgets["run_button"] = ttk.Button(action_row)
    widgets["run_button"].grid(row=0, column=1, sticky="e")

    def tr(key: str, **kwargs: object) -> str:
        return STRINGS[language.get()][key].format(**kwargs)

    def current_settings() -> dict[str, object]:
        return {
            "language": language.get(),
            "source_mode": source_mode.get(),
            "local_path": local_path.get(),
            "github_url": github_url.get(),
            "output_dir": output_dir.get(),
            "width": width_var.get(),
            "height": height_var.get(),
            "commit_message": commit_var.get(),
            "skip_git": skip_git_var.get(),
        }

    def persist_settings() -> None:
        save_gui_settings(settings_path, current_settings())

    def apply_language() -> None:
        root.title(tr("window_title"))
        widgets["language_label"].configure(text=tr("language"))
        widgets["source_label"].configure(text=tr("source"))
        widgets["local_radio"].configure(text=tr("local_folder"))
        widgets["github_radio"].configure(text=tr("github_repo"))
        widgets["local_path_label"].configure(text=tr("local_path"))
        widgets["browse_button"].configure(text=tr("browse"))
        widgets["github_label"].configure(text=tr("github_url"))
        widgets["output_label"].configure(text=tr("output_dir"))
        widgets["size_label"].configure(text=tr("image_size"))
        widgets["commit_label"].configure(text=tr("commit_msg"))
        widgets["skip_check"].configure(text=tr("skip_git"))
        widgets["run_button"].configure(text=tr("run"))
        if status_var.get() in {STRINGS["zh"]["ready"], STRINGS["en"]["ready"]}:
            status_var.set(tr("ready"))

    def append_log(message: str) -> None:
        log_box.insert("end", message + "\n")
        log_box.see("end")
        root.update_idletasks()

    def on_language_change(_: object = None) -> None:
        language.set("zh" if language_box.get() == "中文" else "en")
        apply_language()
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
        commit_message = commit_var.get().strip() or None

        persist_settings()
        append_log(tr("formula_support"))
        append_log(tr("preparing"))

        try:
            summary = run_app(
                repo_dir=repo_dir,
                notes_dir=chosen_local if selected_mode == "local" else None,
                github_url=chosen_github if selected_mode == "github" else None,
                output_dir_arg=output_dir.get().strip() or "output/images",
                width=width,
                height=height,
                skip_git=skip_git_var.get(),
                commit_message=commit_message,
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
        append_log(
            tr(
                "delta",
                created=summary.created_count,
                updated=summary.updated_count,
                unchanged=summary.unchanged_count,
                deleted=summary.deleted_count,
            )
        )
        append_log(tr("output_line", value=summary.output_dir))
        append_log(tr("git_skipped") if skip_git_var.get() else (tr("git_done") if summary.git_pushed else tr("git_no_changes")))

        status_var.set(tr("done"))
        persist_settings()
        messagebox.showinfo(tr("completed_title"), tr("completed_message"))

    def on_close() -> None:
        persist_settings()
        root.destroy()

    widgets["run_button"].configure(command=run_clicked)
    language_box.bind("<<ComboboxSelected>>", on_language_change)
    root.protocol("WM_DELETE_WINDOW", on_close)
    apply_language()
    root.mainloop()


def _pick_directory(target: tk.StringVar) -> None:
    chosen = filedialog.askdirectory()
    if chosen:
        target.set(chosen)
