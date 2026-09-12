import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ApprovedUserNav from '../components/ApprovedUserNav'
import Button from '../components/Button'
import FormField from '../components/FormField'
import NotificationList from '../components/NotificationList'
import StatusBadge from '../components/StatusBadge'
import config from '../config.json'
import { getQuestions, getUser, getUserNotifications, updateUser } from '../services/userService'

const PLACEHOLDER_NAME = 'متقدم جديد'

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('ar')
}

function addDays(value, days) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  date.setDate(date.getDate() + days)
  return date
}

function displayName(name) {
  return !name || name.trim() === PLACEHOLDER_NAME ? '' : name
}

export default function UserDashboardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(null)
  const [mcqAnswers, setMcqAnswers] = useState(null)
  const [openAnswers, setOpenAnswers] = useState(null)
  const [profileDetails, setProfileDetails] = useState({})
  const [questions, setQuestions] = useState(null)
  const [visibleNotes, setVisibleNotes] = useState([])
  const [notifications, setNotifications] = useState([])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')

  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem('wefaq_user') || 'null')
    if (!stored) return navigate('/login', { replace: true })
    Promise.all([getUser(stored.id), getUserNotifications(stored.id), getQuestions()])
      .then(([userData, notificationData, questionData]) => {
        if (userData.user.needs_onboarding) return navigate('/complete-application', { replace: true })
        if (userData.user.status === 'approved' && location.pathname !== '/account') return navigate('/matches', { replace: true })
        setUser(userData.user)
        setMcqAnswers(userData.mcq_answers)
        setOpenAnswers(userData.open_answers)
        setProfileDetails(userData.profile_details || {})
        setVisibleNotes(userData.visible_notes || [])
        setNotifications(notificationData.notifications || [])
        setQuestions(questionData.questions)
        setFormFromUser(userData.user)
      })
      .catch((err) => setError(err.message || 'تعذر جلب بيانات الحساب'))
  }, [navigate, location.pathname])

  function setFormFromUser(value) {
    setForm({
      full_name: displayName(value.full_name), phone: value.phone || '', email: value.email || '',
      birthday: value.birthday || '', gender: value.gender || '', country: value.country || '',
      guardian_relation: value.guardian_relation || '', guardian_phone: value.guardian_phone || '',
    })
  }

  async function handleSave() {
    setSaving(true)
    setError('')
    setSaveMsg('')
    try {
      const result = await updateUser(user.id, form)
      setUser(result.user)
      setEditing(false)
      setSaveMsg('تم حفظ التعديلات بنجاح.')
      localStorage.setItem('wefaq_user', JSON.stringify({ id: result.user.id, code: result.user.code, full_name: result.user.full_name, status: result.user.status, needs_onboarding: result.user.needs_onboarding }))
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  function logout() {
    localStorage.removeItem('wefaq_user')
    navigate('/')
  }

  if (error && !user) return <p dir="rtl" className="py-20 text-center text-brick-500">{error}</p>
  if (!user) return <p dir="rtl" className="py-20 text-center text-muted">جارٍ تحميل الحساب...</p>

  const answerSteps = (questions?.onboarding?.steps || []).filter((step) => !['full_name', 'gender', 'birthday', 'country', 'contact'].includes(step.key))
  const approved = user.status === 'approved'

  return (
    <main dir="rtl" className={`mx-auto max-w-3xl px-4 pt-7 sm:px-6 ${approved ? 'pb-28' : 'pb-12'}`}>
      {location.state?.justCompleted && <p className="mb-5 rounded-xl border border-teal-100 bg-teal-50 px-4 py-3 text-sm text-teal-700">تم إرسال طلبك بنجاح. يمكنك متابعة حالته من هنا.</p>}

      <header className="border-b border-teal-100 pb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="text-sm text-muted">حسابك في وِفاق</p><h1 className="mt-1 font-display text-3xl text-teal-700">{user.full_name}</h1><p className="mt-2 text-sm text-muted">رمز الحساب: <span dir="ltr" className="font-medium text-ink">{user.code}</span></p></div>
          <StatusBadge status={user.status} />
        </div>
        <div className="mt-5 flex flex-wrap gap-x-8 gap-y-2 text-sm"><p><span className="text-muted">تاريخ التقديم:</span> {formatDateTime(user.created_at)}</p>{!approved && <p><span className="text-muted">الرد المتوقع:</span> {formatDateTime(addDays(user.created_at, 3))}</p>}</div>
        {user.status_reason && <p className="mt-4 rounded-xl bg-teal-50 px-4 py-3 text-sm">{user.status_reason}</p>}
      </header>

      {(error || saveMsg) && <p className={`mt-5 rounded-xl px-4 py-3 text-sm ${error ? 'bg-brick-100 text-brick-500' : 'bg-teal-50 text-teal-700'}`}>{error || saveMsg}</p>}

      <section className="py-7 border-b border-teal-100">
        <div className="flex items-center justify-between gap-3"><div><h2 className="font-display text-2xl text-teal-700">البيانات الشخصية</h2><p className="mt-1 text-sm text-muted">بيانات التواصل والحساب الأساسية.</p></div>{!editing && <button type="button" onClick={() => { setEditing(true); setSaveMsg('') }} className="min-h-11 rounded-xl border border-teal-100 px-4 text-sm font-medium text-teal-700">تعديل</button>}</div>
        {editing ? <div className="mt-5 space-y-3">{config.personalFields.map((field) => <FormField key={field.name} field={field} value={form[field.name] || ''} onChange={(name, value) => setForm((current) => ({ ...current, [name]: value }))} />)}<div className="flex gap-2 pt-2"><Button onClick={handleSave} disabled={saving}>{saving ? 'جارٍ الحفظ...' : 'حفظ التعديلات'}</Button><Button variant="secondary" onClick={() => { setEditing(false); setError(''); setFormFromUser(user) }}>إلغاء</Button></div></div> : (
          <dl className="mt-5 grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2"><Info label="الجنس" value={user.gender} /><Info label="الدولة" value={user.country} /><Info label="تاريخ الميلاد" value={user.birthday} /><Info label="رقم الجوال" value={user.phone} /><Info label="البريد الإلكتروني" value={user.email} /><Info label="صلة ولي الأمر" value={user.guardian_relation} /><Info label="رقم ولي الأمر" value={user.guardian_phone} /></dl>
        )}
      </section>

      <section className="grid gap-7 border-b border-teal-100 py-7 md:grid-cols-2">
        <div><h2 className="font-display text-xl text-teal-700">الإشعارات</h2><div className="mt-4"><NotificationList notifications={notifications} /></div></div>
        <div><h2 className="font-display text-xl text-teal-700">رسائل الإدارة</h2>{visibleNotes.length ? <ul className="mt-4 space-y-3">{visibleNotes.map((note) => <li key={note.id} className="border-r-2 border-gold-500 pr-3 text-sm"><p>{note.note_text}</p><p className="mt-1 text-xs text-muted">{note.admin_name || 'الإدارة'}{note.created_at ? ` · ${formatDateTime(note.created_at)}` : ''}</p></li>)}</ul> : <p className="mt-4 text-sm text-muted">لا توجد رسائل من الإدارة حالياً.</p>}</div>
      </section>

      <details className="group border-b border-teal-100 py-7">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between"><div><h2 className="font-display text-2xl text-teal-700">إجابات الطلب</h2><p className="mt-1 text-sm text-muted">راجع المعلومات التي قدمتها عند التسجيل.</p></div><span className="text-2xl text-gold-700 transition-transform group-open:rotate-45">＋</span></summary>
        <div className="mt-6 space-y-7">
          {answerSteps.length > 0 && <AnswerGroup title="بيانات الملف" items={answerSteps.map((step) => [step.title, displayAnswer(profileDetails[step.key])])} />}
          {mcqAnswers && <AnswerGroup title="أسئلة الاختيار" items={(questions?.mcq || []).filter((question) => question.active !== false).map((question) => [question.question, mcqAnswers[`q${question.id}`]])} />}
          {openAnswers && <AnswerGroup title="الأسئلة المفتوحة" items={(questions?.open || []).map((question, index) => [question, openAnswers[`q${index + 1}`]])} />}
        </div>
      </details>

      <div className="pt-7"><Button variant="secondary" onClick={logout}>تسجيل الخروج</Button></div>
      {approved && <ApprovedUserNav />}
    </main>
  )
}

function Info({ label, value }) {
  return <div><dt className="text-xs text-muted">{label}</dt><dd className="mt-1 text-ink">{value || '—'}</dd></div>
}

function AnswerGroup({ title, items }) {
  return <section><h3 className="font-display text-lg text-teal-700">{title}</h3><dl className="mt-3 divide-y divide-teal-50">{items.map(([label, value], index) => <div key={`${label}-${index}`} className="py-3 text-sm"><dt className="text-muted">{label}</dt><dd className="mt-1 whitespace-pre-wrap text-ink">{value || '—'}</dd></div>)}</dl></section>
}

function displayAnswer(value) {
  if (value == null || value === '') return '—'
  if (typeof value !== 'object') return String(value)
  const labels = {
    age_min: 'الحد الأدنى للعمر', age_max: 'الحد الأقصى للعمر', height_min: 'الحد الأدنى للطول',
    height_max: 'الحد الأقصى للطول', marital_preference: 'الحالة الاجتماعية المفضلة',
    ethnicity_preference: 'لون البشرة المفضل', nationality_preference: 'الجنسية المفضلة',
  }
  return Object.entries(value).map(([key, entry]) => `${labels[key] || key}: ${Array.isArray(entry) ? entry.join('، ') : entry}`).join(' · ')
}
