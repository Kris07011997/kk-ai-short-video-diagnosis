#!/usr/bin/env python3
"""Validate source identity and prepare precise, source-derived screenshots."""
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def signature(path: Path) -> dict:
    stat = path.stat()
    return {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def targets(plan: dict) -> list[float]:
    values = [float(item['start']) for item in plan.get('strengths', [])]
    values.extend(float(moment['time']) for issue in plan['issues'] for moment in issue['evidence_moments'])
    return sorted(set(values))


def prepare(plan: dict, evidence_dir: Path) -> list[tuple[float, Path]]:
    manifest_path = evidence_dir / 'manifest.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError('缺少有效 manifest.json，请先运行 prepare_video_review.py。') from exc
    source = Path(plan['source_video']).resolve()
    duration = float(manifest.get('duration_seconds', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('证据清单缺少有效原片时长，请重新准备证据。')
    if any(time < 0 or time >= duration for time in targets(plan)):
        raise ValueError('截图时间必须位于原片有效时长内，不可使用片尾之后的时间点。')
    if any(float(issue['end']) > duration + 0.05 for issue in plan['issues']):
        raise ValueError('问题结束时间超出原片时长。')
    stored = Path(str(manifest.get('source', ''))).expanduser()
    if not stored.is_absolute():
        stored = evidence_dir / stored
    if source != stored.resolve():
        raise ValueError('截图与当前原片来源不一致，请重新准备证据。')
    # v1 manifests did not record source signatures. Re-extract all selected
    # screenshots for those manifests instead of trusting potentially stale images.
    current = signature(source)
    trusted = manifest.get('source_signature') == current
    if manifest.get('source_signature') and not trusted:
        raise ValueError('原片在抽帧后发生变化，请重新准备证据。')
    entries = manifest.get('precise_frames', []) if trusted else []
    ffmpeg = shutil.which('ffmpeg')
    precise_dir = evidence_dir / 'precise'
    precise_dir.mkdir(parents=True, exist_ok=True)
    selected = []
    updated = []
    for time in targets(plan):
        frame = None
        for item in entries:
            try:
                same_time = math.isclose(float(item['time_seconds']), time, abs_tol=0.0005)
                candidate = (evidence_dir / item['file']).resolve()
            except (TypeError, ValueError, KeyError):
                continue
            if same_time and candidate.is_relative_to(evidence_dir) and candidate.is_file():
                if hashlib.sha256(candidate.read_bytes()).hexdigest() == item.get('sha256'):
                    frame = candidate
                    break
        if frame is None:
            if not ffmpeg:
                raise ValueError(f'缺少 {time:.3f}s 的原片截图，需要 FFmpeg 补取指定时间点。')
            frame = precise_dir / f'{time:.3f}.jpg'
            frame.unlink(missing_ok=True)
            result = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                                     '-i', str(source), '-ss', f'{time:.6f}', '-frames:v', '1',
                                     '-q:v', '2', '-update', '1', str(frame)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode or not frame.is_file() or not frame.stat().st_size:
                raise ValueError(f'无法提取 {time:.3f}s 截图；请核对时间点是否位于原片有效画面内。')
        try:
            with Image.open(frame) as image:
                image.verify()
        except OSError as exc:
            raise ValueError(f'截图无法读取：{frame.name}') from exc
        selected.append((time, frame))
        updated.append({'time_seconds': time, 'file': frame.relative_to(evidence_dir).as_posix(),
                        'sha256': hashlib.sha256(frame.read_bytes()).hexdigest()})
    manifest['source_signature'] = current
    manifest['precise_frames'] = updated
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return selected
