"""Experimental Arabic/English image OCR for TABAQ.

Proposes candidate fields for human review only. Never certifies products.
This deliberately does not guess values from a demo reference database.
"""
from __future__ import annotations

from io import BytesIO
import re
from typing import Any

from PIL import Image, ImageOps
from engine import normalize

MODEL_RE = re.compile(r"\bAC\s*[-–]?\s*[0-9]{2,6}(?:\s*[-–]\s*[A-Z0-9]{1,8})?\b", re.I)
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])(?:[0-9٠-٩۰-۹][0-9٠-٩۰-۹.,٬٫]*)(?![A-Za-z0-9])")
ENERGY_TERMS = ("الاستهلاك", "annual consumption", "kwh", "ك.و.س", "كيلوواط")
EFF_TERMS = ("معدل كفاءة", "energy efficiency", "eer", "seER")
LEVEL_TERMS = ("مستوى كفاءة", "energy level", "efficiency level")

def _number(value: str) -> str | None:
    raw = normalize(value).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    raw = raw.replace("٬", ",").replace("٫", ".")
    raw = raw.strip("., ")
    if re.fullmatch(r"\d{1,3}(,\d{3})+(?:\.\d+)?", raw):
        raw = raw.replace(",", "")
    if re.fullmatch(r"\d+(?:\.\d+)?", raw):
        return raw
    return None

def _number_near(lines: list[str], terms: tuple[str,...], *, exclude: tuple[str,...]=()) -> str | None:
    for idx,line in enumerate(lines):
        lower = line.casefold()
        if not any(term.casefold() in lower for term in terms):
            continue
        if exclude and any(term.casefold() in lower for term in exclude):
            continue
        # Prefer the part after a label, then the immediate following line.
        for candidate in (line, lines[idx+1] if idx+1 < len(lines) else ""):
            for part in NUMBER_RE.findall(candidate):
                val = _number(part)
                if val and 0 < float(val) < 1000000:
                    return val
    return None

def parse_text(raw_text: str) -> dict[str, Any]:
    """Extract *only* identifiable hints from OCR text; missing stays missing."""
    lines=[ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    text="\n".join(lines)
    lower=text.casefold()
    result: dict[str,str]={}
    found=MODEL_RE.search(text)
    if found:
        result["model"]=re.sub(r"\s+", "",found.group()).replace("–","-").upper()
    if "نسيم" in lower or "naseem" in lower:
        result["brand"]="نسيم"
    if "الزامل" in lower:
        result["brand"]="الزامل"
    if "samsung" in lower or "سامسونج" in lower:
        result["brand"]="سامسونج"
    if "مكيف" in lower or "air conditioner" in lower:
        result["device_type"]="مكيف"
    if "سبليت" in lower or "split" in lower:
        result["product_type"]="سبليت"
    annual=_number_near(lines,ENERGY_TERMS,exclude=("energy efficiency","معدل كفاءة"))
    if annual: result["annual_consumption"]=annual
    eff=_number_near(lines,EFF_TERMS,exclude=("level","مستوى"))
    if eff: result["energy_efficiency"]=eff
    for idx,line in enumerate(lines):
        if any(t.casefold() in line.casefold() for t in LEVEL_TERMS):
            hit=re.search(r"(?:[:：]\s*|\b)([A-G](?:\+)?|[أابجدهوز])\s*$",line,re.I)
            if hit:
                result["efficiency_level"]=hit.group(1)
            elif idx+1 < len(lines) and re.fullmatch(r"[A-G](?:\+)?|[أابجدهوز]",lines[idx+1],re.I):
                result["efficiency_level"]=lines[idx+1]
            break
    return result

def extract_from_image(image_bytes: bytes) -> dict[str, Any]:
    import pytesseract
    with Image.open(BytesIO(image_bytes)) as im:
        if im.width * im.height > 18_000_000:
            raise ValueError("أبعاد الصورة كبيرة جدًا؛ استخدم صورة أصغر.")
        im=ImageOps.exif_transpose(im).convert("RGB")
        if im.width < 1500:
            scale=min(2.5, 1500/max(im.width,1))
            im=im.resize((round(im.width*scale),round(im.height*scale)))
        im=ImageOps.autocontrast(im.convert("L"))
        try:
            installed=pytesseract.get_languages(config="")
            if "eng" not in installed:
                raise ValueError("حزمة لغة Tesseract الإنجليزية غير متاحة.")
            lang="ara+eng" if "ara" in installed else "eng"
            raw=pytesseract.image_to_string(im,lang=lang,config="--psm 6",timeout=20)
            if not raw.strip() and "ara" in installed:
                raw=pytesseract.image_to_string(im,lang="eng",config="--psm 6",timeout=20)
        except RuntimeError as exc:
            raise ValueError("انتهت مهلة قراءة OCR؛ حاول بصورة أوضح أو أصغر.") from exc
    return {
      "fields":parse_text(raw),
      "raw_text":raw[:18000],
      "available_languages":lang,
      "review_required":True,
      "warning":"هذه اقتراحات قراءة بصرية وليست نتيجة تحقق؛ راجع الحقول يدويًا قبل المقارنة."
    }
