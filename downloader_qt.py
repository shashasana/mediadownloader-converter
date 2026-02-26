"""Main Qt downloader application - Modern 2026 version"""

import os
import json
import uuid
import sys
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget, QMessageBox, QFileDialog,
    QScrollArea, QFrame, QMenuBar, QMenu, QCheckBox, QLineEdit,
    QSpinBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QRunnable, QThreadPool, Slot
from PySide6.QtGui import QFont, QIcon, QAction, QPixmap

import pyperclip

from config import (
    BG, FG, BOX, BTN, GREEN, RED, YELLOW,
    LIGHT_BG, LIGHT_FG, LIGHT_BOX, LIGHT_BTN, LIGHT_GREEN, LIGHT_RED, LIGHT_YELLOW,
    CHECK_CLIPBOARD_INTERVAL, SETTINGS_FILE, FORMATS, QUALITY_OPTIONS,
    YTDLP_PATH, FFMPEG_PATH
)
from download_manager import DownloadManager, DownloadTask, DownloadStatus
from downloader_core import detect_platform, get_output_extension, fetch_media_info
from ui_components_qt import (
    URLInputFrame, DownloadTableFrame, HistoryFrame, LogsFrame, AnimatedButton,
    FileConverterDialog
)

try:
    from plyer import notification
    NOTIFY_AVAILABLE = True
except Exception:
    NOTIFY_AVAILABLE = False


class PreviewWorker(QThread):
    """Worker thread for fetching media info and thumbnail"""
    preview_ready = Signal(dict)
    thumbnail_ready = Signal(object)
    error_signal = Signal(str)
    log_signal = Signal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            info = fetch_media_info(self.url, self.log_signal.emit)
            if info:
                self.preview_ready.emit(info)
                
                # Load thumbnail
                thumb = info.get("thumbnail") or (info.get("thumbnails")[-1]["url"] if info.get("thumbnails") else None)
                if thumb:
                    try:
                        import urllib.request
                        from PIL import Image
                        import io
                        
                        with urllib.request.urlopen(thumb, timeout=10) as response:
                            data = response.read()
                        image = Image.open(io.BytesIO(data))
                        image.thumbnail((96, 96))
                        
                        # Convert to QImage (thread-safe)
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        img_byte_arr = img_byte_arr.getvalue()

                        from PySide6.QtGui import QImage
                        image_obj = QImage.fromData(img_byte_arr)
                        self.thumbnail_ready.emit(image_obj)
                    except Exception as e:
                        self.error_signal.emit(f"Thumbnail error: {e}")
            else:
                self.error_signal.emit("Failed to fetch media info")
        except Exception as e:
            self.error_signal.emit(f"Preview error: {e}")


class ConversionWorker(QThread):
    """Worker thread for MP4 to MP3 conversion"""
    log_signal = Signal(str)
    finished_signal = Signal(int, int)
    
    def __init__(self, files, bitrate):
        super().__init__()
        self.files = files
        self.bitrate = bitrate
    
    def run(self):
        success_count = 0
        for i, input_file in enumerate(self.files, 1):
            try:
                output_file = os.path.splitext(input_file)[0] + ".mp3"
                
                self.log_signal.emit(f"[{i}/{len(self.files)}] Converting: {os.path.basename(input_file)}\n")
                
                # Use ffmpeg to convert
                cmd = [
                    FFMPEG_PATH,
                    "-i", input_file,
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-b:a", self.bitrate,
                    "-y",
                    output_file
                ]
                
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if process.returncode == 0:
                    self.log_signal.emit(f"✓ Converted: {os.path.basename(output_file)}\n")
                    success_count += 1
                else:
                    self.log_signal.emit(f"✗ Failed: {os.path.basename(input_file)}\n")
            
            except Exception as e:
                self.log_signal.emit(f"✗ Error: {str(e)}\n")
        
        self.finished_signal.emit(success_count, len(self.files))


class FileConversionWorker(QThread):
    """Worker thread for universal file conversion"""
    log_signal = Signal(str)
    finished_signal = Signal(bool, str, bool)  # success, output_file, open_after
    
    def __init__(self, input_file, output_format, quality, sample_rate, ffmpeg_path, open_after=False, output_file_path=None, gif_mode="reduce_fps"):
        super().__init__()
        self.input_file = input_file
        self.output_format = output_format
        self.quality = quality
        self.sample_rate = sample_rate
        self.ffmpeg_path = ffmpeg_path
        self.open_after = open_after
        self.gif_mode = gif_mode or "reduce_fps"
        # Use provided output path or generate default
        if output_file_path:
            self.output_file = output_file_path
        else:
            self.output_file = os.path.join(
                os.path.dirname(self.input_file),
                f"{os.path.splitext(os.path.basename(self.input_file))[0]}.{self.output_format}"
            )
    
    def run(self):
        from downloader_core import convert_file
        
        def log_callback(msg):
            self.log_signal.emit(msg)
        
        success = convert_file(
            self.input_file,
            self.output_format,
            self.quality,
            self.sample_rate,
            self.ffmpeg_path,
            log_callback,
            output_file_path=self.output_file,
            gif_mode=self.gif_mode
        )
        self.finished_signal.emit(success, self.output_file, self.open_after)


class BatchFileConversionWorker(QThread):
    """Worker thread for batch file conversion"""
    log_signal = Signal(str)
    single_file_done = Signal(str, bool, str)  # output_file, success, error_msg
    finished_signal = Signal(int, int)  # completed_count, total_count
    
    def __init__(self, input_files, output_format, quality, sample_rate, ffmpeg_path, output_folder=None, gif_mode="reduce_fps"):
        super().__init__()
        self.input_files = input_files
        self.output_format = output_format
        self.quality = quality
        self.sample_rate = sample_rate
        self.ffmpeg_path = ffmpeg_path
        self.output_folder = os.path.normpath(output_folder) if output_folder else ""
        self.gif_mode = gif_mode or "reduce_fps"
        self._should_stop = False
    
    def stop(self):
        """Signal thread to stop"""
        self._should_stop = True
    
    def run(self):
        from downloader_core import convert_file
        
        completed_count = 0
        total_count = len(self.input_files)
        
        self.log_signal.emit(f"Starting batch conversion of {total_count} file(s)...\n")
        
        for idx, input_file in enumerate(self.input_files, 1):
            if self._should_stop:
                self.log_signal.emit("Batch conversion cancelled\n")
                break
            
            try:
                target_dir = self.output_folder or os.path.dirname(input_file)
                output_file = os.path.join(
                    target_dir,
                    f"{os.path.splitext(os.path.basename(input_file))[0]}.{self.output_format}"
                )
                
                self.log_signal.emit(f"[{idx}/{total_count}] Converting: {os.path.basename(input_file)}...\n")
                
                def log_callback(msg):
                    self.log_signal.emit(msg)
                
                success = convert_file(
                    input_file,
                    self.output_format,
                    self.quality,
                    self.sample_rate,
                    self.ffmpeg_path,
                    log_callback,
                    output_file_path=output_file,
                    gif_mode=self.gif_mode
                )
                
                if success:
                    self.log_signal.emit(f"✓ Completed: {os.path.basename(output_file)}\n")
                    self.single_file_done.emit(output_file, True, "")
                    completed_count += 1
                else:
                    error_msg = f"Failed to convert {os.path.basename(input_file)}"
                    self.log_signal.emit(f"✗ {error_msg}\n")
                    self.single_file_done.emit(output_file, False, error_msg)
            
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.log_signal.emit(f"✗ {error_msg}\n")
                self.single_file_done.emit("", False, error_msg)
        
        self.log_signal.emit(f"\n=== Batch conversion complete: {completed_count}/{total_count} files converted ===\n")
        self.finished_signal.emit(completed_count, total_count)


