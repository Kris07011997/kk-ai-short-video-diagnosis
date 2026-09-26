"""Portable behavior checks; run with python -m unittest discover -s tests -v."""
import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from search_embedded_knowledge import fingerprint, search
from validate_video_report_plan import validate


class RetrievalTests(unittest.TestCase):
    def test_no_unrelated_fillers_for_unmatched_query(self):
        self.assertEqual(search('zzzxxyy-nonexistent-phrase', ROOT/'knowledge', 'vlog', 'all'), [])

    def test_blank_query_is_rejected(self):
        with self.assertRaises(ValueError):
            search('   ', ROOT/'knowledge')

    def test_card_identifier_lookup_ignores_wrong_genre(self):
        hits = search('JC-01', ROOT/'knowledge', 'sound', 'cards')
        self.assertEqual([hit['record']['card_id'] for hit in hits], ['JC-01'])

    def test_duplicate_rows_across_indexes_are_merged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'case-maps').mkdir()
            (root/'case-maps/index.json').write_text('{}')
            for path in (root/'evidence', root/'kk-full-library'):
                path.mkdir()
            row = {'case_id': 'KK-001', 'source_file': 'example.xlsx', 'sheet': 'A', 'row': 2, 'text': '镜头提供新信息'}
            text = json.dumps(row, ensure_ascii=False) + '\n'
            (root/'evidence/method-card-evidence.jsonl').write_text(text, encoding='utf-8')
            (root/'kk-full-library/kk-case-evidence-deduped.jsonl').write_text(text, encoding='utf-8')
            hits = search('新信息', root, kind='cases')
            self.assertEqual(len(hits), 1)

    def test_symptom_does_not_force_vlog_genre(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/resolve_case_maps.py'), '开头平，像流水账'], capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [])


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        (self.folder/'sample.mp4').write_bytes(b'schema-test-only')
        self.plan = json.loads((ROOT/'references/report-plan.example.json').read_text(encoding='utf-8'))
        self.plan['source_video'] = 'sample.mp4'
        self.plan['issues'][0]['kk_method']['case_ids'] = ['JC-01']
        self.plan['strengths'] = [{'start': 0.4, 'headline': '事件完整', 'evidence': '动作及结果能够对应。'}]
        self.path = self.folder/'plan.json'

    def tearDown(self):
        self.temp.cleanup()

    def check(self, plan):
        self.path.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
        with patch('validate_video_report_plan.media_duration', return_value=10.0):
            return validate(self.path)

    def test_no_clear_issue_can_be_reported_without_inventing_one(self):
        self.plan.update(issues=[], quick_actions=[], further_learning=[])
        self.assertEqual(self.check(self.plan)['issues'], [])

    def test_limitations_are_not_mistaken_for_performance_promises(self):
        self.plan['issues'][0]['action'] = '先让表达清楚，不保证涨粉，也不承诺做出爆款。'
        self.check(self.plan)

    def test_no_matched_source_requires_an_honest_note(self):
        method = self.plan['issues'][0]['kk_method']
        method['case_ids'] = []
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check(self.plan)
        method['reference_note'] = '依据本片观察，暂未匹配直接教学案例。'
        self.check(self.plan)

    def test_out_of_range_evidence_is_rejected(self):
        self.plan['issues'][0]['evidence_moments'][0]['time'] = 100
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check(self.plan)

    def test_empty_report_without_any_evidence_is_rejected(self):
        self.plan.update(issues=[], strengths=[], quick_actions=[], further_learning=[])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check(self.plan)


if __name__ == '__main__':
    unittest.main()
