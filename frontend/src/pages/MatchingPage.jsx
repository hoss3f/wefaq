import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import { getMyMatches } from '../services/matchingService'

const PROFILE_FIELDS = [
  ['العمر', 'age', ' سنة'], ['الجنسية', 'nationality', ''], ['بلد الإقامة', 'country', ''],
  ['المهنة', 'profession', ''], ['الحالة الاجتماعية', 'marital_status', ''], ['موعد الزواج المفضل', 'marriage_timeline', ''],
]

export default function MatchingPage() {
  const navigate = useNavigate()
  const [matches, setMatches] = useState(null)
  const [index, setIndex] = useState(0)
  const [saved, setSaved] = useState(false)
  const [interested, setInterested] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const session = JSON.parse(localStorage.getItem('wefaq_user') || 'null')
    if (!session) return navigate('/login', { replace: true })
    if (session.status !== 'approved') return navigate('/dashboard', { replace: true })
    getMyMatches(session.id).then((data) => setMatches(data.matches || [])).catch((err) => setError(err.message))
  }, [navigate])

  function next() {
    setIndex((current) => (current + 1) % matches.length)
    setSaved(false)
    setInterested(false)
  }

  if (error) return <div dir="rtl" className="mx-auto max-w-xl px-6 py-20 text-center"><p className="text-brick-500">{error}</p><Button variant="secondary" className="mt-5" onClick={() => navigate('/account')}>الحساب</Button></div>
  if (!matches) return <p dir="rtl" className="py-20 text-center text-muted">جاري البحث عن المرشحين المناسبين...</p>
  if (!matches.length) return <div dir="rtl" className="mx-auto max-w-xl px-6 py-20 text-center"><Card><h1 className="font-display text-2xl text-teal-700">لا توجد نتائج مطابقة حالياً.</h1><p className="mt-3 text-muted">سنظهر لك المرشحين المناسبين عند توفرهم.</p><Button variant="secondary" className="mt-6" onClick={() => navigate('/account')}>الحساب والإعدادات</Button></Card></div>

  const match = matches[index]
  const candidate = match.candidate
  return <main dir="rtl" className="mx-auto min-h-full max-w-xl px-4 py-6 sm:px-6">
    <header className="mb-5 flex items-center justify-between"><div><p className="text-sm text-muted">اكتشف المرشحين المناسبين</p><h1 className="font-display text-3xl text-teal-700">وِفاق</h1></div><button type="button" onClick={() => navigate('/account')} className="min-h-11 rounded-xl border border-teal-100 px-4 text-sm font-medium text-teal-700">الحساب</button></header>
    <Card className="overflow-hidden p-0">
      <div className="relative min-h-44 bg-teal-700 px-6 py-7 text-linen"><div className="absolute inset-0 opacity-10 mashrabiya-bg" /><div className="relative flex items-start justify-between"><div><p className="text-base">نسبة التوافق</p><p className="mt-1 font-display text-6xl leading-none">{match.compatibility_percentage}%</p></div><div className="flex h-20 w-20 items-center justify-center rounded-full border border-linen/50 bg-linen/10 text-center text-sm">الصورة<br />مخفية</div></div></div>
      <div className="p-6"><div className="mb-5 flex items-center justify-between"><h2 className="font-display text-2xl text-teal-700">مرشح مناسب</h2><span className="rounded-full bg-gold-100 px-3 py-1 text-sm text-teal-700">{index + 1} من {matches.length}</span></div>
        <div className="grid grid-cols-2 gap-3">{PROFILE_FIELDS.map(([label, key, suffix]) => candidate[key] && <div key={key} className="rounded-xl bg-teal-50 p-3"><p className="text-xs text-muted">{label}</p><p className="mt-1 font-medium text-ink">{candidate[key]}{suffix}</p></div>)}</div>
        {candidate.profile_description && <section className="mt-5 rounded-xl border border-teal-100 p-4"><h3 className="font-display text-lg text-teal-700">نبذة مختصرة</h3><p className="mt-2 whitespace-pre-wrap leading-relaxed text-ink">{candidate.profile_description}</p></section>}
        <div className="mt-6 grid grid-cols-2 gap-3"><button type="button" onClick={() => setInterested((value) => !value)} className={`min-h-12 rounded-xl border font-medium ${interested ? 'border-teal-600 bg-teal-600 text-linen' : 'border-teal-100 text-teal-700'}`}>{interested ? 'تم إبداء الاهتمام' : '♡ اهتمام'}</button><button type="button" onClick={() => setSaved((value) => !value)} className={`min-h-12 rounded-xl border font-medium ${saved ? 'border-gold-500 bg-gold-100 text-teal-700' : 'border-teal-100 text-teal-700'}`}>{saved ? 'تم الحفظ' : '☆ حفظ'}</button></div>
        <Button onClick={next} className="mt-3 w-full">المرشح التالي ←</Button>
      </div>
    </Card>
    <nav className="mt-5 grid grid-cols-2 rounded-2xl border border-teal-100 bg-white p-2 text-center text-sm"><span className="rounded-xl bg-teal-50 py-3 font-bold text-teal-700">المرشحون</span><button type="button" onClick={() => navigate('/account')} className="rounded-xl py-3 text-muted">الحساب</button></nav>
  </main>
}
