#!/usr/bin/env python3
"""Verify every distributed file, or refresh the manifest after an intentional edit."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST = 'PACKAGE-MANIFEST.json'
EXCLUDED_PARTS = {'.git', '__pycache__', '.pytest_cache', '.venv', 'work', 'outputs'}
EXCLUDED_NAMES = {MANIFEST, '.DS_Store', 'Thumbs.db'}


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in ('.pyc', '.pyo', '.pyd'):
            continue
        data = path.read_bytes()
        result[relative.as_posix()] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--write', action='store_true', help='Refresh the manifest after intentional changes.')
    args = parser.parse_args()
    root = args.root.resolve()
    actual = inventory(root)
    target = root/MANIFEST
    if args.write:
        target.write_text(json.dumps({'algorithm': 'sha256', 'files': actual}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'MANIFEST WRITTEN: {len(actual)} files (manifest excluded).')
        return
    expected = json.loads(target.read_text(encoding='utf-8'))['files']
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name])
    if missing or extra or changed:
        print(json.dumps({'missing': missing, 'extra': extra, 'changed': changed}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(f'PACKAGE VERIFIED: {len(actual)} files match SHA-256 and size; no missing or extra files.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(2)
