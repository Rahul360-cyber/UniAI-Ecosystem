import json
import tempfile
import unittest
from pathlib import Path

from portfolio import (
    add_event, create_profile, delete_profile, get_events, init_portfolio,
    make_report, profile_exists, report_html, report_json, restore_profile,
)


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'test.db'
        init_portfolio(self.db)
        self.token, self.digest = create_profile(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_restore_and_delete(self):
        self.assertTrue(profile_exists(self.db, self.digest))
        self.assertEqual(restore_profile(self.db, self.token), self.digest)
        self.assertIsNone(restore_profile(self.db, 'bad-token'))
        delete_profile(self.db, self.digest)
        self.assertFalse(profile_exists(self.db, self.digest))
        self.assertIsNone(restore_profile(self.db, self.token))

    def test_assessment_and_research_portfolio(self):
        add_event(self.db, self.digest, class_code='ML101', kind='question_topic', topic='Backpropagation')
        add_event(self.db, self.digest, class_code='ML101', kind='assessment',
                  topic='Backpropagation', score=50, stage='Initial assessment', detail='Chain rule')
        add_event(self.db, self.digest, class_code='ML101', kind='assessment',
                  topic='Backpropagation', score=100, stage='Reassessment')
        add_event(self.db, self.digest, class_code='ML101', kind='evidence',
                  topic='Tested a new hypothesis', stage='Experiment',
                  detail='Reproduced a baseline and compared results',
                  evidence_url='https://example.org/project')
        add_event(self.db, self.digest, class_code='MATH1', kind='evidence',
                  topic='Project', stage='Project', detail='Built a proof of concept')
        items = get_events(self.db, self.digest)
        self.assertEqual(len(items), 5)
        report = make_report(items)
        self.assertEqual(report['classes'], ['MATH1', 'ML101'])
        self.assertEqual(report['recorded_question_topics'], {'Backpropagation': 1})
        self.assertEqual(report['per_concept_practice_progress'][0]['change_points'], 50)
        self.assertEqual(report['research_and_learning_evidence_counts']['Experiment'], 1)
        self.assertIn('For human review only', report['decision_notice'])
        self.assertIn('example.org', report_html(report))
        self.assertEqual(json.loads(report_json(report))['total_recorded_assessments'], 2)
        delete_profile(self.db, self.digest)
        self.assertEqual(get_events(self.db, self.digest), [])

    def test_reject_unsafe_urls_and_escape_html(self):
        with self.assertRaises(ValueError):
            add_event(self.db, self.digest, class_code='ML101', kind='evidence',
                      topic='Test', evidence_url='javascript:alert(1)')
        add_event(self.db, self.digest, class_code='ML101', kind='evidence',
                  topic='<script>alert(1)</script>', stage='Project', detail='<img src=x onerror=alert(1)>')
        html = report_html(make_report(get_events(self.db, self.digest)))
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;script&gt;', html)


if __name__ == '__main__':
    unittest.main()
