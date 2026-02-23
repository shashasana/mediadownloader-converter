"""Main downloader application"""

import os
import json
import uuid
import csv
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
import pyperclip
import webbrowser
import threading
import time
import io
import urllib.request
import re

from config import (
    BG, FG, BOX, BTN, GREEN, RED, YELLOW,
    LIGHT_BG, LIGHT_FG, LIGHT_BOX, LIGHT_BTN, LIGHT_GREEN, LIGHT_RED, LIGHT_YELLOW,
    CHECK_CLIPBOARD_INTERVAL, DEFAULT_SETTINGS, SETTINGS_FILE,
    FORMATS, QUALITY_OPTIONS,
    YTDLP_PATH, FFMPEG_PATH
)
from download_manager import DownloadManager, DownloadTask, DownloadStatus
from downloader_core import detect_platform, start_download_thread, get_output_extension, fetch_media_info
from ui_components import URLInputFrame, DownloadTableFrame, HistoryFrame, LogsFrame, get_save_file_dialog

try:
    from plyer import notification
    NOTIFY_AVAILABLE = True
except Exception:
    NOTIFY_AVAILABLE = False

try:
    import pystray
    from PIL import ImageDraw
    TRAY_AVAILABLE = True
except Exception:
    TRAY_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

class DownloaderApp:
    """Main application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Media Downloader")
        self.root.geometry("1100x950")

        self.settings = self.load_settings()
        self.apply_theme_from_settings()

        self.manager = DownloadManager(max_downloads=self.settings.get("max_concurrent", 3))
        self.manager.subscribe("download_progress", self.on_download_progress)
        self.manager.subscribe("download_completed", self.on_download_completed)

        self.clipboard_enabled = self.settings.get("clipboard_enabled", False)
        self.clipboard_auto_add = self.settings.get("clipboard_auto_add", False)
        self.last_clip = ""
        self.task_map = {}
        self.info_cache = {}
        self.tray_icon = None

        self.setup_ui()
        self.register_shortcuts()

        self.check_clipboard()
        self.process_queue()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Unmap>", self.on_minimize)
        self.root.bind("<Control-MouseWheel>", self.on_zoom_scroll)

    def load_settings(self) -> dict:
        settings = DEFAULT_SETTINGS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    user = json.load(f)
                    settings.update(user)
            except Exception:
                pass
        return settings

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def check_versions(self):
        try:
            yt = subprocess.run([YTDLP_PATH, "--version"], capture_output=True, text=True)
            ff = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True)
            yt_v = yt.stdout.strip() if yt.stdout else "Not found"
            ff_v = ff.stdout.split("\n")[0] if ff.stdout else "Not found"
            messagebox.showinfo("Versions", f"yt-dlp: {yt_v}\nffmpeg: {ff_v}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check versions: {e}")
        except Exception:
            pass

    def apply_theme_from_settings(self):
        theme = self.settings.get("theme", "dark")
        if theme == "light":
            self.colors = {
                "BG": LIGHT_BG,
                "FG": LIGHT_FG,
                "BOX": LIGHT_BOX,
                "BTN": LIGHT_BTN,
                "GREEN": LIGHT_GREEN,
                "RED": LIGHT_RED,
                "YELLOW": LIGHT_YELLOW
            }
        else:
            self.colors = {
                "BG": BG,
                "FG": FG,
                "BOX": BOX,
                "BTN": BTN,
                "GREEN": GREEN,
                "RED": RED,
                "YELLOW": YELLOW
            }

        if self.settings.get("high_contrast", False):
            self.colors = {
                "BG": "#000000",
                "FG": "#FFFFFF",
                "BOX": "#111111",
                "BTN": "#FFFFFF",
                "GREEN": "#00FF00",
                "RED": "#FF3333",
                "YELLOW": "#FFFF00"
            }
        self.root.configure(bg=self.colors["BG"])
        try:
            self.root.tk.call("tk", "scaling", self.settings.get("font_scale", 1.0))
        except Exception:
            pass

    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("520x600")
        settings_win.configure(bg=self.colors["BG"])

        canvas = tk.Canvas(settings_win, bg=self.colors["BG"], highlightthickness=0)
        scrollbar = tk.Scrollbar(settings_win, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=self.colors["BG"])
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_configure(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        content.bind("<Configure>", _on_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _e: settings_win.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _e: settings_win.unbind_all("<MouseWheel>"))

        tk.Label(
            content,
            text="Settings",
            bg=self.colors["BG"], fg=self.colors["FG"],
            font=("Segoe UI", 16, "bold")
        ).pack(pady=10)

        def apply_settings():
            self.settings["clipboard_enabled"] = clip_var.get()
            self.settings["clipboard_auto_add"] = auto_add_var.get()
            try:
                max_val = int(max_var.get())
            except Exception:
                max_val = 3
            max_val = max(1, min(10, max_val))
            self.settings["max_concurrent"] = max_val
            self.settings["download_folder"] = folder_var.get()
            self.settings["overwrite_policy"] = overwrite_var.get()
            self.settings["notifications"] = notify_var.get()
            self.settings["theme"] = theme_var.get()
            self.settings["high_contrast"] = contrast_var.get()
            try:
                scale_val = float(font_var.get())
            except Exception:
                scale_val = 1.5
            scale_val = max(0.8, min(2.0, scale_val))
            self.settings["font_scale"] = scale_val
            self.settings["minimize_to_tray"] = tray_var.get()
            self.settings["lock_ctrl_zoom"] = lock_zoom_var.get()
            self.settings["retry_count"] = retry_var.get()
            self.settings["retry_delay"] = delay_var.get()
            self.manager.max_downloads = self.settings.get("max_concurrent", 3)
            self.clipboard_enabled = self.settings.get("clipboard_enabled", False)
            self.clipboard_auto_add = self.settings.get("clipboard_auto_add", False)
            self.save_settings()
            self.apply_theme_from_settings()
            self.setup_ui()

        clip_var = tk.BooleanVar(value=self.settings.get("clipboard_enabled", False))
        auto_add_var = tk.BooleanVar(value=self.settings.get("clipboard_auto_add", False))
        max_var = tk.IntVar(value=self.settings.get("max_concurrent", 3))
        folder_var = tk.StringVar(value=os.path.expanduser(self.settings.get("download_folder", "~/Downloads")))
        overwrite_var = tk.StringVar(value=self.settings.get("overwrite_policy", "ask"))
        notify_var = tk.BooleanVar(value=self.settings.get("notifications", True))
        theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        contrast_var = tk.BooleanVar(value=self.settings.get("high_contrast", False))
        font_var = tk.StringVar(value=str(self.settings.get("font_scale", 1.0)))
        tray_var = tk.BooleanVar(value=self.settings.get("minimize_to_tray", False))
        lock_zoom_var = tk.BooleanVar(value=self.settings.get("lock_ctrl_zoom", False))
        retry_var = tk.IntVar(value=self.settings.get("retry_count", 2))
        delay_var = tk.IntVar(value=self.settings.get("retry_delay", 3))

        tk.Checkbutton(content, text="Enable Clipboard Detection", variable=clip_var, bg=self.colors["BG"], fg=self.colors["FG"], selectcolor=self.colors["BOX"]).pack(anchor="w", padx=20, pady=4)
        tk.Checkbutton(content, text="Auto-add Clipboard URLs", variable=auto_add_var, bg=self.colors["BG"], fg=self.colors["FG"], selectcolor=self.colors["BOX"]).pack(anchor="w", padx=20, pady=4)

        tk.Label(content, text="Max Concurrent Downloads", bg=self.colors["BG"], fg=self.colors["FG"]).pack(anchor="w", padx=20)
        tk.Entry(content, textvariable=max_var, bg=self.colors["BOX"], fg=self.colors["FG"], insertbackground=self.colors["FG"]).pack(fill="x", padx=20, pady=4)

        tk.Label(content, text="Download Folder", bg=self.colors["BG"], fg=self.colors["FG"]).pack(anchor="w", padx=20)
        folder_frame = tk.Frame(content, bg=self.colors["BG"])
        folder_frame.pack(fill="x", padx=20, pady=4)
        tk.Entry(folder_frame, textvariable=folder_var, bg=self.colors["BOX"], fg=self.colors["FG"], insertbackground=self.colors["FG"]).pack(side="left", fill="x", expand=True)
        tk.Button(folder_frame, text="Browse", bg=self.colors["BTN"], fg="white", command=lambda: folder_var.set(filedialog.askdirectory(initialdir=folder_var.get()) or folder_var.get())).pack(side="left", padx=(5, 0))

        tk.Label(content, text="Overwrite Policy", bg=self.colors["BG"], fg=self.colors["FG"]).pack(anchor="w", padx=20)
        tk.OptionMenu(content, overwrite_var, "ask", "overwrite", "skip").pack(anchor="w", padx=20)

        tk.Label(content, text="Theme", bg=self.colors["BG"], fg=self.colors["FG"]).pack(anchor="w", padx=20)
        tk.OptionMenu(content, theme_var, "dark", "light").pack(anchor="w", padx=20)

        tk.Checkbutton(content, text="High Contrast", variable=contrast_var, bg=self.colors["BG"], fg=self.colors["FG"], selectcolor=self.colors["BOX"]).pack(anchor="w", padx=20, pady=4)

        tk.Label(content, text="Font Scale", bg=self.colors["BG"], fg=self.colors["FG"]).pack(anchor="w", padx=20)
        tk.Entry(content, textvariable=font_var, bg=self.colors["BOX"], fg=self.colors["FG"], insertbackground=self.colors["FG"]).pack(fill="x", padx=20, pady=4)

        tk.Checkbutton(content, text="Enable Notifications", variable=notify_var, bg=self.colors["BG"], fg=self.colors["FG"], selectcolor=self.colors["BOX"]).pack(anchor="w", padx=20, pady=4)
        tk.Checkbutton(content, text="Minimize to Tray", variable=tray_var, bg=self.colors["BG"], fg=self.colors["FG"], selectcolor=self.colors["BOX"]).pack(anchor="w", padx=20, pady=4)
        tk.Checkbutton(content, text="Lock Ctrl+Scroll Zoom", variable=lock_zoom_var, bg=self.colors["BG"], fg=self.colors["FG"], selectcolor=self.colors["BOX"]).pack(anchor="w", padx=20, pady=4)

        tk.Label(content, text="Retries", bg=self.colors["BG"], fg=self.colors["FG"]).pack(anchor="w", padx=20)
        tk.Entry(content, textvariable=retry_var, bg=self.colors["BOX"], fg=self.colors["FG"], insertbackground=self.colors["FG"]).pack(fill="x", padx=20, pady=4)
        tk.Label(content, text="Retry Delay (s)", bg=self.colors["BG"], fg=self.colors["FG"]).pack(anchor="w", padx=20)
        tk.Entry(content, textvariable=delay_var, bg=self.colors["BOX"], fg=self.colors["FG"], insertbackground=self.colors["FG"]).pack(fill="x", padx=20, pady=4)

        tk.Button(content, text="Apply", bg=self.colors["BTN"], fg="white", command=apply_settings).pack(pady=10)
        tk.Button(content, text="Check yt-dlp / ffmpeg", bg=self.colors["BOX"], fg=self.colors["FG"], command=self.check_versions).pack(pady=4)
    
    def setup_ui(self):
        """Setup UI components"""
        prior_url = ""
        prior_folder = ""
        prior_title = ""
        prior_format = ""
        prior_quality = ""
        prior_preview = ""
        prior_logs = ""
        prior_error_logs = ""
        try:
            if hasattr(self, "url_frame"):
                prior_url = self.url_frame.get_url()
                prior_folder = self.url_frame.get_output_folder()
                prior_format = self.url_frame.format_var.get()
                prior_quality = self.url_frame.quality_var.get()
            if hasattr(self, "title_override_var"):
                prior_title = self.title_override_var.get()
            if hasattr(self, "preview_text"):
                prior_preview = self.preview_text.get()
            if hasattr(self, "logs_frame"):
                try:
                    prior_logs = self.logs_frame.log.get("1.0", tk.END)
                    prior_error_logs = self.logs_frame.error_log.get("1.0", tk.END)
                except Exception:
                    prior_logs = ""
                    prior_error_logs = ""
        except Exception:
            pass

        for widget in self.root.winfo_children():
            widget.destroy()

        BGc = self.colors["BG"]
        FGc = self.colors["FG"]
        BTNc = self.colors["BTN"]
        GREENc = self.colors["GREEN"]
        REDc = self.colors["RED"]
        YELLOWc = self.colors["YELLOW"]
        scale = self.settings.get("font_scale", 1.0)

        # Header
        header = tk.Frame(self.root, bg=BGc)
        header.pack(fill="x", padx=15, pady=10)
        
        tk.Label(
            header,
            text="📥 Media Downloader",
            bg=BGc, fg=FGc,
            font=("Segoe UI", int(20 * self.settings.get("font_scale", 1.0)), "bold")
        ).pack(side="left")
        
        tk.Button(
            header,
            text="⚙ Settings",
            bg=BGc, fg=FGc,
            bd=0,
            font=("Segoe UI", int(10 * scale)),
            command=self.open_settings
        ).pack(side="right", padx=5)
        
        tk.Button(
            header,
            text="🗑 Clear Logs",
            bg=BGc, fg=FGc,
            bd=0,
            font=("Segoe UI", int(10 * scale)),
            command=self.clear_logs
        ).pack(side="right", padx=5)
        
        # Main scrollable container
        main_frame = tk.Frame(self.root, bg=BGc)
        main_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Canvas for scrolling
        canvas = tk.Canvas(main_frame, bg=BGc, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BGc)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # URL Input
        self.url_frame = URLInputFrame(scrollable_frame, font_scale=scale)
        self.url_frame.pack(fill="x", pady=10)
        self.url_frame.set_output_folder(os.path.expanduser(self.settings.get("download_folder", "~/Downloads")))
        self.apply_presets_to_ui()
        self.url_frame.preset_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_selected_preset())
        self.url_frame.url_text.bind("<KeyRelease>", self.update_platform_hint)
        self.url_frame.set_save_preset_callback(self.save_current_preset)
        if prior_url:
            self.url_frame.set_url(prior_url)
        if prior_folder:
            self.url_frame.set_output_folder(prior_folder)
        if prior_format:
            self.url_frame.format_var.set(prior_format)
        if prior_quality:
            self.url_frame.quality_var.set(prior_quality)
        self.url_frame.update_format_visibility()

        # Preview area: button, thumbnail, editable title, and info
        preview_frame = tk.Frame(scrollable_frame, bg=BGc)
        preview_frame.pack(fill="x", pady=5)

        # Left: Preview button
        tk.Button(
            preview_frame,
            text="Preview Media",
            bg=BTNc,
            fg="white",
            font=("Segoe UI", int(10 * scale)),
            command=self.preview_media,
        ).pack(side="left")

        # Center: thumbnail + title/info
        preview_center = tk.Frame(preview_frame, bg=BGc)
        preview_center.pack(side="left", padx=10, fill="x", expand=True)

        # Thumbnail (small preview)
        self.preview_image_label = tk.Label(preview_center, bg=BGc)
        self.preview_image_label.pack(side="left", padx=(0, 10))
        self._preview_image = None

        # Title + metadata stack
        meta_frame = tk.Frame(preview_center, bg=BGc)
        meta_frame.pack(side="left", fill="x", expand=True)

        # Editable title (override)
        self.title_override_var = tk.StringVar(value=prior_title)
        self.title_entry = tk.Entry(
            meta_frame,
            textvariable=self.title_override_var,
            bg=self.colors["BOX"],
            fg=self.colors["FG"],
            insertbackground=self.colors["FG"],
            width=50
        )
        self.title_entry.pack(side="top", anchor="w", pady=(0, 4))
        
        # Auto-adjust title entry width based on content
        def adjust_title_width(*args):
            content = self.title_override_var.get()
            if content:
                # Calculate width based on content length, min 50, max 120
                new_width = max(50, min(120, len(content)))
                self.title_entry.config(width=new_width)
            else:
                self.title_entry.config(width=50)
        
        self.title_override_var.trace_add("write", adjust_title_width)
        adjust_title_width()  # Initial adjustment

        # Read-only preview info (uploader, duration, etc.)
        self.preview_text = tk.StringVar(value=prior_preview or "No media preview")
        self.preview_label = tk.Label(
            meta_frame,
            textvariable=self.preview_text,
            bg=BGc,
            fg=FGc,
            font=("Segoe UI", int(9 * scale)),
            justify="left",
            anchor="w",
        )
        self.preview_label.pack(side="top", fill="x", expand=True)
        
        # Action buttons
        btn_frame = tk.Frame(scrollable_frame, bg=BGc)
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(
            btn_frame,
            text="Add to Queue",
            bg=GREENc,
            fg="white",
            font=("Segoe UI", int(11 * scale), "bold"),
            command=self.add_to_queue
        ).pack(side="left", padx=5)
        
        tk.Button(
            btn_frame,
            text="Download Now",
            bg=BTNc,
            fg="white",
            font=("Segoe UI", int(11 * scale), "bold"),
            command=self.download_now
        ).pack(side="left", padx=5)
        
        # Downloads table
        self.download_table = DownloadTableFrame(scrollable_frame, font_scale=scale)
        self.download_table.pack(fill="both", expand=True, pady=10)
        self.download_table.tree.bind("<Button-3>", self.show_download_context_menu)
        
        # Clear Finished button
        clear_btn_frame = tk.Frame(scrollable_frame, bg=BGc)
        clear_btn_frame.pack(fill="x", padx=5, pady=5)
        tk.Button(
            clear_btn_frame,
            text="Clear Finished",
            command=self.clear_finished_downloads,
            bg=BTNc,
            fg="white",
            font=("Segoe UI", int(10 * scale)),
        ).pack(side="left", padx=5)
        
        # History
        self.history_frame = HistoryFrame(scrollable_frame, font_scale=scale)
        self.history_frame.pack(fill="both", expand=True, pady=10)
        self.history_frame.set_actions(
            self.open_history_file,
            self.open_history_folder,
            self.copy_history_url,
            self.export_history_csv,
            self.export_history_json
        )
        
        # Logs
        self.logs_frame = LogsFrame(scrollable_frame, font_scale=scale)
        self.logs_frame.pack(fill="both", expand=True, pady=10)
        self.logs_frame.set_copy_errors_callback(self.copy_errors)

        # Restore logs content (so zooming doesn't clear them)
        try:
            if prior_logs:
                self.logs_frame.log.insert("1.0", prior_logs)
            if prior_error_logs:
                self.logs_frame.error_log.insert("1.0", prior_error_logs)
        except Exception:
            pass
        
        # Pack scrollable content
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.restore_ui_state()

    def restore_ui_state(self):
        for task_id, task in self.task_map.items():
            filename = os.path.basename(task.path)
            if task_id not in self.download_table.items:
                self.download_table.add_download(task_id, filename)
            self.download_table.update_download(
                task_id,
                task.status.value,
                task.file_size,
                task.speed,
                task.eta,
                task.progress
            )

        if hasattr(self, "history_frame"):
            self.history_frame.clear_history()
            for item in self.manager.history[:20]:
                self.history_frame.add_history_item(
                    item["file"],
                    item["location"],
                    item["format"],
                    item["status"],
                    item["url"]
                )

    def preview_media(self):
        url = self.url_frame.get_url()
        if not url:
            messagebox.showwarning("Missing", "Enter a media URL")
            return

        info = fetch_media_info(url)
        if info:
            title = info.get("title", "Unknown")
            uploader = info.get("uploader", "Unknown")
            duration = info.get("duration", 0)
            # Update editable title field with detected title
            if hasattr(self, "title_override_var"):
                self.title_override_var.set(title)

            # Get file size for selected quality
            file_size_str = ""
            try:
                quality_choice = self.url_frame.get_quality()
                formats = info.get("formats") or []
                # Find format matching selected quality
                if quality_choice.startswith("Audio"):
                    # For audio, find audio-only format
                    for fmt in formats:
                        if fmt.get("acodec") and fmt.get("acodec") != "none" and not fmt.get("vcodec"):
                            size = fmt.get("filesize") or fmt.get("filesize_approx")
                            if size:
                                file_size_str = f" | Size: {size / (1024*1024):.1f}MB"
                            break
                else:
                    # For video, find best video+audio combo matching quality
                    height_match = re.match(r"^(\d+)p$", quality_choice)
                    if height_match:
                        target_height = int(height_match.group(1))
                        best_size = 0
                        for fmt in formats:
                            fmt_height = fmt.get("height") or 0
                            if fmt_height <= target_height and fmt.get("vcodec") and fmt.get("acodec"):
                                size = fmt.get("filesize") or fmt.get("filesize_approx")
                                if size and size > best_size:
                                    best_size = size
                        if best_size > 0:
                            file_size_str = f" | Size: {best_size / (1024*1024):.1f}MB"
            except Exception:
                pass

            preview = f"By: {uploader} | Duration: {duration}s{file_size_str}"
            if len(preview) > 180:
                preview = preview[:177] + "..."
            self.preview_text.set(preview)
            self.info_cache[url] = info
            thumb = info.get("thumbnail") or (info.get("thumbnails")[-1]["url"] if info.get("thumbnails") else None)
            if thumb and PIL_AVAILABLE:
                try:
                    with urllib.request.urlopen(thumb) as response:
                        data = response.read()
                    image = Image.open(io.BytesIO(data))
                    # Use a small thumbnail so the preview isn't huge
                    image.thumbnail((96, 96))
                    self._preview_image = ImageTk.PhotoImage(image)
                    self.preview_image_label.config(image=self._preview_image)
                except Exception:
                    self.preview_image_label.config(image="")
            else:
                self.preview_image_label.config(image="")

            # Auto-detect available video qualities from formats, if present
            try:
                formats = info.get("formats") or []
                heights = {
                    f.get("height")
                    for f in formats
                    if isinstance(f.get("height"), int)
                }
                if heights:
                    # Build labels from detected heights only
                    available_labels = [f"{h}p" for h in sorted(heights, reverse=True)]
                    # Update quality dropdown if we're in a video format
                    try:
                        current_fmt = self.url_frame.get_format()
                        if current_fmt in ("mp4", "webm") and hasattr(self.url_frame, "set_available_video_qualities"):
                            self.url_frame.set_available_video_qualities(available_labels)
                    except Exception:
                        pass
            except Exception:
                pass
        else:
            self.preview_text.set("Preview failed. Check the URL.")
            self.preview_image_label.config(image="")

    def update_platform_hint(self, _event=None):
        url = self.url_frame.get_url()
        if url.startswith("http"):
            platform = detect_platform(url)
            self.url_frame.set_platform_hint(f"Platform: {platform}")
            if hasattr(self, "_preview_after") and self._preview_after:
                try:
                    self.root.after_cancel(self._preview_after)
                except Exception:
                    pass
            self._preview_after = self.root.after(700, self.preview_media)
    
    def add_to_queue(self):
        """Add URL to download queue"""
        url = self.url_frame.get_url()
        format_choice = self.url_frame.get_format()
        quality_choice = self.url_frame.get_quality()
        
        if not url:
            messagebox.showwarning("Missing", "Enter a media URL")
            return
        
        if not url.startswith("http"):
            messagebox.showerror("Invalid URL", "URL must start with http or https")
            return
        
        if not self.manager.is_queue_available():
            messagebox.showwarning("Limit", f"Queue is full ({self.settings.get('max_concurrent', 3)} max)")
            return
        
        output_folder = self.url_frame.get_output_folder() or os.path.expanduser(self.settings.get("download_folder", "~/Downloads"))
        output_folder = os.path.expanduser(output_folder)
        os.makedirs(output_folder, exist_ok=True)
        
        filename = self.build_filename(url)
        ext = get_output_extension(format_choice)
        save_path = os.path.join(output_folder, f"{filename}{ext}")
        
        if os.path.exists(save_path):
            action = self.settings.get("overwrite_policy", "ask")
            if action == "ask":
                if not messagebox.askyesno("File exists", "File exists. Overwrite?"):
                    return
            elif action == "skip":
                self.logs_frame.add_log("Skipped duplicate file\n")
                return
        
        platform = detect_platform(url)
        task = DownloadTask(
            url=url,
            path=save_path,
            format_choice=format_choice,
            platform=platform
        )
        
        task_id = str(uuid.uuid4())
        self.task_map[task_id] = task
        self.manager.add_task(task)
        
        self.download_table.add_download(task_id, os.path.basename(save_path))
        self.logs_frame.add_log(f"Added to queue: {url}\n")
        self.url_frame.clear()
        
        self.process_queue()
    
    def download_now(self):
        """Immediate download.

        If an output folder is selected, use it directly (no save dialog)
        and auto-generate the filename. Otherwise, fall back to a save
        dialog for maximum control.
        """
        url = self.url_frame.get_url()
        format_choice = self.url_frame.get_format()
        
        if not url:
            messagebox.showwarning("Missing", "Enter a media URL")
            return
        
        explicit_folder = self.url_frame.get_output_folder().strip()
        default_folder = os.path.expanduser(self.settings.get("download_folder", "~/Downloads"))
        filename = self.build_filename(url)

        if explicit_folder:
            # Use chosen output folder directly, like Add to Queue
            output_folder = os.path.expanduser(explicit_folder)
            os.makedirs(output_folder, exist_ok=True)
            ext = get_output_extension(format_choice)
            save_path = os.path.join(output_folder, f"{filename}{ext}")

            if os.path.exists(save_path):
                action = self.settings.get("overwrite_policy", "ask")
                if action == "ask":
                    if not messagebox.askyesno("File exists", "File exists. Overwrite?"):
                        return
                elif action == "skip":
                    self.logs_frame.add_log("Skipped duplicate file\n")
                    return
        else:
            # Fall back to save dialog
            output_folder = default_folder
            ext = get_output_extension(format_choice)
            save_path = get_save_file_dialog(
                format_choice,
                initialdir=output_folder,
                filename=f"{filename}{ext}"
            )
            if not save_path:
                return
        
        # Create task
        platform = detect_platform(url)
        task = DownloadTask(
            url=url,
            path=save_path,
            format_choice=format_choice,
            platform=platform,
            status=DownloadStatus.DOWNLOADING
        )
        
        # Add to active downloads
        task_id = str(uuid.uuid4())
        self.task_map[task_id] = task
        self.manager.active_downloads.append(task)
        
        # Update UI
        filename = os.path.basename(save_path)
        self.download_table.add_download(task_id, filename)
        self.download_table.update_download(
            task_id,
            task.status.value,
            task.file_size,
            task.speed,
            task.eta,
            task.progress
        )
        self.logs_frame.add_log(f"Starting download: {url}\n")
        self.url_frame.clear()
        
        # Start download
        start_download_thread(
            task,
            self.manager,
            self.get_download_settings(),
            on_progress=lambda t: self.on_download_progress(),
            on_log=lambda msg: self.logs_frame.add_log(msg)
        )
    
    def process_queue(self):
        """Process next item in queue"""
        if self.manager.get_active_count() >= self.settings.get("max_concurrent", 3):
            return

        task = self.manager.get_next_task()
        if task:
            # Find task ID
            task_id = None
            for tid, t in self.task_map.items():
                if t is task:
                    task_id = tid
                    break
            
            if task_id:
                task.status = DownloadStatus.DOWNLOADING
                self.download_table.update_download(
                    task_id,
                    task.status.value,
                    task.file_size,
                    task.speed,
                    task.eta,
                    task.progress
                )
                self.logs_frame.add_log(f"Downloading: {task.url}\n")
                start_download_thread(
                    task,
                    self.manager,
                    self.get_download_settings(),
                    on_progress=lambda t: self.on_download_progress(),
                    on_log=lambda msg: self.logs_frame.add_log(msg)
                )
            
            # Schedule next check
            self.root.after(100, self.check_queue_space)
    
    def check_queue_space(self):
        """Periodically check if we can process more"""
        if self.manager.get_queue_count() > 0 and self.manager.get_active_count() < self.settings.get("max_concurrent", 3):
            self.process_queue()
    
    def pause_selected(self):
        selected = self.download_table.tree.selection()
        if not selected:
            return
        item_id = self.download_table.tree.item(selected[0], "text")
        task = self.task_map.get(item_id)
        if task:
            self.manager.pause_task(task)
            self._terminate_process(task)
            self.logs_frame.add_log("Paused download\n")

    def resume_selected(self):
        selected = self.download_table.tree.selection()
        if not selected:
            return
        item_id = self.download_table.tree.item(selected[0], "text")
        task = self.task_map.get(item_id)
        if task and task.status == DownloadStatus.PAUSED:
            self.manager.resume_task(task)
            self.process_queue()
            self.logs_frame.add_log("Resumed download\n")

    def cancel_selected(self):
        selected = self.download_table.tree.selection()
        if not selected:
            return
        item_id = self.download_table.tree.item(selected[0], "text")
        task = self.task_map.get(item_id)
        if task:
            self.manager.cancel_task(task)
            self._terminate_process(task)
            self.logs_frame.add_log("Cancelled download\n")

    def show_download_context_menu(self, event):
        """Show context menu for download table"""
        item = self.download_table.tree.identify("item", event.x, event.y)
        if not item:
            return
        
        # Select the item
        self.download_table.tree.selection_set(item)
        
        # Get task info
        task_id = self.download_table.tree.item(item, "text")
        task = self.task_map.get(task_id)
        if not task:
            return
        
        # Create context menu
        menu = tk.Menu(self.root, tearoff=False)
        
        # Pause button - only if downloading
        if task.status == DownloadStatus.DOWNLOADING:
            menu.add_command(label="Pause", command=self.pause_selected)
        
        # Resume button - only if paused
        if task.status == DownloadStatus.PAUSED:
            menu.add_command(label="Resume", command=self.resume_selected)
        
        # Cancel button - always available for active tasks
        if task.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED, DownloadStatus.QUEUED):
            menu.add_command(label="Cancel", command=self.cancel_selected)
        
        # Show menu at cursor
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.after_idle(menu.destroy)

    def _terminate_process(self, task: DownloadTask):
        if not task or not task.process:
            return
        def _kill():
            try:
                task.process.terminate()
            except Exception:
                pass
        threading.Thread(target=_kill, daemon=True).start()

    def on_download_progress(self):
        """Update UI when download progresses"""
        for task_id, task in self.task_map.items():
            if task in self.manager.active_downloads:
                # ETA should come from task (set by download_manager)
                # If not set, calculate based on progress
                if not task.eta or task.eta == "Calculating...":
                    elapsed = int(time.time() - task.start_time.timestamp())
                    if task.progress > 0 and elapsed > 0:
                        # Estimate time remaining
                        total_time = (elapsed / task.progress) * 100
                        remaining = int(total_time - elapsed)
                        mins, secs = divmod(remaining, 60)
                        task.eta = f"{mins:02d}:{secs:02d}"
                    else:
                        task.eta = "--:--"
                self.download_table.update_download(
                    task_id,
                    task.status.value,
                    task.file_size,
                    task.speed,
                    task.eta,
                    task.progress
                )
    
    def on_download_completed(self):
        """Handle download completion"""
        # Update history
        for item in self.manager.history[:1]:  # Get latest
            self.history_frame.add_history_item(
                item["file"],
                item["location"],
                item["format"],
                item["status"],
                item["url"]
            )

        if self.settings.get("notifications", True):
            status = self.manager.history[0].get("status", "") if self.manager.history else ""
            if status == DownloadStatus.FAILED.value:
                self.notify("Download Failed", "A download failed")
            elif status == DownloadStatus.CANCELLED.value:
                self.notify("Download Cancelled", "A download was cancelled")
            else:
                self.notify("Download Complete", "Your file has finished downloading")

        for task_id, task in self.task_map.items():
            if task.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED):
                if task.status == DownloadStatus.COMPLETED:
                    task.progress = 100.0
                    task.eta = "00:00"
                self.download_table.update_download(
                    task_id,
                    task.status.value,
                    task.file_size,
                    task.speed,
                    task.eta,
                    task.progress
                )
                self.download_table.remove_download(task_id)

        if self.manager.history and self.manager.history[0].get("status") == DownloadStatus.COMPLETED.value:
            latest = self.manager.history[0]
            path = os.path.join(latest["location"], latest["file"])
            if messagebox.askyesno("Download Complete", "Open the downloaded file?"):
                self._open_file_path(path)

        # Try to process next
        self.check_queue_space()
        self.process_queue()

    def build_filename(self, url: str) -> str:
        info = self.info_cache.get(url, {})
        # Prefer user-edited title override if available
        custom_title = ""
        try:
            if hasattr(self, "title_override_var"):
                custom_title = (self.title_override_var.get() or "").strip()
        except Exception:
            custom_title = ""

        title = custom_title or info.get("title", "download")
        uploader = info.get("uploader", "unknown")
        date = info.get("upload_date", datetime.now().strftime("%Y%m%d"))

        if "facebook.com" in url:
            quality = self.url_frame.get_quality()
            fb_name = uploader or "Facebook"
            fb_caption = title or "Post"
            safe = f"{fb_name} - {fb_caption} [{quality}]"
            return "".join(c for c in safe if c not in '\\/:*?"<>|')

        template = self.settings.get("filename_template", "{title} - {uploader}")
        safe = template.format(title=title, uploader=uploader)
        return "".join(c for c in safe if c not in '\\/:*?"<>|')

    def get_download_settings(self) -> dict:
        return {
            "quality_choice": self.url_frame.get_quality(),
            "audio_codec": self.url_frame.get_audio_codec(),
            "audio_bitrate": self.url_frame.get_audio_bitrate(),
            "embed_thumbnail": self.url_frame.get_embed_thumbnail(),
            "embed_metadata": self.url_frame.get_embed_metadata(),
            "subtitles": self.url_frame.get_subtitles(),
            "auto_subtitles": self.url_frame.get_auto_subtitles(),
            "subtitle_langs": self.url_frame.get_subtitle_langs(),
            "retry_count": self.settings.get("retry_count", 2),
            "retry_delay": self.settings.get("retry_delay", 3)
        }

    def _open_file_path(self, path: str):
        if not path:
            return
        
        # Normalize path
        path = os.path.normpath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            # Try to find similar file in the directory
            dir_path = os.path.dirname(path)
            base_name = os.path.splitext(os.path.basename(path))[0]
            
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if file.startswith(base_name):
                        potential_path = os.path.join(dir_path, file)
                        if os.path.isfile(potential_path):
                            path = potential_path
                            break
        
        if not os.path.exists(path):
            messagebox.showerror("Open Failed", f"File not found: {path}")
            return
        
        try:
            os.startfile(path)
            return
        except Exception as e:
            pass
        try:
            subprocess.Popen(["explorer", "/select,", path])
        except Exception as e:
            messagebox.showerror("Open Failed", f"Could not open: {path}\nError: {str(e)}")

    def _open_folder_path(self, path: str):
        if not path:
            return
        if not os.path.exists(path):
            messagebox.showerror("Open Failed", f"Folder not found: {path}")
            return
        try:
            os.startfile(path)
            return
        except Exception:
            pass
        try:
            subprocess.Popen(["explorer", path])
        except Exception:
            messagebox.showerror("Open Failed", f"Could not open: {path}")

    def open_history_file(self):
        item = self.history_frame.get_selected()
        if not item:
            return
        path = os.path.join(item["location"], item["file"])
        self._open_file_path(path)

    def open_history_folder(self):
        item = self.history_frame.get_selected()
        if not item:
            return
        self._open_folder_path(item["location"])

    def copy_history_url(self):
        item = self.history_frame.get_selected()
        if not item:
            return
        pyperclip.copy(item["url"])

    def export_history_csv(self):
        path = os.path.join(os.getcwd(), "history.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["file", "location", "format", "status", "url"])
            for h in self.manager.history:
                writer.writerow([h["file"], h["location"], h["format"], h["status"], h["url"]])
        messagebox.showinfo("Export", f"CSV exported to {path}")

    def export_history_json(self):
        path = os.path.join(os.getcwd(), "history.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.manager.history, f, indent=2)
        messagebox.showinfo("Export", f"JSON exported to {path}")

    def copy_errors(self):
        content = self.logs_frame.error_log.get("1.0", tk.END).strip()
        if content:
            pyperclip.copy(content)
    
    def clear_finished_downloads(self):
        """Remove completed, cancelled, and failed downloads from the table."""
        remove_ids = []
        for task_id, task in list(self.task_map.items()):
            if task.status in (DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED):
                remove_ids.append(task_id)
        
        for task_id in remove_ids:
            self.download_table.remove_download(task_id)
            self.task_map.pop(task_id, None)
    
    def toggle_ctrl_zoom(self):
        """Toggle Ctrl+Scroll zoom on/off (Ctrl+T shortcut)."""
        current = self.settings.get("lock_ctrl_zoom", False)
        self.settings["lock_ctrl_zoom"] = not current
        self.save_settings()
        # Show toast notification
        status = "disabled" if not current else "enabled"
        self.logs_frame.add_log(f"Ctrl+Scroll zoom {status}", "INFO")
    
    def clear_logs(self):
        """Clear logs"""
        self.logs_frame.clear_logs()

    # ================= SHORTCUTS =================

    def register_shortcuts(self):
        self.root.bind("<Control-Return>", lambda e: self.download_now())
        self.root.bind("<Control-Shift-Q>", lambda e: self.add_to_queue())
        self.root.bind("<Control-L>", lambda e: self.clear_logs())
        self.root.bind("<Control-t>", lambda e: self.toggle_ctrl_zoom())

    def on_zoom_scroll(self, event):
        if self.settings.get("lock_ctrl_zoom", False):
            return
        delta = 0.1 if event.delta > 0 else -0.1
        current = float(self.settings.get("font_scale", 1.0))
        new_scale = max(0.8, min(2.0, round(current + delta, 1)))
        if new_scale != current:
            self.settings["font_scale"] = new_scale
            self.save_settings()
            self.apply_theme_from_settings()
            self.setup_ui()

    # ================= NOTIFICATIONS / TRAY =================

    def notify(self, title: str, message: str):
        if NOTIFY_AVAILABLE:
            notification.notify(title=title, message=message, timeout=3)

    def on_minimize(self, event):
        if self.settings.get("minimize_to_tray", False) and TRAY_AVAILABLE:
            if self.root.state() == "iconic":
                self.hide_to_tray()

    def hide_to_tray(self):
        if self.tray_icon:
            return

        image = Image.new("RGB", (64, 64), color=(35, 116, 225))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(49, 162, 76))

        def on_restore(icon, item):
            icon.stop()
            self.tray_icon = None
            self.root.after(0, self.root.deiconify)

        def on_exit(icon, item):
            icon.stop()
            self.tray_icon = None
            self.root.after(0, self.root.destroy)

        menu = pystray.Menu(
            pystray.MenuItem("Restore", on_restore),
            pystray.MenuItem("Exit", on_exit)
        )
        self.tray_icon = pystray.Icon("downloader", image, "Downloader", menu)
        self.root.withdraw()
        self.tray_icon.run_detached()

    def on_close(self):
        if self.settings.get("minimize_to_tray", False) and TRAY_AVAILABLE:
            self.hide_to_tray()
        else:
            self.root.destroy()

    # ================= PRESETS =================

    def apply_presets_to_ui(self):
        presets = self.settings.get("presets", {})
        self.url_frame.preset_combo["values"] = list(presets.keys())
        self.url_frame.preset_var.set(self.settings.get("active_preset", "Default"))

    def apply_selected_preset(self):
        preset_name = self.url_frame.preset_var.get()
        presets = self.settings.get("presets", {})
        preset = presets.get(preset_name)
        if not preset:
            return
        self.settings["active_preset"] = preset_name
        self.save_settings()
        self.url_frame.format_var.set(next((k for k, v in FORMATS.items() if v == preset.get("format_choice")), "MP4 (Video)"))
        mapped_quality = next((k for k, v in QUALITY_OPTIONS.items() if v == preset.get("quality_choice")), None)
        if mapped_quality:
            self.url_frame.quality_var.set(mapped_quality)
        else:
            try:
                values = list(self.url_frame.quality_combo["values"])
                if values:
                    self.url_frame.quality_var.set(values[0])
            except Exception:
                pass
        self.url_frame.audio_codec_var.set(preset.get("audio_codec", "mp3"))
        self.url_frame.audio_bitrate_var.set(preset.get("audio_bitrate", "192k"))
        self.url_frame.set_output_folder(os.path.expanduser(preset.get("download_folder", "~/Downloads")))

    def save_current_preset(self):
        name = self.url_frame.preset_var.get().strip()
        if not name:
            messagebox.showwarning("Preset", "Enter a preset name")
            return
        presets = self.settings.get("presets", {})
        presets[name] = {
            "format_choice": self.url_frame.get_format(),
            "quality_choice": self.url_frame.get_quality(),
            "audio_codec": self.url_frame.get_audio_codec(),
            "audio_bitrate": self.url_frame.get_audio_bitrate(),
            "download_folder": self.url_frame.get_output_folder(),
            "filename_template": self.settings.get("filename_template", "{title} - {uploader} [{date}]")
        }
        self.settings["presets"] = presets
        self.settings["active_preset"] = name
        self.save_settings()
        self.apply_presets_to_ui()
        messagebox.showinfo("Preset", f"Preset '{name}' saved")
    
    def check_clipboard(self):
        """Check clipboard for URLs"""
        if self.clipboard_enabled:
            try:
                text = pyperclip.paste()
                if text != self.last_clip and text.startswith("http"):
                    self.url_frame.set_url(text)
                    platform = detect_platform(text)
                    self.url_frame.set_platform_hint(f"Platform: {platform}")
                    self.last_clip = text
                    if hasattr(self, "_preview_after") and self._preview_after:
                        try:
                            self.root.after_cancel(self._preview_after)
                        except Exception:
                            pass
                    self._preview_after = self.root.after(700, self.preview_media)
                    if self.clipboard_auto_add:
                        self.add_to_queue()
            except:
                pass
        
        self.root.after(CHECK_CLIPBOARD_INTERVAL * 1000, self.check_clipboard)
    
def main():
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

