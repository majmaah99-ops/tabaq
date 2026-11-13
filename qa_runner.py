"""Reproducible tests on synthetic structured labels; no image OCR assessed."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from engine import evaluate
ROOT = Path(__file__).resolve().parent

def run_cases(path: Path | None = None, db_override: dict | None = None) -> dict:
    path = path or ROOT / "data" / "cases_60.json"
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for item in cases:
        refs = db_override if db_override is not None else item["references"]
        actual = evaluate(item["label"], refs)
        passed = actual["status"] == item["expected_status"] and actual["reason_code"] == item["expected_reason"]
        rows.append({"id": item["id"],"category":item["category"],"expected":item["expected_status"],
                     "actual":actual["status"],"reason_expected":item["expected_reason"],
                     "reason_actual":actual["reason_code"],"passed":passed})
    return {"total":len(rows),"passed":sum(x["passed"] for x in rows),
            "failed":sum(not x["passed"] for x in rows),"cases":rows,
            "scope":"Synthetic structured-field rule tests only; no OCR accuracy assessed"}

if __name__ == "__main__":
    result = run_cases()
    print(json.dumps({k:v for k,v in result.items() if k != "cases"}, indent=2))
    if result["failed"]:
        for item in result["cases"]:
            if not item["passed"]:
                print(f"FAILED {item['id']}: expected {item['expected']}/{item['reason_expected']} got {item['actual']}/{item['reason_actual']}")
        sys.exit(1)
