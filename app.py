"""TABAQ — interactive Streamlit MVP with synthetic demo data and four honest outcomes.

Run: streamlit run app.py
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from html import escape
import json
from pathlib import Path
import re

import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError

from engine import FIELDS, FIELD_AR, evaluate
from qa_runner import run_cases

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="طابِق | TABAQ — نموذج أولي", page_icon="🔎", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
  font-family:'Tajawal',Tahoma,Arial,sans-serif !important;
}
[data-testid="stAppViewContainer"] {direction:rtl; background:#f5f8f8;}
[data-testid="stMainBlockContainer"] {max-width:1240px; padding-top:1.6rem;}
[data-testid="stMain"] {direction:rtl;}
[data-testid="stVerticalBlock"] {direction:rtl;}
h1,h2,h3,h4,p,label {text-align:right;}
.hero {background:linear-gradient(110deg,#073f43,#096e63);color:white;
  padding:30px 32px;border-radius:20px;margin-bottom:18px;
  box-shadow:0 14px 28px rgba(13,87,81,.12)}
.hero h1{color:white;font-size:2.65rem;font-weight:800;margin:0 0 4px}
.hero p{color:#d8f5ed;font-size:1.13rem;margin:4px 0}
.hero small{color:#d6e7e4;font-size:.9rem}
.eyebrow {display:inline-block;padding:5px 12px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.2);border-radius:20px;font-size:.84rem;margin-bottom:9px}
.kicker{font-size:.85rem;color:#2c6961;font-weight:800;letter-spacing:.03em}
.notice{border:1px solid #ebd5a4;background:#fff8e8;color:#745215;border-radius:11px;padding:11px 15px;margin:10px 0;font-size:.95rem}
.result {border-radius:15px;padding:17px 20px;margin:12px 0;border:1px solid #b1d7ce;background:#ecf8f3}
.result h3{color:#116b48;margin:0 0 8px}
.result p{margin:0;color:#214a41}
.result.bad{background:#fff0f0;border-color:#f3b1b1}.result.bad h3{color:#a01d24}
.result.warn{background:#fff8e8;border-color:#ecd597}.result.warn h3{color:#8d5f16}
.result.info{background:#edf4ff;border-color:#b1cbe9}.result.info h3{color:#264f87}
.fieldtitle{font-size:1rem;font-weight:800;color:#144b48;margin:7px 0 3px}
[data-testid="stMetric"] {background:white;border-radius:14px;border:1px solid #d9e7e5;padding:16px}
[data-testid="stAlert"] {direction:rtl}
div[data-testid="stTextInput"] input {direction:auto;text-align:right}
[data-testid="stFileUploader"] {direction:rtl}
.stButton>button[kind="primary"]{background:#086f61;border-color:#086f61;border-radius:10px;font-weight:800}
</style>
""", unsafe_allow_html=True)

@st.cache_data

def load_data():
    db = json.loads((ROOT / "database.json").read_text(encoding="utf-8"))
    scenarios = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))
    return db, scenarios


def as_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


def show_ocr(uploaded_bytes: bytes):
    """Experimental OCR preview only; never auto-certifies or silently sets labels."""
    try:
        import pytesseract
        image = Image.open(BytesIO(uploaded_bytes)).convert("RGB")
        raw = pytesseract.image_to_string(image, lang="ara+eng", config="--psm 6")
        raw_en = pytesseract.image_to_string(image, lang="eng", config="--psm 6")
    except ImportError:
        st.warning("هذه الميزة الاختيارية تتطلب تثبيت pytesseract وبرنامج Tesseract وحزمتي اللغة العربية والإنجليزية.")
        return
    except Exception as exc:
        st.warning(f"تعذرت تجربة OCR على هذه الصورة: {exc}")
        return
    st.caption("نص OCR خام تجريبي؛ قد تتغير الأرقام والحروف. لا تُعتمد النتيجة قبل المراجعة اليدوية.")
    st.code(raw or "لم يُستخرج نص", language="text")
    model_match = re.search(r"AC-[A-Za-z0-9-]+", raw + "\n" + raw_en, flags=re.I)
    if model_match:
        st.info(f"رقم طراز محتمل: {model_match.group(0)} — تحقق من الصورة وأدخله يدويًا.")


db, scenarios = load_data()
scenario_by_title = {sc["title"]: sc for sc in scenarios}

