# File Converter Dialog - Flow Diagram

## User Interaction Flow

```
┌─────────────────────────────────────────────────────────┐
│         File Converter Dialog - Initial State            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input Files: [Choose Files button]                    │
│  (File list display)                                   │
│                                                         │
│  [Preview Image Area]                                  │
│                                                         │
│  ✓ "Tip: Drag and drop files here"                    │
│                                                         │
│  ⚠ Format options HIDDEN                              │
│  ⚠ Quality options HIDDEN                             │
│  ⚠ Output display HIDDEN                              │
│                                                         │
│                                              [Convert]  │
│                                              [Cancel]   │
└─────────────────────────────────────────────────────────┘
                          ↓
              User adds files (click or drag/drop)
                          ↓
┌─────────────────────────────────────────────────────────┐
│     After set_input_files([file1.mp3, file2.mp3])       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input Files: 2 files selected                         │
│  • file1.mp3                                           │
│  • file2.mp3                                           │
│                                                         │
│  [Preview Image Area]                                  │
│                                                         │
│  ✓ Output Format: [MP3 ▼] ← Filtered to audio only   │
│                            (MP3, WAV, AAC, OGG, FLAC)  │
│                                                         │
│  Quality: ═══════════● 192 kbps                       │
│  Sample Rate: [44.1kHz ▼]                              │
│                                                         │
│  ✓ Output Names:                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │ file1.mp3                                       │  │
│  │ file2.mp3                                       │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│                                              [Convert]  │
│                                              [Cancel]   │
└─────────────────────────────────────────────────────────┘
                          ↓
                User selects format: WAV
                          ↓
┌─────────────────────────────────────────────────────────┐
│         After on_format_changed() → WAV                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input Files: 2 files selected                         │
│  • file1.mp3                                           │
│  • file2.mp3                                           │
│                                                         │
│  [Preview Image Area]                                  │
│                                                         │
│  ✓ Output Format: [WAV ▼]                             │
│                  (MP3, WAV, AAC, OGG, FLAC)           │
│                                                         │
│  Quality: ═══════════● 192 kbps                       │
│  Sample Rate: [44.1kHz ▼]                              │
│                                                         │
│  ✓ Output Names: [UPDATED]                            │
│  ┌─────────────────────────────────────────────────┐  │
│  │ file1.wav ← Extension changed                   │  │
│  │ file2.wav ← Extension changed                   │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│                                              [Convert]  │
│                                              [Cancel]   │
└─────────────────────────────────────────────────────────┘
                          ↓
                    User clicks Convert
                          ↓
           Batch conversion starts for both files
```

## Method Call Sequence

### When User Adds Files:
```
User Action: Click "Choose Files" → Select file1.mp3, file2.mp3
                ↓
         FileConverterDialog.select_files()
                ↓
         FileConverterDialog.set_input_files([file1.mp3, file2.mp3])
                ↓
         ├─→ _update_file_label()
         │    └─→ Updates: "2 files selected"
         │
         ├─→ _show_conversion_options()
         │    └─→ quality_container.show()
         │    └─→ output_names_label.show()
         │    └─→ output_names_display.show()
         │
         ├─→ _filter_output_formats()
         │    ├─→ Detect: input extension = "mp3"
         │    ├─→ Lookup: format_compatibility['mp3']
         │    ├─→ Result: [MP3, WAV, AAC, OGG, FLAC]
         │    └─→ Update format combo with these options
         │
         ├─→ _update_output_names()
         │    ├─→ For each file: extract basename
         │    ├─→ For each file: add output format extension
         │    └─→ Display: "file1.mp3\nfile2.mp3"
         │
         ├─→ update_preview()
         │    └─→ Updates preview label
         │
         └─→ load_preview_image(first_file)
              └─→ Extracts and shows thumbnail
```

### When User Changes Format to WAV:
```
User Action: Select "WAV" in format combo
                ↓
         FileConverterDialog.on_format_changed()
                ↓
         ├─→ Update quality/sample rate UI
         │    (same as before)
         │
         └─→ _update_output_names()  ← NEW!
              ├─→ Get current format: "WAV"
              ├─→ For each input file: basename + ".wav"
              └─→ Display: "file1.wav\nfile2.wav"
```

