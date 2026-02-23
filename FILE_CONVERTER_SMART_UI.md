# File Converter Smart UI Implementation

## Overview
Implemented intelligent user interface improvements for the FileConverterDialog in the Qt-based media downloader application. The converter now provides context-aware format filtering, conditional UI visibility, and multi-file output display.

## Features Implemented

### 1. Smart Format Filtering
**Purpose:** Only show output formats that are compatible with the selected input file type.

**Implementation:**
- Added `format_compatibility` dictionary in `FileConverterDialog.__init__()` with 20+ format mappings
- Maps input file extensions to arrays of compatible output formats
- Examples:
  - MP3 → [MP3, WAV, AAC, OGG, FLAC] (audio only)
  - MP4 → [MP3, WAV, AAC, OGG, FLAC, MP4, MKV, WebM] (audio + video)
  - JPG → [JPG, PNG, GIF, WebP, BMP] (image only)

**Method:** `_filter_output_formats()`
- Determines input file extension from first selected file
- Retrieves compatible formats from mapping
- Updates format combo box with only compatible options
- Preserves current selection if still compatible

### 2. Conditional UI Visibility
**Purpose:** Hide complex conversion options until files are actually selected.

**Initial State:**
- `quality_container` (format options, quality slider, sample rate) - HIDDEN
- `output_names_label` and `output_names_display` - HIDDEN
- Other UI elements remain visible (file selection button, drag & drop hint)

**When Files Selected:**
- `set_input_files()` method calls `_show_conversion_options()`
- Reveals all conversion controls
- Provides cleaner, less intimidating initial interface

**Method:** `_show_conversion_options()`
- Called automatically when files are added
- Shows: quality_container, output_names_label, output_names_display
- Triggered by: file selection dialog, drag & drop, programmatic calls

### 3. Multi-File Output Display
**Purpose:** Show output filename for each input file when batch converting.

**Implementation:**
- `output_names_display` QTextEdit widget shows one filename per line
- Generated automatically based on:
  - Input file base name
  - Selected output format
  
**Example:**
```
Input Files:
- song1.mp3
- song2.mp3

Output Format: WAV

Output Names:
song1.wav
song2.wav
```

**Method:** `_update_output_names()`
- Generates output filenames for all selected files
- Called when files are added
- Called when output format changes
- Called in `on_format_changed()` for dynamic updates

### 4. Dynamic Format Change Handling
**Method:** `on_format_changed()`
- Updated to call `_update_output_names()` after format selection changes
- Ensures output preview stays synchronized with format selection
- Maintains all existing quality/sample rate logic

## File Structure

### Modified: `ui_components_qt.py`

**Changes in `FileConverterDialog` class:**

1. **In `__init__()`:**
   - Added `self.format_compatibility` dictionary with 20+ format mappings
   - Covers: audio, video, image, and document formats

2. **In `setup_ui()`:**
   - Changed `quality_container` from local to instance variable (`self.quality_container`)
   - Added `self.quality_container.hide()` after creation
   - Added `self.output_names_label` widget (QLabel)
   - Added `self.output_names_display` widget (QTextEdit)
   - Both label and display hidden initially

3. **New method `_show_conversion_options()`:**
   - Shows quality_container, output_names_label, output_names_display
   - Called when files are selected

4. **New method `_filter_output_formats()`:**
   - Filters format combo based on input file extension
   - Uses format_compatibility dictionary
   - Preserves current selection if compatible

5. **New method `_update_output_names()`:**
   - Generates output filename for each input file
   - Displays in output_names_display widget
   - One filename per line

6. **Updated `on_format_changed()`:**
   - Added call to `_update_output_names()` to keep output preview synced
   - Existing quality/sample rate logic unchanged

7. **Updated `set_input_files()`:**
   - Now calls `_show_conversion_options()` to show controls
   - Calls `_filter_output_formats()` for smart filtering
   - Calls `_update_output_names()` to display outputs

## User Experience Flow

### Initial State
1. User opens File Converter dialog
2. Format options are hidden (cleaner interface)
3. File selection button is visible
4. "Tip: Drag and drop files here" hint is visible

### After Adding Files (Single File - MP3)
1. Dialog shows:
   - Selected file: "song.mp3"
   - Output format combo populated with: [MP3, WAV, AAC, OGG, FLAC]
   - Quality/sample rate options visible (filtered for audio)
   - Output name preview: "song.mp3" (updates dynamically)

### After Adding Files (Multiple Files)
1. Dialog shows:
   - Selected files: "3 files selected"
   - File list: Shows all selected files
   - Output format combo: Filtered based on first file
   - Output names display: Shows all 3 output filenames
2. Changing format updates all output names immediately

### After Adding Video File (MP4)
1. Format combo shows: [MP3, WAV, AAC, OGG, FLAC, MP4, MKV, WebM]
2. Quality slider adjusts to video bitrate (kbps)
3. Sample rate options hidden (video doesn't have sample rates)
4. Output preview shows: "video.mp4" (initially)

## Format Compatibility Mappings

### Audio Formats
- MP3, WAV, AAC, OGG, FLAC: ↔ All other audio formats
- Sample rate: 8kHz to 48kHz (configurable per format)

### Video Formats  
- MP4, MKV, AVI, WebM, FLV, MOV, M4V: ↔ All video + audio formats
- Can extract audio to any audio format

### Image Formats
- JPG, JPEG, PNG, GIF, BMP, WebP: ↔ All image formats
- JPEG compression customizable (1-100%)

### Document Formats (Limited)
- PDF, TXT, DOCX: Limited conversion support
- PDF ↔ TXT (basic text extraction)
- DOCX ↔ PDF, TXT (via pandoc if available)

## Code Examples

### Adding Format Compatibility for New Format
```python
self.format_compatibility['wav'] = ['MP3', 'WAV', 'AAC', 'OGG', 'FLAC']
```

### Testing the Implementation
```python
from ui_components_qt import FileConverterDialog

dialog = FileConverterDialog()
dialog.set_input_files(['/path/to/song.mp3', '/path/to/song2.mp3'])

# Outputs will show:
# song.mp3
# song2.mp3

dialog.format_combo.setCurrentText('WAV')

# Outputs will update to:
# song.wav
# song2.wav
```

## Benefits

1. **Reduced Confusion:** Users only see valid conversion options
2. **Cleaner Interface:** Complex options hidden until needed
3. **Batch Awareness:** Multiple files display all output names upfront
4. **Real-time Feedback:** Output names update as users change format
5. **Professional UX:** Follows modern app design principles
   - Progressive disclosure (show options as needed)
   - Smart defaults (filter options based on input)
   - Immediate feedback (output preview updates)

## Testing

All functionality tested with:
- Single file selection
- Multiple file selection  
- Format compatibility mappings
- Output name generation
- Format change handling
- UI visibility state management

All tests pass successfully (see test_file_converter_ui.py).

## Future Enhancements

1. Individual file previews in output names display
2. Per-file format selection (different output formats for different inputs)
3. Custom filename patterns
4. Format recommendations based on file content analysis
5. Conversion preset profiles (e.g., "High Quality", "Small File Size")
