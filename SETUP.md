# 🚀 Setup & Installation Guide

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **OS**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **RAM**: 2GB
- **Disk Space**: 500MB (including FFmpeg)

### Recommended Requirements
- **Python**: 3.10 or higher
- **OS**: Windows 11, macOS 12+, or Linux (Ubuntu 20.04+)
- **RAM**: 4GB+
- **Disk Space**: 1GB

---

## Prerequisites

You need to install **FFmpeg** before running the application:

### Windows
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add to PATH:
   - Right-click "This PC" → Properties
   - Click "Advanced system settings"
   - Click "Environment Variables"
   - Click "New" under System variables
   - Variable name: `PATH`
   - Variable value: `C:\ffmpeg\bin` (or your extraction path)
4. Verify: Open Command Prompt and type `ffmpeg -version`

### macOS
```bash
# Using Homebrew (recommended)
brew install ffmpeg

# Or using MacPorts
sudo port install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### Linux (Fedora/RHEL)
```bash
sudo dnf install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

---

## Installation Steps

### 1. Clone the Repository
```bash
git clone https://github.com/shashasana/mediadownloader-converter.git
cd mediadownloader-converter
```

### 2. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install --upgrade pip
pip install PyQt5 yt-dlp
```

Or install from requirements (if available):
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python downloader_qt.py --version
```

---

## Quick Start

### Running the Application

**Windows:**
```bash
python downloader_qt.py
```

**macOS/Linux:**
```bash
python3 downloader_qt.py
```

### First Use
1. **Launch** the application
2. **Paste URL** of the video/audio you want to convert
3. **Choose Format** (MP3, WAV, MP4, etc.)
4. **Select Quality** (for MP3: V0 VBR recommended)
5. **Click Download & Convert**
6. **Check output** in the Downloads folder

---

## Configuration

### Default Settings
Settings are stored in `config.py` and `settings.json`:

**Auto-Applied:**
- ✅ MP3 Quality: V0 VBR (Transparent)
- ✅ Sample Rate: Auto (keeps original)
- ✅ Output Format: MP3
- ✅ Output Folder: `./Downloads`

### Customize Output Folder
Edit `settings.json`:
```json
{
  "output_folder": "C:/Your/Custom/Path",
  "default_format": "MP3",
  "default_quality": "V0"
}
```

---

## Troubleshooting

### FFmpeg Not Found
**Problem:** "FFmpeg not found" error
**Solution:** 
1. Verify FFmpeg is installed: `ffmpeg -version`
2. Add FFmpeg to PATH (see Prerequisites section)
3. Restart the application

### PyQt5 Issues
**Problem:** "ModuleNotFoundError: No module named 'PyQt5'"
**Solution:**
```bash
pip install PyQt5
```

### Slow Conversion
**Problem:** Conversion taking too long
**Solution:**
- This is normal for V0 VBR (best quality takes longer)
- Use V2 or 320k CBR for faster conversion
- Check CPU usage - background processes may be slowing it down

### Audio Quality Issues
**Problem:** Output sounds strange or distorted
**Solution:**
- Use V0 VBR for best quality
- Try different sample rates (44100 Hz recommended)
- Check source file quality

---

## Features Overview

### Audio Conversion
- 7 quality presets (96k to 320k + VBR options)
- Variable Bit Rate (V0, V2) support
- 8 sample rate options (8kHz to 48kHz)
- Smart format detection

### Video Conversion
- MP4, MKV, AVI, WebM, MOV support
- Audio extraction to MP3, WAV, AAC, OGG, FLAC

### Smart UI
- Shows only compatible output formats
- Displays multiple output filenames
- Real-time preview of conversions

---

## Advanced Usage

### Command Line (Future Support)
```bash
# Download and convert to MP3 with V0 quality
python downloader_qt.py "https://youtube.com/watch?v=..." --format mp3 --quality v0
```

### Batch Processing
Create `batch.txt` with URLs (one per line) and process multiple files.

---

## Support

### Getting Help
1. **Check documentation**: See [README_DOCUMENTATION.md](README_DOCUMENTATION.md)
2. **Quick answers**: See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. **Feature details**: See [MP3_QUALITY_FEATURES.md](MP3_QUALITY_FEATURES.md)
4. **Troubleshooting**: See [QUICK_REFERENCE.md#Troubleshooting](QUICK_REFERENCE.md)

### Reporting Issues
- Check this setup guide first
- Review [QUICK_REFERENCE.md](QUICK_REFERENCE.md) troubleshooting section
- Include your OS, Python version, and error message

---

## Uninstallation

### Remove Virtual Environment
```bash
# Windows
.venv\Scripts\deactivate
rmdir /s .venv

# macOS/Linux
deactivate
rm -rf .venv
```

### Remove FFmpeg (if needed)
- Windows: Delete FFmpeg folder and remove from PATH
- macOS: `brew uninstall ffmpeg`
- Linux: `sudo apt-get remove ffmpeg`

---

## Next Steps

✅ Setup complete!

1. **Read**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (5 min overview)
2. **Learn**: [MP3_QUALITY_QUICK_GUIDE.md](MP3_QUALITY_QUICK_GUIDE.md) (quality options)
3. **Explore**: [COMPLETE_IMPLEMENTATION.md](COMPLETE_IMPLEMENTATION.md) (full features)

Enjoy your professional-grade media converter! 🎵
