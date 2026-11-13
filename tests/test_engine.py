import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import evaluate, normalize, positive_decimal
from qa_runner import run_cases

ROOT = Path(__file__).resolve().parents[1]
DB = json.loads((ROOT / "database.json").read_text(encoding="utf-8"))
LABEL = {k:v for k,v in DB["AC-18000-X"].items() if k in
         ("brand","model","device_type","product_type","annual_consumption","energy_efficiency","efficiency_level")}

class RuleEngineTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertEqual(evaluate(LABEL, DB)["status"],"MATCH")
    def test_discrepancy_annual_consumption(self):
        r=evaluate(dict(LABEL,annual_consumption=3100),DB)
        self.assertEqual(r["status"],"DISCREPANCY")
        self.assertEqual([x["field"] for x in r["comparisons"] if x["outcome"]=="DIFF"],["annual_consumption"])
    def test_unreadable_grade_abstains(self):
        self.assertEqual(evaluate(dict(LABEL,efficiency_level=""),DB)["status"],"INCONCLUSIVE")
    def test_missing_model_abstains(self):
        self.assertEqual(evaluate(dict(LABEL,model="غير مقروء"),DB)["reason_code"],"MODEL_UNREADABLE")
    def test_unknown_model_no_reference(self):
        self.assertEqual(evaluate(dict(LABEL,model="AC-99999-Z"),DB)["status"],"NO_REFERENCE")
    def test_arabic_digits_consistent(self):
        self.assertEqual(positive_decimal("٢٬٤٠٠"),positive_decimal(2400))
    def test_bad_number_abstains(self):
        self.assertEqual(evaluate(dict(LABEL,annual_consumption="−1"),DB)["status"],"INCONCLUSIVE")
    def test_missing_field_not_mismatch(self):
        self.assertEqual(evaluate(dict(LABEL,brand="",annual_consumption=3100),DB)["status"],"INCONCLUSIVE")
    def test_no_fuzzy_model_identity(self):
        self.assertNotEqual(normalize("AC-18000-X",model=True),normalize("AC18000X",model=True))
        self.assertEqual(evaluate(dict(LABEL,model="AC18000X"),DB)["status"],"NO_REFERENCE")
    def test_non_synthetic_ref_cannot_be_trusted(self):
        records={"AC-18000-X":dict(DB["AC-18000-X"],origin="official")}
        self.assertEqual(evaluate(LABEL,records)["reason_code"],"REFERENCE_UNVERIFIED")
    def test_four_image_scenarios(self):
        scenarios=json.loads((ROOT/"data"/"scenarios.json").read_text(encoding="utf-8"))
        for item in scenarios:
            with self.subTest(key=item["key"]):
                self.assertEqual(evaluate(item["label"],DB)["status"],item["expected_status"])
    def test_60_cases(self):
        result=run_cases()
        self.assertEqual(result["total"],60)
        self.assertEqual(result["failed"],0)

if __name__=="__main__":
    unittest.main()
