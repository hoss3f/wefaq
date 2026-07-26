<div align="center">

# 🕌 وِفاق · WEFAQ

### منصة تعارف حلال، بستر واحترام

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?style=flat-square&logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=flat-square&logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/TailwindCSS-Styling-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-07405E?style=flat-square&logo=sqlite&logoColor=white)

</div>

---

## ✨ لماذا وِفاق؟

| 🔒 خصوصية وستر | 🕌 ضوابط شرعية | 🤝 جدية في التعارف |
|:---:|:---:|:---:|
| لا صور مكشوفة، لا دردشة مفتوحة عشوائية — كل تواصل بإشراف وموافقة | أسئلة وفلاتر مبنية على معايير التوافق الأسري والديني | إشراف إداري كامل على الحسابات والتفاعلات لضمان جدية الأعضاء |

---

## 🗂️ هيكل المشروع

\`\`\`text
wefaq/
│
├── 🐍 backend/                  Flask API
│   ├── routes/                   auth · user · admin · notifications
│   ├── data/                     أسئلة، مدير عام، مستخدمون تجريبيون (JSON)
│   ├── instance/                 قاعدة بيانات SQLite (تُنشأ تلقائياً)
│   ├── app.py                    نقطة تشغيل الخادم
│   ├── config.py                 إعدادات التطبيق
│   ├── models.py                 جداول قاعدة البيانات
│   ├── utils.py                  دوال مساعدة
│   ├── test_phase1.py            🧪 اختبار البنية التحتية
│   └── test_phase2.py            🧪 اختبار المصادقة وواجهات API
│
└── ⚛️ frontend/                 React + Tailwind
    ├── src/
    │   ├── config.json            رابط الـ API والحقول الديناميكية
    │   ├── components/            مكونات قابلة لإعادة الاستخدام
    │   ├── pages/                 صفحات التطبيق
    │   ├── services/              الاتصال بالـ API
    │   └── App.jsx                ربط المسارات
    └── test_phase3.mjs           🧪 اختبار تدفق البيانات الكامل
\`\`\`

---

## ⚙️ التشغيل

### 1️⃣ الخادم الخلفي

\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate       # macOS/Linux
# .\venv\Scripts\Activate.ps1  # PowerShell (ويندوز)
pip install flask flask-sqlalchemy
python app.py
\`\`\`

📍 يعمل على \`http://localhost:5000\` وينشئ قاعدة البيانات وحساب المدير العام تلقائياً عند أول تشغيل.

<div align="center">

| 👤 الحقل | القيمة |
|:---:|:---:|
| البريد | \`super@wefaq.com\` |
| كلمة المرور | \`SuperAdmin@2026\` |

</div>

### 2️⃣ الواجهة الأمامية

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

📍 تعمل على \`http://localhost:5173\` — تأكد من تشغيل الخادم أولاً.

---

## 🧪 الاختبارات

| الأمر | الغرض |
|---|---|
| \`python backend/test_phase1.py\` | 🗄️ قاعدة البيانات والملفات |
| \`python backend/test_phase2.py\` | 🔐 المصادقة وواجهات API |
| \`node frontend/test_phase3.mjs\` | 🔄 تدفق البيانات الكامل (يتطلب تشغيل الخادم) |

---

## 🛡️ ملاحظة أمنية

> ⚠️ كلمة مرور المدير العام والمفتاح السري في \`config.py\` **للتطوير فقط** — غيّرهما قبل أي نشر فعلي.

<div align="center">

---
صُنع بـ 💚 لتعارف أنقى

</div>
