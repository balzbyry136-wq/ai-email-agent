# AI Email Agent — مساعد إدارة البريد الإلكتروني

مشروع كامل يتصل بحساب Gmail، يصنّف الإيميلات ويلخصها بالذكاء الاصطناعي، ويقترح ردود لا تُرسل إلا بعد موافقتك.

> **مهم**: هذا التطبيق يتصل بحسابك الحقيقي على Gmail. الرد لا يُرسل تلقائياً أبداً — تتم مراجعتك والموافقة أولاً على كل رد قبل إرساله.

---

## المتطلبات

- Python 3.10+
- حساب Google (Gmail)
- مفتاح Anthropic API (من https://console.anthropic.com)

---

## الخطوة 1: الحصول على مفتاح Anthropic API

1. روح لـ https://console.anthropic.com/settings/keys
2. أنشئ مفتاح جديد وانسخه (تحتاج تفعيل الفوترة على الحساب لاستخدام الـ API)

---

## الخطوة 2: إعداد مشروع Google Cloud (لـ Gmail API)

1. روح لـ https://console.cloud.google.com وأنشئ مشروع جديد
2. من القائمة، فعّل **Gmail API**: ابحث عنه في "APIs & Services" → "Library"
3. اذهب لـ "APIs & Services" → "OAuth consent screen":
   - اختر "External"
   - عبّي اسم التطبيق وإيميلك
   - في صفحة "Scopes" أضف: `gmail.readonly`, `gmail.send`, `gmail.modify`
   - في "Test users" أضف إيميلك أنت (طالما التطبيق لسا بوضع Testing)
4. اذهب لـ "Credentials" → "Create Credentials" → "OAuth client ID":
   - نوع التطبيق: **Web application**
   - Authorized redirect URIs: أضف `http://localhost:8000/auth/callback`
5. حمّل ملف الاعتماد (JSON) وسمّه `credentials.json`، وحطه داخل مجلد `backend/`

---

## الخطوة 3: تجهيز البيئة المحلية

```bash
cd backend
python -m venv venv
source venv/bin/activate   # على ويندوز: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# افتح .env وعبّي: ANTHROPIC_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
```

`GOOGLE_CLIENT_ID` و `GOOGLE_CLIENT_SECRET` تلقاهم داخل ملف `credentials.json` نفسه اللي حملته.

---

## الخطوة 4: تشغيل السيرفر (Backend)

```bash
cd backend
uvicorn main:app --reload
```

السيرفر يشتغل على: `http://localhost:8000`
تقدر تشوف توثيق الـ API تلقائياً على: `http://localhost:8000/docs`

---

## الخطوة 5: تشغيل الواجهة (Frontend)

الواجهة ملف HTML واحد بسيط، أسهل طريقة لتشغيله محلياً:

```bash
cd frontend
python -m http.server 5500
```

بعدها افتح المتصفح على: `http://localhost:5500`

---

## الخطوة 6: الاستخدام

1. اضغط **"تسجيل دخول Google"** — بيفتح نافذة جديدة لتسجيل الدخول والموافقة على الصلاحيات
2. بعد الموافقة، ارجع للواجهة، حط نفس بريدك الإلكتروني بالحقل، واضغط **"مزامنة الآن"**
3. راح تظهر آخر 10 إيميلات مصنفة (عاجل / يحتاج رد / عادي / سبام) مع ملخص ومهام مستخرجة
4. لو فيه رد مقترح، تقدر تعدّله بالمربع، وتضغط **"وافق وأرسل"** ليُرسل فعلياً، أو **"رفض"** لتجاهله

---

## هيكل المشروع

```
email-agent/
├── backend/
│   ├── main.py            # نقاط الـ API الرئيسية
│   ├── models.py          # جداول قاعدة البيانات
│   ├── schemas.py         # التحقق من صحة البيانات
│   ├── gmail_service.py   # الاتصال بـ Gmail API
│   ├── ai_service.py      # التصنيف والتلخيص عبر Claude
│   ├── database.py        # إعداد SQLite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html         # الـ Dashboard (ملف واحد، بدون build step)
└── README.md
```

قاعدة البيانات SQLite (ملف `email_agent.db`) تُنشأ تلقائياً أول مرة تشغّل السيرفر - ما تحتاج تنصيب Postgres أو أي شيء إضافي.

---

## ملاحظات أمان مهمة

- ملفات `.env` و `credentials.json` **لا ترفعها لأي مكان عام** (git، إلخ) — فيها بيانات حساسة
- بوضع "Testing" بـ Google OAuth consent screen، فقط الإيميلات اللي تضيفها كـ "Test users" تقدر تسجل دخول
- التطبيق حالياً يخزن الـ tokens بشكل غير مشفر بقاعدة البيانات المحلية — مناسب للتطوير والاستخدام الشخصي، لكن لو تبي تنشره لعدة مستخدمين لازم تشفّرها (مثلاً بمكتبة `cryptography`)
- ما فيه إرسال تلقائي لأي رد إطلاقاً بدون ضغطتك على "وافق وأرسل"

---

## أفكار للتوسع لاحقاً

- دعم عدة مستخدمين بشكل كامل (حالياً مصمم لمستخدم واحد بشكل أساسي)
- Webhook بدل الـ polling اليدوي (Gmail Push Notifications عبر Google Cloud Pub/Sub)
- ربط بـ Google Calendar لتحويل الـ Action Items لأحداث تلقائياً
- صلاحيات إرسال شبه تلقائي لفئات إيميلات محددة بعد بناء الثقة
