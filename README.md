<div align="center">

# 🕌 وِفاق · WEFAQ

### Halal Matchmaking Platform

منصة تعارف حلال، بستر واحترام

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/TailwindCSS-Styling-06B6D4?logo=tailwindcss&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-07405E?logo=sqlite&logoColor=white)

</div>

---

## About

وِفاق تطبيق ويب يساعد الشباب والشابات على التعارف الجاد بقصد الزواج، ضمن ضوابط الستر والاحترام. المستخدم يُنشئ حساباً، يجيب على أسئلة التوافق، ثم يتصفح ويتواصل تحت إشراف إداري كامل — بدون صور مكشوفة ولا دردشة عشوائية مفتوحة.

## ✨ What It Does

- 🔒 **ستر وخصوصية**: لا صور مكشوفة ولا تواصل مباشر بدون موافقة، كل تفاعل يمر بإشراف.
- 🕌 **فلترة على أساس التوافق**: أسئلة مبنية على معايير دينية وأسرية لترشيح التوافق بين الطرفين.
- 🤝 **إشراف إداري كامل**: مراجعة الحسابات والتفاعلات لضمان جدية الأعضاء ومنع إساءة الاستخدام.

## 🛠️ Built With

- **Python + Flask**: الخادم الخلفي وقاعدة البيانات
- **SQLite**: قاعدة بيانات تُنشأ تلقائياً عند أول تشغيل
- **React + Tailwind CSS**: الواجهة الأمامية

## 📁 Folder Structure

```
wefaq/
├── backend/
│   ├── routes/            # auth, user, admin, notifications
│   ├── data/               # أسئلة، مدير عام، مستخدمون تجريبيون (JSON)
│   ├── instance/           # قاعدة بيانات SQLite (تُنشأ تلقائياً)
│   ├── app.py              # نقطة تشغيل الخادم
│   ├── config.py           # إعدادات التطبيق
│   ├── models.py           # جداول قاعدة البيانات
│   └── utils.py            # دوال مساعدة
└── frontend/
    └── src/
        ├── config.json      # رابط الـ API والحقول الديناميكية
        ├── components/      # مكونات قابلة لإعادة الاستخدام
        ├── pages/           # صفحات التطبيق
        ├── services/        # الاتصال بالـ API
        └── App.jsx          # ربط المسارات
```

## 🚀 Getting Started

**1. جهّز بيئة Python للخادم:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # على ويندوز: venv\Scripts\activate
```

**2. ثبّت المكتبات:**
```bash
pip install flask flask-sqlalchemy
```

**3. شغّل الخادم:**
```bash
python app.py
```
يعمل على `http://localhost:5000` وينشئ قاعدة البيانات وحساب المدير العام تلقائياً (`super@wefaq.com` / `SuperAdmin@2026`).

**4. ثبّت وشغّل الواجهة الأمامية** (في نافذة طرفية جديدة):
```bash
cd frontend
npm install
npm run dev
```
تفتح على `http://localhost:5173` — تأكد أن الخادم يعمل أولاً.

## 🧪 الاختبارات

```bash
python backend/test_phase1.py     # قاعدة البيانات والملفات
python backend/test_phase2.py     # المصادقة وواجهات API
node frontend/test_phase3.mjs     # تدفق البيانات الكامل (يتطلب تشغيل الخادم)
```

## 🛡️ ملاحظة أمنية

كلمة مرور المدير العام والمفتاح السري في `config.py` **للتطوير فقط** — غيّرهما قبل أي نشر فعلي.
