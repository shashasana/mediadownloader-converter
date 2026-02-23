"""Qt UI components for the downloader"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QCheckBox, QSpinBox, QFileDialog, QScrollArea, QMenu, QLayout,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, Property, QPoint, QSize
from PySide6.QtGui import QFont, QPalette, QColor, QTextCursor, QPixmap
try:
    from config import FORMATS, QUALITY_OPTIONS, AUDIO_CODECS, AUDIO_BITRATES, MP3_QUALITY_PRESETS, SAMPLE_RATES
except ImportError:
    from config import FORMATS, QUALITY_OPTIONS, AUDIO_CODECS, AUDIO_BITRATES
    SAMPLE_RATES = ["Auto", "48000", "44100", "32000", "22050", "16000", "11025", "8000"]
    MP3_QUALITY_PRESETS = [
        ("320 kbps (Best Quality - CBR)", "320k"),
        ("V0 (Variable Bit Rate - Transparent)", "V0"),
        ("V2 (Variable Bit Rate - High Quality)", "V2"),
        ("256 kbps (High Quality)", "256k"),
        ("192 kbps (Standard Quality)", "192k"),
        ("128 kbps (Low Quality)", "128k"),
        ("96 kbps (Minimal)", "96k"),
    ]
from downloader_core import get_output_extension
import os


class URLInputTextEdit(QTextEdit):
    """Custom QTextEdit that handles URL input with Enter to new line"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def keyPressEvent(self, event):
        # Allow Enter to create new line, but Ctrl+Enter to submit
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Just insert a new line
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


class FlowLayout(QLayout):
    """Layout that arranges widgets in a flow (wraps to next line)"""
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []
    
    def addItem(self, item):
        self._items.append(item)
    
    def count(self):
        return len(self._items)
    
    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def expandingDirections(self):
        return Qt.Orientation(0)
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size
    
    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        
        for item in self._items:
            widget = item.widget()
            if widget:
                space_x = spacing
                space_y = spacing
                
                next_x = x + item.sizeHint().width() + space_x
                if next_x - space_x > rect.right() and line_height > 0:
                    x = rect.x()
                    y = y + line_height + space_y
                    next_x = x + item.sizeHint().width() + space_x
                    line_height = 0
                
                if not test_only:
                    item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                
                x = next_x
                line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height - rect.y()
    
    def spacing(self):
        if self._spacing >= 0:
            return self._spacing
        return 10


