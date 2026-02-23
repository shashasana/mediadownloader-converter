"""Core download functionality"""

import os
import subprocess
import threading
import time
from download_manager import DownloadTask, DownloadStatus
from config import YTDLP_PATH, FFMPEG_PATH
from tkinter import messagebox
import re

SPEED_MULTIPLIERS = {
    "B/s": 1,
    "KiB/s": 1024,
    "MiB/s": 1024 * 1024,
    "GiB/s": 1024 * 1024 * 1024
}

def _parse_speed(speed_str: str) -> float:
    try:
        match = re.match(r"(\d+\.\d+)(\w+/s)", speed_str)
        if match:
            val = float(match.group(1))
            unit = match.group(2)
            return val * SPEED_MULTIPLIERS.get(unit, 1)
    except Exception:
        pass
    return 0.0

def _format_speed(value: float) -> str:
    if value <= 0:
        return "0 B/s"
    if value >= SPEED_MULTIPLIERS["GiB/s"]:
        return f"{value / SPEED_MULTIPLIERS['GiB/s']:.2f}GiB/s"
    if value >= SPEED_MULTIPLIERS["MiB/s"]:
        return f"{value / SPEED_MULTIPLIERS['MiB/s']:.2f}MiB/s"
    if value >= SPEED_MULTIPLIERS["KiB/s"]:
        return f"{value / SPEED_MULTIPLIERS['KiB/s']:.2f}KiB/s"
    return f"{value:.2f}B/s"

def detect_platform(url: str) -> str:
    """Detect content platform from URL"""
    if "instagram.com" in url:
        return "Instagram"
    if "facebook.com" in url:
        return "Facebook"
    if "music.youtube.com" in url:
        return "YT Music"
    if "youtube.com" in url:
        return "YouTube"
    if "tiktok.com" in url:
        return "TikTok"
    if "spotify.com" in url:
        return "Spotify"
    return "Unknown"

def get_format_args(format_choice: str, quality_choice: str, audio_codec: str, audio_bitrate: str) -> list:
    """Get yt-dlp format arguments based on format and quality"""
    fmt = format_choice
    quality = quality_choice

    if fmt in ("mp4", "webm") and quality.startswith("audio"):
        quality = "best"

    video_quality_map = {
        "2160p": "bestvideo[height<=2160]+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best",
        "720p": "bestvideo[height<=720]+bestaudio/best",
        "480p": "bestvideo[height<=480]+bestaudio/best",
        "360p": "bestvideo[height<=360]+bestaudio/best",
    }
    height_match = re.match(r"^(\d+)p$", quality)
    if height_match:
        height = int(height_match.group(1))
        video_quality_map[quality] = f"bestvideo[height<={height}]+bestaudio/best"

    if fmt == "mp3":
        return ["-f", "bestaudio", "-x", "--audio-format", audio_codec, "--audio-quality", audio_bitrate]

    if fmt == "flac":
        return ["-f", "bestaudio", "-x", "--audio-format", "flac"]

    if fmt == "webm":
        if quality in video_quality_map:
            return ["-f", f"{video_quality_map[quality]}[ext=webm]"]
        return ["-f", "best[ext=webm]"]

    if fmt == "mp4":
        if quality in video_quality_map:
            return ["-f", f"{video_quality_map[quality]}[ext=mp4]"]
        return ["-f", "best[ext=mp4]"]

    return []

def get_output_extension(format_choice: str) -> str:
    """Get file extension for format choice"""
    ext_map = {
        "mp4": ".mp4",
        "mp3": ".mp3",
        "flac": ".flac",
        "webm": ".webm",
        "best": ""
    }
    return ext_map.get(format_choice, "")

def parse_progress(line: str) -> dict:
    """Parse yt-dlp progress line"""
    result = {
        "progress": 0.0,
        "speed": "0 B/s",
        "eta": "00:00",
        "size": "Unknown"
    }

    try:
        percent_match = re.search(r'(\d+\.\d+)%', line)
        if percent_match:
            result["progress"] = float(percent_match.group(1))

        speed_match = re.search(r'(\d+\.\d+\w+/s)', line)
        if speed_match:
            result["speed"] = speed_match.group(1)

        eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
        if eta_match:
            result["eta"] = eta_match.group(1)

        size_match = re.search(r'of\s+(~?\d+\.\d+\w+)', line)
        if size_match:
            result["size"] = size_match.group(1).replace("~", "")
    except:
        pass

    return result

