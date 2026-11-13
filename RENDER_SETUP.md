# نشر «طابِق» على Render

هذه النسخة **Streamlit Web Service** وليست **Static Site**.

## الخطوات اليدوية

1. في Render ارجع من صفحة `Static Site` واضغط **New → Web Service**، أو اختر **New → Blueprint** لاستخدام ملف `render.yaml`.
2. اربط GitHub بحسابك وحدد المستودع `majmaah99-ops/tabaq`.
3. عند استخدام Web Service اختر **Language / Runtime: Docker** و **Branch: main** و **Dockerfile Path: ./Dockerfile** و **Root Directory: .**.
4. اسم مقترح: `tabaq-web`. يمكنك اختيار خطة Free إن كانت متاحة لحسابك.
5. لا تضع Build Command أو Start Command يدويًا في وضع Docker؛ يستخدم Dockerfile الأمر المناسب وبيئة PORT التي يمنحها Render.
6. اضغط **Deploy Web Service** وافتح الرابط الذي تمنحه Render بعد نجاح البناء. لا تُفترض أي صيغة أو نطاق URL قبل تأكيد النشر.
7. جرّب أربع حالات المطابقة؛ ثم ارفع صورة PNG/JPG واضغط زر استخراج حقول OCR لمراجعتها يدويًا.

## OCR

تثبت بيئة Docker أدوات Tesseract اللغتين `ara` و`eng` و`pytesseract`. استخراج الحقول **اقتراحات أولية** وليس توثيقًا لصحة المنتج. إذا لم تتعرف الأداة على حقل مهم فسيبقى فارغًا، ومحرك القرار يمتنع عن إصدار نتيجة متطابقة.

## تنبيه

المراجع اصطناعية للتجربة فقط. لا تتوفر قاعدة بيانات أو API رسمي للهيئة. لا تستخدم البيانات لاتخاذ قرارات نظامية أو لإثبات التزوير. لا ترفع صورًا تحتوي على معلومات شخصية.
