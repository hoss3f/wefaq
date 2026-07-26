# وِفاق (WEFAQ)

منصة تعارف حلال بستر واحترام. المشروع مبني من جزأين منفصلين: خادم خلفي (backend) بلغة Python وFlask، وواجهة أمامية (frontend) بReact وTailwind CSS.

## هيكل المشروع

```
wefaq/
  backend/
    data/            ملفات JSON (الأسئلة، المدير العام، مستخدمون تجريبيون)
    instance/         قاعدة بيانات SQLite (تُنشأ تلقائياً عند التشغيل)
    routes/           مسارات API (المصادقة، المستخدم، الإداري، الإشعارات)
    app.py            نقطة تشغيل الخادم
    config.py         إعدادات التطبيق
    models.py         جداول قاعدة البيانات
    utils.py          دوال مساعدة
    test_phase1.py    اختبار البنية التحتية وقاعدة البيانات
    test_phase2.py    اختبار المصادقة وواجهات API
  frontend/
    src/
      config.json     رابط الـ API وحقول النماذج الديناميكية
      components/      مكونات واجهة قابلة لإعادة الاستخدام
      pages/           صفحات التطبيق
      services/        دوال الاتصال بالـ API
      App.jsx          ربط المسارات
    test_phase3.mjs    اختبار تدفق البيانات الكامل بين الواجهة والخادم
```

## تشغيل الخادم الخلفي

```bash
cd backend
python -m venv venv
# macOS/Linux
source venv/bin/activate
# PowerShell على ويندوز
.\venv\Scripts\Activate.ps1
# أو Command Prompt على ويندوز
venv\Scripts\activate.bat
pip install flask flask-sqlalchemy
python app.py
```

يعمل الخادم على `http://localhost:5000`، وينشئ قاعدة البيانات وحساب المدير العام تلقائياً عند أول تشغيل.

بيانات دخول المدير العام الافتراضية:
- البريد: `super@wefaq.com`
- كلمة المرور: `SuperAdmin@2026`

## تشغيل الواجهة الأمامية

```bash
cd frontend
npm install
npm run dev
```

تفتح الواجهة على `http://localhost:5173`. تأكد من تشغيل الخادم الخلفي أولاً على المنفذ 5000.

## تشغيل الاختبارات

```bash
# اختبار قاعدة البيانات والملفات
cd backend && python test_phase1.py

# اختبار المصادقة وواجهات API
cd backend && python test_phase2.py

# اختبار تدفق البيانات الكامل (يتطلب تشغيل الخادم على المنفذ 5000)
cd frontend && node test_phase3.mjs
```

## ملاحظة أمنية

كلمة مرور المدير العام وحساسة المفتاح السري في `config.py` معدّة للتطوير فقط. يجب تغييرهما قبل أي نشر فعلي للمشروع.