class PreviewCard(QFrame):
    """Individual preview card for a URL"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFixedSize(280, 120)  # Fixed size for grid layout
        
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Thumbnail
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(80, 80)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setText("...")
        layout.addWidget(self.thumbnail)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.title_label = QLabel("Loading...")
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(35)
        info_layout.addWidget(self.title_label)
        
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Segoe UI", 8))
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)

        # Apply default theme after widgets are created
        self.apply_theme("dark")
    
    def set_loading(self, url):
        """Show loading state"""
        self.title_label.setText(f"Fetching...")
        self.info_label.setText(url[:30] + "..." if len(url) > 30 else url)
        self.thumbnail.setText("...")
    
    def set_data(self, title, info_text, pixmap=None):
        """Set preview data"""
        # Truncate title if too long
        if len(title) > 40:
            title = title[:37] + "..."
        self.title_label.setText(title)
        self.info_label.setText(info_text)
        if pixmap:
            self.thumbnail.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.thumbnail.setText("No\nPreview")
    
    def set_error(self, url):
        """Show error state"""
        self.title_label.setText("Failed")
        self.info_label.setText(url[:30] + "..." if len(url) > 30 else url)
        self.thumbnail.setText("✗")

    def apply_theme(self, theme: str):
        if theme == "light":
            self.setStyleSheet(
                """
                PreviewCard {
                    background-color: #ffffff;
                    border: 2px solid #1877f2;
                    border-radius: 8px;
                    padding: 8px;
                }
                """
            )
            self.thumbnail.setStyleSheet(
                "border: 1px solid #cbd5e1; border-radius: 4px; background-color: #f1f5f9;"
            )
            self.info_label.setStyleSheet("color: #4b5563;")
        else:
            self.setStyleSheet(
                """
                PreviewCard {
                    background-color: #2a2a2a;
                    border: 2px solid #2374e1;
                    border-radius: 8px;
                    padding: 8px;
                }
                """
            )
            self.thumbnail.setStyleSheet(
                "border: 1px solid #555; border-radius: 4px; background-color: #1a1a1a;"
            )
            self.info_label.setStyleSheet("color: #aaa;")


class AnimatedButton(QPushButton):
    """Button with hover and press animations"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._scale = 1.0
        self.setMouseTracking(True)
        
    def get_scale(self):
        return self._scale
    
    def set_scale(self, scale):
        self._scale = scale
        self.update()
    
    scale = Property(float, get_scale, set_scale)
    
    def enterEvent(self, event):
        """Animate on hover"""
        anim = QPropertyAnimation(self, b"scale", self)
        anim.setDuration(150)
        anim.setStartValue(1.0)
        anim.setEndValue(1.05)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Animate on leave"""
        anim = QPropertyAnimation(self, b"scale", self)
        anim.setDuration(150)
        anim.setStartValue(self._scale)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Animate on press"""
        self._press_anim = QPropertyAnimation(self, b"scale", self)
        self._press_anim.setDuration(80)
        self._press_anim.setStartValue(self._scale)
        self._press_anim.setEndValue(0.98)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._press_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Animate on release"""
        self._press_anim = QPropertyAnimation(self, b"scale", self)
        self._press_anim.setDuration(80)
        self._press_anim.setStartValue(self._scale)
        self._press_anim.setEndValue(1.0)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._press_anim.start()
        super().mouseReleaseEvent(event)


class URLInputFrame(QWidget):
    """Enhanced URL input with format selection"""
    
    url_changed = Signal(str)
    duplicate_urls_detected = Signal(list)  # Signal for duplicate URLs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_text = ""
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Label
        label = QLabel("Media URL")
        label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(label)
        
        # Platform hint
        self.platform_hint = QLabel("Platform: Unknown")
        self.platform_hint.setStyleSheet("color: #FFC107;")
        layout.addWidget(self.platform_hint)
        
        # URL count
        self.url_count_label = QLabel("URLs: 0")
        self.url_count_label.setStyleSheet("color: #8b8b8b;")
        layout.addWidget(self.url_count_label)
        
        # URL input
        self.url_input = URLInputTextEdit()
        self.url_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.url_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        metrics = self.url_input.fontMetrics()
        line_height = metrics.lineSpacing()
        target_height = int(line_height * 10 + 12)
        self.url_input.setFixedHeight(target_height)
        self.url_input.setPlaceholderText("Enter media URL(s) here... (one per line for multiple downloads)\nPress Enter to move to next line")
        self.url_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.url_input)
        
        # Format selection (below URL box, always visible)
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(list(FORMATS.keys()))
        self.format_combo.currentTextChanged.connect(self.update_format_visibility)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Quality selection (below format, always visible)
        self.quality_frame = QWidget()
        quality_layout = QHBoxLayout(self.quality_frame)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        quality_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_OPTIONS)
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        layout.addWidget(self.quality_frame)
        
        # Audio codec selection
        self.audio_frame = QWidget()
        audio_layout = QHBoxLayout(self.audio_frame)
        audio_layout.setContentsMargins(0, 0, 0, 0)
        audio_layout.addWidget(QLabel("Audio Codec:"))
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(AUDIO_CODECS)
        audio_layout.addWidget(self.audio_codec_combo)
        audio_layout.addWidget(QLabel("Quality:"))
        self.audio_bitrate_combo = QComboBox()
        # Populate with MP3 quality presets (including V0/V2 VBR)
        for label, value in MP3_QUALITY_PRESETS:
            self.audio_bitrate_combo.addItem(label, value)
        # Set default to 320k
        for i in range(self.audio_bitrate_combo.count()):
            if self.audio_bitrate_combo.itemData(i) == "320k":
                self.audio_bitrate_combo.setCurrentIndex(i)
                break
        audio_layout.addWidget(self.audio_bitrate_combo)
        audio_layout.addStretch()
        layout.addWidget(self.audio_frame)
        
        # Output folder
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Output Folder:"))
        self.folder_input = QLineEdit()
        self.folder_input.setMaximumWidth(400)
        folder_layout.addWidget(self.folder_input)
        self.browse_btn = AnimatedButton("Browse")
        self.browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.browse_btn)
        folder_layout.addStretch()
        layout.addLayout(folder_layout)
        
        self.update_format_visibility()
    
    def _on_text_changed(self):
        url = self.url_input.toPlainText().strip()
        self.url_changed.emit(url)
        # Update URL count
        text = self.url_input.toPlainText().strip()
        if not text:
            count = 0
        else:
            count = len([line for line in text.split('\n') if line.strip().startswith('http')])
        self.url_count_label.setText(f"URLs: {count}")
        
        # Check for duplicate URLs within the input
        urls = self.get_urls()
        if len(urls) > 1:
            # Check if there are duplicates
            seen = set()
            duplicates = []
            for url in urls:
                if url in seen:
                    duplicates.append(url)
                seen.add(url)
            
            if duplicates:
                self.duplicate_urls_detected.emit(duplicates)
        
        # Emit empty signal for auto-clearing previews
        if not url:
            self.url_changed.emit("")  # Signal to clear previews
        
        self._last_text = text
    
    def _auto_resize_input(self):
        """Auto-resize URL input based on content"""
        doc = self.url_input.document()
        height = doc.size().height() + 10
        # Expand to show all URLs with no scroll bar
        target_height = int(max(60, height))
        self.url_input.setMinimumHeight(target_height)
        self.url_input.setMaximumHeight(target_height)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder:
            self.folder_input.setText(folder)
    
    def update_format_visibility(self):
        fmt = self.get_format()
        self.audio_frame.setVisible(fmt == "mp3")
        self.quality_frame.setVisible(fmt in ("mp4", "webm"))
    
    def get_url(self):
        return self.url_input.toPlainText().strip()
    
    def get_urls(self):
        """Get list of URLs (one per line) - removes duplicates"""
        text = self.url_input.toPlainText().strip()
        urls = [line.strip() for line in text.split('\n') if line.strip().startswith('http')]
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        return unique_urls if unique_urls else [text] if text else []
    
    def set_url(self, url):
        self.url_input.setPlainText(url)
    
    def clear(self):
        self.url_input.clear()
    
    def get_format(self):
        return FORMATS.get(self.format_combo.currentText(), "mp4")
    
    def get_quality(self):
        return self.quality_combo.currentText()
    
    def get_audio_codec(self):
        return self.audio_codec_combo.currentText()
    
    def get_audio_bitrate(self):
        # Return the actual quality value (e.g., "320k", "V0", "V2")
        return self.audio_bitrate_combo.currentData() or self.audio_bitrate_combo.currentText()
    
    def get_output_folder(self):
        return self.folder_input.text()
    
    def set_output_folder(self, folder):
        self.folder_input.setText(folder)
    
    def set_platform_hint(self, text):
        self.platform_hint.setText(text)
    
    def set_available_video_qualities(self, qualities):
        current = self.quality_combo.currentText()
        self.quality_combo.clear()
        self.quality_combo.addItems(qualities)
        if current in qualities:
            self.quality_combo.setCurrentText(current)


class DownloadTableFrame(QWidget):
    """Download progress table"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "File", "Status", "Size", "Speed", "ETA", "Progress"
        ])
        
        # Center align all headers
        header = self.table.horizontalHeader()
        for i in range(6):
            item = self.table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # File column stretches
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.table)
    
    def add_download(self, task_id, filename):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(filename))
        self.table.setItem(row, 1, QTableWidgetItem("Queued"))
        self.table.setItem(row, 2, QTableWidgetItem("Unknown"))
        self.table.setItem(row, 3, QTableWidgetItem("0 B/s"))
        self.table.setItem(row, 4, QTableWidgetItem("--:--"))
        self.table.setItem(row, 5, QTableWidgetItem("0%"))
        # Store task_id in first column
        self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, task_id)
    
    def update_download(self, task_id, status, size, speed, eta, progress):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                # Reuse existing items instead of creating new ones
                status_item = self.table.item(row, 1)
                if not status_item:
                    status_item = QTableWidgetItem()
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 1, status_item)
                status_item.setText(status)
                
                size_item = self.table.item(row, 2)
                if not size_item:
                    size_item = QTableWidgetItem()
                    size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 2, size_item)
                size_item.setText(size)
                
                speed_item = self.table.item(row, 3)
                if not speed_item:
                    speed_item = QTableWidgetItem()
                    speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 3, speed_item)
                speed_item.setText(speed)
                
                eta_item = self.table.item(row, 4)
                if not eta_item:
                    eta_item = QTableWidgetItem()
                    eta_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 4, eta_item)
                eta_item.setText(eta)
                
                progress_item = self.table.item(row, 5)
                if not progress_item:
                    progress_item = QTableWidgetItem()
                    progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 5, progress_item)
                progress_item.setText(f"{progress:.1f}%")
                break
    
    def remove_download(self, task_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.table.removeRow(row)
                break
    
    def clear_all(self):
        self.table.setRowCount(0)


class HistoryFrame(QWidget):
    """Download history view"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "File", "Location", "Format", "Status", "URL"
        ])
        
        # Center align all headers
        header = self.table.horizontalHeader()
        for i in range(5):
            item = self.table.horizontalHeaderItem(i)
            if item:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header.setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
    
    def add_history_item(self, file, location, format, status, url):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(file))
        self.table.setItem(row, 1, QTableWidgetItem(location))
        self.table.setItem(row, 2, QTableWidgetItem(format))
        self.table.setItem(row, 3, QTableWidgetItem(status))
        self.table.setItem(row, 4, QTableWidgetItem(url))
        # Store data
        self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, {
            "file": file, "location": location, "format": format,
            "status": status, "url": url
        })
    
    def clear_all(self):
        self.table.setRowCount(0)
    
    def get_selected(self):
        rows = self.table.selectedItems()
        if rows:
            return self.table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        return None


class LogsFrame(QWidget):
    """Logs display"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        # Clear button
        self.clear_btn = AnimatedButton("Clear Logs")
        self.clear_btn.clicked.connect(self.clear)
        layout.addWidget(self.clear_btn)
        self.clear_btn.hide()  # Hide initially
    
    def add_log(self, message):
        self.log_text.append(message.strip())
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def add_log_raw(self, message):
        # Optimize: use single cursor operation
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(message)
        
        # Limit log size to prevent memory bloat (keep last 10000 lines)
        doc = self.log_text.document()
        if doc.lineCount() > 10000:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, doc.lineCount() - 10000)
            cursor.removeSelectedText()
        
        # Scroll to end
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
    
    def clear(self):
        self.log_text.clear()


