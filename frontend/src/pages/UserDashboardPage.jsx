// frontend/src/pages/UserDashboardPage.jsx
import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import Card from '../components/Card'
import StatusBadge from '../components/StatusBadge'
import NotificationList from '../components/NotificationList'
import Button from '../components/Button'
import FormField from '../components/FormField'
import config from '../config.json'
import { getUser, getUserNotifications, updateUser, getQuestions } from '../services/userService'

const PLACEHOLDER_NAME = 'متقدم جديد'

function addDays(isoDate, days) {
  if (!isoDate) return null
  const d = new Date(isoDate)
  if (Number.isNaN(d.getTime())) return null
  d.setDate(d.getDate() + days)
  return d
}

function formatDateTime(value) {
  if (!value) return '—'
  const d = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('ar')
}

function displayName(name) {
  if (!name || name.trim() === PLACEHOLDER_NAME) return ''
  return name
}

export default function UserDashboardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(null)
  const [mcqAnswers, setMcqAnswers] = useState(null)
  const [openAnswers, setOpenAnswers] = useState(null)
  const [questions, setQuestions] = useState(null)
  const [visibleNotes, setVisibleNotes] = useState([])
  const [notifications, setNotifications] = useState([])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const justCompleted = Boolean(location.state?.justCompleted)

  useEffect(() => {
    const stored = localStorage.getItem('wefaq_user')
    if (!stored) {
      navigate('/login')
      return
    }
    const { id } = JSON.parse(stored)

    Promise.all([getUser(id), getUserNotifications(id), getQuestions()])
      .then(([userData, notifData, questionsData]) => {
        if (userData.user.needs_onboarding) {
          navigate('/complete-application', { replace: true })
          return
        }
        if (userData.user.status === 'approved' && location.pathname !== '/account') {
          navigate('/matches', { replace: true })
          return
        }
        setUser(userData.user)
        setMcqAnswers(userData.mcq_answers)
        setOpenAnswers(userData.open_answers)
        setVisibleNotes(userData.visible_notes || [])
        setQuestions(questionsData.questions)
        setNotifications(notifData.notifications || [])
        setForm({
          full_name: displayName(userData.user.full_name),
          phone: userData.user.phone || '',
          email: userData.user.email || '',
          birthday: userData.user.birthday || '',
          gender: userData.user.gender || '',
          country: userData.user.country || '',
          guardian_relation: userData.user.guardian_relation || '',
          guardian_phone: userData.user.guardian_phone || ''
        })
      })
      .catch(() => setError('تعذر جلب بيانات الحساب'))
  }, [navigate, location.pathname])

  function handleLogout() {
    localStorage.removeItem('wefaq_user')
    navigate('/')
  }

  function handleFieldChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  async function handleSave() {
    setSaving(true)
    setError('')
    setSaveMsg('')
    try {
      const res = await updateUser(user.id, form)
      setUser(res.user)
      setEditing(false)
      setSaveMsg('تم حفظ التعديلات بنجاح')
      localStorage.setItem('wefaq_user', JSON.stringify({
        id: res.user.id,
        code: res.user.code,
        full_name: res.user.full_name,
        status: res.user.status,
        needs_onboarding: res.user.needs_onboarding
      }))
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (error && !user) {
    return <p className="text-center text-brick-500 py-20">{error}</p>
  }

  if (!user) {
    return <p className="text-center text-muted py-20">جارٍ التحميل...</p>
  }

  const expectedResponse = addDays(user.created_at, 3)

  return (
    <div className="max-w-3xl mx-auto px-6 py-12 space-y-6">
      {justCompleted && (
        <div className="bg-teal-50 border border-teal-100 rounded-xl px-4 py-3 text-sm text-teal-700">
          تم إرسال طلبك بنجاح. يمكنك متابعة حالته وتفاصيله من هنا.
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <div className="flex items-center justify-between mb-4 gap-3">
            <h1 className="font-display text-2xl text-teal-700">مرحباً، {user.full_name}</h1>
            <StatusBadge status={user.status} />
          </div>
          <p className="text-muted text-sm mb-2">كود الحساب: {user.code}</p>

          <div className="text-sm space-y-1 mb-4 bg-teal-50 rounded-xl p-3">
            <p>
              <span className="text-muted">تاريخ تقديم الطلب:</span>{' '}
              {formatDateTime(user.created_at)}
            </p>
            <p>
              <span className="text-muted">الرد المتوقع:</span>{' '}
              {formatDateTime(expectedResponse)}
            </p>
          </div>

          {user.status_reason && (
            <p className="text-sm text-ink bg-teal-50 rounded-xl p-3 mt-4">{user.status_reason}</p>
          )}

          {error && <p className="text-brick-500 text-sm mt-3">{error}</p>}
          {saveMsg && <p className="text-teal-700 text-sm mt-3">{saveMsg}</p>}

          {editing ? (
            <div className="mt-6 space-y-3">
              {config.personalFields.map((field) => (
                <FormField
                  key={field.name}
                  field={field}
                  value={form[field.name] || ''}
                  onChange={handleFieldChange}
                />
              ))}
              <div className="flex gap-3 pt-2">
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? 'جارٍ الحفظ...' : 'حفظ التعديلات'}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setEditing(false)
                    setError('')
                    setForm({
                      full_name: displayName(user.full_name),
                      phone: user.phone || '',
                      email: user.email || '',
                      birthday: user.birthday || '',
                      gender: user.gender || '',
                      country: user.country || '',
                      guardian_relation: user.guardian_relation || '',
                      guardian_phone: user.guardian_phone || ''
                    })
                  }}
                >
                  إلغاء
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-6 grid sm:grid-cols-2 gap-2 text-sm">
              <p><span className="text-muted">الجنس:</span> {user.gender || '—'}</p>
              <p><span className="text-muted">الدولة:</span> {user.country || '—'}</p>
              <p><span className="text-muted">تاريخ الميلاد:</span> {user.birthday || '—'}</p>
              <p><span className="text-muted">الجوال:</span> {user.phone || '—'}</p>
              <p><span className="text-muted">البريد:</span> {user.email || '—'}</p>
              <p><span className="text-muted">ولي الأمر:</span> {user.guardian_relation || '—'}</p>
            </div>
          )}

          <div className="flex gap-3 mt-6 flex-wrap">
            {user.status === 'approved' && <Button onClick={() => navigate('/matches')}>العودة إلى المرشحين</Button>}
            {!editing && (
              <Button onClick={() => { setEditing(true); setSaveMsg('') }}>
                تعديل البيانات
              </Button>
            )}
            <Button variant="secondary" onClick={handleLogout}>
              تسجيل الخروج
            </Button>
          </div>
        </Card>

        <div className="space-y-6">
          <Card>
            <h2 className="font-display text-lg text-teal-700 mb-4">الإشعارات</h2>
            <NotificationList notifications={notifications} />
          </Card>

          <Card>
            <h2 className="font-display text-lg text-teal-700 mb-4">رسائل الإداري</h2>
            {visibleNotes.length === 0 ? (
              <p className="text-muted text-sm">لا توجد رسائل مرئية حالياً</p>
            ) : (
              <ul className="space-y-2">
                {visibleNotes.map((n) => (
                  <li key={n.id} className="text-sm bg-teal-50 rounded-lg p-3">
                    <p>{n.note_text}</p>
                    <p className="text-xs text-muted mt-1">
                      {n.admin_name || 'الإدارة'}
                      {n.created_at ? ` · ${formatDateTime(n.created_at)}` : ''}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <Card>
        <h2 className="font-display text-xl text-teal-700 mb-2">تفاصيل طلبك</h2>
        <p className="text-muted text-sm mb-6">ملخص ما أرسلته لفريق المراجعة.</p>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-display text-base text-teal-700 mb-3">أسئلة الاختيار</h3>
            {mcqAnswers ? (
              <ul className="space-y-2 text-sm">
                {(questions?.mcq || []).map((q) => (
                  <li key={q.id} className="bg-teal-50 rounded-lg p-3">
                    <p className="text-muted mb-1">{q.question}</p>
                    <p className="text-ink">{mcqAnswers[`q${q.id}`] || '—'}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted text-sm">لا توجد إجابات بعد</p>
            )}
          </div>

          <div>
            <h3 className="font-display text-base text-teal-700 mb-3">الأسئلة المفتوحة</h3>
            {openAnswers ? (
              <ul className="space-y-2 text-sm">
                {(questions?.open || []).map((q, idx) => (
                  <li key={idx} className="bg-teal-50 rounded-lg p-3">
                    <p className="text-muted mb-1">{q}</p>
                    <p className="text-ink whitespace-pre-wrap">{openAnswers[`q${idx + 1}`] || '—'}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted text-sm">لا توجد إجابات بعد</p>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