def fetch_media_info(url: str, log_callback=None) -> dict:
    """Fetch media metadata using yt-dlp"""
    if not os.path.exists(YTDLP_PATH):
        if log_callback:
            log_callback("yt-dlp not found. Check YTDLP_PATH in config.py\n")
        return {}

    try:
        if "spotify.com" in url:
            try:
                import urllib.parse
                import urllib.request
                import json

                oembed_url = "https://open.spotify.com/oembed?url=" + urllib.parse.quote(url, safe="")
                with urllib.request.urlopen(oembed_url, timeout=10) as response:
                    data = response.read()
                payload = json.loads(data.decode("utf-8"))
                return {
                    "title": payload.get("title") or "Spotify Track",
                    "uploader": payload.get("provider_name") or "Spotify",
                    "thumbnail": payload.get("thumbnail_url"),
                    "duration": 0,
                    "formats": []
                }
            except Exception as e:
                if log_callback:
                    log_callback(f"Spotify preview failed: {e}\n")

        process = subprocess.run(
            [YTDLP_PATH, "-J", "--no-warnings", url],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if process.returncode == 0 and process.stdout:
            import json
            return json.loads(process.stdout)
        if log_callback:
            err = process.stderr.strip() if process.stderr else "Unknown error"
            log_callback(f"yt-dlp preview failed: {err}\n")
    except Exception as e:
        if log_callback:
            log_callback(f"yt-dlp preview error: {e}\n")
    return {}

def build_command(task: DownloadTask, settings: dict) -> list:
    """Build yt-dlp command based on task and settings"""
    format_args = get_format_args(
        task.format_choice,
        settings.get("quality_choice", "best"),
        settings.get("audio_codec", "mp3"),
        settings.get("audio_bitrate", "192k")
    )

    cmd = [
        YTDLP_PATH,
        "--ffmpeg-location", os.path.dirname(FFMPEG_PATH),
        # Avoid .part files and resume artifacts
        "--no-part",
        "--newline",
        "-o", task.path
    ]

    if settings.get("embed_thumbnail", True):
        cmd.append("--embed-thumbnail")
    if settings.get("embed_metadata", True):
        cmd.append("--add-metadata")
    if settings.get("subtitles", False):
        cmd.append("--write-subs")
    if settings.get("auto_subtitles", False):
        cmd.append("--write-auto-subs")

    langs = settings.get("subtitle_langs", "en.*")
    if settings.get("subtitles", False) or settings.get("auto_subtitles", False):
        cmd.extend(["--sub-langs", langs])
        cmd.append("--embed-subs")

    if format_args:
        cmd.extend(format_args)

    cmd.append(task.url)
    return cmd

def download_task(task: DownloadTask, manager, settings: dict, on_progress_callback=None, on_log_callback=None):
    """Execute a download task"""
    retry_count = int(settings.get("retry_count", 0))
    retry_delay = int(settings.get("retry_delay", 2))
    attempts = 0

    while attempts <= retry_count:
        try:
            task.platform = detect_platform(task.url)
            task.status = DownloadStatus.DOWNLOADING

            if task.platform in ["Instagram", "Facebook"] and "private" in task.url:
                task.status = DownloadStatus.FAILED
                if on_log_callback:
                    on_log_callback("Error: Private post not supported\n")
                manager.complete_task(task, False)
                return

            cmd = build_command(task, settings)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            task.process = process

            for line in process.stdout:
                if task.status in [DownloadStatus.CANCELLED, DownloadStatus.PAUSED]:
                    try:
                        process.terminate()
                    except Exception:
                        pass
                    return
                if on_log_callback:
                    on_log_callback(line)

                if "[download]" in line and "%" in line:
                    prog_data = parse_progress(line)
                    task.file_size = prog_data.get("size", task.file_size)
                    if prog_data.get("speed"):
                        speed_val = _parse_speed(prog_data["speed"])
                        if speed_val > 0:
                            task.speed_history.append(speed_val)
                            if len(task.speed_history) > 5:
                                task.speed_history.pop(0)
                            avg_speed = sum(task.speed_history) / len(task.speed_history)
                            prog_data["speed"] = _format_speed(avg_speed)
                    manager.update_progress(
                        task,
                        prog_data["progress"],
                        prog_data["speed"],
                        prog_data["eta"]
                    )
                    if on_progress_callback:
                        on_progress_callback(task)

            if task.status in [DownloadStatus.CANCELLED, DownloadStatus.PAUSED]:
                return

            try:
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
                return

            if process.returncode == 0:
                task.progress = 100.0
                manager.complete_task(task, True)
                if on_log_callback:
                    on_log_callback("âœ“ Download completed successfully!\n")
                return

            attempts += 1
            if attempts <= retry_count:
                if on_log_callback:
                    on_log_callback(f"Retrying in {retry_delay}s... ({attempts}/{retry_count})\n")
                time.sleep(retry_delay)
            else:
                manager.complete_task(task, False)
                if on_log_callback:
                    on_log_callback("âœ— Download failed\n")
                return

        except Exception as e:
            attempts += 1
            if on_log_callback:
                on_log_callback(f"Error: {str(e)}\n")
            if attempts > retry_count:
                task.status = DownloadStatus.FAILED
                manager.complete_task(task, False)
                return


def convert_file(input_file: str, output_format: str, quality: str, sample_rate: str, ffmpeg_path: str, log_callback=None, output_file_path=None, gif_mode="reduce_fps") -> bool:
    """Convert a file using available tools (ffmpeg, Pillow, cairosvg)."""
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    if not input_file or not os.path.exists(input_file):
        log("Input file not found.\n")
        return False

    output_format = (output_format or "").lower().lstrip(".")
    if not output_format:
        log("Missing output format.\n")
        return False

    if output_file_path:
        output_file = output_file_path
    else:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = os.path.dirname(input_file)
        output_file = os.path.join(output_dir, f"{base_name}.{output_format}")

    input_ext = os.path.splitext(input_file)[1].lower().lstrip(".")

    image_exts = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "svg"}
    audio_exts = {"mp3", "wav", "aac", "ogg", "flac", "m4a", "aiff"}
    video_exts = {"mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "gif"}

    def _parse_quality(val: str):
        text = str(val).strip()
        if text.lower().startswith("v") and text[1:].isdigit():
            return ("vbr", int(text[1:]))
        if text.endswith("k") and text[:-1].isdigit():
            return ("bitrate", text)
        if text.isdigit():
            return ("bitrate", f"{text}k")
        return ("bitrate", None)

    def _looks_like_svg(path: str) -> bool:
        try:
            with open(path, "rb") as f:
                head = f.read(2048)
            text = head.decode("utf-8", errors="ignore").lower()
            return "<svg" in text or "w3.org/2000/svg" in text
        except Exception:
            return False

    def _convert_svg_with_cairosvg() -> bool:
        try:
            from cairosvg import svg2png, svg2pdf
            if output_format == "pdf":
                svg2pdf(url=input_file, write_to=output_file)
                log(f"âœ“ Converted: {os.path.basename(output_file)}\n")
                return True

            temp_png = output_file if output_format == "png" else f"{output_file}.png"
            svg2png(url=input_file, write_to=temp_png)
            if output_format == "png":
                log(f"âœ“ Converted: {os.path.basename(output_file)}\n")
                return True

            from PIL import Image
            img = Image.open(temp_png)
            if output_format in {"jpg", "jpeg"} and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            quality_val = 90
            try:
                quality_val = int(str(quality))
            except Exception:
                pass
            img.save(output_file, quality=max(1, min(quality_val, 100)))
            try:
                os.remove(temp_png)
            except Exception:
                pass
            log(f"âœ“ Converted: {os.path.basename(output_file)}\n")
            return True
        except Exception as e:
            log(f"SVG conversion failed (cairosvg). Error: {e}\n")
            return False

    # SVG conversion via cairosvg when available
    if input_ext == "svg" and output_format in {"png", "jpg", "jpeg", "pdf"}:
        if _convert_svg_with_cairosvg():
            return True

    # Image conversion via Pillow
    if output_format in image_exts and input_ext in image_exts and input_ext != "svg":
        try:
            from PIL import Image
            img = Image.open(input_file)
            if output_format in {"jpg", "jpeg"} and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            save_kwargs = {}
            if output_format in {"jpg", "jpeg", "webp"}:
                try:
                    quality_val = int(str(quality))
                except Exception:
                    quality_val = 90
                save_kwargs["quality"] = max(1, min(quality_val, 100))
                if output_format in {"jpg", "jpeg"}:
                    save_kwargs["optimize"] = True
            elif output_format == "gif" and input_ext == "gif":
                # GIF -> GIF compression modes.
                # - reduce_fps: drop frames proportionally to percentage.
                # - fast_forward: keep all frames and scale frame durations.
                # - slack_emoji_128kb: auto-tune for <=128KB with best-effort quality.
                try:
                    quality_val = int(str(quality))
                    quality_val = max(1, min(100, quality_val))
                    mode = str(gif_mode or "reduce_fps").strip().lower()
                    if mode not in {"reduce_fps", "fast_forward", "slack_emoji_128kb"}:
                        mode = "reduce_fps"

                    mode_label_map = {
                        "reduce_fps": "Reduce Framerate",
                        "fast_forward": "Fast Forward",
                        "slack_emoji_128kb": "Slack Emoji (Auto 128KB)",
                    }
                    mode_label = mode_label_map.get(mode, "Reduce Framerate")
                    log(f"GIF mode: {mode_label}, percent: {quality_val}%\n")

                    def _size_change_text(input_size: int, output_size: int) -> str:
                        if input_size <= 0:
                            return "size unknown"
                        change = ((input_size - output_size) / input_size) * 100
                        if change >= 0:
                            return f"saved {change:.1f}%"
                        return f"grew {abs(change):.1f}%"

                    # Detect if animated by checking for multiple frames
                    is_animated = False
                    n_frames = 1
                    try:
                        img.seek(1)
                        is_animated = True
                        n_frames = getattr(img, 'n_frames', 1)
                        img.seek(0)
                        log(f"Detected animated GIF with {n_frames} frames\n")
                    except EOFError:
                        log("Detected static GIF\n")

                    # Load all frames once for GIF processing modes.
                    frames = []
                    durations = []
                    loop_value = img.info.get('loop', 0)
                    total_frames = n_frames if is_animated else 1
                    log(f"Processing {total_frames} frames...\n")
                    for frame_num in range(total_frames):
                        if is_animated:
                            img.seek(frame_num)
                        frame = img.copy().convert("RGBA")
                        frame_duration = int(img.info.get('duration', 100))
                        durations.append(max(10, frame_duration))
                        frames.append(frame)

                    if mode == "slack_emoji_128kb":
                        import shutil
                        target_size = 128 * 1024
                        log(f"Slack target size: {target_size / 1024:.0f}KB\n")

                        try:
                            resample_lanczos = Image.Resampling.LANCZOS
                        except AttributeError:
                            resample_lanczos = Image.LANCZOS

                        try:
                            dither_none = Image.Dither.NONE
                        except AttributeError:
                            dither_none = Image.NONE

                        # Ordered from higher quality to stronger compression.
                        candidate_presets = [
                            (128, 128, 1),
                            (112, 128, 1),
                            (96, 128, 1),
                            (96, 96, 1),
                            (96, 64, 1),
                            (96, 64, 2),
                            (88, 64, 2),
                            (80, 64, 2),
                            (80, 48, 2),
                            (72, 48, 2),
                            (72, 32, 2),
                            (64, 32, 2),
                            (64, 32, 3),
                            (56, 32, 3),
                            (56, 24, 3),
                            (48, 24, 3),
                            (48, 16, 4),
                            (40, 16, 4),
                        ]

                        # Use quality percentage as preference for where to start searching.
                        if quality_val >= 80:
                            start_idx = 0
                        elif quality_val >= 60:
                            start_idx = 2
                        elif quality_val >= 40:
                            start_idx = 5
                        elif quality_val >= 25:
                            start_idx = 8
                        else:
                            start_idx = 11
                        ordered_candidates = candidate_presets[start_idx:] + candidate_presets[:start_idx]

                        best_tmp = None
                        best_size = None
                        best_meta = None
                        created_tmp = []

                        for attempt, (max_dim, colors, frame_step) in enumerate(ordered_candidates, 1):
                            if total_frames <= 1 or frame_step <= 1:
                                selected_indices = [0] if total_frames == 1 else list(range(total_frames))
                            else:
                                selected_indices = list(range(0, total_frames, frame_step))
                                if selected_indices[-1] != total_frames - 1:
                                    selected_indices.append(total_frames - 1)

                            selected_frames = []
                            selected_durations = []
                            for pos, idx in enumerate(selected_indices):
                                next_idx = selected_indices[pos + 1] if pos + 1 < len(selected_indices) else total_frames
                                merged_duration = sum(durations[idx:next_idx])
                                selected_durations.append(max(10, merged_duration))

                                base_frame = frames[idx]
                                w, h = base_frame.size
                                if max(w, h) > max_dim:
                                    scale = max_dim / float(max(w, h))
                                    new_size = (
                                        max(1, int(round(w * scale))),
                                        max(1, int(round(h * scale)))
                                    )
                                    work_frame = base_frame.resize(new_size, resample=resample_lanczos)
                                else:
                                    work_frame = base_frame.copy()

                                pal_frame = work_frame.convert(
                                    "P",
                                    palette=Image.ADAPTIVE,
                                    colors=colors,
                                    dither=dither_none
                                )
                                selected_frames.append(pal_frame)

                            tmp_output = f"{output_file}.slack_tmp_{attempt}.gif"
                            created_tmp.append(tmp_output)
                            selected_frames[0].save(
                                tmp_output,
                                save_all=True,
                                append_images=selected_frames[1:],
                                duration=selected_durations,
                                loop=loop_value,
                                optimize=True
                            )

                            out_size = os.path.getsize(tmp_output)
                            log(
                                f"Slack try {attempt}/{len(ordered_candidates)}: "
                                f"{max_dim}px, {colors} colors, step {frame_step}, "
                                f"frames {len(selected_frames)}/{total_frames} -> {out_size/1024:.1f}KB\n"
                            )

                            if best_size is None or out_size < best_size:
                                best_size = out_size
                                best_tmp = tmp_output
                                best_meta = (max_dim, colors, frame_step, len(selected_frames))

                            if out_size <= target_size:
                                break

                        if not best_tmp or not os.path.exists(best_tmp):
                            return False

                        shutil.copy2(best_tmp, output_file)

                        # Cleanup temporary files
                        for tmp in created_tmp:
                            if tmp != best_tmp:
                                try:
                                    os.remove(tmp)
                                except Exception:
                                    pass
                        try:
                            os.remove(best_tmp)
                        except Exception:
                            pass

                        input_size = os.path.getsize(input_file)
                        output_size = os.path.getsize(output_file)
                        size_text = _size_change_text(input_size, output_size)
                        hit_target = output_size <= target_size
                        if best_meta:
                            dim, colors, step, kept = best_meta
                            log(
                                f"Slack result: {output_size/1024:.1f}KB "
                                f"({'target reached' if hit_target else 'best effort'}) | "
                                f"{dim}px, {colors} colors, step {step}, frames {kept}/{total_frames}\n"
                            )
                        log(f"Compressed GIF: {input_size/1024:.1f}KB -> {output_size/1024:.1f}KB ({size_text})\n")
                        return True

                    # Handle percentage-based modes.
                    if quality_val < 100:
                        quality_ratio = quality_val / 100.0

                        if mode == "fast_forward":
                            # GIF frame timing is effectively centisecond-based in many players.
                            # Distribute rounding so total duration tracks the requested percentage.
                            target_total_cs = max(
                                len(durations),
                                int(round((sum(durations) * quality_ratio) / 10.0))
                            )
                            scaled_cs = []
                            error = 0.0
                            for d in durations:
                                target_cs = (d * quality_ratio) / 10.0 + error
                                cs = int(round(target_cs))
                                if cs < 1:
                                    cs = 1
                                scaled_cs.append(cs)
                                error = target_cs - cs

                            diff = target_total_cs - sum(scaled_cs)
                            idx = 0
                            while diff != 0 and scaled_cs:
                                pos = idx % len(scaled_cs)
                                if diff > 0:
                                    scaled_cs[pos] += 1
                                    diff -= 1
                                elif scaled_cs[pos] > 1:
                                    scaled_cs[pos] -= 1
                                    diff += 1
                                idx += 1

                            scaled_durations = [cs * 10 for cs in scaled_cs]
                            input_ms = sum(durations)
                            output_ms = sum(scaled_durations)

                            frames[0].save(
                                output_file,
                                save_all=True,
                                append_images=frames[1:],
                                duration=scaled_durations,
                                loop=loop_value,
                                optimize=True
                            )

                            input_size = os.path.getsize(input_file)
                            output_size = os.path.getsize(output_file)
                            size_text = _size_change_text(input_size, output_size)
                            log(f"Fast-forwarded duration: {input_ms/1000:.2f}s -> {output_ms/1000:.2f}s ({quality_val}%)\n")
                            log(f"Kept all frames: {total_frames}/{total_frames}\n")
                            log(f"Compressed GIF: {input_size/1024:.1f}KB -> {output_size/1024:.1f}KB ({size_text})\n")
                            return True

                        target_frames = max(1, int(round(total_frames * quality_ratio)))
                        if target_frames >= total_frames:
                            selected_indices = list(range(total_frames))
                        elif target_frames == 1:
                            selected_indices = [0]
                        else:
                            selected_indices = [int(round(i * (total_frames - 1) / (target_frames - 1))) for i in range(target_frames)]

                        selected_frames = [frames[i] for i in selected_indices]
                        # Preserve total playback time by merging skipped frame durations.
                        selected_durations = []
                        for pos, idx in enumerate(selected_indices):
                            next_idx = selected_indices[pos + 1] if pos + 1 < len(selected_indices) else total_frames
                            merged_duration = sum(durations[idx:next_idx])
                            selected_durations.append(max(10, merged_duration))
                        log(f"Keeping {len(selected_frames)}/{total_frames} frames (quality {quality_val}%)\n")

                        selected_frames[0].save(
                            output_file,
                            save_all=True,
                            append_images=selected_frames[1:],
                            duration=selected_durations,
                            loop=loop_value,
                            optimize=True
                        )

                        input_size = os.path.getsize(input_file)
                        output_size = os.path.getsize(output_file)
                        size_text = _size_change_text(input_size, output_size)
                        log(f"Reduced frames to {len(selected_frames)}/{total_frames}: {input_size/1024:.1f}KB -> {output_size/1024:.1f}KB ({size_text})\n")
                        return True

                    # 100%: copy original to preserve exact frame data and timing.
                    import shutil
                    log("Quality at 100% - copying original GIF\n")
                    shutil.copy2(input_file, output_file)
                    input_size = os.path.getsize(input_file)
                    log(f"Converted: {input_size/1024:.1f}KB ({total_frames} frames)\n")
                    return True

                except Exception as e:
                    log(f"GIF processing error: {e}\n")
                    import traceback
                    log(traceback.format_exc() + "\n")
                    # Fallback: copy original
                    try:
                        import shutil
                        shutil.copy2(input_file, output_file)
                        return True
                    except Exception as copy_e:
                        log(f"Failed to copy original: {copy_e}\n")
                        return False
            elif output_format == "gif":
                # Non-GIF -> GIF should convert normally; frame-percentage compression is GIF -> GIF only.
                save_kwargs["optimize"] = True
            elif output_format == "png":
                save_kwargs["optimize"] = True
            img.save(output_file, **save_kwargs)
            log(f"âœ“ Converted: {os.path.basename(output_file)}\n")
            return True
        except Exception as e:
            if output_format in {"png", "jpg", "jpeg", "pdf"} and _looks_like_svg(input_file):
                log("Input looks like SVG; trying cairosvg.\n")
                return _convert_svg_with_cairosvg()
            log(f"Image conversion failed: {e}\n")
            return False

    # ffmpeg conversion for audio/video and other supported formats
    if not ffmpeg_path or not os.path.exists(ffmpeg_path):
        log("ffmpeg not found. Check FFMPEG_PATH in config.py\n")
        return False

    try:
        cmd = [ffmpeg_path, "-i", input_file]
        mode, val = _parse_quality(quality)

        if output_format in audio_exts:
            cmd.extend(["-vn"])
            if mode == "vbr" and val is not None:
                cmd.extend(["-q:a", str(val)])
            elif val:
                cmd.extend(["-b:a", val])
            if sample_rate and sample_rate.lower() != "auto":
                cmd.extend(["-ar", sample_rate])
        elif output_format in video_exts:
            if mode == "bitrate" and val:
                cmd.extend(["-b:v", val])

        cmd.extend(["-y", output_file])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode == 0 and os.path.exists(output_file):
            log(f"âœ“ Converted: {os.path.basename(output_file)}\n")
            return True

        if result.stderr:
            log(result.stderr + "\n")
        return False
    except Exception as e:
        log(f"Conversion failed: {e}\n")
        return False

def start_download_thread(task: DownloadTask, manager, settings: dict, on_progress=None, on_log=None):
    """Start download in background thread"""
    thread = threading.Thread(
        target=download_task,
        args=(task, manager, settings, on_progress, on_log),
        daemon=True
    )
    thread.start()
    return thread