class FileConverterDialog(QWidget):
    """Universal file converter dialog"""
    convert_requested = Signal(list, str, str, str, str, bool)  # input_files (list), output_format, quality, sample_rate, open_after, is_batch
    back_to_downloader = Signal()  # Signal to go back to downloader
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_files = []  # Support multiple files
        self.setAcceptDrops(True)
        
        # Format compatibility map: input format -> allowed output formats
        self.format_compatibility = {
            # Audio formats
            'mp3': ['WAV', 'AAC', 'FLAC', 'OGG', 'M4A'],
            'wav': ['MP3', 'AAC', 'FLAC', 'OGG', 'M4A'],
            'aac': ['MP3', 'WAV', 'FLAC', 'OGG'],
            'm4a': ['MP3', 'WAV', 'FLAC', 'OGG'],
            'ogg': ['MP3', 'WAV', 'AAC'],
            'flac': ['WAV', 'MP3', 'AAC', 'OGG'],
            'aiff': ['WAV', 'MP3', 'AAC', 'FLAC'],
            
            # Video formats
            'mp4': ['AVI', 'MOV', 'MKV', 'WMV', 'FLV', 'WEBM', 'MP3', 'WAV', 'AAC'],
            'avi': ['MP4', 'MOV', 'MKV', 'WMV', 'MP3', 'WAV', 'AAC'],
            'mov': ['MP4', 'AVI', 'MKV', 'MP3', 'WAV', 'AAC'],
            'mkv': ['MP4', 'AVI', 'MOV', 'MP3', 'WAV', 'AAC'],
            'wmv': ['MP4', 'AVI'],
            'flv': ['MP4', 'AVI', 'MOV'],
            'webm': ['MP4', 'MKV'],
            'm4v': ['MP4', 'AVI', 'MKV', 'MP3', 'WAV', 'AAC'],
            
            # Image formats
            'jpg': ['PNG', 'GIF', 'BMP', 'TIFF', 'WEBP', 'PDF'],
            'jpeg': ['PNG', 'GIF', 'BMP', 'TIFF', 'WEBP', 'PDF'],
            'png': ['JPG', 'GIF', 'BMP', 'TIFF', 'WEBP', 'PDF'],
            'gif': ['PNG', 'JPG', 'MP4', 'WEBM'],
            'bmp': ['PNG', 'JPG', 'TIFF'],
            'tiff': ['JPG', 'PNG', 'PDF'],
            'tif': ['JPG', 'PNG', 'PDF'],
            'webp': ['JPG', 'PNG', 'GIF'],
            'psd': ['JPG', 'PNG', 'TIFF'],
            'ai': ['PDF', 'SVG', 'PNG'],
            
            # Document formats
            'doc': ['PDF', 'DOCX', 'TXT', 'RTF', 'HTML', 'ODT', 'EPUB'],
            'docx': ['PDF', 'TXT', 'RTF', 'HTML', 'ODT', 'EPUB'],
            'pdf': ['DOCX', 'TXT', 'HTML', 'EPUB', 'JPG', 'PNG'],
            'txt': ['PDF', 'DOCX', 'HTML', 'RTF'],
            'rtf': ['DOCX', 'PDF', 'TXT'],
            'html': ['PDF', 'DOCX', 'TXT', 'EPUB'],
            'htm': ['PDF', 'DOCX', 'TXT', 'EPUB'],
            'md': ['PDF', 'DOCX', 'HTML'],
            'odt': ['PDF', 'DOCX', 'TXT', 'HTML'],
            'epub': ['PDF', 'DOCX', 'HTML'],
            'mobi': ['PDF', 'EPUB', 'HTML'],
            
            # Spreadsheet formats
            'xls': ['XLSX', 'CSV', 'PDF', 'HTML', 'JSON', 'ODS', 'TXT'],
            'xlsx': ['CSV', 'PDF', 'HTML', 'JSON', 'ODS', 'TXT'],
            'csv': ['XLSX', 'TXT', 'JSON', 'HTML', 'PDF'],
            'ods': ['XLSX', 'CSV', 'PDF', 'HTML'],
            'tsv': ['CSV', 'XLSX', 'HTML'],
            
            # Presentation formats
            'ppt': ['PDF', 'JPG', 'PNG', 'HTML'],
            'pptx': ['PDF', 'JPG', 'PNG', 'HTML'],
            'odp': ['PDF', 'PPTX', 'JPG', 'PNG'],
            
            # Archive formats
            'zip': ['7Z', 'RAR', 'TAR'],
            'rar': ['ZIP', '7Z', 'TAR'],
            '7z': ['ZIP', 'RAR', 'TAR'],
            'tar': ['ZIP', '7Z'],
            'gz': ['ZIP', '7Z'],
            'tgz': ['ZIP', '7Z'],
            
            # Data formats
            'json': ['CSV', 'XLSX', 'HTML', 'XML'],
            'xml': ['JSON', 'CSV', 'XLSX'],
            'svg': ['PNG', 'JPG', 'PDF'],
        }
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # File selection with multiple file support
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No files selected")
        self.file_label.setStyleSheet("color: #888; font-style: italic;")
        file_btn = AnimatedButton("Choose Files")
        file_btn.clicked.connect(self.select_files)
        file_layout.addWidget(QLabel("Input Files:"))
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(file_btn)
        layout.addLayout(file_layout)
        
        # File list display (scrollable)
        self.file_list = QTextEdit()
        self.file_list.setReadOnly(True)
        self.file_list.setMaximumHeight(100)
        self.file_list.setStyleSheet("background-color: #f5f5f5; color: #333; font-size: 9pt;")
        self.file_list.setPlaceholderText("Selected files will appear here...")
        layout.addWidget(self.file_list)
        
        # Preview image (for videos/images)
        self.preview_image = QLabel()
        self.preview_image.setStyleSheet("border: 1px solid #ddd; background-color: #f5f5f5;")
        self.preview_image.setMaximumHeight(150)
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_image)
        
        # Format and quality options container (hidden until files selected)
        self.options_container = QWidget()
        options_layout = QVBoxLayout(self.options_container)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(5)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            # Audio
            "MP3", "WAV", "AAC", "FLAC", "OGG", "M4A", "AIFF",
            # Video
            "MP4", "MKV", "AVI", "MOV", "WEBM", "FLV", "WMV",
            # Images
            "JPG", "PNG", "GIF", "BMP", "TIFF", "WEBP", "SVG",
            # Documents
            "PDF", "DOCX", "TXT", "RTF", "HTML", "ODT", "EPUB", "MOBI",
            # Spreadsheets
            "XLSX", "CSV", "ODS", "JSON", "TSV",
            # Presentations
            "PPTX", "PPT",
            # Archives
            "ZIP", "RAR", "7Z", "TAR",
            # Data
            "XML"
        ])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo, 1)
        options_layout.addLayout(format_layout)
        
        # Quality/Bitrate selector for MP3 (with presets)
        self.mp3_quality_widget = QWidget()
        self.mp3_quality_layout = QHBoxLayout(self.mp3_quality_widget)
        self.mp3_quality_layout.setContentsMargins(0, 0, 0, 0)
        self.mp3_quality_layout.addWidget(QLabel("MP3 Quality:"))
        self.mp3_quality_combo = QComboBox()
        # Populate with MP3 quality presets
        for label, value in MP3_QUALITY_PRESETS:
            self.mp3_quality_combo.addItem(label, value)
        self.mp3_quality_combo.setCurrentIndex(0)  # Default to 320kbps
        self.mp3_quality_layout.addWidget(self.mp3_quality_combo, 1)
        self.mp3_quality_layout.addStretch()
        
        # Sample rate selector for audio formats
        self.sample_rate_widget = QWidget()
        self.sample_rate_layout = QHBoxLayout(self.sample_rate_widget)
        self.sample_rate_layout.setContentsMargins(0, 0, 0, 0)
        self.sample_rate_layout.addWidget(QLabel("Sample Rate:"))
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(SAMPLE_RATES)
        self.sample_rate_combo.setCurrentText("Auto")
        self.sample_rate_layout.addWidget(self.sample_rate_combo, 1)
        self.sample_rate_layout.addStretch()
        
        # Generic quality slider (for other formats)
        self.generic_quality_widget = QWidget()
        self.generic_quality_layout = QHBoxLayout(self.generic_quality_widget)
        self.generic_quality_layout.setContentsMargins(0, 0, 0, 0)
        self.generic_quality_layout.addWidget(QLabel("Quality:"))
        self.quality_slider = QSpinBox()
        self.quality_slider.setMinimum(32)
        self.quality_slider.setMaximum(320)
        self.quality_slider.setValue(320)
        self.quality_slider.setSuffix(" kbps")
        self.generic_quality_layout.addWidget(self.quality_slider)
        self.quality_label = QLabel("(Audio bitrate)")
        self.generic_quality_layout.addWidget(self.quality_label)
        self.generic_quality_layout.addStretch()
        
        # Add quality widgets to options container
        options_layout.addWidget(self.mp3_quality_widget)
        options_layout.addWidget(self.sample_rate_widget)
        options_layout.addWidget(self.generic_quality_widget)
        
        layout.addWidget(self.options_container)
        self.options_container.hide()  # Hide until files are selected
        
        # Output filenames display (for multiple files)
        self.output_names_label = QLabel("Output Names:")
        self.output_names_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.output_names_label)
        self.output_names_label.hide()  # Hide until files are selected
        
        self.output_names_display = QTextEdit()
        self.output_names_display.setMaximumHeight(80)
        self.output_names_display.setStyleSheet("background-color: #ffffff; color: #333; font-size: 9pt;")
        self.output_names_display.setPlaceholderText("Output filenames will appear here...")
        layout.addWidget(self.output_names_display)
        self.output_names_display.hide()  # Hide until files are selected

        # Info box with quality info (for audio formats only)
        self.info_text = QLabel()
        self.info_text.setStyleSheet("color: #6fa8dc; font-size: 9pt; font-style: italic;")
        self.info_text.setText("Tip: 320kbps CBR provides maximum quality. V0/V2 use VBR (Variable Bit Rate) for efficient file size.")
        layout.addWidget(self.info_text)
        self.info_text.hide()  # Hide by default, show only for audio formats

        # Open-after-convert
        self.open_after_checkbox = QCheckBox("Open file after conversion")
        self.open_after_checkbox.setChecked(True)
        layout.addWidget(self.open_after_checkbox)

        # Drag & drop hint
        drop_hint = QLabel("Tip: Drag and drop one or multiple files here")
        drop_hint.setStyleSheet("color: #6fa8dc; font-style: italic;")
        layout.addWidget(drop_hint)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.back_btn = AnimatedButton("Back")
        self.back_btn.setMinimumWidth(100)
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.hide()  # Hidden by default, shown after cancel/conversion
        btn_layout.addWidget(self.back_btn)
        
        btn_layout.addStretch()
        
        self.convert_btn = AnimatedButton("Convert")
        self.convert_btn.setMinimumWidth(100)
        self.convert_btn.clicked.connect(self.convert)
        btn_layout.addWidget(self.convert_btn)
        
        self.cancel_btn = AnimatedButton("Cancel")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self.reset_fields)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Ensure proper initial button state (Convert/Cancel visible, Back hidden)
        self.back_btn.hide()
        self.convert_btn.show()
        self.cancel_btn.show()
    
    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to convert",
            os.path.expanduser("~/Downloads"),
            "All Files (*.*)"
        )
        if file_paths:
            self.set_input_files(file_paths)
    
    def on_format_changed(self):
        output_format = self.format_combo.currentText()
        
        # Show/hide quality options based on format
        is_mp3 = output_format == "MP3"
        is_audio = output_format in ["MP3", "WAV", "AAC", "OGG", "FLAC", "M4A", "AIFF"]
        is_video = output_format in ["MP4", "MKV", "AVI", "MOV", "WEBM", "FLV", "WMV"]
        is_image = output_format in ["JPG", "PNG", "GIF", "BMP", "TIFF", "WEBP", "SVG"]
        is_document = output_format in ["PDF", "DOCX", "TXT", "RTF", "HTML", "ODT", "EPUB", "MOBI", 
                                        "XLSX", "CSV", "ODS", "JSON", "TSV", "XML",
                                        "PPTX", "PPT",
                                        "ZIP", "RAR", "7Z", "TAR"]
        
        # Show/hide MP3 quality widget
        self.mp3_quality_widget.setVisible(is_mp3)
        
        # Show/hide sample rate widget for audio formats only
        self.sample_rate_widget.setVisible(is_audio)
        
        # Update generic quality slider and label based on format
        if is_video:
            self.quality_label.setText("(Video bitrate)")
            self.quality_slider.setMinimum(500)
            self.quality_slider.setMaximum(8000)
            self.quality_slider.setValue(2500)
            self.quality_slider.setSuffix(" kbps")
        elif output_format in ["WAV", "AAC", "OGG", "FLAC", "M4A", "AIFF"]:
            self.quality_label.setText("(Audio bitrate)")
            self.quality_slider.setMinimum(32)
            self.quality_slider.setMaximum(320)
            self.quality_slider.setValue(192)
            self.quality_slider.setSuffix(" kbps")
        elif is_image:
            self.quality_label.setText("(Quality %)")
            self.quality_slider.setMinimum(1)
            self.quality_slider.setMaximum(100)
            self.quality_slider.setValue(85)
            self.quality_slider.setSuffix("%")
        
        # Show/hide generic quality slider based on format
        # Only show for audio (non-MP3), video, and image formats
        show_quality_slider = not (is_mp3 or is_document)
        self.generic_quality_widget.setVisible(show_quality_slider)
        
        # Show/hide audio quality tip only for audio formats
        self.info_text.setVisible(is_audio)
        
        # Update output names display with new format
        self._update_output_names()
        # Update preview display based on selected format
        if self.input_files:
            self.load_preview_image(self.input_files[0])
    
    def set_input_file(self, file_path):
        self.input_files = [file_path]
        self._update_file_label()
        if file_path:
            self.load_preview_image(file_path)
    
    def set_input_files(self, file_paths):
        """Set multiple input files"""
        self.input_files = file_paths if isinstance(file_paths, list) else [file_paths]
        self._update_file_label()
        
        # Show format and quality options now that files are selected
        self._show_conversion_options()
        
        # Filter output formats based on input file type
        self._filter_output_formats()
        
        # Update output names display
        self._update_output_names()
        
        if self.input_files:
            self.load_preview_image(self.input_files[0])
            # Show Convert button when files are selected
            self.back_btn.hide()
            self.convert_btn.show()
            self.cancel_btn.show()
    
    def _show_conversion_options(self):
        """Show format and quality options after files are selected"""
        self.options_container.show()
        self.output_names_label.show()
        self.output_names_display.show()
        
        # Ensure visibility and labels match current format
        self.on_format_changed()
    
    def _filter_output_formats(self):
        """Filter output formats based on input file type"""
        if not self.input_files:
            return
        
        # Get input file extension
        input_file = self.input_files[0]
        input_ext = os.path.splitext(input_file)[1].lower().lstrip('.')
        
        # Get compatible formats
        compatible_formats = self.format_compatibility.get(input_ext, [
            "MP3", "WAV", "AAC", "OGG", "FLAC",
            "MP4", "MKV", "AVI", "WebM", "FLV",
            "JPG", "PNG", "GIF", "WebP", "BMP"
        ])
        
        # Update format combo with only compatible formats
        current_text = self.format_combo.currentText()
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        self.format_combo.addItems(compatible_formats)
        
        # Try to restore previous selection if compatible
        index = self.format_combo.findText(current_text)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        else:
            self.format_combo.setCurrentIndex(0)
        
        self.format_combo.blockSignals(False)
        # Refresh visibility for audio-only options/tip
        self.on_format_changed()
    
    def _update_output_names(self):
        """Update display of output filenames for all selected files"""
        if not self.input_files:
            self.output_names_display.clear()
            return
        
        output_format = self.format_combo.currentText().lower()
        output_names = []
        
        for input_file in self.input_files:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_name = f"{base_name}.{output_format}"
            output_names.append(output_name)
        
        self.output_names_display.setText("\n".join(output_names))
    
    def _update_file_label(self):
        """Update file label and list display"""
        if not self.input_files:
            self.file_label.setText("No files selected")
            self.file_list.clear()
        elif len(self.input_files) == 1:
            self.file_label.setText(os.path.basename(self.input_files[0]))
            self.file_list.setText(os.path.basename(self.input_files[0]))
        else:
            self.file_label.setText(f"{len(self.input_files)} files selected")
            file_list_text = "\n".join([f"• {os.path.basename(f)}" for f in self.input_files])
            self.file_list.setText(file_list_text)
    
    def load_preview_image(self, file_path):
        """Display preview/thumbnail of the INPUT file"""
        try:
            input_format = os.path.splitext(file_path)[1].lower().lstrip('.')
            
            # Try to extract thumbnail from video files
            if input_format in ['mp4', 'mkv', 'avi', 'webm', 'flv', 'mov', 'm4v', 'mkv']:
                try:
                    # Try to use ffmpeg to extract thumbnail
                    from config import FFMPEG_PATH
                    import subprocess
                    import tempfile
                    
                    if os.path.exists(FFMPEG_PATH):
                        # Create temporary file for thumbnail
                        temp_thumb = os.path.join(tempfile.gettempdir(), "converter_thumb.jpg")
                        
                        # Extract first frame as thumbnail
                        cmd = [
                            FFMPEG_PATH,
                            "-i", file_path,
                            "-ss", "00:00:01",  # Get frame at 1 second
                            "-vf", "scale=200:150",
                            "-vframes", "1",
                            "-y",  # Overwrite
                            temp_thumb
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, timeout=10)
                        
                        if result.returncode == 0 and os.path.exists(temp_thumb):
                            pixmap = QPixmap(temp_thumb)
                            if not pixmap.isNull():
                                scaled = pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
                                self.preview_image.setPixmap(scaled)
                                self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                return
                except Exception:
                    pass
            
            # Try to load image directly for image formats
            elif input_format in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                try:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
                        self.preview_image.setPixmap(scaled)
                        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        return
                except Exception:
                    pass
            
            # Fallback: Show file type icon/text
            self._show_file_type_preview(input_format)
            
        except Exception as e:
            self._show_file_type_preview("")
    
    def _show_file_type_preview(self, file_format):
        """Show file type icon when preview can't be extracted"""
        self.preview_image.clear()
        
        if file_format in ['mp3', 'wav', 'aac', 'ogg', 'flac', 'm4a']:
            self.preview_image.setText("🎵 Audio File")
            self.preview_image.setStyleSheet("border: 2px solid #4CAF50; background-color: #1a1a1a; color: #90EE90; font-weight: bold; font-size: 14pt;")
        elif file_format in ['mp4', 'mkv', 'avi', 'webm', 'flv', 'mov', 'm4v']:
            self.preview_image.setText("🎬 Video File")
            self.preview_image.setStyleSheet("border: 2px solid #2196F3; background-color: #1a1a1a; color: #87CEEB; font-weight: bold; font-size: 14pt;")
        elif file_format in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
            self.preview_image.setText("🖼️ Image File")
            self.preview_image.setStyleSheet("border: 2px solid #FF9800; background-color: #1a1a1a; color: #FFB347; font-weight: bold; font-size: 14pt;")
        elif file_format in ['pdf', 'docx', 'txt', 'xlsx']:
            self.preview_image.setText(f"📄 {file_format.upper()} File")
            self.preview_image.setStyleSheet("border: 2px solid #9C27B0; background-color: #1a1a1a; color: #DA70D6; font-weight: bold; font-size: 14pt;")
        else:
            self.preview_image.setText(f"📁 {file_format.upper() if file_format else 'File'}")
            self.preview_image.setStyleSheet("border: 2px solid #607D8B; background-color: #1a1a1a; color: #90A4AE; font-weight: bold; font-size: 14pt;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path:
                    file_paths.append(file_path)
            if file_paths:
                self.set_input_files(file_paths)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def convert(self):
        if not self.input_files:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "Please select input file(s) first")
            return
        
        output_format = self.format_combo.currentText().lower()
        open_after = self.open_after_checkbox.isChecked()
        
        # Get quality based on format
        if output_format == "mp3":
            quality = self.mp3_quality_combo.currentData() or "320k"
        else:
            quality = str(self.quality_slider.value())
        
        # Get sample rate if audio format
        sample_rate = "auto"
        if output_format in ["mp3", "wav", "aac", "ogg", "flac"]:
            sample_rate = self.sample_rate_combo.currentText().lower()
        
        # For batch conversion, emit signal with all files
        is_batch = len(self.input_files) > 1
        self.convert_requested.emit(self.input_files, output_format, quality, sample_rate, open_after, is_batch)

    def reset_fields(self):
        """Reset all converter fields without closing"""
        self.input_files = []
        self.file_label.setText("No files selected")
        self.file_list.clear()
        self.preview_image.clear()  # Clear both text and pixmap
        self.preview_image.setPixmap(QPixmap())  # Explicitly clear pixmap
        self.format_combo.setCurrentIndex(0)
        self.mp3_quality_combo.setCurrentIndex(0)
        self.sample_rate_combo.setCurrentText("Auto")
        self.quality_slider.setValue(320)
        self.open_after_checkbox.setChecked(True)
        # Hide options and output display
        self.options_container.hide()
        self.output_names_label.hide()
        self.output_names_display.hide()
        self.output_names_display.clear()
        # Show back button after cancel
        self.back_btn.show()
        self.convert_btn.hide()
        self.cancel_btn.hide()
    
    def go_back(self):
        """Go back to downloader dashboard"""
        self.back_to_downloader.emit()
        # Reset for next time
        self.reset_to_initial_state()
    
    def reset_to_initial_state(self):
        """Reset to initial state with convert/cancel buttons visible"""
        self.input_files = []
        self.file_label.setText("No files selected")
        self.file_list.clear()
        self.preview_image.clear()  # Clear both text and pixmap
        self.preview_image.setPixmap(QPixmap())  # Explicitly clear pixmap
        self.format_combo.setCurrentIndex(0)
        self.mp3_quality_combo.setCurrentIndex(0)
        self.sample_rate_combo.setCurrentText("Auto")
        self.quality_slider.setValue(320)
        self.open_after_checkbox.setChecked(True)
        # Hide options and output display
        self.options_container.hide()
        self.output_names_label.hide()
        self.output_names_display.hide()
        self.output_names_display.clear()
        # Show convert/cancel, hide back
        self.back_btn.hide()
        self.convert_btn.show()
        self.cancel_btn.show()
