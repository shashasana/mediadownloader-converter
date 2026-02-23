"""UI components for the downloader"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
from config import BG, FG, BOX, BTN, GREEN, RED, YELLOW, FORMATS, FILE_TYPES, QUALITY_OPTIONS, AUDIO_CODECS, AUDIO_BITRATES
from downloader_core import get_output_extension

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

class URLInputFrame(tk.Frame):
    """Enhanced URL input with format selection"""
    
    def __init__(self, parent, font_scale: float = 1.0, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.font_scale = font_scale
        
        # Label
        tk.Label(
            self,
            text="Media URL",
            bg=BG, fg=FG,
            font=("Segoe UI", int(11 * self.font_scale))
        ).pack(anchor="w", pady=(0, 5))

        self.platform_hint = tk.StringVar(value="Platform: Unknown")
        tk.Label(
            self,
            textvariable=self.platform_hint,
            bg=BG, fg=YELLOW,
            font=("Segoe UI", int(9 * self.font_scale))
        ).pack(anchor="w")
        
        # Input frame with scrollbar
        input_frame = tk.Frame(self, bg=BOX, highlightthickness=1, highlightbackground="#444")
        input_frame.pack(fill="both", expand=True, pady=3)
        
        # Text widget with auto-wrap
        self.url_text = tk.Text(
            input_frame,
            bg=BOX,
            fg=FG,
            insertbackground=FG,
            height=3,
            width=80,
            wrap="word",
            font=("Segoe UI", int(10 * self.font_scale))
        )
        self.url_text.pack(padx=2, pady=2)

        if DND_AVAILABLE:
            try:
                self.url_text.drop_target_register(DND_FILES)
                self.url_text.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass
        
        # Preset selection frame
        preset_frame = tk.Frame(self, bg=BG)
        preset_frame.pack(fill="x", pady=(6, 0))

        tk.Label(preset_frame, text="Preset:", bg=BG, fg=FG).pack(side="left")
        self.preset_var = tk.StringVar(value="Default")
        self.preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            values=["Default"],
            state="readonly",
            width=20
        )
        self.preset_combo.pack(side="left", padx=8)
        self.save_preset_btn = tk.Button(preset_frame, text="Save Preset", bg=BTN, fg="white")
        self.save_preset_btn.pack(side="left", padx=6)

        # Format selection frame
        format_frame = tk.Frame(self, bg=BG)
        format_frame.pack(fill="x", pady=(6, 0))
        
        tk.Label(
            format_frame,
            text="Format:",
            bg=BG, fg=FG
        ).pack(side="left")
        
        self.format_var = tk.StringVar(value="MP4 (Video)")
        self.format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.format_var,
            values=list(FORMATS.keys()),
            state="readonly",
            width=20
        )
        self.format_combo.pack(side="left", padx=8)
        self.format_combo.bind("<<ComboboxSelected>>", lambda e: self.update_format_visibility())

        # Quality frame (toggle)
        self.quality_frame = tk.Frame(self, bg=BG)
        self.quality_frame.pack(fill="x", pady=(6, 0))
        tk.Label(self.quality_frame, text="Quality:", bg=BG, fg=FG).pack(side="left")
        self.quality_var = tk.StringVar(value="1080p")
        self.quality_combo = ttk.Combobox(
            self.quality_frame,
            textvariable=self.quality_var,
            values=list(QUALITY_OPTIONS.keys()),
            state="readonly",
            width=18
        )
        self.quality_combo.pack(side="left", padx=8)

        # Output folder
        folder_frame = tk.Frame(self, bg=BG)
        folder_frame.pack(fill="x", pady=(6, 0))

        tk.Label(folder_frame, text="Output Folder:", bg=BG, fg=FG).pack(side="left")
        self.folder_var = tk.StringVar(value="")
        self.folder_entry = tk.Entry(
            folder_frame,
            textvariable=self.folder_var,
            bg=BOX, fg=FG,
            insertbackground=FG,
            width=30
        )
        self.folder_entry.pack(side="left", padx=8)
        tk.Button(
            folder_frame,
            text="Browse",
            bg=BTN, fg="white",
            command=self._browse_folder
        ).pack(side="left")

        # Advanced options toggle
        self.advanced_open = tk.BooleanVar(value=False)
        self.advanced_btn = tk.Button(
            self,
            text="▼ Advanced",
            bg=BOX, fg=FG,
            bd=0,
            command=self.toggle_advanced
        )
        self.advanced_btn.pack(anchor="w", pady=(6, 0))

        self.advanced_frame = tk.Frame(self, bg=BG)

        # Audio options
        self.audio_frame = tk.Frame(self.advanced_frame, bg=BG)
        self.audio_frame.pack(fill="x", pady=(6, 0))

        tk.Label(self.audio_frame, text="Audio Codec:", bg=BG, fg=FG).pack(side="left")
        self.audio_codec_var = tk.StringVar(value=AUDIO_CODECS[0])
        self.audio_codec_combo = ttk.Combobox(
            self.audio_frame,
            textvariable=self.audio_codec_var,
            values=AUDIO_CODECS,
            state="readonly",
            width=10
        )
        self.audio_codec_combo.pack(side="left", padx=8)

        tk.Label(self.audio_frame, text="Bitrate:", bg=BG, fg=FG).pack(side="left", padx=(10, 0))
        self.audio_bitrate_var = tk.StringVar(value=AUDIO_BITRATES[3])
        self.audio_bitrate_combo = ttk.Combobox(
            self.audio_frame,
            textvariable=self.audio_bitrate_var,
            values=AUDIO_BITRATES,
            state="readonly",
            width=8
        )
        self.audio_bitrate_combo.pack(side="left", padx=8)

        # Subtitles and embed options
        self.toggle_frame = tk.Frame(self.advanced_frame, bg=BG)
        self.toggle_frame.pack(fill="x", pady=(6, 0))

        self.embed_thumb_var = tk.BooleanVar(value=True)
        self.embed_meta_var = tk.BooleanVar(value=True)
        self.subs_var = tk.BooleanVar(value=False)
        self.auto_subs_var = tk.BooleanVar(value=False)
        self.sub_lang_var = tk.StringVar(value="en.*")

        tk.Checkbutton(self.toggle_frame, text="Embed Thumbnail", variable=self.embed_thumb_var, bg=BG, fg=FG, selectcolor=BOX).pack(side="left")
        tk.Checkbutton(self.toggle_frame, text="Embed Metadata", variable=self.embed_meta_var, bg=BG, fg=FG, selectcolor=BOX).pack(side="left", padx=8)
        tk.Checkbutton(self.toggle_frame, text="Subtitles", variable=self.subs_var, bg=BG, fg=FG, selectcolor=BOX).pack(side="left", padx=8)
        tk.Checkbutton(self.toggle_frame, text="Auto Subs", variable=self.auto_subs_var, bg=BG, fg=FG, selectcolor=BOX).pack(side="left", padx=8)

        self.lang_frame = tk.Frame(self.advanced_frame, bg=BG)
        self.lang_frame.pack(fill="x", pady=(6, 0))
        tk.Label(self.lang_frame, text="Subtitle Langs:", bg=BG, fg=FG).pack(side="left")
        tk.Entry(self.lang_frame, textvariable=self.sub_lang_var, bg=BOX, fg=FG, insertbackground=FG, width=20).pack(side="left", padx=8)

        self.update_format_visibility()
    
    def get_url(self) -> str:
        """Get URL from text widget"""
        return self.url_text.get("1.0", tk.END).strip()
    
    def clear(self):
        """Clear input"""
        self.url_text.delete("1.0", tk.END)
    
    def set_url(self, url: str):
        """Set URL"""
        self.url_text.delete("1.0", tk.END)
        self.url_text.insert("1.0", url)
    
    def get_format(self) -> str:
        """Get selected format"""
        return FORMATS.get(self.format_var.get(), "best")

    def update_format_visibility(self):
        fmt = self.get_format()
        video_qualities = ["2160p", "1440p", "1080p", "720p", "480p", "360p"]
        audio_qualities = ["Audio (320k)", "Audio (192k)"]

        show_quality = fmt in ("mp3", "mp4", "webm")
        if show_quality:
            if not self.quality_frame.winfo_ismapped():
                self.quality_frame.pack(fill="x", pady=(6, 0))
        else:
            if self.quality_frame.winfo_ismapped():
                self.quality_frame.pack_forget()

        if fmt in ("mp4", "webm"):
            self.quality_combo["values"] = video_qualities
            if self.quality_var.get() not in video_qualities:
                self.quality_var.set(video_qualities[0] if video_qualities else "")
        elif fmt == "mp3":
            self.quality_combo["values"] = audio_qualities
            if self.quality_var.get() not in audio_qualities:
                self.quality_var.set(audio_qualities[0] if audio_qualities else "")

        if fmt == "mp3":
            if not self.audio_frame.winfo_ismapped():
                self.audio_frame.pack(fill="x", pady=(6, 0))
        else:
            if self.audio_frame.winfo_ismapped():
                self.audio_frame.pack_forget()

        if fmt in ("jpg", "png"):
            if self.toggle_frame.winfo_ismapped():
                self.toggle_frame.pack_forget()
            if self.lang_frame.winfo_ismapped():
                self.lang_frame.pack_forget()
        else:
            if not self.toggle_frame.winfo_ismapped():
                self.toggle_frame.pack(fill="x", pady=(6, 0))
            if not self.lang_frame.winfo_ismapped():
                self.lang_frame.pack(fill="x", pady=(6, 0))

    def set_available_video_qualities(self, labels):
        """Restrict video quality dropdown to the given labels while keeping current selection if possible."""
        if not isinstance(labels, (list, tuple)) or not labels:
            return
        current = self.quality_var.get()
        self.quality_combo["values"] = labels
        if current in labels:
            # Keep current selection
            self.quality_var.set(current)
        else:
            # Default to Best if available
            self.quality_var.set(labels[0])

    def get_quality(self) -> str:
        """Get selected quality"""
        label = self.quality_var.get().strip()
        if label in QUALITY_OPTIONS:
            return QUALITY_OPTIONS[label]
        if re.match(r"^\d+p$", label):
            return label
        return "best"

    def get_output_folder(self) -> str:
        """Get output folder"""
        return self.folder_var.get().strip()

    def set_output_folder(self, folder: str):
        """Set output folder"""
        self.folder_var.set(folder)

    def get_audio_codec(self) -> str:
        return self.audio_codec_var.get()

    def get_audio_bitrate(self) -> str:
        return self.audio_bitrate_var.get()

    def get_embed_thumbnail(self) -> bool:
        return self.embed_thumb_var.get()

    def get_embed_metadata(self) -> bool:
        return self.embed_meta_var.get()

    def get_subtitles(self) -> bool:
        return self.subs_var.get()

    def get_auto_subtitles(self) -> bool:
        return self.auto_subs_var.get()

    def get_subtitle_langs(self) -> str:
        return self.sub_lang_var.get()

    def set_platform_hint(self, text: str):
        self.platform_hint.set(text)

    def set_save_preset_callback(self, callback):
        self.save_preset_btn.config(command=callback)

    def toggle_advanced(self):
        if self.advanced_open.get():
            self.advanced_frame.pack_forget()
            self.advanced_btn.config(text="▼ Advanced")
            self.advanced_open.set(False)
        else:
            self.advanced_frame.pack(fill="x", pady=(4, 0))
            self.advanced_btn.config(text="▲ Advanced")
            self.advanced_open.set(True)

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.folder_var.set(folder)

    def _on_drop(self, event):
        try:
            data = event.data.strip()
            if data:
                self.set_url(data)
        except Exception:
            pass

class DownloadTableFrame(tk.Frame):
    """Table showing active and queued downloads"""
    
    def __init__(self, parent, font_scale: float = 1.0, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.font_scale = font_scale
        
        tk.Label(
            self,
            text="Downloads",
            bg=BG, fg=FG,
            font=("Segoe UI", int(11 * self.font_scale))
        ).pack(anchor="w", pady=(0, 5))
        
        # Create Treeview
        self.tree = ttk.Treeview(
            self,
            columns=("File", "Status", "Size", "Speed", "ETA", "Progress"),
            height=6,
            show="headings"
        )
        
        # Define columns
        self.tree.column("File", width=150, anchor="w")
        self.tree.column("Status", width=80, anchor="center")
        self.tree.column("Size", width=80, anchor="center")
        self.tree.column("Speed", width=80, anchor="center")
        self.tree.column("ETA", width=60, anchor="center")
        self.tree.column("Progress", width=120, anchor="center")
        
        # Headers
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        
        # Styling
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=BOX, foreground=FG, fieldbackground=BOX)
        style.configure("Treeview.Heading", background="#333333", foreground=FG)
        style.map("Treeview", background=[("selected", BTN)])
        style.configure("Green.Horizontal.TProgressbar", troughcolor=BOX, bordercolor=BOX, background=GREEN, lightcolor=GREEN, darkcolor=GREEN)

        # Tag for active downloads to show a green background bar effect
        self.tree.tag_configure("downloading", background=GREEN, foreground="white")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.items = {}  # Map task id to tree item
    
    def add_download(self, task_id: str, filename: str):
        """Add download to table"""
        item = self.tree.insert("", "end", text=task_id)
        self.tree.set(item, "File", filename)
        self.tree.set(item, "Status", "Queued")
        self.tree.set(item, "Size", "-")
        self.tree.set(item, "Speed", "-")
        self.tree.set(item, "ETA", "-")
        self.tree.set(item, "Progress", "0%")
        self.items[task_id] = item
    
    def update_download(self, task_id: str, status: str, size: str, speed: str, eta: str, progress: float):
        """Update download progress"""
        if task_id in self.items:
            item = self.items[task_id]
            self.tree.set(item, "Status", status)
            self.tree.set(item, "Size", size)
            self.tree.set(item, "Speed", speed)
            self.tree.set(item, "ETA", eta)
            # Render text-based progress bar: all green filled blocks
            bar_len = 10
            filled = max(0, min(bar_len, int(progress / 10)))
            # Use green filled block █ for all (no empty blocks for cleaner look)
            bar = "█" * filled if filled > 0 else "▋" if progress > 0 else "░"
            # Pad to 10 chars
            bar = bar.ljust(bar_len, "░")
            progress_text = f"{bar} {progress:.1f}%"
            self.tree.set(item, "Progress", progress_text)

            # Highlight active downloads with a green row background
            if status.lower() == "downloading":
                self.tree.item(item, tags=("downloading",))
            else:
                self.tree.item(item, tags=())
    
    def remove_download(self, task_id: str):
        """Remove download from table"""
        if task_id in self.items:
            self.tree.delete(self.items[task_id])
            del self.items[task_id]
    
    def clear(self):
        """Clear all items"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.items.clear()

