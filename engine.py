"""TABAQ v1.2 — deterministic, synthetic-only comparison engine.

This does NOT authenticate products, query SASO, or make regulatory determinations.
Input is structured text, whether entered manually or reviewed after OCR.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
import unicodedata
from typing import Any, Mapping

FIELDS = (
    "brand", "model", "device_type", "product_type",
    "annual_consumption", "energy_efficiency", "efficiency_level",
)
NUMERIC = {"annual_consumption", "energy_efficiency"}
FIELD_AR = {
    "brand": "العلامة التجارية",
    "model": "رقم الموديل",
    "device_type": "نوع الجهاز",
    "product_type": "نوع المنتج",
    "annual_consumption": "الاستهلاك السنوي (ك.و.س)",
    "energy_efficiency": "معدل كفاءة الطاقة",
    "efficiency_level": "مستوى كفاءة الطاقة",
}
STATUS_AR = {
    "MATCH": "متطابق ضمن الحقول المفحوصة",
    "DISCREPANCY": "اختلاف يستدعي المراجعة",
    "INCONCLUSIVE": "غير محسوم",
    "NO_REFERENCE": "مرجع غير متاح",
}
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
DIACRITICS = re.compile(r"[\u064b-\u065f\u0670]")
MISSING_TOKENS = {"", "غير مقروء", "غير واضح", "غير متاح", "unknown", "n/a", "none", "null", "؟", "?", "-"}


def normalize(value: Any, *, model: bool = False) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).translate(DIGITS)
    text = DIACRITICS.sub("", text).replace("ـ", "")
    text = " ".join(text.strip().casefold().split())
    # Model IDs: no fuzzy substitution, no dropping hyphens or similar characters.
    return text.upper() if model else text


def is_missing(value: Any) -> bool:
    return value is None or normalize(value) in MISSING_TOKENS


def positive_decimal(value: Any) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError("قيمة عددية غير صالحة")
    raw = unicodedata.normalize("NFKC", str(value)).translate(DIGITS)
    raw = raw.replace("٬", ",").replace("٫", ".").strip()
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", raw):
        raw = raw.replace(",", "")
    if not re.fullmatch(r"\d+(\.\d+)?", raw):
        raise ValueError("تنسيق العدد غير صالح")
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("عدد غير صالح") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("يجب أن تكون القيمة موجبة")
    return number


def _result(status: str, reason: str, explanation: str, rows: list[dict] | None = None,
            missing: list[str] | None = None, reference: Mapping[str, Any] | None = None) -> dict:
    return {
        "status": status,
        "status_ar": STATUS_AR[status],
        "reason_code": reason,
        "explanation_ar": explanation,
        "comparisons": rows or [],
        "missing_fields": missing or [],
        "reference_id": reference.get("reference_id") if reference else None,
        "reference_date": reference.get("last_updated") if reference else None,
        "reference_source": "بيانات اختبار اصطناعية — لا تمثل سجلات الهيئة",
        "official_verification": False,
        "scope_note_ar": "مطابقة بيانات تجريبية وليست إثباتًا لأصالة المنتج أو سلامته أو وجود مخالفة نظامية.",
    }


def evaluate(label: Mapping[str, Any] | None, references: Mapping[str, dict]) -> dict:
    """Four-way decision, fail-closed on incomplete/malformed data."""
    if not isinstance(label, Mapping):
        return _result("INCONCLUSIVE", "LABEL_MISSING", "لم تُدخل بيانات الملصق.")
    model = label.get("model")
    if is_missing(model):
        return _result("INCONCLUSIVE", "MODEL_UNREADABLE", "تعذر قراءة رقم الموديل؛ أعد التصوير أو أدخله يدويًا.", missing=["model"])
    normalized_model = normalize(model, model=True)
    # Strict model lookup: do not guess or use approximate string matching.
    reference = None
    for key, val in references.items():
        if normalize(key, model=True) == normalized_model:
            reference = val
            break
    if reference is None:
        return _result("NO_REFERENCE", "MODEL_NOT_FOUND", f"لا يوجد سجل تجريبي للطراز {str(model)}. لا يمكن إصدار حكم على بيانات المنتج.")
    if reference.get("origin") != "synthetic":
        return _result("INCONCLUSIVE", "REFERENCE_UNVERIFIED", "مصدر السجل المرجعي غير موثق لهذا النموذج التجريبي.", reference=reference)

    missing: list[str] = []
    invalid: list[str] = []
    rows: list[dict] = []
    for field in FIELDS:
        left, right = label.get(field), reference.get(field)
        if is_missing(left) or is_missing(right):
            missing.append(field)
            rows.append({"field": field, "field_ar": FIELD_AR[field], "label": left, "reference": right, "outcome": "MISSING"})
            continue
        if field in NUMERIC:
            try:
                same = positive_decimal(left) == positive_decimal(right)
            except ValueError:
                invalid.append(field)
                rows.append({"field": field, "field_ar": FIELD_AR[field], "label": left, "reference": right, "outcome": "INVALID"})
                continue
        else:
            same = normalize(left, model=field == "model") == normalize(right, model=field == "model")
        rows.append({"field": field, "field_ar": FIELD_AR[field], "label": left, "reference": right,
                     "outcome": "MATCH" if same else "DIFF"})

    # Conservatively abstain if any mandatory field cannot be checked. Differences
    # in other fields remain visible in rows, but no overall mismatch judgement.
    if missing or invalid:
        names = [FIELD_AR[x] for x in missing + invalid]
        return _result("INCONCLUSIVE", "FIELDS_INCOMPLETE", "لا يمكن إصدار نتيجة نهائية؛ الحقول التالية ناقصة أو غير صالحة: " + "، ".join(names) + ".", rows, missing + invalid, reference)
    different = [r for r in rows if r["outcome"] == "DIFF"]
    if different:
        names = "، ".join(row["field_ar"] for row in different)
        return _result("DISCREPANCY", "FIELD_MISMATCH", "اختلاف في " + names + ". يجب مراجعة الملصق والسجل قبل اتخاذ أي إجراء.", rows, reference=reference)
    return _result("MATCH", "ALL_FIELDS_MATCH", "تطابقت الحقول السبعة في نطاق المقارنة التجريبية.", rows, reference=reference)