"""Language compatibility and PDF regression tests."""
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_visual_pdf_report import build, body_fields, extract_body_text
from report_language import language_of, report_filename
from validate_video_report_plan import validate


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.folder/'sample.mp4').write_bytes(b'schema-test-only')
        self.plan = json.loads((ROOT/'references/report-plan.en.example.json').read_text(encoding='utf-8'))
        self.plan['source_video'] = 'sample.mp4'

    def check(self):
        path = self.folder/'plan.json'
        path.write_text(json.dumps(self.plan, ensure_ascii=False), encoding='utf-8')
        with patch('validate_video_report_plan.media_duration', return_value=10.0):
            return validate(path)

    def test_legacy_plan_defaults_to_chinese(self):
        del self.plan['language']
        self.assertEqual(language_of(self.check()), 'zh')
        self.assertEqual(report_filename(self.plan), 'KK-AI短片诊断报告.pdf')

    def test_english_language_and_filename(self):
        self.assertEqual(self.check()['language'], 'en')
        self.assertEqual(report_filename(self.plan), 'KK-AI-Video-Diagnosis-Report.pdf')

    def test_unknown_or_non_string_language_is_rejected(self):
        for value in ('fr', '', None, ['en']):
            with self.subTest(value=value):
                self.plan['language'] = value
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.check()

    def test_legacy_metadata_still_valid_in_english_plan(self):
        self.plan['further_learning'][0].update(source_type='暂未匹配直接案例', reference_level='方法级')
        self.check()

    def test_matched_source_still_requires_attribution(self):
        self.plan['further_learning'][0]['source_type'] = 'daily_shot'
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check()
        self.plan['further_learning'][0].update(source_id='FORMAT-TEST', title='Format-only source')
        self.check()

    def test_shot_group_still_requires_both_timelines(self):
        self.plan['further_learning'][0]['reference_level'] = 'shot_group'
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check()
        self.plan['further_learning'][0].update(user_start=1, user_end=4, source_start=2, source_end=5,
            user_group_label='Current sequence', source_group_label='Reference sequence')
        self.check()

    def test_pdfs_localize_labels_and_preserve_long_prose(self):
        frame = self.folder/'format-only.png'
        Image.new('RGB', (320, 180), '#427AA3').save(frame)
        for language, template, expected, unwanted in (
            ('en', 'report-plan.en.example.json', 'Evidence and viewing impact', '原片证据与观看影响'),
            ('zh', 'report-plan.example.json', '原片证据与观看影响', 'Evidence and viewing impact'),
        ):
            with self.subTest(language=language):
                plan = json.loads((ROOT/'references'/template).read_text(encoding='utf-8'))
                prose = ('A repeated insert adds no new information, so remove it and preserve the action. '
                         if language == 'en' else '重复特写没有提供新信息，可删除并保留动作过程。')
                plan['issues'][0]['evidence'] = prose * 45 + ' END-OF-LONG-PARAGRAPH'
                plan['further_learning'][0].update(source_type='暂未匹配直接案例', reference_level='方法级')
                output = self.folder/report_filename(plan)
                build(plan, output, [(1.0, frame), (4.0, frame)])
                reader = PdfReader(output)
                text = '\n'.join(page.extract_text() or '' for page in reader.pages)
                normalize = lambda s: re.sub(r'\s+', '', str(s))
                body = extract_body_text(reader, plan)
                self.assertIn(expected, text)
                self.assertNotIn(unwanted, text)
                if language == 'en':
                    self.assertNotRegex(text, r'[\u4e00-\u9fff]')
                for field in body_fields(plan):
                    if field:
                        self.assertIn(normalize(field), normalize(body))
                self.assertGreater(len(reader.pages), 4)
                self.assertGreater(sum(len(page.images) for page in reader.pages), 0)


if __name__ == '__main__':
    unittest.main()
