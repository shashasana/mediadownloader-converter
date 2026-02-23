# Quick Reference Card - MP3 Quality Settings

## What Was Added

### ✅ V0 VBR Support
- Variable Bit Rate at highest quality
- Transparent audio (you won't hear difference)
- ~25% smaller than 320k CBR
- **FFmpeg**: `-q:a 0`

### ✅ 7 Quality Presets
1. 320 kbps (Best Quality - CBR)
2. **V0 (Variable Bit Rate - Transparent)** ← NEW
3. V2 (Variable Bit Rate - High Quality) ← NEW
4. 256 kbps (High Quality)
5. 192 kbps (Standard Quality)
6. 128 kbps (Low Quality)
7. 96 kbps (Minimal)

### ✅ 8 Sample Rate Options
- Auto (recommended)
- 48000 Hz (professional)
- 44100 Hz (CD quality)
- 32000, 22050, 16000, 11025, 8000 Hz

---

## Where to Use It

**File Converter Tab** → Select MP3 Format → Two new dropdowns appear:
1. "MP3 Quality" dropdown (select quality preset)
2. "Sample Rate" dropdown (select sample rate)

---

## Quick Decision

| Need | Setting |
|------|---------|
| **Best quality** | V0 VBR + Auto sample rate |
| **Safe/compatible** | 192k CBR + Auto sample rate |
| **Maximum** | 320k CBR + Auto sample rate |
| **Balanced** | V2 VBR + Auto sample rate |
| **Small files** | 128k CBR + Auto sample rate |

---

## The Difference

```
V0 VBR (Recommended):
✓ Transparent quality
✓ 25% smaller files
✓ Professional standard
✓ Efficient encoding
✗ Slightly slower

320k CBR (Traditional):
✓ Maximum quality guarantee
✓ All frequencies preserved
✓ Fast encoding
✗ Larger files
✗ Less efficient
```

---

## File Sizes (10 minutes of music)

| Quality | Size | Notes |
|---------|------|-------|
| 96k | 3.6 MB | Voice only |
| 128k | 4.8 MB | Low quality |
| 192k | 7.2 MB | Standard |
| V2 VBR | ~7 MB | Balanced |
| 256k | 9.6 MB | High |
| V0 VBR | ~9 MB | Transparent |
| 320k | 12 MB | Maximum |

---

## Top 3 Recommendations

### 🏆 #1: V0 VBR (Best Overall)
```
Quality:      V0 (Variable Bit Rate - Transparent)
Sample Rate:  Auto
File Size:    ~9 MB per 10 min
Use Case:     Archiving, listening at home
```

### 🥈 #2: 192k CBR (Most Compatible)
```
Quality:      192 kbps (Standard Quality)
Sample Rate:  44100 Hz
File Size:    ~7.2 MB per 10 min
Use Case:     Mobile devices, universal use
```

### 🥉 #3: 320k CBR (Maximum)
```
Quality:      320 kbps (Best Quality - CBR)
Sample Rate:  48000 Hz
File Size:    ~12 MB per 10 min
Use Case:     Professional, high-end audio
```

---

## What Each VBR Quality Means

- **V0**: Highest quality (transparent audio)
- **V2**: Very high quality (imperceptible loss)
- **V4-V9**: Available but not in presets (lower quality)

---

## Sample Rate Guide

- **44100 Hz**: Most compatible (CD standard)
- **48000 Hz**: Professional/broadcast standard
- **Auto**: Recommended (keeps original)

---

## Settings.json Support

Your settings are saved in settings.json:
- Default quality set to 320k (safe)
- Can be customized
- Persists between sessions

---

## Technical Details

### FFmpeg Commands Generated:

**V0 VBR:**
```bash
ffmpeg -i input.mp4 -vn -acodec libmp3lame -ar auto -q:a 0 output.mp3
```

**320k CBR:**
```bash
ffmpeg -i input.mp4 -vn -acodec libmp3lame -ar auto -b:a 320k output.mp3
```

**192k at 44.1kHz:**
```bash
ffmpeg -i input.mp4 -vn -acodec libmp3lame -ar 44100 -b:a 192k output.mp3
```

---

## Compatibility

- ✅ All MP3 bitrates work on all devices
- ✅ All sample rates supported by modern players
- ✅ Backward compatible with existing conversions
- ✅ FFmpeg fallback for missing libraries

---

## Encoding Speed

| Quality | Speed |
|---------|-------|
| 320k CBR | Fast ⚡⚡⚡ |
| 192k CBR | Fast ⚡⚡⚡ |
| 128k CBR | Fast ⚡⚡⚡ |
| V2 VBR | Slow ⚡ |
| V0 VBR | Slow ⚡ |

VBR is slower because it analyzes audio complexity.
This is normal and expected.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **V0 is slow** | Normal - VBR analyzes audio |
| **File too large** | Try V2 VBR or 256k CBR |
| **File too small** | Verify bitrate - check logs |
| **Quality issues** | Use V0 or 320k for best results |
| **Device incompatible** | All MP3 formats work everywhere |

---

## Summary

✅ You now have:
- Variable Bit Rate (V0/V2) support
- 7 quality presets (96k to 320k + VBR)
- 8 sample rate options (8kHz to 48kHz)
- Recommended settings for every use case
- Full backward compatibility

**Next time you convert to MP3:**
1. Select format: MP3
2. Select quality: V0 (Variable Bit Rate - Transparent)
3. Select sample rate: Auto
4. Click Convert
5. Enjoy transparent quality with 25% smaller files!

