"""Configuration and theme settings"""

# Paths
YTDLP_PATH = r"C:\yt-dlp\yt-dlp.exe"
FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"

# Settings
MAX_DOWNLOADS = 10
CHECK_CLIPBOARD_INTERVAL = 3

# Theme colors
BG = "#18191a"
FG = "#e4e6eb"
BOX = "#242526"
BTN = "#2374e1"
GREEN = "#31a24c"
RED = "#e74c3c"
YELLOW = "#f39c12"

LIGHT_BG = "#f5f6f7"
LIGHT_FG = "#1c1e21"
LIGHT_BOX = "#ffffff"
LIGHT_BTN = "#1877f2"
LIGHT_GREEN = "#2ecc71"
LIGHT_RED = "#e74c3c"
LIGHT_YELLOW = "#f1c40f"

SETTINGS_FILE = "settings.json"

# Formats
FORMATS = {
    "MP4 (Video)": "mp4",
    "MP3 (Audio)": "mp3",
    "WebM (Video)": "webm"
}

QUALITY_OPTIONS = ["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p"]

AUDIO_CODECS = ["mp3", "aac", "m4a", "opus"]
AUDIO_BITRATES = ["64k", "96k", "128k", "192k", "256k", "320k"]

# MP3 Quality Presets (for file converter)
MP3_QUALITY_PRESETS = [
    ("320 kbps (Best Quality - CBR)", "320k"),
    ("V0 (Variable Bit Rate - Transparent)", "V0"),
    ("V2 (Variable Bit Rate - High Quality)", "V2"),
    ("256 kbps (High Quality)", "256k"),
    ("192 kbps (Standard Quality)", "192k"),
    ("128 kbps (Low Quality)", "128k"),
    ("96 kbps (Minimal)", "96k"),
]

# Sample rate options for audio conversion (Hz)
SAMPLE_RATES = ["Auto", "48000", "44100", "32000", "22050", "16000", "11025", "8000"]

DEFAULT_SETTINGS = {
    "theme": "dark",
    "high_contrast": False,
    "font_scale": 1.5,
    "download_folder": "~/Downloads",
    "max_concurrent": 3,
    "clipboard_enabled": False,
    "clipboard_auto_add": False,
    "overwrite_policy": "ask",
    "notifications": True,
    "minimize_to_tray": False,
    "lock_ctrl_zoom": False,
    "format_choice": "mp4",
    "quality_choice": "best",
    "audio_codec": "mp3",
    "audio_bitrate": "192k",
    "embed_thumbnail": True,
    "embed_metadata": True,
    "subtitles": False,
    "auto_subtitles": False,
    "subtitle_langs": "en.*",
    "retry_count": 2,
    "retry_delay": 3,
    "filename_template": "{title} - {uploader}",
    "presets": {
        "Default": {
            "format_choice": "mp4",
            "quality_choice": "best",
            "audio_codec": "mp3",
            "audio_bitrate": "192k",
            "download_folder": "~/Downloads",
            "filename_template": "{title}"
        }
    },
    "active_preset": "Default"
}

FILE_TYPES = [
    ("MP4 Video", "*.mp4"),
    ("MP3 Audio", "*.mp3"),
    ("WebM Video", "*.webm"),
    ("All Files", "*.*")
]
