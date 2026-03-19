from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from .app import AppError, reset_formula_memory_and_backgrounds, run_app
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
from .renderer import MATPLOTLIB_AVAILABLE, MATH_FONT_CHOICES, TEXT_FONT_CHOICES

SETTINGS_FILE_NAME = ".gui_settings.json"
BACKGROUND_LIBRARY_RELATIVE_DIR = Path("assets") / "backgrounds"
MODE_OPTIONS = ["white", "specific", "random_group", "random_all"]
SURFACE = "#f5f7fb"
CARD = "#ffffff"
TEXT = "#0f172a"
MUTED = "#475569"
BORDER = "#dbe4f0"
ACCENT = "#2563eb"
ACCENT_TEXT = "#ffffff"
DANGER = "#dc2626"
DANGER_TEXT = "#ffffff"

STRINGS = {
    "zh": {
        "window_title": "DailyTipsApp",
        "language": "??",
        "source": "??",
        "local_folder": "?????",
        "github_repo": "GitHub ????",
        "local_path": "????",
        "browse": "??",
        "github_url": "GitHub ??",
        "output_dir": "??????",
        "cloud_dir": "??????",
        "cloud_dir_hint": "????? PNG ???????????????",
        "device_model": "iPhone ??",
        "custom_size": "?????",
        "image_size": "????",
        "background_section": "????",
        "background_groups": "??",
        "background_images": "??",
        "add_group": "????",
        "delete_group": "????",
        "add_images": "????",
        "delete_image": "????",
        "clear_all": "???????",
        "background_mode": "????",
        "specific_image": "????",
        "random_group": "??????",
        "random_all": "????",
        "white_mode": "????",
        "style_section": "????",
        "text_font": "????",
        "formula_font": "????",
        "text_color": "????",
        "formula_color": "????",
        "show_panel": "???????",
        "pick_color": "????",
        "run": "????",
        "ready": "???",
        "running": "???...",
        "done": "???",
        "failed": "???",
        "preparing": "????????...",
        "invalid_size_title": "????",
        "invalid_size_message": "???????????",
        "completed_title": "????",
        "completed_message": "?????",
        "run_failed_title": "????",
        "cloud_missing_title": "???????",
        "cloud_missing_message": "?????????????????",
        "cloud_create_failed": "?????????",
        "reset_confirm_title": "????",
        "reset_confirm_message": "??????????????????????????????????",
        "reset_result": "???????? {metadata} ????????? {cloud} ??????????? {index} ???????? {backgrounds} ??",
        "reset_done": "????",
        "source_line": "??: {value}",
        "markdown_files": "???? Markdown ???: {value}",
        "items": "???????: {value}",
        "images": "????: {value}",
        "delta": "??: {created}???: {updated}????: {unchanged}???: {deleted}",
        "output_line": "??????: {value}",
        "cloud_line": "??????: {value}",
        "cloud_sync": "??????: {value}",
        "cloud_skipped": "???????????",
        "formula_support": "????: ???" if MATPLOTLIB_AVAILABLE else "????: ??? matplotlib???????????",
        "group_name_prompt": "???????",
        "group_name_title": "????",
        "no_group_selected": "?????????",
        "confirm_delete_group": "???????{name}?????????",
        "confirm_delete_image": "???????{name}???",
        "library_error": "????????",
        "background_mode_prompt": "????",
        "no_image_available": "????",
        "no_group_available": "????",
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
        "output_dir": "App data dir",
        "cloud_dir": "Cloud image dir",
        "cloud_dir_hint": "Required. Final PNG files and the image index file will be written here directly",
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
        "clear_all": "Clear cache and library",
        "background_mode": "Background mode",
        "specific_image": "Specific image",
        "random_group": "Random from group",
        "random_all": "Random from all",
        "white_mode": "White background",
        "style_section": "Render style",
        "text_font": "Text font",
        "formula_font": "Formula font",
        "text_color": "Text color",
        "formula_color": "Formula color",
        "show_panel": "Keep translucent card",
        "pick_color": "Pick color",
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
        "reset_confirm_title": "Confirm clear",
        "reset_confirm_message": "This removes generated images, formula cache records, and user background images. Continue?",
        "reset_result": "Removed {metadata} local metadata files, {cloud} cloud images, {index} image index files, and {backgrounds} background images.",
        "reset_done": "Cleared.",
        "source_line": "Source: {value}",
        "markdown_files": "Scanned markdown files: {value}",
        "items": "Extracted items: {value}",
        "images": "Generated images: {value}",
        "delta": "Created: {created}, Updated: {updated}, Unchanged: {unchanged}, Deleted: {deleted}",
        "output_line": "App data dir: {value}",
        "cloud_line": "Cloud image dir: {value}",
        "cloud_sync": "Image index file: {value}",
        "cloud_skipped": "Cloud directory is not set.",
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
    _apply_styles(root)
    root.configure(bg=SURFACE)

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
    show_content_panel = tk.BooleanVar(value=bool(saved["show_content_panel"]))
    text_font_family = tk.StringVar(value=str(saved["text_font_family"]))
    math_font_family = tk.StringVar(value=str(saved["math_font_family"]))
    text_color = tk.StringVar(value=str(saved["text_color"]))
    math_color = tk.StringVar(value=str(saved["math_color"]))
    status_var = tk.StringVar(value=STRINGS[language.get()]["ready"])

    frame = ttk.Frame(root, padding=16, style="App.TFrame")
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(0, weight=3)
    frame.columnconfigure(1, weight=2)
    frame.rowconfigure(1, weight=1)
    frame.rowconfigure(2, weight=1)

    widgets: dict[str, object] = {}

    top = ttk.Frame(frame, style="App.TFrame")
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
    left.rowconfigure(9, weight=1)

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
    widgets["browse_local_button"] = ttk.Button(local_row, style="Ghost.TButton", command=lambda: _pick_directory(local_path))
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
    widgets["browse_cloud_button"] = ttk.Button(cloud_row, style="Ghost.TButton", command=lambda: _pick_directory(cloud_dir))
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

    style_frame = ttk.LabelFrame(left, padding=12)
    style_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(16, 0))
    style_frame.columnconfigure(1, weight=1)
    style_frame.columnconfigure(3, weight=1)
    widgets["style_frame"] = style_frame

    widgets["text_font_label"] = ttk.Label(style_frame)
    widgets["text_font_label"].grid(row=0, column=0, sticky="w")
    text_font_box = ttk.Combobox(style_frame, state="readonly", width=22)
    text_font_box.grid(row=0, column=1, sticky="ew", padx=(8, 16), pady=(0, 10))

    widgets["math_font_label"] = ttk.Label(style_frame)
    widgets["math_font_label"].grid(row=0, column=2, sticky="w")
    math_font_box = ttk.Combobox(style_frame, state="readonly", width=22)
    math_font_box.grid(row=0, column=3, sticky="ew", padx=(8, 0), pady=(0, 10))

    widgets["text_color_label"] = ttk.Label(style_frame)
    widgets["text_color_label"].grid(row=1, column=0, sticky="w")
    text_color_row = ttk.Frame(style_frame, style="App.TFrame")
    text_color_row.grid(row=1, column=1, sticky="w", padx=(8, 16), pady=(0, 10))
    widgets["text_color_button"] = ttk.Button(text_color_row, style="Ghost.TButton")
    widgets["text_color_button"].pack(side="left")
    text_color_preview = tk.Label(text_color_row, width=10, relief="solid", bd=1, bg=text_color.get())
    text_color_preview.pack(side="left", padx=(8, 0))

    widgets["math_color_label"] = ttk.Label(style_frame)
    widgets["math_color_label"].grid(row=1, column=2, sticky="w")
    math_color_row = ttk.Frame(style_frame, style="App.TFrame")
    math_color_row.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(0, 10))
    widgets["math_color_button"] = ttk.Button(math_color_row, style="Ghost.TButton")
    widgets["math_color_button"].pack(side="left")
    math_color_preview = tk.Label(math_color_row, width=10, relief="solid", bd=1, bg=math_color.get())
    math_color_preview.pack(side="left", padx=(8, 0))

    widgets["panel_check"] = ttk.Checkbutton(style_frame, variable=show_content_panel)
    widgets["panel_check"].grid(row=2, column=0, columnspan=4, sticky="w")

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

    group_button_row = ttk.Frame(right, style="App.TFrame")
    group_button_row.grid(row=3, column=0, sticky="ew", pady=(8, 0), padx=(0, 8))
    widgets["add_group_button"] = ttk.Button(group_button_row, style="Ghost.TButton")
    widgets["add_group_button"].pack(side="left")
    widgets["delete_group_button"] = ttk.Button(group_button_row, style="Danger.TButton")
    widgets["delete_group_button"].pack(side="left", padx=(8, 0))

    image_button_row = ttk.Frame(right, style="App.TFrame")
    image_button_row.grid(row=3, column=1, sticky="ew", pady=(8, 0))
    widgets["add_images_button"] = ttk.Button(image_button_row, style="Ghost.TButton")
    widgets["add_images_button"].pack(side="left")
    widgets["delete_image_button"] = ttk.Button(image_button_row, style="Danger.TButton")
    widgets["delete_image_button"].pack(side="left", padx=(8, 0))

    bottom = ttk.Frame(frame, style="App.TFrame")
    bottom.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
    bottom.columnconfigure(0, weight=1)
    bottom.rowconfigure(0, weight=1)
    log_box = tk.Text(bottom, height=12, wrap="word", bg=CARD, fg=TEXT, relief="flat", highlightthickness=1, highlightbackground=BORDER)
    log_box.grid(row=0, column=0, sticky="nsew", pady=(8, 12))
    action_row = ttk.Frame(bottom, style="App.TFrame")
    action_row.grid(row=1, column=0, sticky="ew")
    action_row.columnconfigure(0, weight=1)
    ttk.Label(action_row, textvariable=status_var, style="Subtle.TLabel").grid(row=0, column=0, sticky="w")
    widgets["clear_button"] = ttk.Button(action_row, style="Danger.TButton")
    widgets["clear_button"].grid(row=0, column=1, sticky="e", padx=(0, 8))
    widgets["run_button"] = ttk.Button(action_row, style="Primary.TButton")
    widgets["run_button"].grid(row=0, column=2, sticky="e")

    device_label_to_key = {profile.label: profile.key for profile in DEVICE_PROFILES}
    device_box["values"] = [profile.label for profile in DEVICE_PROFILES]
    current_device = get_device_profile(device_model.get())
    device_box.set(current_device.label)
    text_font_key_to_label = {key: label for label, key in TEXT_FONT_CHOICES}
    text_font_label_to_key = {label: key for label, key in TEXT_FONT_CHOICES}
    math_font_key_to_label = {key: label for label, key in MATH_FONT_CHOICES}
    math_font_label_to_key = {label: key for label, key in MATH_FONT_CHOICES}
    text_font_box["values"] = [label for label, _ in TEXT_FONT_CHOICES]
    math_font_box["values"] = [label for label, _ in MATH_FONT_CHOICES]
    text_font_box.set(text_font_key_to_label.get(text_font_family.get(), TEXT_FONT_CHOICES[0][0]))
    math_font_box.set(math_font_key_to_label.get(math_font_family.get(), MATH_FONT_CHOICES[0][0]))

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

    def update_color_preview(widget: tk.Label, color_value: str) -> None:
        try:
            widget.configure(bg=color_value)
        except tk.TclError:
            widget.configure(bg="#000000")

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
        widgets["clear_button"].configure(text=tr("clear_all"))
        widgets["run_button"].configure(text=tr("run"))
        widgets["style_frame"].configure(text=tr("style_section"))
        widgets["text_font_label"].configure(text=tr("text_font"))
        widgets["math_font_label"].configure(text=tr("formula_font"))
        widgets["text_color_label"].configure(text=tr("text_color"))
        widgets["math_color_label"].configure(text=tr("formula_color"))
        widgets["text_color_button"].configure(text=tr("pick_color"))
        widgets["math_color_button"].configure(text=tr("pick_color"))
        widgets["panel_check"].configure(text=tr("show_panel"))
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

    def choose_color(target: tk.StringVar, preview: tk.Label) -> None:
        selected = colorchooser.askcolor(color=target.get(), parent=root)[1]
        if selected:
            target.set(selected)
            update_color_preview(preview, selected)
            persist_settings()

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

    def handle_clear_all() -> None:
        if not messagebox.askyesno(tr("reset_confirm_title"), tr("reset_confirm_message")):
            return
        chosen_cloud_dir = Path(cloud_dir.get().strip()).expanduser() if cloud_dir.get().strip() else None
        summary = reset_formula_memory_and_backgrounds(
            repo_dir=repo_dir,
            output_dir_arg=output_dir.get().strip() or ".dailytipsapp",
            cloud_dir=chosen_cloud_dir,
            background_library_dir=background_library_dir,
        )
        refresh_group_list()
        append_log(tr("reset_result", metadata=summary.removed_metadata_count, cloud=summary.removed_cloud_count, index=summary.removed_index_count, backgrounds=summary.removed_background_count))
        status_var.set(tr("reset_done"))
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

    def on_text_font_change(_: object = None) -> None:
        text_font_family.set(text_font_label_to_key.get(text_font_box.get(), TEXT_FONT_CHOICES[0][1]))
        persist_settings()

    def on_math_font_change(_: object = None) -> None:
        math_font_family.set(math_font_label_to_key.get(math_font_box.get(), MATH_FONT_CHOICES[0][1]))
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
        if chosen_cloud_dir is None:
            messagebox.showerror(tr("run_failed_title"), tr("cloud_skipped"))
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
            show_content_panel=show_content_panel.get(),
            text_font_family=text_font_family.get(),
            math_font_family=math_font_family.get(),
            text_color=text_color.get(),
            math_color=math_color.get(),
        )

        persist_settings()
        append_log(tr("formula_support"))
        append_log(tr("preparing"))

        try:
            summary = run_app(
                repo_dir=repo_dir,
                notes_dir=chosen_local if selected_mode == "local" else None,
                github_url=chosen_github if selected_mode == "github" else None,
                output_dir_arg=output_dir.get().strip() or ".dailytipsapp",
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
        append_log(tr("output_line", value=summary.data_dir))
        append_log(tr("cloud_line", value=summary.cloud_dir))
        append_log(tr("cloud_sync", value=summary.index_path))

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
    widgets["clear_button"].configure(command=handle_clear_all)
    widgets["run_button"].configure(command=run_clicked)
    widgets["text_color_button"].configure(command=lambda: choose_color(text_color, text_color_preview))
    widgets["math_color_button"].configure(command=lambda: choose_color(math_color, math_color_preview))

    language_box.bind("<<ComboboxSelected>>", on_language_change)
    device_box.bind("<<ComboboxSelected>>", on_device_change)
    bg_mode_box.bind("<<ComboboxSelected>>", on_mode_change)
    group_choice_box.bind("<<ComboboxSelected>>", on_group_choice_change)
    image_choice_box.bind("<<ComboboxSelected>>", on_image_choice_change)
    text_font_box.bind("<<ComboboxSelected>>", on_text_font_change)
    math_font_box.bind("<<ComboboxSelected>>", on_math_font_change)
    group_list.bind("<<ListboxSelect>>", on_group_select)
    image_list.bind("<<ListboxSelect>>", on_image_select)
    show_content_panel.trace_add("write", lambda *_: persist_settings())

    update_color_preview(text_color_preview, text_color.get())
    update_color_preview(math_color_preview, math_color.get())
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

def _apply_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("App.TFrame", background=SURFACE)
    style.configure("TLabelframe", background=SURFACE, borderwidth=0, relief="flat")
    style.configure("TLabelframe.Label", background=SURFACE, foreground=TEXT, font=("Segoe UI", 11, "bold"))
    style.configure("TFrame", background=SURFACE)
    style.configure("TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("Field.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 9))
    style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("Subtle.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 9))
    style.configure(
        "TEntry",
        fieldbackground=CARD,
        background=CARD,
        foreground=TEXT,
        insertcolor=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=8,
    )
    style.configure(
        "TCombobox",
        fieldbackground=CARD,
        background=CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        arrowsize=14,
        padding=6,
    )
    style.map("TCombobox", fieldbackground=[("readonly", CARD)], foreground=[("readonly", TEXT)])
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground=ACCENT_TEXT,
        borderwidth=0,
        focusthickness=0,
        padding=(14, 9),
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", "#1d4ed8"), ("pressed", "#1e40af")],
        foreground=[("disabled", "#cbd5e1")],
    )
    style.configure(
        "Ghost.TButton",
        background=CARD,
        foreground=TEXT,
        borderwidth=1,
        focusthickness=0,
        padding=(12, 8),
        font=("Segoe UI", 10),
    )
    style.map(
        "Ghost.TButton",
        background=[("active", "#eef2ff"), ("pressed", "#e2e8f0")],
        foreground=[("disabled", "#94a3b8")],
    )
    style.configure(
        "Danger.TButton",
        background=DANGER,
        foreground=DANGER_TEXT,
        borderwidth=0,
        focusthickness=0,
        padding=(12, 8),
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#b91c1c"), ("pressed", "#991b1b")],
        foreground=[("disabled", "#fecaca")],
    )

