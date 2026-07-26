// frontend/src/pages/HomePage.jsx
import { Link } from 'react-router-dom'
import config from '../config.json'
import MashrabiyaDivider from '../components/MashrabiyaDivider'
import Card from '../components/Card'

export default function HomePage() {
  return (
    <div>
      <section className="max-w-3xl mx-auto text-center px-6 py-20">
        <h1 className="font-display text-5xl text-teal-700 mb-4">{config.appName}</h1>
        <p className="text-lg text-muted mb-8">{config.appTagline}</p>
        <p className="text-ink leading-relaxed mb-10">
          منصة تُعنى بمساعدتك على التعرف على شريك حياة بطريقة تحفظ الحياء وتراعي الضوابط الشرعية.
          يراجع فريق مختص كل طلب بعناية قبل أي تواصل.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <Link to="/login" className="bg-teal-600 text-linen px-8 py-3 rounded-xl font-medium hover:bg-teal-700">
            دخول بالكود
          </Link>
          <Link to="/admin/login" className="border border-teal-600 text-teal-600 px-8 py-3 rounded-xl font-medium hover:bg-teal-50">
            دخول الإداريين
          </Link>
        </div>
        <p className="text-muted text-sm mt-4">
          المتقدم يدخل بكوده الخاص، والإداري يدخل ببريده وكلمة المرور.
        </p>
      </section>

      <MashrabiyaDivider />

      <section className="max-w-5xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-6">
        <Card>
          <h3 className="font-display text-xl text-teal-700 mb-2">الستر أولاً</h3>
          <p className="text-muted text-sm leading-relaxed">
            بياناتك لا تظهر لأحد إلا لفريق المراجعة المختص، وبموافقتك في كل خطوة.
          </p>
        </Card>
        <Card>
          <h3 className="font-display text-xl text-teal-700 mb-2">مراجعة إنسانية</h3>
          <p className="text-muted text-sm leading-relaxed">
            كل طلب يُراجع من قبل إداري مختص، وليس بشكل آلي بحت، لضمان الجدية والاحترام.
          </p>
        </Card>
        <Card>
          <h3 className="font-display text-xl text-teal-700 mb-2">إشعار بكل خطوة</h3>
          <p className="text-muted text-sm leading-relaxed">
            تصلك إشعارات فور تحديث حالة طلبك، دون الحاجة لمتابعة مستمرة.
          </p>
        </Card>
      </section>
    </div>
  )
}