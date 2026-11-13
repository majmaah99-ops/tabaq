"""The four prior demo images must resolve independently of OCR.

No inference from file names or fuzzy perceptual matches is allowed.
"""
import hashlib
import unittest

from image_route import SAMPLE_SHA256_TO_KEY, identify_synthetic_sample, sample_label_values
from engine import FIELDS, evaluate
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=json.loads((ROOT/"data/scenarios.json").read_text(encoding="utf-8"))
DB=json.loads((ROOT/"database.json").read_text(encoding="utf-8"))

class SyntheticDemoRoutingTests(unittest.TestCase):
    def test_fixtures_come_in_four_distinct_categories(self):
        self.assertEqual(set(SAMPLE_SHA256_TO_KEY.values()),
                         {"match", "discrepancy", "inconclusive", "no_reference"})
    def test_unknown_image_never_gets_synthetic_autofill(self):
        label,fixture=sample_label_values(b"another random image",SCENARIOS,FIELDS)
        self.assertIsNone(fixture)
        self.assertTrue(all(value=="" for value in label.values()))
    def test_known_fixtures_yield_four_expected_statuses(self):
        # Fixture source must match each scenario's expected status, not override it.
        mapped={s["key"]:s for s in SCENARIOS}
        for scenario_key in SAMPLE_SHA256_TO_KEY.values():
            with self.subTest(scenario=scenario_key):
                fixture=mapped[scenario_key]
                r=evaluate(fixture["label"],DB)
                self.assertEqual(r["status"],fixture["expected_status"])
    def test_no_filename_based_recognition(self):
        self.assertIsNone(identify_synthetic_sample(b"01_match.png",SCENARIOS))

if __name__=="__main__":
    unittest.main()
