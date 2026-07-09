# تقارير الجودة — مولّد تقارير الصيانة والاستعداد المدرسي

تطبيق ويب (PWA) لإصدار تقارير جودة أعمال الصيانة الميدانية بنفس قالب PowerPoint المعتمد، مع تعبئة تلقائية لبيانات المدرسة ورفع الصور مباشرة أثناء الزيارة.

## البنية

```
backend/    FastAPI + SQLite + محرك توليد PPTX (python-pptx)
frontend/   React + Vite (PWA)
```

## التشغيل محلياً (تطوير)

### الباك-إند

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.services.excel_import   # استيراد بيانات المدارس من ملف الإكسل المرفق
APP_PASSWORD=your-password uvicorn app.main:app --reload --port 8000
```

### الفرونت-إند

```bash
cd frontend
npm install
npm run dev
```

افتح `http://localhost:5173` وسجّل الدخول بكلمة المرور المحددة في `APP_PASSWORD`.

## التشغيل بـ Docker (إنتاج)

```bash
APP_PASSWORD=your-strong-password SECRET_KEY=$(openssl rand -hex 32) docker compose up -d --build
```

يشغّل حاوية واحدة تخدم الواجهة + الـ API على المنفذ 8000، مع تخزين قاعدة البيانات والصور في volume دائم (`app_data`).

## تحديث بيانات المدارس

ارفع ملف إكسل جديد (بنفس الأعمدة) عبر:

```
POST /api/schools/import   (multipart file)
```

أو استبدل `backend/app/assets/schools_seed.xlsx` وأعد تشغيل الحاوية (يُستورد تلقائياً عند الإقلاع).

## متغيرات البيئة

| المتغير | الوصف | الافتراضي |
|---|---|---|
| `APP_PASSWORD` | كلمة مرور الدخول للتطبيق | `changeme` |
| `SECRET_KEY` | مفتاح توقيع جلسة الدخول | يجب تغييره في الإنتاج |
| `DATABASE_URL` | رابط قاعدة Postgres (Neon). إن لم يُحدَّد يُستخدم SQLite محلياً | SQLite محلي |
| `R2_ENDPOINT_URL` | نقطة وصول Cloudflare R2 (S3-compatible) | — |
| `R2_ACCESS_KEY_ID` | مفتاح وصول R2 | — |
| `R2_SECRET_ACCESS_KEY` | المفتاح السري لـ R2 | — |
| `R2_BUCKET` | اسم الحاوية (bucket) في R2 | — |
| `FRONTEND_ORIGIN` | نطاق الفرونت-إند المسموح له بالـ CORS (وضع التطوير فقط) | `http://localhost:5173` |

> **تخزين الصور**: عند ضبط متغيرات `R2_*` الأربعة تُرفع الصور المضغوطة إلى Cloudflare R2 (دائمة، لا تُفقد عند إعادة النشر). بدونها يستخدم التطبيق القرص المحلي (للتطوير فقط).
> **قاعدة البيانات**: عند ضبط `DATABASE_URL` لرابط Neon Postgres تُخزَّن البيانات في السحابة. الكود يتوافق مع Postgres وSQLite تلقائياً.

## معمارية النشر الدائم (مجانية)

- **التشغيل**: Google Cloud Run (يشغّل الـ Dockerfile مباشرة)
- **قاعدة البيانات**: Neon Postgres
- **تخزين الصور**: Cloudflare R2 (١٠ جيجا مجاناً، نقل بيانات مجاني)

الحاوية عديمة الحالة (كل البيانات في Neon + R2)، فتصلح لأي منصة حاويات.

## خارطة الطريق

هذا الإصدار يغطي **مولّد التقارير** فقط. المراحل القادمة حسب الرؤية الكاملة:
- جدولة زيارات ذكية حسب الموقع الجغرافي للمدارس
- ربط عقود المقاولين ببنودها لكل مدرسة
- ملف متابعة تراكمي لكل مدرسة عبر الزيارات
- تقارير مخصصة على مستوى بند/مدرسة/نطاق جغرافي

بنية البيانات الحالية (المدرسة تحمل الإحداثيات، والتقارير مرتبطة بالمدرسة) مصممة لدعم هذه المراحل دون إعادة هيكلة.
