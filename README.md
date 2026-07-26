<div align="center">

# وِفاق · WEFAQ

**منصة تعارف حلال، بستر واحترام**

`Python` · `Flask` · `React` · `Tailwind CSS`

</div>

---

## 🧩 البنية

مشروعان منفصلان: **خادم** (Flask) و**واجهة** (React).

```
wefaq/
├── backend/            Flask API + SQLite
│   ├── routes/          مصادقة · مستخدم · إدارة · إشعارات
│   ├── data/             ملفات JSON (أسئلة، مدير عام، مستخدمون تجريبيون)
│   ├── app.py            نقطة التشغيل
│   └── models.py         جداول قاعدة البيانات
│
└── frontend/           React + Tailwind
    └── src/
        ├── pages/         الصفحات
        ├── components/    مكونات قابلة لإعادة الاستخدام
        └── services/      الاتصال بالـ API
```

---

## ⚙️ التشغيل

### 1) الخادم الخلفي

```bash
cd backend
python -m venv venv
source venv/bin/activate       # macOS/Linux
# .\venv\Scripts\Activate.ps1  # PowerShell
pip install flask flask-sqlalchemy
python app.py
```

→ يعمل على `http://localhost:5000` وينشئ قاعدة البيانات والمدير العام تلقائياً.

| الحقل | القيمة |
|---|---|
| البريد | `super@wefaq.com` |
| كلمة المرور | `SuperAdmin@2026` |

### 2) الواجهة الأمامية

```bash
cd frontend
npm install
npm run dev
```

→ تعمل على `http://localhost:5173` (شغّل الخادم أولاً).

---

## ✅ الاختبارات

| الأمر | الغرض |
|---|---|
| `cd backend && python test_phase1.py` | قاعدة البيانات والملفات |
| `cd backend && python test_phase2.py` | المصادقة وواجهات API |
| `cd frontend && node test_phase3.mjs` | تدفق البيانات الكامل (يتطلب تشغيل الخادم) |

---

## 🔐 أمان

> إعدادات `config.py` (كلمة مرور المدير العام، المفتاح السري) للتطوير فقط — **غيّرها قبل أي نشر فعلي**.
