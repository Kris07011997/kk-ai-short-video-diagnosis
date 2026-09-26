#!/usr/bin/env python3
"""Report PDF readiness separately from source-video processing readiness."""
import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path


def check(output: Path) -> dict:
    packages = {name: importlib.util.find_spec(name) is not None for name in ('reportlab', 'PIL', 'pypdf')}
    binaries = {name: shutil.which(name) for name in ('ffmpeg', 'ffprobe')}
    writable = False
    try:
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=output):
            writable = True
    except OSError:
        pass
    font_ready = (Path(__file__).resolve().parents[1] / 'assets/fonts/NotoSansSC-Regular.ttf').is_file()
    ready = sys.version_info >= (3, 10) and all(packages.values()) and writable and font_ready
    return {'python': sys.version.split()[0], 'packages': packages,
            'binaries': binaries, 'output_directory_writable': writable, 'bundled_font_available': font_ready,
            'ready_for_pdf': ready, 'ready_for_video_processing': all(binaries.values()),
            'ready_for_full_workflow': ready and all(binaries.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = check(Path(args.output_dir).expanduser().resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ready_for_pdf'] else 2)