## Format Compatibility Logic

```
format_compatibility = {
    'mp3':  [MP3, WAV, AAC, OGG, FLAC],           ← Audio only
    'mp4':  [MP3, WAV, AAC, OGG, FLAC,            ← Audio + Video
             MP4, MKV, WebM],
    'mkv':  [MP3, WAV, AAC, OGG, FLAC,            ← Audio + Video  
             MP4, MKV, AVI, WebM],
    'jpg':  [JPG, PNG, GIF, WebP, BMP],          ← Image only
    ...
}

When _filter_output_formats() is called:
  1. Get input file extension: "mp3"
  2. Look up: format_compatibility["mp3"]
  3. Get result: [MP3, WAV, AAC, OGG, FLAC]
  4. Update format dropdown with ONLY these options
  5. User sees only compatible formats ✓
```

## State Transitions

```
┌──────────────────┐
│  Dialog Created  │
└────────┬─────────┘
         │
         ├→ setup_ui() called
         │  ├→ quality_container created
         │  ├→ quality_container.hide()
         │  ├→ output_names_label created  
         │  ├→ output_names_label.hide()
         │  └→ output_names_display created
         │     └→ output_names_display.hide()
         │
         ↓
┌─────────────────────────────┐
│  INITIAL STATE (No Files)   │
│  ✓ File selection visible   │
│  ✗ Format options hidden    │
│  ✗ Output display hidden    │
└────────┬────────────────────┘
         │
         ← User adds files
         │
         ↓
┌──────────────────────────────┐
│  FILES ADDED (set_input_files called)
│  ├→ _show_conversion_options()
│  │  └→ Show format, quality, outputs
│  ├→ _filter_output_formats()  
│  │  └→ Populate with compatible formats
│  └→ _update_output_names()
│     └→ Display output filenames
└────────┬─────────────────────┘
         │
         ↓
┌──────────────────────────────┐
│  FILES SELECTED (Format options visible)
│  ✓ File selection visible    │
│  ✓ Format options visible    │
│  ✓ Output display visible    │
│  ✓ Format dropdown filtered  │
└────────┬─────────────────────┘
         │
         ← User changes format
         │
         ↓
┌──────────────────────────────┐
│  FORMAT CHANGED (on_format_changed called)
│  └→ _update_output_names()
│     └→ Output names updated with new format
└────────┬─────────────────────┘
         │
         ← User clicks Convert
         │
         ↓
┌──────────────────────────────┐
│  CONVERSION STARTED           │
│  (Queue added to download manager)
│                               │
└──────────────────────────────┘
```

## Widget Visibility Management

### Initial Setup (setup_ui)
```
Create: quality_container
        └─ quality_combo_layout
           ├─ mp3_quality_layout  
           ├─ sample_rate_layout
           └─ generic_quality_layout
        └ HIDE

Create: output_names_label
        └ HIDE

Create: output_names_display  
        └ HIDE
```

### When Files Added (set_input_files)
```
Call: _show_conversion_options()
      ├─ quality_container.show()      ← NOW VISIBLE
      ├─ output_names_label.show()     ← NOW VISIBLE
      └─ output_names_display.show()   ← NOW VISIBLE

Call: on_format_changed()
      ├─ Show/hide sub-options based on format
      ├─ Update quality slider ranges
      └─ Call _update_output_names()   ← DISPLAY UPDATES
```

## Key Design Decisions

1. **Filtering happens automatically** - No need for user to choose compatibility, it's done for them

2. **Options hidden initially** - Reduces visual clutter and cognitive load

3. **Output names update in real-time** - User always sees accurate preview

4. **Format dictionary is extensible** - Easy to add new format combinations

5. **Works with existing code** - No breaking changes to downloader or other components

6. **Batch-aware** - All output filenames displayed, not just first file

This design follows modern UX principles of progressive disclosure and smart defaults.