class HistoryFrame(tk.Frame):
    """Toggleable history panel"""
    
    def __init__(self, parent, font_scale: float = 1.0, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.font_scale = font_scale
        
        # Header with toggle button
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", pady=(0, 5))
        
        tk.Label(
            header,
            text="History",
            bg=BG, fg=FG,
            font=("Segoe UI", int(11 * self.font_scale))
        ).pack(side="left")
        
        self.toggle_btn = tk.Button(
            header,
            text="▼ Hide",
            bg=BOX, fg=FG,
            bd=0,
            command=self.toggle_history
        )
        self.toggle_btn.pack(side="right")
        
        # History content
        self.history_frame = tk.Frame(self, bg=BG)
        self.history_frame.pack(fill="both", expand=True)

        # Search
        search_frame = tk.Frame(self.history_frame, bg=BG)
        search_frame.pack(fill="x", pady=(0, 5))
        tk.Label(search_frame, text="Search:", bg=BG, fg=FG).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg=BOX, fg=FG, insertbackground=FG, width=30)
        self.search_entry.pack(side="left", padx=8)
        self.search_var.trace_add("write", lambda *_: self.apply_filter())
        
        # Treeview for history
        self.tree = ttk.Treeview(
            self.history_frame,
            columns=("File", "Location", "Format", "Status", "URL"),
            height=4,
            show="headings"
        )
        
        self.tree.column("File", width=120, anchor="w")
        self.tree.column("Location", width=200, anchor="w")
        self.tree.column("Format", width=60, anchor="center")
        self.tree.column("Status", width=60, anchor="center")
        self.tree.column("URL", width=200, anchor="w")
        
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        
        style = ttk.Style()
        style.configure("Treeview", background=BOX, foreground=FG, fieldbackground=BOX)
        style.configure("Treeview.Heading", background="#333333", foreground=FG)
        
        scrollbar = ttk.Scrollbar(self.history_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Action buttons
        action_frame = tk.Frame(self.history_frame, bg=BG)
        action_frame.pack(fill="x", pady=(6, 0))

        self.open_file_btn = tk.Button(action_frame, text="Open File", bg=BTN, fg="white")
        self.open_file_btn.pack(side="left", padx=4)
        self.open_folder_btn = tk.Button(action_frame, text="Open Folder", bg=BTN, fg="white")
        self.open_folder_btn.pack(side="left", padx=4)
        self.copy_url_btn = tk.Button(action_frame, text="Copy URL", bg=BTN, fg="white")
        self.copy_url_btn.pack(side="left", padx=4)
        self.export_csv_btn = tk.Button(action_frame, text="CSV", bg=BOX, fg=FG)
        self.export_csv_btn.pack(side="right", padx=4)
        self.export_json_btn = tk.Button(action_frame, text="JSON", bg=BOX, fg=FG)
        self.export_json_btn.pack(side="right", padx=4)

        self.is_open = True
        self._all_items = []
    
    def add_history_item(self, filename: str, location: str, format_name: str, status: str, url: str):
        """Add item to history"""
        item = (filename, location, format_name, status, url)
        self._all_items.insert(0, item)
        self.tree.insert("", 0, values=item)
        
        # Keep only last 20 items
        items = self.tree.get_children()
        while len(items) > 20:
            self.tree.delete(items[-1])
            items = self.tree.get_children()
    
    def clear_history(self):
        """Clear all history"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._all_items = []

    def apply_filter(self):
        """Filter history based on search"""
        query = self.search_var.get().lower().strip()
        self.tree.delete(*self.tree.get_children())
        for item in self._all_items:
            if not query or any(query in str(v).lower() for v in item):
                self.tree.insert("", tk.END, values=item)

    def get_selected(self):
        """Get selected history item"""
        selection = self.tree.selection()
        if not selection:
            return None
        values = self.tree.item(selection[0], "values")
        return {
            "file": values[0],
            "location": values[1],
            "format": values[2],
            "status": values[3],
            "url": values[4]
        }

    def set_actions(self, open_file_cb, open_folder_cb, copy_url_cb, export_csv_cb, export_json_cb):
        """Assign button actions"""
        self.open_file_btn.config(command=open_file_cb)
        self.open_folder_btn.config(command=open_folder_cb)
        self.copy_url_btn.config(command=copy_url_cb)
        self.export_csv_btn.config(command=export_csv_cb)
        self.export_json_btn.config(command=export_json_cb)
    
    def toggle_history(self):
        """Toggle history visibility"""
        if self.is_open:
            self.history_frame.pack_forget()
            self.toggle_btn.config(text="▶ Show")
            self.is_open = False
        else:
            self.history_frame.pack(fill="both", expand=True)
            self.toggle_btn.config(text="▼ Hide")
            self.is_open = True

class LogsFrame(tk.Frame):
    """Debug logs display"""
    
    def __init__(self, parent, font_scale: float = 1.0, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.font_scale = font_scale
        
        tk.Label(
            self,
            text="Logs",
            bg=BG, fg=FG,
            font=("Segoe UI", int(11 * self.font_scale))
        ).pack(anchor="w", pady=(0, 5))
        
        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True)
        log_scroll = tk.Scrollbar(log_frame, orient="vertical")
        self.log = tk.Text(
            log_frame,
            bg=BOX,
            fg=FG,
            insertbackground=FG,
            height=6,
            font=("Consolas", int(9 * self.font_scale)),
            yscrollcommand=log_scroll.set
        )
        log_scroll.config(command=self.log.yview)
        self.log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        error_header = tk.Frame(self, bg=BG)
        error_header.pack(fill="x", pady=(6, 2))
        tk.Label(error_header, text="Errors", bg=BG, fg=RED, font=("Segoe UI", int(10 * self.font_scale), "bold")).pack(side="left")
        self.copy_error_btn = tk.Button(error_header, text="Copy Errors", bg=BOX, fg=FG)
        self.copy_error_btn.pack(side="right")

        error_log_frame = tk.Frame(self, bg=BG)
        error_log_frame.pack(fill="both", expand=True)
        error_scroll = tk.Scrollbar(error_log_frame, orient="vertical")
        self.error_log = tk.Text(
            error_log_frame,
            bg=BOX,
            fg=RED,
            insertbackground=FG,
            height=4,
            font=("Consolas", int(9 * self.font_scale)),
            yscrollcommand=error_scroll.set
        )
        error_scroll.config(command=self.error_log.yview)
        self.error_log.pack(side="left", fill="both", expand=True)
        error_scroll.pack(side="right", fill="y")
    
    def add_log(self, message: str):
        """Add message to logs"""
        self.log.insert(tk.END, message)
        self.log.see(tk.END)

        if "error" in message.lower() or "failed" in message.lower():
            self.error_log.insert(tk.END, message)
            self.error_log.see(tk.END)
    
    def clear_logs(self):
        """Clear all logs"""
        self.log.delete("1.0", tk.END)
        self.error_log.delete("1.0", tk.END)

    def set_copy_errors_callback(self, callback):
        self.copy_error_btn.config(command=callback)

def get_save_file_dialog(format_choice: str, initialdir: str = "", filename: str = "") -> str:
    """Open file save dialog with appropriate extension"""
    ext = get_output_extension(format_choice)
    default_name = filename if filename else (f"download{ext}" if ext else "download")

    file = filedialog.asksaveasfilename(
        title="Save Download As",
        defaultextension=ext if ext else ".mp4",
        initialfile=default_name,
        initialdir=initialdir or None,
        filetypes=FILE_TYPES
    )

    return file