st.markdown("""
<div class="hero">
 <span class="eyebrow">TABAQ · MVP v1.2 · نسخة تحكيم تجريبية</span>
 <h1>طابِق <span style="opacity:.75;font-size:1.4rem">| TABAQ</span></h1>
 <p>محرك المطابقة الذكية لبيانات المنتجات</p>
 <small>من التحقق إلى الدليل — مطابقة مفسَّرة · أدلة قابلة للمراجعة · امتناع عند نقص البيانات</small>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="notice">⚠️ جميع السجلات والملصقات المعروضة اصطناعية للتجربة، ولا تمثل بيانات فعلية أو تحققًا رسميًا من الهيئة السعودية للمواصفات والمقاييس والجودة.</div>', unsafe_allow_html=True)

tab_demo, tab_qa, tab_about = st.tabs(["🔎 تجربة المطابقة", "📊 اختبارات الجودة", "ℹ️ حول النموذج"])
with tab_demo:
    st.subheader("اختبر الحالات الأربع")
    selected_title = st.selectbox("اختر السيناريو", list(scenario_by_title), index=0)
    scenario = scenario_by_title[selected_title]
    st.caption("القيم في النموذج تُملأ من ملف السيناريو التجريبي المصاحب للصورة، وليست ناتجة عن OCR. يمكن تعديلها يدويًا.")
    image_col, form_col = st.columns([0.9, 1.25], gap="large")
    with image_col:
        st.markdown('<div class="fieldtitle">صورة الملصق التجريبي</div>', unsafe_allow_html=True)
        upload = st.file_uploader("ارفع صورة أخرى لمعاينتها", type=["png", "jpg", "jpeg"], key="custom_upload")
        original_image_path = ROOT / scenario["image"]
        image_bytes = None
        if upload is not None:
            image_bytes = upload.getvalue()
            if len(image_bytes) > 8 * 1024 * 1024:
                st.error("حجم الصورة كبير؛ الحد التجريبي 8 ميجابايت.")
                image_bytes = None
            else:
                try:
                    st.image(Image.open(BytesIO(image_bytes)), caption="صورة مرفوعة — تُعرض فقط ولا تُحلَّل تلقائيًا", use_column_width=True)
                except (UnidentifiedImageError, OSError):
                    st.error("تعذر قراءة ملف الصورة.")
                    image_bytes = None
        else:
            st.image(str(original_image_path), caption="ملصق اصطناعي مصاحب للسيناريو", use_column_width=True)
        if image_bytes is not None:
            with st.expander("🧪 تجربة قراءة OCR الحقيقية — اختيارية وغير معتمدة"):
                st.caption("تجربة استخراج نص خام إذا كان Tesseract متاحًا على جهاز التشغيل. يلزم مراجعة القيم وتصحيحها قبل استخدامها.")
                if st.button("قراءة النص OCR", key="ocr_button"):
                    show_ocr(image_bytes)
        st.info("رفع صورة مختلفة لا يغير الحقول تلقائيًا. راجع القيم أدناه لتتوافق مع الصورة التي اخترتها.")

    with form_col:
        st.markdown('<div class="fieldtitle">البيانات المراد فحصها</div>', unsafe_allow_html=True)
        with st.form(key=f"match_form_{scenario['key']}", clear_on_submit=False):
            label = {}
            field_col1, field_col2 = st.columns(2, gap="small")
            for i, field in enumerate(FIELDS):
                with (field_col1 if i % 2 == 0 else field_col2):
                    label[field] = st.text_input(FIELD_AR[field], value=str(scenario["label"].get(field, "")),
                                                 key=f"input_{scenario['key']}_{field}")
            submitted = st.form_submit_button("🔍 إجراء المطابقة", type="primary", use_container_width=True)
    if submitted:
        result = evaluate(label, db)
        st.session_state["last_result"] = {"scenario": scenario["key"], "label": label, "result": result,
                                          "image_uploaded": upload.name if upload is not None else None}

    saved = st.session_state.get("last_result")
    if saved and saved["scenario"] == scenario["key"]:
        result = saved["result"]
        presentation = {
            "MATCH": ("", "✅"),
            "DISCREPANCY": ("bad", "⚠️"),
            "INCONCLUSIVE": ("warn", "❓"),
            "NO_REFERENCE": ("info", "ℹ️"),
        }
        css_class, emoji = presentation[result["status"]]
        st.markdown(f'<div class="result {css_class}"><h3>{emoji} {escape(result["status_ar"])}</h3><p>{escape(result["explanation_ar"])}</p></div>', unsafe_allow_html=True)
        st.caption("النتيجة تخص الحقول اليدوية أو بيانات السيناريو فقط؛ لم يثبت النظام تطابق محتوى الصورة المرفوعة مع هذه الحقول.")
        st.subheader("جدول أدلة المقارنة")
        if result["comparisons"]:
            display = []
            for r in result["comparisons"]:
                display.append({"الحقل": r["field_ar"], "بيانات الملصق": "—" if r["label"] is None else str(r["label"]),
                                "السجل التجريبي": "—" if r["reference"] is None else str(r["reference"]),
                                "المراجعة": {"MATCH":"✅ متطابق", "DIFF":"⚠️ مختلف", "MISSING":"❓ ناقص", "INVALID":"❓ غير صالح"}[r["outcome"]]})
            st.dataframe(pd.DataFrame(display), hide_index=True, use_container_width=True)
        report = {
            "project": "طابِق | TABAQ", "version": "1.2.0",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_policy": "Synthetic demo data only; no governmental reference or live verification",
            "scenario": scenario["key"], "uploaded_file_name": saved["image_uploaded"],
            "entered_label_fields": saved["label"], "evaluation": result,
        }
        st.download_button("⬇️ تحميل مسودة تقرير الأدلة JSON", as_json(report),
                           file_name=f"TABAQ_{scenario['key']}_report.json", mime="application/json", type="primary")
        st.caption(result["scope_note_ar"] + " لا يُرسل هذا النموذج أي بلاغ رسميًا.")
    else:
        st.caption("اضغط «إجراء المطابقة» لعرض حالة النتيجة وتقرير الأدلة.")

with tab_qa:
    st.subheader("نتائج اختبار محرك القواعد")
    summary = run_cases(ROOT / "data" / "cases_60.json", db_override=None)
    total, passed = summary["total"], summary["passed"]
    metrics = st.columns(3)
    metrics[0].metric("الحالات المنفذة", str(total))
    metrics[1].metric("حالات ناجحة", str(passed))
    metrics[2].metric("مطابقة النتائج المتوقعة", f"{100 * passed / total:.0f}%" if total else "—")
    st.progress(passed / total if total else 0)
    rows = [
        {"الحالة": item["id"], "النوع": item["category"], "المتوقع": item["expected"],
         "الناتج": item["actual"], "النتيجة": "✅ ناجح" if item["passed"] else "❌ فشل"}
        for item in summary["cases"]
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=310)
    st.download_button("⬇️ تنزيل تقرير الاختبار JSON", as_json(summary),
                       file_name="TABAQ_QA_results.json", mime="application/json")
    st.warning("هذه اختبارات قواعد على بيانات منظمة اصطناعية؛ لا تقيس دقة OCR على الصور الحقيقية، ولا تمثل تحققًا ميدانيًا من المنتجات.")

with tab_about:
    st.subheader("ماذا يثبت هذا النموذج؟")
    st.markdown("""
- مقارنة **سبعة حقول** باستخدام محرك قواعد مستقل عن الواجهة.
- إظهار **أربع حالات**: متطابق، اختلاف، غير محسوم، مرجع غير متاح.
- الامتناع عن إصدار حكم نهائي عند نقص حقل أساسي أو فساد القيمة العددية.
- توليد **مسودة أدلة JSON** للمراجعة البشرية.
- تنفيذ **60 اختبارًا آليًا اصطناعيًا** وعرض النجاح الفعلي.

**ما لا يثبته بعد:** لا يوجد اتصال رسمي بقاعدة بيانات «تأكد»، ولا تعرف تلقائي موثوق على حقول الملصق من الصورة. تجربة OCR الاختيارية تعرض النص الخام للمراجعة اليدوية فقط. هذا النموذج لا يصدر حكمًا بالتزوير أو المطابقة التنظيمية.
    """)
    st.markdown("**المصدر الرسمي لتطبيق تأكد:** https://www.saso.gov.sa/ar/takad_app/pages/default.aspx")
    st.caption("الواجهة وبيانات المنتجات اختبارية وغير تابعة للهيئة.")