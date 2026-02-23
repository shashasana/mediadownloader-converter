# MP3 Conversion Quality Guide - Quick Reference

## Quality Presets Available

When converting to MP3, you now have these quality options:

### 1. **320 kbps (Best Quality - CBR)**
- **Bitrate**: 320 kilobits per second (constant)
- **File Size**: ~1.2 MB per minute of audio
- **Quality**: Lossless-like, all frequencies preserved up to 20kHz
- **Encoding Speed**: Fast
- **Best For**: Archiving, high-end listening, maximum quality needs
- **FFmpeg Command**: `-b:a 320k`

### 2. **V0 (Variable Bit Rate - Transparent)**
- **Bitrate**: ~240 kbps average (varies 200-320 kbps)
- **File Size**: ~0.9 MB per minute of audio
- **Quality**: Transparent (indistinguishable from original for most people)
- **Encoding Speed**: Slower than CBR
- **Best For**: Archiving, listening at home, professional use
- **FFmpeg Command**: `-q:a 0`
- **Note**: This is what most audiophiles prefer

### 3. **V2 (Variable Bit Rate - High Quality)**
- **Bitrate**: ~190 kbps average (varies 170-210 kbps)
- **File Size**: ~0.7 MB per minute of audio
- **Quality**: Very high, imperceptible quality loss for most
- **Encoding Speed**: Slower than CBR
- **Best For**: Good balance of quality and file size
- **FFmpeg Command**: `-q:a 2`

### 4. **256 kbps (High Quality)**
- **Bitrate**: 256 kilobits per second (constant)
- **File Size**: ~1.0 MB per minute of audio
- **Quality**: Excellent, minimal difference from 320k for most
- **Best For**: Good quality without maximum file size
- **FFmpeg Command**: `-b:a 256k`

### 5. **192 kbps (Standard Quality)**
- **Bitrate**: 192 kilobits per second (constant)
- **File Size**: ~0.72 MB per minute of audio
- **Quality**: Good for most purposes, slight loss at high frequencies
- **Best For**: Balanced quality/size, portable devices
- **FFmpeg Command**: `-b:a 192k`

### 6. **128 kbps (Low Quality)**
- **Bitrate**: 128 kilobits per second (constant)
- **File Size**: ~0.48 MB per minute of audio
- **Quality**: Noticeable compression, suitable for speech
- **Best For**: Minimal storage, streaming
- **FFmpeg Command**: `-b:a 128k`

### 7. **96 kbps (Minimal)**
- **Bitrate**: 96 kilobits per second (constant)
- **File Size**: ~0.36 MB per minute of audio
- **Quality**: Significant compression artifacts, mostly for voice
- **Best For**: Maximum compression, voice files
- **FFmpeg Command**: `-b:a 96k`

---

## Sample Rates Explained

The sample rate determines how many times per second the audio is "sampled":

- **Auto**: Let FFmpeg detect the best sample rate (recommended)
- **48000 Hz**: Professional/broadcast quality (48 kHz)
- **44100 Hz**: CD quality (standard, most compatible)
- **32000 Hz**: Good quality, smaller files
- **22050 Hz**: Half of CD quality, for voice/low quality needs
- **16000 Hz**: Telephony quality
- **11025 Hz**: Reduced quality
- **8000 Hz**: Speech only, minimal quality

**Most Common:** 44100 Hz or 48000 Hz

---

## Quick Decision Guide

### I want the BEST quality possible
→ Use **320 kbps (CBR)** or **V0 (VBR)**
- V0 saves more space while maintaining transparency
- 320k is maximum MP3 quality guarantee

### I want good quality with reasonable file size
→ Use **V2 (VBR)** or **256 kbps (CBR)**
- V2 recommended - best balance
- Most people won't hear the difference from 320k

### I want a balanced setup
→ Use **192 kbps (CBR)**
- Works on all devices
- Good enough for most listeners
- Reasonable file size

### I want the smallest files
→ Use **128 kbps (CBR)** or **96 kbps (CBR)**
- Still acceptable quality for casual listening
- Minimal storage requirements

