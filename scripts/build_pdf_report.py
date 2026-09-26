#!/usr/bin/env python3
"""Single entrypoint: validate evidence, render and deliver exactly one PDF."""
import argparse
import re
import sys
import tempfile
from pathlib import Path

from check_environment import check
from report_language import report_filename
from validate_video_report_plan import resolve_path, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan')
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    plan_path = Path(args.plan).expanduser().resolve()
    evidence_dir = Path(args.evidence_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not check(output_dir)['ready_for_pdf']:
        raise SystemExit('ERROR: PDF 环境未就绪，请检查 Python 版本、requirements.txt 与输出权限。')
    from pypdf import PdfReader
    from build_visual_pdf_report import body_fields, build, extract_body_text
    from verify_evidence_manifest import prepare
    plan = validate(plan_path)
    plan['source_video'] = str(resolve_path(plan['source_video'], plan_path.parent))
    frames = prepare(plan, evidence_dir)
    output = output_dir / report_filename(plan)
    # Render inside the caller-selected evidence directory, never the system temp.
    with tempfile.TemporaryDirectory(prefix='.pdf-render-', dir=evidence_dir) as staging:
        candidate = Path(staging) / output.name
        build(plan, candidate, frames)
        reader = PdfReader(candidate)
        if not reader.pages:
            raise ValueError('PDF 没有页面。')
        normalize = lambda value: re.sub(r'\s+', '', str(value))
        extracted = normalize(extract_body_text(reader, plan))
        missing = [str(value)[:50] for value in body_fields(plan) if value and normalize(value) not in extracted]
        if missing:
            raise ValueError('PDF 存在未完整输出的正文：' + '；'.join(missing[:5]))
        image_count = sum(len(page.images) for page in reader.pages)
        if not image_count:
            raise ValueError('PDF 缺少原片截图。')
        candidate.replace(output)
    print(f'PDF: {output}')
    print(f'Pages: {len(reader.pages)} | Embedded images: {image_count}')
    print('结构与全文检查通过；请渲染并逐页完成视觉复核。')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(2)
