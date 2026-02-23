# File Converter Smart UI - Quick Start Guide

## What's New

The FileConverterDialog has been upgraded with intelligent features that make batch file conversion more intuitive:

### 1. Format Filtering
When you select a file, only compatible output formats are shown.

**Example:** Select an MP3 file → Output format options: MP3, WAV, AAC, OGG, FLAC (audio formats only)

### 2. Smart UI
Conversion options are hidden when you first open the dialog, giving you a clean interface. They appear automatically when you add files.

**Timeline:**
- Dialog opens → No format/quality options visible (clean!)
- Add files → Format, quality, and preview options appear

### 3. Multi-File Preview
When converting multiple files, you see all output filenames before starting the conversion.

**Example:**
```
Selected: 3 files
Output Format: MP3

Output Names:
song1.mp3
song2.mp3
song3.mp3
```

## Usage Workflows

### Workflow 1: Single Audio File
1. Click "Choose Files" → Select "podcast.mp4"
2. Dialog shows format options (audio + video formats available)
3. Select "MP3" from Output Format dropdown
4. Output preview shows: "podcast.mp3"
5. Click "Convert"

### Workflow 2: Batch Audio Files
1. Click "Choose Files" → Select "song1.mp3", "song2.mp3", "song3.mp3"
2. Format options appear (audio formats)
3. Output Names shows:
   ```
   song1.mp3
   song2.mp3
   song3.mp3
   ```
4. Change format to "WAV" → Output Names update to:
   ```
   song1.wav
   song2.wav
   song3.wav
   ```
5. Click "Convert"

### Workflow 3: Image Batch Conversion
1. Drag & drop 5 PNG files onto the dialog
2. Format options appear (image formats: JPG, PNG, GIF, WebP, BMP)
3. Output Names shows all 5 filenames
4. Select "JPG" → Preview updates to show .jpg extensions
5. Adjust Quality slider (JPEG compression)
6. Click "Convert"

### Workflow 4: Video with Audio Extraction
1. Select "movie.mkv"
2. Format options include both video AND audio formats
3. Select "MP3" to extract audio
4. Quality slider adjusts to audio bitrate (32-320 kbps)
5. Output preview: "movie.mp3"
6. Click "Convert" → Audio extracted from video

## Format Support

### Audio → Audio
- MP3, WAV, AAC, OGG, FLAC (all inter-convertible)
- Quality: 32-320 kbps
- Sample Rate: 8kHz - 48kHz

### Video → Video  
- MP4, MKV, AVI, WebM, FLV
- Quality: 500-8000 kbps
- All formats inter-convertible

### Video → Audio
- Extract audio from any video format to MP3, WAV, AAC, OGG, FLAC

### Image → Image
- JPG, PNG, GIF, WebP, BMP
- Quality: 1-100%
- All formats inter-convertible

### Document (Limited)
- PDF, TXT, DOCX (basic support)
- Conversions: PDF↔TXT, DOCX↔TXT, DOCX→PDF

## Tips & Tricks

### Batch Converting with Different Qualities
1. Select all audio files
2. Change Output Format
3. Adjust Quality slider before conversion
4. All files will use the same quality settings

### Mixed File Types
When selecting multiple files of different types:
- Format list filtered for first selected file's type
- Example: Select [mp3, wav, flac] → Shows audio formats only ✓
- Example: Select [mp4, jpg] → Shows MP4-compatible formats only

### Output Preview
- The "Output Name:" field shows what the first file will be named
- The "Output Names:" display shows all output filenames
- Changes in real-time as you adjust format

### Drag & Drop
- Drag one or multiple files onto the dialog
- Conversion options appear automatically
- Works with Windows Explorer or other file managers

## Common Questions

**Q: What if I select files with different types (e.g., MP3 and MP4)?**
A: The format filtering uses the first file. If the first file is MP3, you'll see audio formats. To see all options, select the MP4 first.

**Q: Can I change the output format?**
A: Yes! The format dropdown updates automatically based on your input files. Just select a different format - output filenames update in real-time.

**Q: What happens if a format combination is unsupported?**
A: The format dropdown only shows supported combinations. Unsupported combinations don't appear.

**Q: Can I use different quality settings for different files?**
A: Not currently - all files in a batch use the same quality settings. This may be added as a future feature.

**Q: Where do the converted files go?**
A: They're saved in the same directory as the original files (or a configured output folder).

## Advanced Settings

### Quality Presets
- **MP3:** CBR 128/192/256/320 kbps or V0/V2 VBR
- **Video:** 500-8000 kbps (bitrate)
- **Audio (WAV/FLAC):** 32-320 kbps
- **Image:** 1-100% JPEG quality

### Sample Rates (Audio Only)
- 8 kHz (telephony)
- 16 kHz (wideband)
- 22.05 kHz (radio)
- 44.1 kHz (CD quality)
- 48 kHz (professional audio)

## Troubleshooting

**Issue: Format dropdown is empty**
- Solution: Ensure file is actually selected and supported format

**Issue: Output names not updating when changing format**
- Solution: Click the format dropdown again or wait a moment for refresh

**Issue: Quality options not visible**
- Solution: Add files first - options appear automatically

**Issue: Conversion fails for specific file**
- Solution: Check file isn't corrupted; try different format; check disk space