### I'm storing for long-term archiving
→ Use **V0 (VBR)** or **320 kbps (CBR)**
- Why re-encode later? Store at best quality now
- V0 is "good enough" if space is a concern

### I'm sharing with others
→ Use **192 kbps (CBR)**
- Compatible with all devices
- Good quality/size ratio
- Universally accepted standard

---

## VBR vs CBR Comparison

| Aspect | V0 VBR | V2 VBR | 320 CBR | 192 CBR |
|--------|--------|--------|---------|---------|
| **Perceived Quality** | Transparent | Very High | Best | Good |
| **File Size** | ~0.9 MB/min | ~0.7 MB/min | ~1.2 MB/min | ~0.72 MB/min |
| **Encoding Speed** | Slower | Slower | Fast | Fast |
| **Device Compatibility** | Excellent | Excellent | Excellent | Excellent |
| **Storage Efficient** | Yes | Yes | No | Yes |
| **Best Use** | Archiving | Balanced | Maximum Quality | Standard |

---

## Example Conversions

### Example 1: Convert 10-minute video to V0 MP3
```
Input: video.mp4 (100 MB)
Output Quality: V0 (VBR)
Sample Rate: Auto
Expected Size: ~9 MB
Command: ffmpeg -i video.mp4 -vn -acodec libmp3lame -q:a 0 output.mp3
```

### Example 2: Convert audio to 192k MP3 for mobile
```
Input: audio.wav (50 MB)
Output Quality: 192 kbps (CBR)
Sample Rate: 44100 Hz
Expected Size: ~3.6 MB
Command: ffmpeg -i audio.wav -acodec libmp3lame -ar 44100 -b:a 192k output.mp3
```

### Example 3: Convert music collection to V2 VBR
```
Input: music_album/ (multiple files)
Output Quality: V2 (VBR)
Sample Rate: 48000 Hz
Expected Size: ~70% of 320k CBR equivalent
Batch Command: for f in *.wav; do ffmpeg -i "$f" -acodec libmp3lame -ar 48000 -q:a 2 "${f%.wav}.mp3"; done
```

---

## Technical Details

### What does -q:a do?
- Used for VBR encoding in libmp3lame
- `-q:a 0` = highest quality (V0)
- `-q:a 2` = very high quality (V2)
- `-q:a 4` = high quality (V4)
- Lower numbers = better quality but larger files

### What does -b:a do?
- Sets constant bitrate for CBR encoding
- `-b:a 320k` = 320 kilobits per second
- `-b:a 192k` = 192 kilobits per second
- Fixed bitrate throughout file

### What does -ar do?
- Sets the output audio sample rate
- `-ar 44100` = 44.1 kHz (CD quality)
- `-ar 48000` = 48 kHz (professional)
- Omit or use "auto" to keep original sample rate

---

## Troubleshooting

### "Conversion is very slow"
- V0/V2 VBR encoding is slower than CBR
- This is normal - it's analyzing audio complexity
- Consider using 256k CBR for faster conversion

### "File seems too large"
- 320 kbps CBR will create large files
- Try V0 VBR instead - better quality/size ratio
- Or reduce to 256k or 192k bitrate

### "File seems low quality"
- Check if you used too low bitrate
- Minimum recommended: 128 kbps
- For high quality: use V0 or V2 VBR

### "Not compatible with device"
- Stick with standard CBR bitrates (192k, 256k, 320k)
- Avoid V0/V2 VBR if using very old devices
- MP3 is universally supported on modern devices

---

## Summary Table

| Need | Recommendation | Why |
|------|-----------------|-----|
| **Maximum Quality** | 320 kbps CBR | No compromises |
| **Best Overall** | V0 VBR | Transparent + efficient |
| **Balanced** | V2 VBR | Great quality, smaller files |
| **Standard** | 192 kbps CBR | Universal, trusted |
| **Portable** | 128 kbps CBR | Small files, decent quality |
| **Archiving** | V0 or V2 VBR | Future-proof encoding |
| **Old Device** | 192 kbps CBR | Guaranteed compatibility |

