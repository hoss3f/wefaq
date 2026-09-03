<div align="center">

# 🕌 وِفاق · WEFAQ

### Halal Matchmaking Platform
منصة تعارف حلال، بستر واحترام

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-Build-646CFF?logo=vite&logoColor=white)
![Tailwind](https://img.shields.io/badge/TailwindCSS-Styling-06B6D4?logo=tailwindcss&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)

[نبذة](#-نبذة) · [المميزات](#-المميزات) · [التقنيات](#️-التقنيات) · [الهيكل](#-هيكل-المشروع) · [التشغيل](#-التشغيل) · 

</div>

---

## 📖 نبذة

وِفاق تطبيق ويب يساعد الشباب والشابات على التعارف الجاد بقصد الزواج، ضمن ضوابط الستر والاحترام. المتقدم يدخل بكود من الإدارة، يكمل بياناته وإجاباته، ثم يتابع حالة طلبه — تحت إشراف إداري كامل من الاستقبال إلى القرار.

## ✨ المميزات

<table>
<tr>
<td width="33%" valign="top">

**🔒 ستر وخصوصية**
لا صور مكشوفة ولا تواصل مباشر بدون موافقة، كل تفاعل يمر بإشراف.

</td>
<td width="33%" valign="top">

**🕌 فلترة على أساس التوافق**
أسئلة مبنية على معايير دينية وأسرية لترشيح التوافق بين الطرفين.

</td>
<td width="33%" valign="top">

**🤝 إشراف إداري كامل**
مراجعة الحسابات والتفاعلات لضمان جدية الأعضاء ومنع إساءة الاستخدام.

</td>
</tr>
</table>

## 🛠️ التقنيات

| الجزء | التقنيات |
|:---|:---|
| **Backend** | Flask · Flask-SQLAlchemy · Flask-CORS · PostgreSQL |
| **Frontend** | React 18 · React Router · Vite · Tailwind CSS |

## 📁 هيكل المشروع

```text
wefaq/
├── requirements.txt
│
├── backend/
│   ├── app.py                    نقطة تشغيل الخادم وتهيئة قاعدة البيانات
│   ├── config.py                 إعدادات الاتصال والمسارات
│   ├── .env                      DATABASE_URL · SECRET_KEY · إعدادات SMTP (أنشئه من .env.example)
│   ├── security.py               تعقيم المدخلات والتحقق من صحتها
│   ├── utils.py                  تشفير، توليد أكواد، مزامنة JSON، بريد الترحيب
│   ├── test_system.py            اختبار النظام الشامل
│   ├── models/
│   │   ├── db_schemes/           جداول: users, admins, answers, notes, notifications
│   │   └── data/                 admins.json · questions.json · users.json
│   ├── routes/                   auth · user · admin · matching · notifications
│   ├── services/
│   │   └── matching_service.py   منطق ترشيح التوافق بين المتقدمين
│   └── uploads/                  صور المستخدمين المرفوعة
│
└── frontend/
    ├── test_phase3.mjs                 اختبار تدفق كامل
    ├── test_onboarding_and_admin.mjs    اختبار أول دخول + مزامنة الإداريين
    └── src/
        ├── config.json           رابط API + حقول النموذج + خطوات التسجيل
        ├── components/           Card, Button, ProgressSteps ...
        ├── pages/                الرئيسية، الدخول، التسجيل، إكمال الطلب، اللوحات
        └── services/             استدعاءات API (auth · user · admin · matching)
```

## 🚀 التشغيل

### 0. قاعدة البيانات

المشروع يعتمد على **PostgreSQL** فقط (لا يوجد دعم SQLite). جهّز قاعدة بيانات فارغة (محلياً أو عبر Neon/Supabase مثلاً)، ثم:

```bash
cd backend
cp .env.example .env   # Windows: copy .env.example .env
```

عدّل `backend/.env` وضع فيه `DATABASE_URL` الحقيقي (و`SECRET_KEY`). إعدادات `SMTP_*` اختيارية — بدونها يتم تخطي إرسال بريد الترحيب بصمت.

### 1. الخادم 
```bash
cd backend
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows Command Prompt
venv\Scripts\activate.bat

pip install -r requirements.txt
# أو من جذر المشروع: pip install -r ../requirements.txt
python app.py
```


📍 يعمل على `http://localhost:5000` وينشئ الجداول وحساب المدير العام تلقائياً في قاعدة البيانات المحددة في `DATABASE_URL`.

### 2. الواجهة الأمامية

> نافذة طرفية جديدة، مع بقاء الخادم يعمل

```bash
cd frontend
npm install
npm run dev
```

📍 تفتح على `http://localhost:5173`
