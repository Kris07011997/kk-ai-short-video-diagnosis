#!/usr/bin/env python3
"""Prepare deterministic video evidence for short-form video review.

Requires ffmpeg and ffprobe on PATH. Produces metadata, evenly sampled frames,
scene-change frames, and an optional mono WAV track. It never modifies the
source video.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def fail(message: str, hint: str | None = None, code: int = 2) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    if hint:
        print(f"HINT: {hint}", file=sys.stderr)
    raise SystemExit(code)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        summary = detail[-1] if detail else "unknown ffmpeg error"
        fail(f"Video processing failed: {summary}")


def format_timestamp(seconds: float) -> str:
    milliseconds = int(round(max(0.0, seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}-{minutes:02d}-{secs:02d}.{millis:03d}"


def probe_video(ffprobe: str, source: Path) -> dict:
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(source),
        ]
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        fail("ffprobe returned invalid JSON.")


def extract_interval_frames(
    ffmpeg: str, source: Path, output: Path, duration: float, max_frames: int, frame_interval: float = 0.1
) -> list[dict]:
    output.mkdir(parents=True, exist_ok=True)
    if duration <= 0:
        timestamps = [0.0]
    else:
        count = min(max_frames, max(2, math.ceil(duration / 3.0) + 1))
        timestamps = [duration * index / (count - 1) for index in range(count)]

    frames: list[dict] = []
    for index, timestamp in enumerate(timestamps, start=1):
        safe_timestamp = min(timestamp, max(0.0, duration - frame_interval - 0.001)) if duration else 0.0
        filename = f"{index:03d}_{format_timestamp(safe_timestamp)}.jpg"
        destination = output / filename
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{safe_timestamp:.3f}",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                "-y",
                str(destination),
            ]
        )
        frames.append({"time_seconds": round(safe_timestamp, 3), "file": str(destination)})
    return frames


def extract_scene_frames(
    ffmpeg: str, source: Path, output: Path, threshold: float
) -> list[dict]:
    output.mkdir(parents=True, exist_ok=True)
    pattern = output / "scene-%03d.jpg"
    command = [
        ffmpeg,
        "-hide_banner",
        "-i",
        str(source),
        "-vf",
        f"select='eq(n,0)+gt(scene,{threshold})',showinfo",
        "-fps_mode",
        "vfr",
        "-q:v",
        "2",
        "-y",
        str(pattern),
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()
        summary = detail[-1] if detail else "unknown scene detection error"
        fail(f"Scene detection failed: {summary}")

    timestamps = [float(value) for value in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    files = sorted(output.glob("scene-*.jpg"))
    frames: list[dict] = []
    for index, file_path in enumerate(files):
        timestamp = timestamps[index] if index < len(timestamps) else 0.0
        renamed = output / f"{index + 1:03d}_{format_timestamp(timestamp)}.jpg"
        file_path.replace(renamed)
        frames.append({"time_seconds": round(timestamp, 3), "file": str(renamed)})
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare frames and metadata for short-video diagnosis."
    )
    parser.add_argument("video", help="Path to the source video")
    parser.add_argument("--output", help="Output directory; defaults to <video>_review")
    parser.add_argument(
        "--max-frames", type=int, default=24, help="Maximum interval frames (default: 24)"
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=0.32,
        help="FFmpeg scene threshold (default: 0.32)",
    )
    parser.add_argument(
        "--extract-audio", action="store_true", help="Also extract a 16 kHz mono WAV file"
    )
    args = parser.parse_args()

    source = Path(args.video).expanduser().resolve()
    if not source.is_file():
        fail(f"Video not found: {source}", "Check the path and quote paths that contain spaces.")
    if args.max_frames < 2 or args.max_frames > 100:
        fail("--max-frames must be between 2 and 100.")
    if not 0.0 < args.scene_threshold < 1.0:
        fail("--scene-threshold must be between 0 and 1.")

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else source.with_name(f"{source.stem}_review")
    )

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        swift = shutil.which("swift")
        macos_fallback = Path(__file__).with_name("prepare_video_review_macos.swift")
        if sys.platform == "darwin" and swift and macos_fallback.is_file():
            if args.extract_audio:
                print(
                    "WARNING: macOS fallback extracts frames but does not extract audio.",
                    file=sys.stderr,
                )
            command = [
                swift,
                str(macos_fallback),
                str(source),
                str(output),
                str(args.max_frames),
            ]
            try:
                completed = subprocess.run(command, check=True, text=True)
            except subprocess.CalledProcessError:
                fail(
                    "The macOS native video fallback failed.",
                    "Open the original video directly or install FFmpeg and retry.",
                )
            raise SystemExit(completed.returncode)
        fail(
            "ffmpeg and ffprobe are required but were not found on PATH.",
            "Install FFmpeg, or use the bundled macOS fallback on a Mac.",
        )

    output.mkdir(parents=True, exist_ok=True)

    metadata = probe_video(ffprobe, source)
    video_stream = next((item for item in metadata.get("streams", []) if item.get("codec_type") == "video"), {})
    try:
        duration = float(video_stream.get("duration", metadata.get("format", {}).get("duration", 0.0)))
    except (TypeError, ValueError):
        duration = 0.0
    try:
        frame_interval = 1.0 / float(Fraction(video_stream.get("avg_frame_rate", "0/1")))
    except (ValueError, ZeroDivisionError):
        frame_interval = 0.1

    interval_frames = extract_interval_frames(
        ffmpeg, source, output / "interval", duration, args.max_frames, frame_interval
    )
    scene_frames = extract_scene_frames(
        ffmpeg, source, output / "scenes", args.scene_threshold
    )

    audio_file = None
    has_audio = any(item.get("codec_type") == "audio" for item in metadata.get("streams", []))
    if args.extract_audio and not has_audio:
        print("WARNING: Source video has no audio track; no audio evidence was extracted.", file=sys.stderr)
    if args.extract_audio and has_audio:
        audio_path = output / "audio.wav"
        run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-y",
                str(audio_path),
            ]
        )
        audio_file = str(audio_path)

    manifest = {
        "source": str(source),
        "source_signature": {"size": source.stat().st_size, "mtime_ns": source.stat().st_mtime_ns},
        "duration_seconds": round(duration, 3),
        "interval_frames": interval_frames,
        "scene_frames": scene_frames,
        "audio_file": audio_file,
        "limitations": [
            "Interval frames summarize the timeline but do not prove motion continuity.",
            "Scene detection can miss subtle cuts or treat flashes as cuts.",
            "Use the original video and audio whenever the platform can read them.",
        ],
    }

    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("PREPARE VIDEO REVIEW: SUCCESS")
    print(f"Source: {source}")
    print(f"Duration: {duration:.3f}s")
    print(f"Interval frames: {len(interval_frames)}")
    print(f"Scene frames: {len(scene_frames)}")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
