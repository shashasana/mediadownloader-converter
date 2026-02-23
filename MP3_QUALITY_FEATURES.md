# MP3 Quality Conversion Features - Update Summary

## Overview
Updated the file converter with enhanced MP3 quality options including Variable Bit Rate (VBR) support, sample rate selection, and quality presets.

---

## Changes Made

### 1. **config.py** - Added Quality Presets
```python
MP3_QUALITY_PRESETS = [
    ("320 kbps (Best Quality - CBR)", "320k"),
    ("V0 (Variable Bit Rate - Transparent)", "V0"),
    ("V2 (Variable Bit Rate - High Quality)", "V2"),
    ("256 kbps (High Quality)", "256k"),
    ("192 kbps (Standard Quality)", "192k"),
    ("128 kbps (Low Quality)", "128k"),
    ("96 kbps (Minimal)", "96k"),
]

SAMPLE_RATES = ["Auto", "48000", "44100", "32000", "22050", "16000", "11025", "8000"]
```

### 2. **ui_components_qt.py** - Enhanced FileConverterDialog
- **MP3 Quality Combo Box**: Dropdown with predefined quality presets
- **Sample Rate Selector**: Choose from common sample rates or "Auto"
- **Conditional Display**: MP3-specific options shown only for MP3 format
- **Updated Signal**: Now passes `(input_file, output_format, quality, sample_rate, open_after)`

**Quality Preset Explanations:**
- **320 kbps (Best Quality - CBR)**: Constant Bit Rate at maximum quality, largest file size
- **V0 (VBR)**: Variable Bit Rate with highest quality, transparent audio, efficient file size
- **V2 (VBR)**: Variable Bit Rate, high quality, smaller files than V0
- **256/192/128/96 kbps**: Constant Bit Rates at various quality levels

### 3. **downloader_qt.py** - Updated FileConversionWorker
- Added `sample_rate` parameter to constructor
- Updated signal to pass quality and sample_rate separately
- Updated `start_file_conversion()` to handle new parameters

### 4. **downloader_core.py** - Enhanced convert_file() Function

**New Parameters:**
- `quality`: Now accepts strings like "320k", "V0", "V2" in addition to numeric values
- `sample_rate`: Added support for sample rate conversion (e.g., "44100", "48000", or "auto")

**VBR Support for MP3:**
```python
if quality.upper() in ["V0", "V2", "V4", "V6", "V8", "V9"]:
    # Variable Bit Rate using -q:a option
    cmd.extend(["-q:a", quality.upper()[1:]])  # "V0" → "0"
elif quality.endswith("k"):
    # Constant Bit Rate like "320k"
    cmd.extend(["-b:a", quality])
```

**Sample Rate Handling:**
```python
if sample_rate and sample_rate.lower() != "auto":
    cmd.extend(["-ar", sample_rate])
```

---

## VBR vs CBR Explanation

### **VBR (Variable Bit Rate) - V0, V2**
- **What it is**: Adjusts bitrate on-the-fly based on audio complexity
- **Advantages**: 
  - Smaller file size than CBR at same quality
  - Near-transparent quality (especially V0)
  - More efficient audio encoding
- **Disadvantages**: 
  - Slightly slower encoding
  - Some older devices may have compatibility issues
- **Use cases**: Archiving, listening to at home, efficient storage

### **CBR (Constant Bit Rate) - 320k, 256k, etc.**
- **What it is**: Maintains fixed bitrate throughout entire file
- **Advantages**:
  - Predictable file size
  - Maximum compatibility with all devices
  - Simpler streaming
- **Disadvantages**:
  - Less efficient (wastes bits on silent parts)
  - Larger files for same quality level
- **Use cases**: Streaming, mobile devices, maximum compatibility

---

## What "Best" Quality Means

**320 kbps CBR** is considered "best" because:
- It's the maximum standard MP3 bitrate
- Maintains complete fidelity to original audio
- No quality loss from lossy compression artifacts
- All frequencies (up to 20kHz) are fully preserved

**However, V0 VBR is arguably "transparent"** (indistinguishable from original) because:
- It dynamically allocates more bits to complex audio
- Can achieve transparency at lower average bitrate
- Still maintains quality while saving space
- Many audiophiles prefer V0 over 320k CBR

---

## UI Features

### For MP3 Format:
- **Quality Preset Dropdown**: Shows 7 quality options with descriptions
- **Sample Rate Combo**: Select "Auto" or specific sample rate (8kHz to 48kHz)
- **Info Text**: Explains VBR vs CBR differences

### For Other Audio Formats (WAV, AAC, OGG, FLAC):
- **Generic Quality Slider**: For backward compatibility
- **Sample Rate Selector**: Still available for format conversion

### For Video/Image Formats:
- **Generic Quality Slider**: Maintains original functionality

---

## Example FFmpeg Commands Generated

### MP3 with V0 VBR:
```bash
ffmpeg -i input.mp4 -vn -acodec libmp3lame -ar 44100 -q:a 0 -y output.mp3
```

### MP3 with 320k CBR:
```bash
ffmpeg -i input.mp4 -vn -acodec libmp3lame -ar 44100 -b:a 320k -y output.mp3
```

### MP3 with Custom Sample Rate:
```bash
ffmpeg -i input.mp4 -vn -acodec libmp3lame -ar 48000 -b:a 192k -y output.mp3
```

---

## Testing the Changes

1. Open the File Converter tab
2. Select an audio/video file to convert
3. Choose "MP3" as the output format
4. Notice the **MP3 Quality** dropdown appears with presets
5. Select **"V0 (Variable Bit Rate - Transparent)"** or any other preset
6. Choose a sample rate (or "Auto")
7. Click Convert
8. Check logs for ffmpeg command details

---

## Quality Recommendations

| Use Case | Recommendation | Reason |
|----------|-----------------|---------|
| **Archiving** | V0 VBR | Best quality with efficient storage |
| **Mobile Device** | 192k CBR | Good balance of quality and file size |
| **Streaming** | 128k CBR | Lowest bandwidth, acceptable quality |
| **High-End Audio** | V0 VBR | Nearly transparent, professional quality |
| **Maximum Quality** | 320k CBR | Absolute best MP3 quality available |
| **Compatibility** | 192k CBR | Works with all devices, good quality |