class UpdateResourcesWorker(QThread):
    """Worker to update external resources like yt-dlp"""
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)  # success, message

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            messages = []
            success = True

            # Update yt-dlp
            if not os.path.exists(YTDLP_PATH):
                messages.append("yt-dlp.exe not found. Check YTDLP_PATH in config.py")
                success = False
            else:
                self.log_signal.emit("Updating yt-dlp...\n")
                result = subprocess.run(
                    [YTDLP_PATH, "-U"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if result.returncode == 0:
                    if result.stdout:
                        self.log_signal.emit(result.stdout + "\n")
                    messages.append("yt-dlp updated successfully.")
                else:
                    if result.stderr:
                        self.log_signal.emit(result.stderr + "\n")
                    messages.append("yt-dlp update failed. See logs for details.")
                    success = False

            # Update Python packages
            self.log_signal.emit("Updating Python packages...\n")
            pkg_list = [
                "PySide6", "pyperclip", "Pillow", "pdf2image",
                "python-docx", "openpyxl", "reportlab", "PyPDF2",
                "fastanime", "beautifulsoup4", "playwright", "selenium",
                "anipy-cli"
            ]
            pip_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", *pkg_list],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if pip_result.returncode == 0:
                if pip_result.stdout:
                    self.log_signal.emit(pip_result.stdout + "\n")
                messages.append("Python packages updated successfully.")
            else:
                if pip_result.stderr:
                    self.log_signal.emit(pip_result.stderr + "\n")
                messages.append("Python packages update failed. See logs for details.")
                success = False

            messages.append("FFmpeg is not auto-updated. Please update it manually if needed.")
            self.finished_signal.emit(success, "\n".join(messages))
        except Exception as e:
            self.finished_signal.emit(False, f"Update failed: {e}")


class DownloadWorker(QThread):
    """Worker thread for downloading media"""
    progress_signal = Signal()
    log_signal = Signal(str)
    completed_signal = Signal(bool)  # success
    
    def __init__(self, task, manager, settings):
        super().__init__()
        self.task = task
        self.manager = manager
        self.settings = settings
        self._last_progress_time = 0
        self._progress_throttle = 0.5  # Emit progress max 2 times per second (reduced from 3)
        self._log_buffer = []
        self._last_log_time = 0
        self._log_throttle = 0.2  # Emit logs max 5 times per second (reduced from 10)
        self._should_stop = False
    
    def stop(self):
        """Signal thread to stop - non-blocking"""
        self._should_stop = True
        if self.task and self.task.process:
            # Perform process termination in background to avoid blocking UI
            def terminate_process_async():
                try:
                    # Try taskkill first on Windows
                    if os.name == 'nt':
                        try:
                            subprocess.run(['taskkill', '/F', '/PID', str(self.task.process.pid)], 
                                         capture_output=True, timeout=2)
                            return
                        except:
                            pass
                    # Fallback to terminate
                    try:
                        self.task.process.terminate()
                        # Wait a bit for graceful termination
                        self.task.process.wait(timeout=2)
                    except:
                        try:
                            self.task.process.kill()
                        except:
                            pass
                except Exception:
                    pass
            
            # Run termination in daemon thread to avoid blocking
            import threading
            thread = threading.Thread(target=terminate_process_async, daemon=True)
            thread.start()
    
    def run(self):
        from downloader_core import download_task
        import time
        
        try:
            def on_progress(t):
                # Throttle progress updates to prevent UI flooding
                now = time.time()
                if now - self._last_progress_time >= self._progress_throttle:
                    self._last_progress_time = now
                    self.progress_signal.emit()
            
            def on_log(msg):
                # Buffer logs and emit in batches
                self._log_buffer.append(msg)
                now = time.time()
                if now - self._last_log_time >= self._log_throttle:
                    self._last_log_time = now
                    if self._log_buffer:
                        combined = "".join(self._log_buffer)
                        self._log_buffer.clear()
                        self.log_signal.emit(combined)
            
            # Run the download
            download_task(self.task, self.manager, self.settings, on_progress, on_log)
            
            # Flush any remaining logs
            if self._log_buffer:
                combined = "".join(self._log_buffer)
                self._log_buffer.clear()
                self.log_signal.emit(combined)
            
            # Emit completion
            success = self.task.status == DownloadStatus.COMPLETED
            self.completed_signal.emit(success)
        
        except Exception as e:
            # Catch any unhandled exceptions to prevent app crash
            self.log_signal.emit(f"✗ Worker error: {str(e)}\n")
            self.completed_signal.emit(False)


class DownloaderAppQt(QMainWindow):
    """Modern Qt-based downloader application"""
    
    # Signals for thread-safe UI updates
    log_signal = Signal(str)
    progress_signal = Signal()
    download_completed_signal = Signal()  # Thread-safe completion
    history_updated_signal = Signal()  # Thread-safe history updates
    
    def __init__(self):
        super().__init__()
        
        self._is_shutting_down = False  # Flag to prevent new threads during shutdown
        
        self.settings = self.load_settings()
        self.manager = DownloadManager(max_downloads=self.settings.get("max_concurrent", 3))
        self.manager.subscribe("download_progress", self.on_download_progress)
        # Emit signal instead of calling directly to ensure it runs on main thread
        self.download_completed_signal.connect(self.on_download_completed)
        self.manager.subscribe("download_completed", lambda: self.download_completed_signal.emit())
        # Subscribe to history updates
        self.history_updated_signal.connect(self.load_history)
        self.manager.subscribe("history_updated", lambda: self.history_updated_signal.emit())
        
        self.clipboard_enabled = self.settings.get("clipboard_enabled", False)
        self.clipboard_auto_add = self.settings.get("clipboard_auto_add", False)
        self.last_clip = ""
        self.task_map = {}
        self.info_cache = {}
        self.thumbnail_cache = {}
        self.url_input_focused = False
        self._preview_in_progress = False
        self._log_buffer = []
        self._log_flush_timer = QTimer()
        self._log_flush_timer.setSingleShot(True)
        self._log_flush_timer.timeout.connect(self._flush_logs)
        self._auto_preview_timer = QTimer()
        self._auto_preview_timer.setSingleShot(True)
        self._auto_preview_timer.timeout.connect(self.preview_all_media)
        
        # Connect signals
        self.log_signal.connect(self.add_log_safe)
        self.progress_signal.connect(self.update_all_downloads)
        
        self.setup_ui()
        self.apply_theme()
        
        # Timers
        self.clipboard_timer = QTimer()
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(CHECK_CLIPBOARD_INTERVAL * 1000)
        
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.process_queue)
        self.queue_timer.start(1000)  # Reduced frequency from 500ms to 1000ms
    
    def load_settings(self):
        settings = {
            "max_concurrent": 3,
            "clipboard_enabled": False,
            "clipboard_auto_add": False,
            "download_folder": "~/Downloads",
            "overwrite_policy": "ask",
            "notifications": True,
            "theme": "dark",
            "high_contrast": False,
            "font_scale": 1.0,
            "minimize_to_tray": False,
            "retry_count": 2,
            "retry_delay": 3,
            "embed_thumbnail": True,
            "embed_metadata": True,
            "quality_choice": "best",
            "audio_codec": "mp3",
            "audio_bitrate": "320k",
            "presets": {}
        }
        
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
    
    def closeEvent(self, event):
        """Properly clean up threads before closing"""
        # Set flag to prevent new threads from starting
        self._is_shutting_down = True
        
        try:
            # Stop timers first
            if hasattr(self, 'clipboard_timer'):
                self.clipboard_timer.stop()
            if hasattr(self, 'queue_timer'):
                self.queue_timer.stop()
            
            # Disconnect all signals before cleanup
            if hasattr(self, 'progress_signal'):
                try:
                    self.progress_signal.disconnect()
                except:
                    pass
            if hasattr(self, 'log_signal'):
                try:
                    self.log_signal.disconnect()
                except:
                    pass
            
            # Clean up all download workers - call stop() first to kill subprocesses
            if hasattr(self, '_download_workers'):
                for task_id, worker in list(self._download_workers.items()):
                    if worker:
                        try:
                            # Call stop() to force kill subprocess with taskkill
                            if hasattr(worker, 'stop'):
                                worker.stop()
                            # Disconnect signals
                            worker.progress_signal.disconnect()
                            worker.log_signal.disconnect()
                            worker.completed_signal.disconnect()
                            worker.finished.disconnect()
                        except:
                            pass
                        
                        if worker.isRunning():
                            worker.quit()
                            if not worker.wait(2000):
                                worker.terminate()
                                worker.wait(500)
                self._download_workers.clear()
            
            # Clean up bulk preview workers
            if hasattr(self, '_bulk_preview_workers'):
                for worker in self._bulk_preview_workers[:]:
                    if worker:
                        try:
                            worker.finished.disconnect()
                        except:
                            pass
                        if worker.isRunning():
                            worker.quit()
                            if not worker.wait(2000):
                                worker.terminate()
                                worker.wait(500)
                self._bulk_preview_workers.clear()
            
            # Clean up file conversion worker
            if hasattr(self, '_file_conversion_worker'):
                if self._file_conversion_worker:
                    try:
                        self._file_conversion_worker.finished.disconnect()
                    except:
                        pass
                    if self._file_conversion_worker.isRunning():
                        self._file_conversion_worker.quit()
                        if not self._file_conversion_worker.wait(2000):
                            self._file_conversion_worker.terminate()
                            self._file_conversion_worker.wait(500)
                    self._file_conversion_worker = None
            
            # Clean up batch file conversion worker
            if hasattr(self, '_batch_file_conversion_worker'):
                if self._batch_file_conversion_worker:
                    try:
                        if hasattr(self._batch_file_conversion_worker, 'stop'):
                            self._batch_file_conversion_worker.stop()
                        self._batch_file_conversion_worker.finished.disconnect()
                    except:
                        pass
                    if self._batch_file_conversion_worker.isRunning():
                        self._batch_file_conversion_worker.quit()
                        if not self._batch_file_conversion_worker.wait(2000):
                            self._batch_file_conversion_worker.terminate()
                            self._batch_file_conversion_worker.wait(500)
                    self._batch_file_conversion_worker = None
            
            # Clean up update resources worker
            if hasattr(self, '_update_resources_worker'):
                if self._update_resources_worker:
                    try:
                        self._update_resources_worker.finished.disconnect()
                    except:
                        pass
                    if self._update_resources_worker.isRunning():
                        self._update_resources_worker.quit()
                        if not self._update_resources_worker.wait(2000):
                            self._update_resources_worker.terminate()
                            self._update_resources_worker.wait(500)
                    self._update_resources_worker = None
            
            self.save_settings()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        event.accept()
    
    def setup_ui(self):
        self.setWindowTitle("Media Downloader - Qt Modern")
        self.setGeometry(100, 100, 1100, 900)
        
        # Menu bar
        self.create_menu_bar()
        
        # Central widget with scrollable content
        central = QWidget()
        self.setCentralWidget(central)
        central_layout = QVBoxLayout(central)
        central_layout.setSpacing(0)
        central_layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        central_layout.addWidget(self.main_scroll)
        
        content = QWidget()
        self.main_scroll.setWidget(content)
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Main downloader panel (hidden on converter tab)
        self.main_panel = QWidget()
        main_panel_layout = QVBoxLayout(self.main_panel)
        main_panel_layout.setSpacing(15)
        main_panel_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Media Downloader")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_panel_layout.addWidget(title)
        
        # URL Input Frame
        self.url_frame = URLInputFrame()
        self.url_frame.url_changed.connect(self.update_platform_hint)
        self.url_frame.url_changed.connect(self._schedule_auto_preview)
        self.url_frame.url_changed.connect(self._update_button_visibility)
        self.url_frame.duplicate_urls_detected.connect(self._show_duplicate_url_warning)
        self.url_frame.format_combo.currentTextChanged.connect(self._on_format_changed)
        self.url_frame.url_input.focusInEvent = lambda e: self._on_url_focus_in(e)
        self.url_frame.url_input.focusOutEvent = lambda e: self._on_url_focus_out(e)
        self.url_frame.set_output_folder(os.path.expanduser(
            self.settings.get("download_folder", "~/Downloads")
        ))
        main_panel_layout.addWidget(self.url_frame)
        
        # Preview section with bulk support
        self.preview_container = QWidget()
        preview_container_layout = QVBoxLayout(self.preview_container)
        preview_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_header_widget = QWidget()
        preview_header = QHBoxLayout(self.preview_header_widget)
        preview_header.setContentsMargins(0, 0, 0, 0)
        preview_btn = AnimatedButton("Preview All URLs")
        preview_btn.clicked.connect(self.preview_all_media)
        preview_header.addWidget(preview_btn)
        
        clear_previews_btn = AnimatedButton("Clear Previews")
        clear_previews_btn.clicked.connect(self.clear_previews)
        preview_header.addWidget(clear_previews_btn)
        preview_header.addStretch()
        preview_container_layout.addWidget(self.preview_header_widget)
        
        # Preview cards (show all without scroll cap)
        from ui_components_qt import FlowLayout
        self.preview_cards_frame = QFrame()
        self.preview_cards_frame.setStyleSheet(
            "QFrame { border: 1px solid #444; border-radius: 4px; background-color: #1a1a1a; }"
        )
        self.preview_cards_layout = FlowLayout(self.preview_cards_frame, margin=10, spacing=10)
        preview_container_layout.addWidget(self.preview_cards_frame)
        
        main_panel_layout.addWidget(self.preview_container)
        
        # Store preview cards
        self.preview_cards = {}
        
        # Action buttons
        btn_frame = QWidget()
        btn_layout = QHBoxLayout(btn_frame)
        
        self.add_queue_btn = AnimatedButton("Add to Queue")
        self.add_queue_btn.clicked.connect(self.add_to_queue)
        self.add_queue_btn.setStyleSheet("background-color: #31a24c; color: white; font-weight: bold;")
        btn_layout.addWidget(self.add_queue_btn)
        
        self.download_now_btn = AnimatedButton("Download Now")
        self.download_now_btn.clicked.connect(self.download_now)
        btn_layout.addWidget(self.download_now_btn)
        
        # Initially hide add_queue_btn (only show when multiple URLs)
        self.add_queue_btn.hide()
        
        btn_layout.addStretch()
        main_panel_layout.addWidget(btn_frame)

        main_layout.addWidget(self.main_panel)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Downloads tab
        downloads_widget = QWidget()
        downloads_layout = QVBoxLayout(downloads_widget)
        self.download_table = DownloadTableFrame()
        downloads_layout.addWidget(self.download_table, 1)  # Stretch to expand with window
        
        # Download controls
        control_layout = QHBoxLayout()
        self.pause_btn = AnimatedButton("Pause")
        self.pause_btn.clicked.connect(self.pause_selected)
        control_layout.addWidget(self.pause_btn)
        
        self.resume_btn = AnimatedButton("Resume")
        self.resume_btn.clicked.connect(self.resume_selected)
        control_layout.addWidget(self.resume_btn)
        
        self.retry_btn = AnimatedButton("Retry")
        self.retry_btn.clicked.connect(self.retry_selected)
        control_layout.addWidget(self.retry_btn)
        
        self.cancel_download_btn = AnimatedButton("Cancel")
        self.cancel_download_btn.clicked.connect(self.cancel_selected)
        control_layout.addWidget(self.cancel_download_btn)
        
        control_layout.addStretch()
        downloads_layout.addLayout(control_layout)
        
        # Hide download control buttons initially
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.retry_btn.hide()
        self.cancel_download_btn.hide()
        
        self.tabs.addTab(downloads_widget, "Downloads")
        
        # History tab
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        self.history_frame = HistoryFrame()
        history_layout.addWidget(self.history_frame)
        
        # History controls
        history_control_layout = QHBoxLayout()
        self.open_file_btn = AnimatedButton("Open File")
        self.open_file_btn.clicked.connect(self.open_history_file)
        history_control_layout.addWidget(self.open_file_btn)
        
        self.open_folder_btn = AnimatedButton("Open Folder")
        self.open_folder_btn.clicked.connect(self.open_history_folder)
        history_control_layout.addWidget(self.open_folder_btn)
        
        # Hide history buttons initially
        self.open_file_btn.hide()
        self.open_folder_btn.hide()
        
        history_control_layout.addStretch()
        history_layout.addLayout(history_control_layout)
        
        self.tabs.addTab(history_widget, "History")
        
        # Logs tab
        self.logs_frame = LogsFrame()
        self.tabs.addTab(self.logs_frame, "Logs")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        main_layout.addWidget(self.tabs)
        
        # Load history
        self.load_history()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.clear()
        
        # Files menu
        file_menu = menubar.addMenu("Files")
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Top-level converter action
        converter_action = QAction("Converter", self)
        converter_action.triggered.connect(self.open_file_converter)
        menubar.addAction(converter_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def apply_theme(self):
        theme = self.settings.get("theme", "dark")
        
        if theme == "dark":
            bg, fg, box, btn = BG, FG, BOX, BTN
            green, red, yellow = GREEN, RED, YELLOW
            border_color = "#444"
            grid_color = "#333"
            hint_color = "#FFC107"
        else:
            bg, fg, box, btn = LIGHT_BG, LIGHT_FG, LIGHT_BOX, LIGHT_BTN
            green, red, yellow = LIGHT_GREEN, LIGHT_RED, LIGHT_YELLOW
            border_color = "#cbd5e1"
            grid_color = "#e5e7eb"
            hint_color = "#8a6b00"
        
        stylesheet = f"""
            QMainWindow {{
                background-color: {bg};
            }}
            QWidget {{
                background-color: {bg};
                color: {fg};
                font-family: "Segoe UI";
                font-size: 10pt;
            }}
            QLabel {{
                color: {fg};
            }}
            QPushButton {{
                background-color: {btn};
                color: white;
                border: 1px solid {btn};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {btn}dd;
                border: 1px solid {btn}dd;
            }}
            QPushButton:pressed {{
                background-color: {btn};
                border: 1px solid {btn};
                color: white;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {box};
                color: {fg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px;
            }}
            QTableWidget {{
                background-color: {box};
                color: {fg};
                gridline-color: {grid_color};
                border-radius: 6px;
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {btn};
            }}
            QHeaderView::section {{
                background-color: {box};
                color: {fg};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            QTabWidget::pane {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {bg};
            }}
            QTabBar::tab {{
                background-color: {box};
                color: {fg};
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {btn};
                color: white;
            }}
            QMenuBar {{
                background-color: {box};
                color: {fg};
            }}
            QMenuBar::item:selected {{
                background-color: {btn};
            }}
            QMenu {{
                background-color: {box};
                color: {fg};
                border: 1px solid {border_color};
            }}
            QMenu::item:selected {{
                background-color: {btn};
            }}
            QMessageBox QPushButton, QDialogButtonBox QPushButton {{
                background-color: {btn};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QDialogButtonBox::button {{
                background-color: {btn};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QDialogButtonBox::button:hover, QMessageBox QPushButton:hover {{
                background-color: {btn}dd;
                color: white;
            }}
            QDialogButtonBox::button:pressed, QMessageBox QPushButton:pressed {{
                background-color: {btn}aa;
                color: white;
            }}
        """
        
        self.setStyleSheet(stylesheet)
        self._apply_preview_card_theme()
        self._apply_preview_container_theme()

        # Update platform hint color for current theme
        try:
            self.url_frame.platform_hint.setStyleSheet(f"color: {hint_color};")
        except Exception:
            pass

    def _apply_preview_card_theme(self):
        theme = self.settings.get("theme", "dark")
        for card in self.preview_cards.values():
            try:
                card.apply_theme(theme)
            except Exception:
                pass

    def _apply_preview_container_theme(self):
        theme = self.settings.get("theme", "dark")
        if hasattr(self, "preview_cards_frame"):
            if theme == "light":
                self.preview_cards_frame.setStyleSheet(
                    "QFrame { border: 1px solid #cbd5e1; border-radius: 4px; background-color: #ffffff; }"
                )
            else:
                self.preview_cards_frame.setStyleSheet(
                    "QFrame { border: 1px solid #444; border-radius: 4px; background-color: #1a1a1a; }"
                )
    
    def update_platform_hint(self, url):
        if url.startswith("http"):
            platform = detect_platform(url)
            self.url_frame.set_platform_hint(f"Platform: {platform}")

    def _show_duplicate_url_warning(self, duplicate_urls):
        """Show warning when duplicate URLs are detected in input"""
        if not duplicate_urls:
            return
        
        dup_list = "\n".join([f"• {url[:80]}..." if len(url) > 80 else f"• {url}" for url in duplicate_urls])
        QMessageBox.warning(
            self,
            "Duplicate URLs Detected",
            f"The following URL(s) appear multiple times in the input field:\n\n{dup_list}\n\n"
            "Duplicates will be automatically removed when previewing or downloading."
        )

    def _update_button_visibility(self, url_text):
        """Show Add to Queue when there are URLs"""
        urls = self.url_frame.get_urls()
        if len(urls) >= 1:
            self.add_queue_btn.show()
        else:
            self.add_queue_btn.hide()
        
        # Auto-clear previews when URL text is empty
        if not url_text:
            self.clear_previews()

    def _schedule_auto_preview(self, url_text):
        if not url_text:
            return
        # Debounce to avoid firing on every keystroke
        self._auto_preview_timer.start(600)

    def _on_format_changed(self, _value):
        url_text = self.url_frame.get_url()
        if not url_text:
            return
        self._refresh_preview_sizes()
        self._auto_preview_timer.start(300)

    def _refresh_preview_sizes(self):
        format_choice = self.url_frame.get_format()
        for url, card in self.preview_cards.items():
            info = self.info_cache.get(url)
            if not info:
                continue
            title = info.get("title", "Unknown")
            uploader = info.get("uploader", "Unknown")
            duration = info.get("duration", 0)
            size_str = self._get_expected_size_str(info, format_choice)

            if duration >= 3600:
                duration_str = f"{duration // 3600}h {(duration % 3600) // 60}m"
            elif duration >= 60:
                duration_str = f"{duration // 60}m {duration % 60}s"
            else:
                duration_str = f"{duration}s"

            info_text = f"{uploader}\n{duration_str} | {size_str}"
            card.set_data(title, info_text)
    
    def _on_url_focus_in(self, event):
        """Track when user is typing in URL field"""
        self.url_input_focused = True
        from PySide6.QtWidgets import QTextEdit
        QTextEdit.focusInEvent(self.url_frame.url_input, event)
    
    def _on_url_focus_out(self, event):
        """Track when user leaves URL field"""
        self.url_input_focused = False
        from PySide6.QtWidgets import QTextEdit
        QTextEdit.focusOutEvent(self.url_frame.url_input, event)

    def _set_preview_collapsed(self, collapsed: bool):
        """Collapse or expand preview area"""
        if not hasattr(self, "preview_cards_frame") or not hasattr(self, "preview_container"):
            return
        if collapsed:
            self.preview_cards_frame.setVisible(False)
            header_height = self.preview_header_widget.sizeHint().height() if hasattr(self, "preview_header_widget") else 0
            target_height = header_height + 12
            self.preview_container.setMinimumHeight(target_height)
            self.preview_container.setMaximumHeight(target_height)
        else:
            self.preview_cards_frame.setVisible(True)
            self.preview_container.setMinimumHeight(0)
            self.preview_container.setMaximumHeight(16777215)
    
    def preview_all_media(self):
        """Preview all URLs entered"""
        urls = self.url_frame.get_urls()
        
        if not urls:
            QMessageBox.warning(self, "Missing", "Enter media URL(s)")
            return
        
        self._set_preview_collapsed(False)
        
        # Clear existing previews
        self.clear_previews()
        
        self.log_signal.emit(f"Previewing {len(urls)} URL(s)...\n")
        self._preview_in_progress = True
        
        # Create preview card for each URL
        for url in urls:
            from ui_components_qt import PreviewCard
            card = PreviewCard()
            card.set_loading(url)
            card.apply_theme(self.settings.get("theme", "dark"))
            self.preview_cards[url] = card
            self.preview_cards_layout.addWidget(card)
        
        # Fetch info for each URL asynchronously
        class BulkPreviewWorker(QThread):
            single_preview_ready = Signal(str, dict)  # url, info
            single_thumbnail_ready = Signal(str, object)  # url, image
            single_error = Signal(str)  # url
            log_signal = Signal(str)
            
            def __init__(self, urls):
                super().__init__()
                self.urls = urls
            
            def run(self):
                for url in self.urls:
                    try:
                        info = fetch_media_info(url, self.log_signal.emit)
                        if info:
                            self.single_preview_ready.emit(url, info)
                            
                            # Load thumbnail
                            thumb = info.get("thumbnail") or (info.get("thumbnails")[-1]["url"] if info.get("thumbnails") else None)
                            if thumb:
                                try:
                                    import urllib.request
                                    from PIL import Image
                                    import io
                                    
                                    with urllib.request.urlopen(thumb, timeout=10) as response:
                                        data = response.read()
                                    image = Image.open(io.BytesIO(data))
                                    image.thumbnail((80, 80))
                                    
                                    img_byte_arr = io.BytesIO()
                                    image.save(img_byte_arr, format='PNG')
                                    img_byte_arr = img_byte_arr.getvalue()
                                    
                                    from PySide6.QtGui import QImage
                                    image_obj = QImage.fromData(img_byte_arr)
                                    self.single_thumbnail_ready.emit(url, image_obj)
                                except Exception:
                                    pass
                        else:
                            self.single_error.emit(url)
                    except Exception:
                        self.single_error.emit(url)
        
        worker = BulkPreviewWorker(urls)
        worker.single_preview_ready.connect(self.on_single_preview_ready)
        worker.single_thumbnail_ready.connect(self.on_single_thumbnail_ready)
        worker.single_error.connect(self.on_single_preview_error)
        worker.log_signal.connect(self.add_log_safe)
        worker.finished.connect(lambda *args: setattr(self, "_preview_in_progress", False))
        worker.start()
        
        # Keep reference
        if not hasattr(self, '_bulk_preview_workers'):
            self._bulk_preview_workers = []
        self._bulk_preview_workers.append(worker)
        worker.finished.connect(lambda: self._bulk_preview_workers.remove(worker) if worker in self._bulk_preview_workers else None)
    
    def on_single_preview_ready(self, url, info):
        """Handle single preview ready"""
        if url in self.preview_cards:
            title = info.get("title", "Unknown")
            uploader = info.get("uploader", "Unknown")
            duration = info.get("duration", 0)
            
            size_str = self._get_expected_size_str(info, self.url_frame.get_format())
            
            # Format duration
            if duration >= 3600:
                duration_str = f"{duration // 3600}h {(duration % 3600) // 60}m"
            elif duration >= 60:
                duration_str = f"{duration // 60}m {duration % 60}s"
            else:
                duration_str = f"{duration}s"
            
            info_text = f"{uploader}\n{duration_str} | {size_str}"
            
            self.preview_cards[url].set_data(title, info_text)
            self.info_cache[url] = info
            thumb_url = info.get("thumbnail")
            if thumb_url:
                self._cache_thumbnail_for_url(url, thumb_url)
    
    def on_single_thumbnail_ready(self, url, image_obj):
        """Handle single thumbnail ready"""
        if url in self.preview_cards:
            card = self.preview_cards[url]
            # Update thumbnail on existing card
            pixmap = QPixmap.fromImage(image_obj)
            card.thumbnail.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _cache_thumbnail_for_url(self, url: str, thumb_url: str):
        """Download and cache thumbnail for later embedding."""
        if url in self.thumbnail_cache:
            return
        import threading
        import hashlib
        import urllib.request

        def _worker():
            try:
                output_folder = self.url_frame.get_output_folder() or os.path.expanduser(
                    self.settings.get("download_folder", "~/Downloads")
                )
                cache_dir = os.path.join(os.path.expanduser(output_folder), ".thumb_cache")
                os.makedirs(cache_dir, exist_ok=True)
                url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
                ext = ".jpg"
                lower = thumb_url.lower()
                if ".png" in lower:
                    ext = ".png"
                elif ".webp" in lower:
                    ext = ".webp"
                file_path = os.path.join(cache_dir, f"{url_hash}{ext}")
                with urllib.request.urlopen(thumb_url, timeout=15) as response:
                    data = response.read()
                with open(file_path, "wb") as f:
                    f.write(data)
                self.thumbnail_cache[url] = file_path
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
    
    def on_single_preview_error(self, url):
        """Handle single preview error"""
        if url in self.preview_cards:
            self.preview_cards[url].set_error(url)
    
    def clear_previews(self):
        """Clear all preview cards"""
        # Remove all widgets from layout first
        while self.preview_cards_layout.count() > 0:
            item = self.preview_cards_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        # Clear the dictionary
        self.preview_cards.clear()
        self.info_cache.clear()
    
    def is_url_already_downloading(self, url):
        """Check if URL is already in download queue or history"""
        # Check current tasks in queue
        for task in self.task_map.values():
            if task.url == url:
                return True
        
        # Check in manager's queue
        for task in self.manager.queue:
            if task.url == url:
                return True
        
        # Check in manager's active downloads
        for task in self.manager.active_downloads:
            if task.url == url:
                return True
        
        return False
    
    def add_to_queue(self):
        """Add URL(s) to download queue"""
        urls = self.url_frame.get_urls()
        
        if not urls:
            QMessageBox.warning(self, "Missing", "Enter media URL(s)")
            return
        
        # Check for duplicate URLs already downloading
        duplicate_urls = [url for url in urls if self.is_url_already_downloading(url)]
        if duplicate_urls:
            dup_list = "\n".join([f"• {url}" for url in duplicate_urls])
            reply = QMessageBox.question(
                self,
                "Duplicate URLs",
                f"The following URL(s) are already in the queue:\n\n{dup_list}\n\nContinue with remaining URLs?"
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            # Filter out duplicates
            urls = [url for url in urls if url not in duplicate_urls]
            if not urls:
                self.log_signal.emit("All URL(s) are already in queue. Skipped.\n")
                return
        
        # Check if previews exist
        missing_previews = [url for url in urls if url not in self.info_cache]
        if missing_previews:
            reply = QMessageBox.question(
                self,
                "No Previews",
                f"{len(missing_previews)} URL(s) don't have preview info.\n"
                "Files will be named 'download - unknown'.\n\n"
                "Click 'Preview All URLs' first for proper filenames.\n\n"
                "Continue anyway?"
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        format_choice = self.url_frame.get_format()
        added_count = 0
        
        self.log_signal.emit(f"Adding {len(urls)} URL(s) to queue...\n")
        
        for idx, url in enumerate(urls, 1):
            if not url.startswith("http"):
                self.log_signal.emit(f"Skipped invalid URL: {url}\n")
                continue
            
            if not self.manager.is_queue_available():
                QMessageBox.warning(self, "Limit", f"Queue is full ({self.settings.get('max_concurrent', 3)} max). Added {added_count} of {len(urls)} URLs.")
                break
            
            output_folder = self.url_frame.get_output_folder() or os.path.expanduser(
                self.settings.get("download_folder", "~/Downloads")
            )
            output_folder = os.path.expanduser(output_folder)
            os.makedirs(output_folder, exist_ok=True)
            
            filename = self.build_filename(url)
            ext = get_output_extension(format_choice)
            save_path = os.path.join(output_folder, f"{filename}{ext}")
            
            if os.path.exists(save_path):
                action = self.settings.get("overwrite_policy", "ask")
                if action == "ask":
                    reply = QMessageBox.question(self, "File exists", f"File exists: {os.path.basename(save_path)}\nOverwrite?")
                    if reply != QMessageBox.StandardButton.Yes:
                        self.log_signal.emit(f"Skipped existing file: {os.path.basename(save_path)}\n")
                        continue
                elif action == "skip":
                    self.log_signal.emit(f"Skipped duplicate file: {os.path.basename(save_path)}\n")
                    continue
            
            platform = detect_platform(url)
            task = DownloadTask(
                url=url,
                path=save_path,
                format_choice=format_choice,
                platform=platform
            )
            task.thumbnail_path = self.thumbnail_cache.get(url, "")
            task.thumbnail_url = self.info_cache.get(url, {}).get("thumbnail", "")

            # Use preview size for selected format if available
            info = self.info_cache.get(url, {})
            size_val = self._get_expected_size_value(info, format_choice)
            if size_val:
                task.file_size = self._format_size_value(size_val)
            
            task_id = str(uuid.uuid4())
            self.task_map[task_id] = task
            self.manager.add_task(task)
            
            self.download_table.add_download(task_id, os.path.basename(save_path))
            # Update size immediately if known
            self.download_table.update_download(
                task_id,
                task.status.value,
                task.file_size,
                task.speed,
                task.eta,
                task.progress
            )
            self.log_signal.emit(f"[{idx}/{len(urls)}] Added: {os.path.basename(save_path)}\n")
            added_count += 1
        
        # Update button visibility after adding downloads
        self._update_download_buttons_visibility()
        
        if added_count > 0:
            self.url_frame.clear()
            self.clear_previews()
            self.log_signal.emit(f"Successfully added {added_count} download(s) to queue\n")
            self.process_queue()
        elif len(urls) > 0:
            self.log_signal.emit("No URLs were added to queue\n")
    
    def download_now(self):
        """Immediate download"""
        try:
            # Don't start new downloads during shutdown
            if self._is_shutting_down:
                return
            
            url = self.url_frame.get_url()
            format_choice = self.url_frame.get_format()
            
            if not url:
                QMessageBox.warning(self, "Missing", "Enter a media URL")
                return
            
            # Check if URL is already downloading
            if self.is_url_already_downloading(url):
                QMessageBox.warning(
                    self,
                    "Duplicate URL",
                    f"This URL is already in the download queue.\n\n{url}"
                )
                return

            if self._preview_in_progress:
                QMessageBox.information(self, "Preview in progress", "Preview is still fetching. Please wait.")
                return
            
            output_folder = self.url_frame.get_output_folder() or os.path.expanduser(
                self.settings.get("download_folder", "~/Downloads")
            )
            output_folder = os.path.expanduser(output_folder)
            os.makedirs(output_folder, exist_ok=True)
            
            filename = self.build_filename(url)
            ext = get_output_extension(format_choice)
            save_path = os.path.join(output_folder, f"{filename}{ext}")
            
            platform = detect_platform(url)
            task = DownloadTask(
                url=url,
                path=save_path,
                format_choice=format_choice,
                platform=platform
            )
            task.thumbnail_path = self.thumbnail_cache.get(url, "")
            task.thumbnail_url = self.info_cache.get(url, {}).get("thumbnail", "")

            info = self.info_cache.get(url, {})
            size_val = self._get_expected_size_value(info, format_choice)
            if size_val:
                task.file_size = self._format_size_value(size_val)
            
            task_id = str(uuid.uuid4())
            self.task_map[task_id] = task
            
            self.download_table.add_download(task_id, os.path.basename(save_path))
            self.log_signal.emit(f"Starting download: {url}\n")
            self.url_frame.clear()
            self._set_preview_collapsed(True)
            
            # Update button visibility
            self._update_download_buttons_visibility()
            
            # Start download with QThread worker
            worker = DownloadWorker(task, self.manager, self.get_download_settings())
            worker.progress_signal.connect(self.progress_signal.emit)
            worker.log_signal.connect(self.add_log_safe)
            worker.completed_signal.connect(lambda *args: None)  # Handled by manager
            worker.start()
            
            # Keep reference
            if not hasattr(self, '_download_workers'):
                self._download_workers = {}
            self._download_workers[task_id] = worker
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Download error: {str(e)}")
            self.log_signal.emit(f"✗ Download error: {str(e)}\n")
    
    def process_queue(self):
        """Process next item in queue"""
        try:
            # Don't process queue during shutdown
            if self._is_shutting_down:
                return
            
            if self.manager.get_active_count() >= self.settings.get("max_concurrent", 3):
                return
            
            task = self.manager.get_next_task()
            if task:
                task_id = None
                for tid, t in self.task_map.items():
                    if t is task:
                        task_id = tid
                        break
                
                if task_id:
                    task.status = DownloadStatus.DOWNLOADING
                    self._set_preview_collapsed(True)
                    self.download_table.update_download(
                        task_id,
                        task.status.value,
                        task.file_size,
                        task.speed,
                        task.eta,
                        task.progress
                    )
                    self.log_signal.emit(f"Downloading: {task.url}\n")
                    
                    # Start download with QThread worker
                    worker = DownloadWorker(task, self.manager, self.get_download_settings())
                    worker.progress_signal.connect(self.progress_signal.emit)
                    worker.log_signal.connect(self.add_log_safe)
                    worker.completed_signal.connect(lambda *args: None)  # Handled by manager
                    worker.start()
                    
                    # Keep reference
                    if not hasattr(self, '_download_workers'):
                        self._download_workers = {}
                    self._download_workers[task_id] = worker
        except Exception as e:
            self.log_signal.emit(f"✗ Queue processing error: {str(e)}\n")
    
    def pause_selected(self):
        """Pause selected download - non-blocking"""
        selected = self.download_table.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        task_id = self.download_table.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task = self.task_map.get(task_id)
        if task:
            self.manager.pause_task(task)
            
            # Pause process in background
            if task.process:
                def pause_process_async():
                    try:
                        self.task.process.terminate()
                    except Exception:
                        pass
                
                import threading
                thread = threading.Thread(target=pause_process_async, daemon=True)
                thread.start()
            
            self.log_signal.emit("Paused download\n")
    
    def resume_selected(self):
        """Resume selected download"""
        selected = self.download_table.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        task_id = self.download_table.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task = self.task_map.get(task_id)
        if task and task.status == DownloadStatus.PAUSED:
            self.manager.resume_task(task)
            self.process_queue()
            self.log_signal.emit("Resumed download\n")
    
    def cancel_selected(self):
        """Cancel selected download - non-blocking"""
        selected = self.download_table.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        task_id = self.download_table.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task = self.task_map.get(task_id)
        if task:
            self.manager.cancel_task(task)
            
            # Terminate process in background to avoid blocking UI
            if task.process and task_id in self._download_workers:
                worker = self._download_workers.get(task_id)
                if worker:
                    worker.stop()  # This will handle async termination
            
            self.log_signal.emit("Cancelled download\n")
    
    def retry_selected(self):
        """Retry selected failed download from scratch"""
        selected = self.download_table.table.selectedItems()
        if not selected:
            self.log_signal.emit("No download selected\n")
            return
        
        row = selected[0].row()
        task_id = self.download_table.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task = self.task_map.get(task_id)
        
        if not task:
            self.log_signal.emit("Task not found\n")
            return
        
        if task.status not in [DownloadStatus.FAILED, DownloadStatus.COMPLETED]:
            self.log_signal.emit("Can only retry failed or completed downloads\n")
            return

        # Remove any partially downloaded files before retrying
        try:
            output_dir = os.path.dirname(task.path)
            base_name = os.path.splitext(os.path.basename(task.path))[0]
            if os.path.isdir(output_dir):
                for file in os.listdir(output_dir):
                    if file.startswith(base_name) and file.lower().endswith(
                        (".mp3", ".webm", ".m4a", ".mp4", ".part", ".webp", ".jpg", ".jpeg", ".png")
                    ):
                        try:
                            os.remove(os.path.join(output_dir, file))
                        except Exception:
                            pass
            elif os.path.isfile(task.path):
                os.remove(task.path)
        except Exception:
            pass
        
        # Clean up old worker thread if it exists
        if hasattr(self, '_download_workers') and task_id in self._download_workers:
            old_worker = self._download_workers.pop(task_id)
            if old_worker:
                try:
                    # Kill subprocess first
                    if hasattr(old_worker, 'stop'):
                        old_worker.stop()
                    # Then stop the thread
                    if old_worker.isRunning():
                        old_worker.quit()
                        old_worker.wait(500)
                        if old_worker.isRunning():
                            old_worker.terminate()
                            old_worker.wait(500)
                except:
                    pass
        
        # Reset task to queued state
        task.status = DownloadStatus.QUEUED
        task.process = None
        task.last_error = ""
        task.progress = 0.0
        task.speed = ""
        task.eta = ""
        
        # Add back to manager's queue
        if task not in self.manager.queue:
            self.manager.queue.append(task)
        
        # Update UI
        self.download_table.update_download(
            task_id,
            task.status.value,
            task.file_size,
            task.speed,
            task.eta,
            task.progress
        )
        self.download_table.table.selectRow(row)
        
        # Retry the download
        self.log_signal.emit(f"Retrying download: {os.path.basename(task.path)}\n")
        self.process_queue()
    
    def on_download_progress(self):
        """Update UI on download progress"""
        self.progress_signal.emit()
    
    def update_all_downloads(self):
        """Update all download rows - batched to reduce overhead"""
        if not hasattr(self, '_update_pending'):
            self._update_pending = False
        
        if self._update_pending:
            return
        
        self._update_pending = True
        QTimer.singleShot(1000, self._do_update_downloads)  # Increased from 500ms to 1000ms
    
    def _do_update_downloads(self):
        """Actually perform the UI updates - only update changed items"""
        if not hasattr(self, '_task_state_cache'):
            self._task_state_cache = {}
        
        # Disable updates during batch operation to prevent multiple repaints
        self.download_table.table.setUpdatesEnabled(False)
        try:
            for task_id, task in self.task_map.items():
                # Create current state tuple
                current_state = (
                    task.status.value,
                    task.file_size,
                    task.speed,
                    task.eta,
                    round(task.progress, 1)  # Round to reduce precision changes
                )
                
                # Only update if state changed
                if self._task_state_cache.get(task_id) != current_state:
                    self._task_state_cache[task_id] = current_state
                    self.download_table.update_download(
                        task_id,
                        task.status.value,
                        task.file_size,
                        task.speed,
                        task.eta,
                        task.progress
                    )
        finally:
            self.download_table.table.setUpdatesEnabled(True)
        self._update_pending = False
        
        # Update button visibility in case downloads were removed
        self._update_download_buttons_visibility()
    
    def on_download_completed(self):
        """Handle download completion"""
        for task_id, task in list(self.task_map.items()):
            if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
                self.download_table.update_download(
                    task_id,
                    task.status.value,
                    task.file_size,
                    task.speed,
                    task.eta,
                    task.progress
                )
                
                # Clean up worker thread - wait for it to finish
                if hasattr(self, '_download_workers') and task_id in self._download_workers:
                    worker = self._download_workers.pop(task_id)
                    if worker:
                        try:
                            # Give thread a moment to finish gracefully
                            if worker.isRunning():
                                worker.quit()
                                if not worker.wait(1000):
                                    worker.terminate()
                                    worker.wait(500)
                        except Exception:
                            pass
        
        # Defer heavy operations to next event loop iteration
        QTimer.singleShot(10, self._show_completion_ui)
        self.process_queue()
    
    def _show_notification(self):
        """Show notification in background thread"""
        if NOTIFY_AVAILABLE and self.settings.get("notifications", True):
            try:
                notification.notify(
                    title="Download Complete",
                    message="Your download has finished!",
                    timeout=5
                )
            except Exception:
                pass
    
    def _show_completion_ui(self):
        """Show completion notification and update history (deferred)"""
        # Defer heavy operations to background/timers
        import threading
        
        # Show notification in background thread (non-blocking)
        threading.Thread(target=self._show_notification, daemon=True).start()
        
        # Defer history loading to next event cycle
        #QTimer.singleShot(50, self.load_history) # DISABLED - causes freeze
        
        # Show message box (non-modal so UI stays responsive)
        if self.manager.history and self.manager.history[0].get("status") == DownloadStatus.COMPLETED.value:
            latest = self.manager.history[0]
            path = os.path.join(latest["location"], latest["file"])
            msg = QMessageBox(self)
            msg.setWindowTitle("Download Complete")
            msg.setText("Open the downloaded file?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setModal(False)
            msg.buttonClicked.connect(lambda btn, p=path: self._open_file_path(p)
                                      if msg.standardButton(btn) == QMessageBox.StandardButton.Yes else None)
            msg.show()
    
    def build_filename(self, url: str) -> str:
        """Build filename from URL and info"""
        info = self.info_cache.get(url, {})
        title = info.get("title", "download")
        uploader = info.get("uploader", "unknown")
        
        # Sanitize filename
        import re
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        uploader = re.sub(r'[<>:"/\\|?*]', '', uploader)
        
        # Use template from settings (don't include date)
        template = self.settings.get("filename_template", "{title}")
        try:
            filename = template.format(title=title, uploader=uploader)
        except KeyError:
            # If template has unknown fields, fall back to title only
            filename = title
        
        return filename[:200]  # Limit length
    
    def get_download_settings(self) -> dict:
        """Get current download settings"""
        return {
            "quality_choice": self.url_frame.get_quality(),
            "audio_codec": self.url_frame.get_audio_codec(),
            "audio_bitrate": self.url_frame.get_audio_bitrate(),
            "embed_thumbnail": self.settings.get("embed_thumbnail", True),
            "embed_metadata": self.settings.get("embed_metadata", True),
            "subtitles": self.settings.get("subtitles", False),
            "auto_subtitles": self.settings.get("auto_subtitles", False),
            "subtitle_langs": self.settings.get("subtitle_langs", "en.*"),
            "retry_count": self.settings.get("retry_count", 2),
            "retry_delay": self.settings.get("retry_delay", 3)
        }
    
    def check_clipboard(self):
        """Check clipboard for URLs"""
        if not self.clipboard_enabled or self.url_input_focused:
            return
        
        try:
            text = pyperclip.paste()
            if text != self.last_clip and text.startswith("http"):
                # Only update if URL field is empty or hasn't been modified
                current_url = self.url_frame.get_url()
                if not current_url or current_url == self.last_clip:
                    self.url_frame.set_url(text)
                    platform = detect_platform(text)
                    self.url_frame.set_platform_hint(f"Platform: {platform}")
                    
                    if self.clipboard_auto_add:
                        self.add_to_queue()
                
                self.last_clip = text
        except:
            pass
    
    def load_history(self):
        """Load history into table"""
        self.history_frame.clear_all()
        for item in self.manager.history[:20]:
            self.history_frame.add_history_item(
                item["file"],
                item["location"],
                item["format"],
                item["status"],
                item["url"]
            )
        
        # Update button visibility
        self._update_history_buttons_visibility()
    
    def open_history_file(self):
        """Open file from history"""
        item = self.history_frame.get_selected()
        if not item:
            return
        path = os.path.join(item["location"], item["file"])
        self._open_file_path(path)
    
    def open_history_folder(self):
        """Open folder from history"""
        item = self.history_frame.get_selected()
        if not item:
            return
        self._open_folder_path(item["location"])
    
    def _open_file_path(self, path: str):
        """Open file with system default"""
        if not path:
            return
        
        path = os.path.normpath(os.path.expanduser(path))
        
        if not os.path.exists(path):
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
            QMessageBox.critical(self, "Open Failed", f"File not found: {path}")
            return
        
        try:
            os.startfile(path)
        except Exception as e:
            try:
                subprocess.Popen(["explorer", "/select,", path])
            except Exception:
                QMessageBox.critical(self, "Open Failed", f"Could not open: {path}\nError: {str(e)}")
    
    def _open_folder_path(self, path: str):
        """Open folder"""
        if not path or not os.path.exists(path):
            QMessageBox.critical(self, "Open Failed", f"Folder not found: {path}")
            return
        
        try:
            os.startfile(path)
        except Exception:
            try:
                subprocess.Popen(["explorer", path])
            except Exception as e:
                QMessageBox.critical(self, "Open Failed", f"Could not open: {path}")
    
    def save_current_preset(self):
        """Save current settings as preset"""
        # Simplified for now
        QMessageBox.information(self, "Preset", "Preset saving coming soon!")
    
    def add_log_safe(self, message):
        """Thread-safe log addition"""
        self._log_buffer.append(message)
        if not self._log_flush_timer.isActive():
            self._log_flush_timer.start(500)

    def _flush_logs(self):
        if not self._log_buffer:
            return
        combined = "".join(self._log_buffer)
        self._log_buffer.clear()
        self.logs_frame.add_log_raw(combined)
        
        # Update logs button visibility
        self._update_logs_button_visibility()

    def _format_size_value(self, size_val):
        try:
            if size_val >= 1000**3:
                return f"{size_val / (1000**3):.2f} GB"
            return f"{size_val / (1000**2):.1f} MB"
        except Exception:
            return "Unknown"

    def _get_expected_size_str(self, info: dict, format_choice: str) -> str:
        size_val = self._get_expected_size_value(info, format_choice)
        if not size_val:
            return "Size: Unknown"
        return f"Size: {self._format_size_value(size_val)}"

    def _get_expected_size_value(self, info: dict, format_choice: str):
        try:
            formats = info.get("formats") or []
            candidates = []
            if format_choice == "mp3":
                candidates = [f for f in formats if f.get("vcodec") == "none"]
            elif format_choice in ("mp4", "webm"):
                candidates = [f for f in formats if f.get("ext") == format_choice and f.get("vcodec") != "none"]
            if not candidates:
                candidates = formats

            best_size = 0
            for fmt in candidates:
                filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0
                if filesize > best_size:
                    best_size = filesize
            return best_size if best_size > 0 else None
        except Exception:
            return None
    
    def open_settings(self):
        """Open settings dialog"""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QScrollArea, QGroupBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumSize(600, 700)
        
        main_layout = QVBoxLayout(dialog)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # General settings group
        general_group = QGroupBox("General")
        general_layout = QVBoxLayout(general_group)
        
        clipboard_check = QCheckBox("Enable Clipboard Detection")
        clipboard_check.setChecked(self.settings.get("clipboard_enabled", False))
        general_layout.addWidget(clipboard_check)
        
        auto_add_check = QCheckBox("Auto-add Clipboard URLs")
        auto_add_check.setChecked(self.settings.get("clipboard_auto_add", False))
        general_layout.addWidget(auto_add_check)
        
        notify_check = QCheckBox("Enable Notifications")
        notify_check.setChecked(self.settings.get("notifications", True))
        general_layout.addWidget(notify_check)

        update_resources_btn = QPushButton("Update Resources (yt-dlp + Python packages)")
        update_resources_btn.clicked.connect(self.update_resources)
        general_layout.addWidget(update_resources_btn)

        update_ffmpeg_btn = QPushButton("Update FFmpeg (open download page)")
        update_ffmpeg_btn.clicked.connect(self.open_ffmpeg_update_page)
        general_layout.addWidget(update_ffmpeg_btn)
        
        layout.addWidget(general_group)
        
        # Download settings group
        download_group = QGroupBox("Downloads")
        download_layout = QVBoxLayout(download_group)
        
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("Max Concurrent Downloads:"))
        max_spin = QSpinBox()
        max_spin.setRange(1, 10)
        max_spin.setValue(self.settings.get("max_concurrent", 3))
        max_layout.addWidget(max_spin)
        max_layout.addStretch()
        download_layout.addLayout(max_layout)
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Download Folder:"))
        folder_input = QLineEdit()
        folder_input.setText(os.path.expanduser(self.settings.get("download_folder", "~/Downloads")))
        folder_layout.addWidget(folder_input)
        browse_folder_btn = QPushButton("Browse")
        browse_folder_btn.clicked.connect(lambda: folder_input.setText(
            QFileDialog.getExistingDirectory(dialog, "Select Download Folder") or folder_input.text()
        ))
        folder_layout.addWidget(browse_folder_btn)
        download_layout.addLayout(folder_layout)
        
        overwrite_layout = QHBoxLayout()
        overwrite_layout.addWidget(QLabel("Overwrite Policy:"))
        overwrite_combo = QComboBox()
        overwrite_combo.addItems(["ask", "overwrite", "skip"])
        overwrite_combo.setCurrentText(self.settings.get("overwrite_policy", "ask"))
        overwrite_layout.addWidget(overwrite_combo)
        overwrite_layout.addStretch()
        download_layout.addLayout(overwrite_layout)
        
        retry_layout = QHBoxLayout()
        retry_layout.addWidget(QLabel("Retry Count:"))
        retry_spin = QSpinBox()
        retry_spin.setRange(0, 10)
        retry_spin.setValue(self.settings.get("retry_count", 2))
        retry_layout.addWidget(retry_spin)
        retry_layout.addWidget(QLabel("Delay (seconds):"))
        delay_spin = QSpinBox()
        delay_spin.setRange(1, 60)
        delay_spin.setValue(self.settings.get("retry_delay", 3))
        retry_layout.addWidget(delay_spin)
        retry_layout.addStretch()
        download_layout.addLayout(retry_layout)
        
        layout.addWidget(download_group)
        
        # Media settings group
        media_group = QGroupBox("Media Options")
        media_layout = QVBoxLayout(media_group)
        
        embed_thumb_check = QCheckBox("Embed Thumbnail")
        embed_thumb_check.setChecked(self.settings.get("embed_thumbnail", True))
        media_layout.addWidget(embed_thumb_check)
        
        embed_meta_check = QCheckBox("Embed Metadata")
        embed_meta_check.setChecked(self.settings.get("embed_metadata", True))
        media_layout.addWidget(embed_meta_check)
        
        subtitles_check = QCheckBox("Download Subtitles")
        subtitles_check.setChecked(self.settings.get("subtitles", False))
        media_layout.addWidget(subtitles_check)
        
        auto_subs_check = QCheckBox("Download Auto-generated Subtitles")
        auto_subs_check.setChecked(self.settings.get("auto_subtitles", False))
        media_layout.addWidget(auto_subs_check)
        
        layout.addWidget(media_group)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        theme_combo = QComboBox()
        theme_combo.addItems(["dark", "light"])
        theme_combo.setCurrentText(self.settings.get("theme", "dark"))
        theme_layout.addWidget(theme_combo)
        theme_layout.addStretch()
        appearance_layout.addLayout(theme_layout)
        
        contrast_check = QCheckBox("High Contrast Mode")
        contrast_check.setChecked(self.settings.get("high_contrast", False))
        appearance_layout.addWidget(contrast_check)
        
        layout.addWidget(appearance_group)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_color = LIGHT_BTN if self.settings.get("theme", "dark") == "light" else BTN
        button_box.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {btn_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_color}dd;
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {btn_color}aa;
                color: white;
            }}
            """
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        main_layout.addWidget(button_box)
        
        if dialog.exec():
            self.settings["clipboard_enabled"] = clipboard_check.isChecked()
            self.settings["clipboard_auto_add"] = auto_add_check.isChecked()
            self.settings["notifications"] = notify_check.isChecked()
            self.settings["max_concurrent"] = max_spin.value()
            self.settings["download_folder"] = folder_input.text()
            self.settings["overwrite_policy"] = overwrite_combo.currentText()
            self.settings["retry_count"] = retry_spin.value()
            self.settings["retry_delay"] = delay_spin.value()
            self.settings["embed_thumbnail"] = embed_thumb_check.isChecked()
            self.settings["embed_metadata"] = embed_meta_check.isChecked()
            self.settings["subtitles"] = subtitles_check.isChecked()
            self.settings["auto_subtitles"] = auto_subs_check.isChecked()
            self.settings["theme"] = theme_combo.currentText()
            self.settings["high_contrast"] = contrast_check.isChecked()
            
            self.clipboard_enabled = self.settings["clipboard_enabled"]
            self.clipboard_auto_add = self.settings["clipboard_auto_add"]
            self.manager.max_downloads = self.settings["max_concurrent"]
            
            self.save_settings()
            self.apply_theme()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About",
            "Media Downloader Qt\nModern 2026 Edition\n\nBuilt with PySide6"
        )

    def update_resources(self):
        """Update external resources like yt-dlp"""
        QMessageBox.information(self, "Update Resources", "Update started. Check Logs for progress.")
        worker = UpdateResourcesWorker()
        worker.log_signal.connect(self.add_log_safe)
        worker.finished_signal.connect(lambda success, msg: QMessageBox.information(
            self,
            "Update Resources",
            msg
        ))
        worker.start()

        if not hasattr(self, '_update_resources_worker'):
            self._update_resources_worker = None
        self._update_resources_worker = worker

    def open_ffmpeg_update_page(self):
        """Open FFmpeg download page and current FFmpeg folder"""
        try:
            import webbrowser
            webbrowser.open("https://www.gyan.dev/ffmpeg/builds/")
        except Exception:
            pass
        try:
            ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
            if ffmpeg_dir and os.path.exists(ffmpeg_dir):
                os.startfile(ffmpeg_dir)
        except Exception:
            pass
    
    def open_file_converter(self):
        """Open universal file converter in a new tab"""
        if hasattr(self, "_file_converter_tab") and self._file_converter_tab is not None:
            index = self.tabs.indexOf(self._file_converter_tab)
            if index != -1:
                self.tabs.setCurrentIndex(index)
                return

        converter_tab = FileConverterDialog(self)
        converter_tab.convert_requested.connect(self.start_file_conversion)
        converter_tab.back_to_downloader.connect(lambda: self.tabs.setCurrentIndex(0))  # Switch to downloads tab
        self._file_converter_tab = converter_tab
        self.tabs.addTab(converter_tab, "File Converter")
        self.tabs.setCurrentWidget(converter_tab)

    def _on_tab_changed(self, index):
        current = self.tabs.widget(index)
        if hasattr(self, "_file_converter_tab") and current == self._file_converter_tab:
            self.main_panel.setVisible(False)
        else:
            self.main_panel.setVisible(True)
            self._restore_previews_if_needed()
    
    def _update_download_buttons_visibility(self):
        """Show/hide download control buttons based on whether there are downloads"""
        has_downloads = self.download_table.table.rowCount() > 0
        self.pause_btn.setVisible(has_downloads)
        self.resume_btn.setVisible(has_downloads)
        self.retry_btn.setVisible(has_downloads)
        self.cancel_download_btn.setVisible(has_downloads)
    
    def _update_history_buttons_visibility(self):
        """Show/hide history buttons based on whether there's history"""
        has_history = self.history_frame.table.rowCount() > 0
        self.open_file_btn.setVisible(has_history)
        self.open_folder_btn.setVisible(has_history)
    
    def _update_logs_button_visibility(self):
        """Show/hide clear logs button based on whether there are logs"""
        has_logs = len(self.logs_frame.log_text.toPlainText().strip()) > 0
        self.logs_frame.clear_btn.setVisible(has_logs)

    def _restore_previews_if_needed(self):
        if self.preview_cards:
            return
        if not self.info_cache:
            return

        from ui_components_qt import PreviewCard
        for url, info in self.info_cache.items():
            card = PreviewCard()
            card.apply_theme(self.settings.get("theme", "dark"))

            title = info.get("title", "Unknown")
            uploader = info.get("uploader", "Unknown")
            duration = info.get("duration", 0)

            size_str = "Size: Unknown"
            try:
                formats = info.get("formats") or []
                best_size = 0
                for fmt in formats:
                    filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0
                    if filesize > best_size:
                        best_size = filesize

                if best_size > 0:
                    if best_size >= 1000**3:  # GB
                        size_str = f"Size: {best_size / (1000**3):.2f} GB"
                    else:  # MB
                        size_str = f"Size: {best_size / (1000**2):.1f} MB"
            except Exception:
                pass

            if duration >= 3600:
                duration_str = f"{duration // 3600}h {(duration % 3600) // 60}m"
            elif duration >= 60:
                duration_str = f"{duration // 60}m {duration % 60}s"
            else:
                duration_str = f"{duration}s"

            info_text = f"{uploader}\n{duration_str} | {size_str}"
            card.set_data(title, info_text)

            self.preview_cards[url] = card
            self.preview_cards_layout.addWidget(card)
    
    def start_file_conversion(self, input_files, output_format, quality, sample_rate, output_folder, open_after, is_batch=False, gif_mode="reduce_fps"):
        """Start file conversion in worker thread (handles single or batch)"""
        # Convert input_files to list if it's a single file
        if isinstance(input_files, str):
            input_files = [input_files]

        # Use provided output folder or default
        if not output_folder:
            output_folder = os.path.expanduser(self.settings.get("download_folder", "~/Downloads"))
        output_folder = os.path.normpath(output_folder)
        os.makedirs(output_folder, exist_ok=True)
        
        # Handle batch vs single conversion
        if len(input_files) > 1:
            # Batch conversion
            self.log_signal.emit(f"Starting batch conversion of {len(input_files)} files...\n")
            worker = BatchFileConversionWorker(input_files, output_format, quality, sample_rate, FFMPEG_PATH, output_folder, gif_mode)
            worker.log_signal.connect(self.add_log_safe)
            worker.single_file_done.connect(self.on_single_conversion_done)
            worker.finished_signal.connect(self.on_batch_conversion_finished)
            worker.start()
            
            if not hasattr(self, '_batch_file_conversion_worker'):
                self._batch_file_conversion_worker = None
            self._batch_file_conversion_worker = worker
        else:
            # Single file conversion
            input_file = input_files[0]
            output_file = os.path.join(
                output_folder,
                f"{os.path.splitext(os.path.basename(input_file))[0]}.{output_format}"
            )
            if os.path.abspath(output_file) == os.path.abspath(input_file):
                output_file = os.path.join(
                    output_folder,
                    f"{os.path.splitext(os.path.basename(input_file))[0]}_converted.{output_format}"
                )
            self.log_signal.emit(f"Starting conversion: {os.path.basename(input_file)} → {os.path.basename(output_file)}\n")
            
            worker = FileConversionWorker(input_file, output_format, quality, sample_rate, FFMPEG_PATH, open_after, output_file_path=output_file, gif_mode=gif_mode)
            worker.log_signal.connect(self.add_log_safe)
            worker.finished_signal.connect(self.on_conversion_finished)
            worker.start()
            
            if not hasattr(self, '_file_conversion_worker'):
                self._file_conversion_worker = None
            self._file_conversion_worker = worker
    
    def on_conversion_finished(self, success, output_file, open_after):
        """Handle conversion completion"""
        if success:
            # Create custom message box with folder button
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Conversion Complete")
            msg_box.setText(f"File converted successfully!\n\nOutput: {os.path.basename(output_file)}")
            msg_box.setInformativeText(f"Location: {os.path.normpath(os.path.dirname(output_file))}")
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            # Add Open Folder button
            open_folder_btn = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(QMessageBox.StandardButton.Ok)
            
            msg_box.exec()
            
            # Handle button clicks
            if msg_box.clickedButton() == open_folder_btn:
                try:
                    if os.name == 'nt':
                        subprocess.Popen(["explorer", "/select,", os.path.normpath(output_file)])
                    else:
                        subprocess.Popen(["xdg-open", os.path.dirname(output_file)])
                except Exception:
                    pass
            
            if open_after and output_file and os.path.exists(output_file):
                try:
                    os.startfile(output_file)
                except Exception:
                    pass
            # Send completion notification
            try:
                if NOTIFY_AVAILABLE and self.settings.get("notifications", True):
                    notification.notify(
                        title="Conversion Complete",
                        message=os.path.basename(output_file),
                        timeout=5
                    )
            except Exception:
                pass
            # Show back button after successful conversion
            if hasattr(self, '_file_converter_tab'):
                self._file_converter_tab.back_btn.show()
                self._file_converter_tab.convert_btn.hide()
                self._file_converter_tab.cancel_btn.hide()
        else:
            ext = os.path.splitext(output_file)[1].lstrip(".") if output_file else ""
            target = ext.upper() if ext else "target format"
            QMessageBox.critical(
                self,
                "Conversion Failed",
                f"Failed to convert file to {target}.\n\nThis format may not be supported. Check logs for details."
            )
            # Show back button after failed conversion too
            if hasattr(self, '_file_converter_tab'):
                self._file_converter_tab.back_btn.show()
                self._file_converter_tab.convert_btn.hide()
                self._file_converter_tab.cancel_btn.hide()
    
    def on_single_conversion_done(self, output_file, success, error_msg):
        """Handle individual file completion in batch"""
        # This is called for each file in batch conversion
        pass
    
    def on_batch_conversion_finished(self, completed_count, total_count):
        """Handle batch conversion completion"""
        if completed_count == total_count:
            QMessageBox.information(
                self,
                "Batch Conversion Complete",
                f"All {total_count} files converted successfully!"
            )
        else:
            QMessageBox.warning(
                self,
                "Batch Conversion Complete",
                f"Conversion complete: {completed_count}/{total_count} files successfully converted"
            )
        
        # Show back button after batch conversion
        if hasattr(self, '_file_converter_tab'):
            self._file_converter_tab.back_btn.show()
            self._file_converter_tab.convert_btn.hide()
            self._file_converter_tab.cancel_btn.hide()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern cross-platform style
    
    window = DownloaderAppQt()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
