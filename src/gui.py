from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .app import AppError, run_app
from .renderer import DEFAULT_HEIGHT, DEFAULT_WIDTH


def launch_gui() -> None:
    root = tk.Tk()
    root.title("DailyTipsApp")
    root.geometry("760x520")
    root.minsize(700, 480)

    repo_dir = Path(__file__).resolve().parent.parent

    source_mode = tk.StringVar(value="local")
    local_path = tk.StringVar()
    github_url = tk.StringVar(value="https://github.com/PalaiologosLei/DailyTips")
    output_dir = tk.StringVar(value="output/images")
    width_var = tk.StringVar(value=str(DEFAULT_WIDTH))
    height_var = tk.StringVar(value=str(DEFAULT_HEIGHT))
    commit_var = tk.StringVar(value="")
    skip_git_var = tk.BooleanVar(value=False)
    status_var = tk.StringVar(value="Ready.")

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="Source").grid(row=0, column=0, sticky="w")
    source_row = ttk.Frame(frame)
    source_row.grid(row=0, column=1, sticky="ew", pady=(0, 12))
    ttk.Radiobutton(source_row, text="Local folder", value="local", variable=source_mode).pack(side="left")
    ttk.Radiobutton(source_row, text="GitHub public repo", value="github", variable=source_mode).pack(
        side="left", padx=(16, 0)
    )

    ttk.Label(frame, text="Local path").grid(row=1, column=0, sticky="w")
    local_row = ttk.Frame(frame)
    local_row.grid(row=1, column=1, sticky="ew", pady=(0, 12))
    local_row.columnconfigure(0, weight=1)
    ttk.Entry(local_row, textvariable=local_path).grid(row=0, column=0, sticky="ew")
    ttk.Button(local_row, text="Browse", command=lambda: _pick_directory(local_path)).grid(row=0, column=1, padx=(8, 0))

    ttk.Label(frame, text="GitHub URL").grid(row=2, column=0, sticky="w")
    ttk.Entry(frame, textvariable=github_url).grid(row=2, column=1, sticky="ew", pady=(0, 12))

    ttk.Label(frame, text="Output dir").grid(row=3, column=0, sticky="w")
    ttk.Entry(frame, textvariable=output_dir).grid(row=3, column=1, sticky="ew", pady=(0, 12))

    size_row = ttk.Frame(frame)
    size_row.grid(row=4, column=1, sticky="w", pady=(0, 12))
    ttk.Label(frame, text="Image size").grid(row=4, column=0, sticky="w")
    ttk.Entry(size_row, width=10, textvariable=width_var).pack(side="left")
    ttk.Label(size_row, text="x").pack(side="left", padx=8)
    ttk.Entry(size_row, width=10, textvariable=height_var).pack(side="left")

    ttk.Label(frame, text="Commit msg").grid(row=5, column=0, sticky="w")
    ttk.Entry(frame, textvariable=commit_var).grid(row=5, column=1, sticky="ew", pady=(0, 12))

    ttk.Checkbutton(frame, text="Skip git add / commit / push", variable=skip_git_var).grid(
        row=6, column=1, sticky="w", pady=(0, 12)
    )

    log_box = tk.Text(frame, height=12, wrap="word")
    log_box.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(8, 12))
    frame.rowconfigure(7, weight=1)

    action_row = ttk.Frame(frame)
    action_row.grid(row=8, column=0, columnspan=2, sticky="ew")
    action_row.columnconfigure(0, weight=1)
    ttk.Label(action_row, textvariable=status_var).grid(row=0, column=0, sticky="w")

    def append_log(message: str) -> None:
        log_box.insert("end", message + "\n")
        log_box.see("end")
        root.update_idletasks()

    def run_clicked() -> None:
        log_box.delete("1.0", "end")
        status_var.set("Running...")

        try:
            width = int(width_var.get().strip())
            height = int(height_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid size", "Width and height must be integers.")
            status_var.set("Ready.")
            return

        selected_mode = source_mode.get()
        chosen_local = Path(local_path.get().strip()).expanduser().resolve() if local_path.get().strip() else None
        chosen_github = github_url.get().strip() or None
        commit_message = commit_var.get().strip() or None

        append_log("Preparing notes source...")

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
            messagebox.showerror("Run failed", str(error))
            status_var.set("Failed.")
            return

        append_log(f"Source: {summary.source_description}")
        append_log(f"Scanned markdown files: {summary.markdown_file_count}")
        append_log(f"Extracted items: {summary.item_count}")
        append_log(f"Generated images: {summary.image_count}")
        append_log(f"Output directory: {summary.output_dir}")
        append_log("Git sync skipped." if skip_git_var.get() else ("Git sync completed." if summary.git_pushed else "No git changes detected."))

        status_var.set("Done.")
        messagebox.showinfo("Completed", "Processing finished.")

    ttk.Button(action_row, text="Run", command=run_clicked).grid(row=0, column=1, sticky="e")

    root.mainloop()


def _pick_directory(target: tk.StringVar) -> None:
    chosen = filedialog.askdirectory()
    if chosen:
        target.set(chosen)
