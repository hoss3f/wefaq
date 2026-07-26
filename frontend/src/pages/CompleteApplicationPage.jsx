// frontend/src/pages/CompleteApplicationPage.jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import config from '../config.json'
import Card from '../components/Card'
import Button from '../components/Button'
import FormField from '../components/FormField'
import ProgressSteps from '../components/ProgressSteps'
import { getQuestions, getUser, completeApplication } from '../services/userService'

const STEPS = config.registrationSteps
const PLACEHOLDER_NAME = 'متقدم جديد'

function displayName(name) {
  if (!name || name.trim() === PLACEHOLDER_NAME) return ''
  return name
}

export default function CompleteApplicationPage() {
  const navigate = useNavigate()
  const [userId, setUserId] = useState(null)
  const [userCode, setUserCode] = useState('')
  const [stepIndex, setStepIndex] = useState(0)
  const [questions, setQuestions] = useState(null)
  const [personal, setPersonal] = useState({})
  const [mcqAnswers, setMcqAnswers] = useState({})
  const [openAnswers, setOpenAnswers] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [booting, setBooting] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('wefaq_user')
    if (!stored) {
      navigate('/login')
      return
    }

    const session = JSON.parse(stored)
    setUserId(session.id)
    setUserCode(session.code || '')

    Promise.all([getUser(session.id), getQuestions()])
      .then(([userData, questionsData]) => {
        if (!userData.user.needs_onboarding) {
          navigate('/dashboard', { replace: true })
          return
        }

        const u = userData.user
        setPersonal({
          full_name: displayName(u.full_name),
          phone: u.phone || '',
          email: u.email || '',
          birthday: u.birthday || '',
          gender: u.gender || '',
          country: u.country || '',
          guardian_relation: u.guardian_relation || '',
          guardian_phone: u.guardian_phone || ''
        })
        if (userData.mcq_answers) setMcqAnswers(userData.mcq_answers)
        if (userData.open_answers) setOpenAnswers(userData.open_answers)
        setQuestions(questionsData.questions)
      })
      .catch(() => setError('تعذر تحميل بيانات الطلب'))
      .finally(() => setBooting(false))
  }, [navigate])

  function handlePersonalChange(name, value) {
    setPersonal((prev) => ({ ...prev, [name]: value }))
  }

  function handleMcqChange(questionKey, value) {
    setMcqAnswers((prev) => ({ ...prev, [questionKey]: value }))
  }

  function handleOpenChange(questionKey, value) {
    setOpenAnswers((prev) => ({ ...prev, [questionKey]: value }))
  }

  function goNext() {
    setError('')
    if (stepIndex === 0) {
      const missing = config.personalFields.filter((f) => f.required && !personal[f.name]?.toString().trim())
      if (missing.length > 0) {
        setError('الرجاء تعبئة جميع الحقول المطلوبة')
        return
      }
      if (!personal.full_name || personal.full_name.trim() === PLACEHOLDER_NAME) {
        setError('الرجاء إدخال اسمك الكامل')
        return
      }
    }
    if (stepIndex === 1) {
      const unanswered = (questions?.mcq || []).some((q) => !mcqAnswers[`q${q.id}`])
      if (unanswered) {
        setError('الرجاء الإجابة على جميع أسئلة الاختيار')
        return
      }
    }
    setStepIndex((i) => Math.min(i + 1, STEPS.length - 1))
  }

  function goBack() {
    setError('')
    setStepIndex((i) => Math.max(i - 1, 0))
  }

  async function handleFinalSubmit() {
    setLoading(true)
    setError('')
    try {
      const res = await completeApplication(userId, personal, mcqAnswers, openAnswers)
      localStorage.setItem('wefaq_user', JSON.stringify({
        id: res.user.id,
        code: res.user.code,
        full_name: res.user.full_name,
        status: res.user.status,
        needs_onboarding: false
      }))
      navigate('/dashboard', { replace: true, state: { justCompleted: true } })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (booting) {
    return <p className="text-center text-muted py-20">جارٍ تجهيز طلبك...</p>
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="mb-6 text-center">
        <h1 className="font-display text-2xl text-teal-700 mb-2">إكمال طلبك</h1>
        <p className="text-muted text-sm">
          مرحباً بك في وِفاق. عبّئ بياناتك ثم أجب عن الأسئلة لإرسال طلبك.
          {userCode ? <> كودك: <span className="text-gold-700 font-medium">{userCode}</span></> : null}
        </p>
      </div>

      <ProgressSteps steps={STEPS} currentIndex={stepIndex} />

      <Card>
        {stepIndex === 0 && (
          <div>
            <h2 className="font-display text-xl text-teal-700 mb-2">البيانات الشخصية</h2>
            <p className="text-muted text-sm mb-4">هذه صفة حسابك — أدخل بياناتك الحقيقية بدقة.</p>
            {config.personalFields.map((field) => (
              <FormField
                key={field.name}
                field={field}
                value={personal[field.name]}
                onChange={handlePersonalChange}
              />
            ))}
          </div>
        )}

        {stepIndex === 1 && (
          <div>
            <h2 className="font-display text-xl text-teal-700 mb-4">أسئلة الاختيار من متعدد</h2>
            {questions?.mcq.map((q) => (
              <div key={q.id} className="mb-5">
                <p className="mb-2 font-medium">{q.question}</p>
                <div className="flex flex-wrap gap-2">
                  {q.options.map((option) => (
                    <button
                      key={option}
                      type="button"
                      onClick={() => handleMcqChange(`q${q.id}`, option)}
                      className={`px-4 py-2 rounded-xl border text-sm transition-colors
                        ${mcqAnswers[`q${q.id}`] === option
                          ? 'bg-teal-600 text-linen border-teal-600'
                          : 'border-teal-100 text-ink hover:bg-teal-50'}`}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {stepIndex === 2 && (
          <div>
            <h2 className="font-display text-xl text-teal-700 mb-4">أسئلة مفتوحة</h2>
            <p className="text-muted text-sm mb-4">أجب بما يعكس شخصيتك بصدق — لا توجد إجابات خاطئة.</p>
            {questions?.open.map((question, index) => (
              <label key={index} className="block mb-4">
                <span className="block mb-1 text-sm font-medium">{question}</span>
                <textarea
                  className="w-full rounded-xl border border-teal-100 px-4 py-3 bg-linen focus-visible:outline-2 focus-visible:outline-gold-500"
                  rows={3}
                  value={openAnswers[`q${index + 1}`] || ''}
                  onChange={(e) => handleOpenChange(`q${index + 1}`, e.target.value)}
                />
              </label>
            ))}
          </div>
        )}

        {stepIndex === 3 && (
          <div>
            <h2 className="font-display text-xl text-teal-700 mb-4">مراجعة الطلب</h2>
            <p className="text-muted text-sm mb-4">
              راجع ملخص طلبك ثم أرسله. سيظهر لك بعد الإرسال كامل التفاصيل في لوحة حسابك.
            </p>
            <div className="space-y-4 text-sm">
              <div className="bg-teal-50 rounded-xl p-4 space-y-1">
                <p className="font-medium text-teal-700 mb-2">البيانات الشخصية</p>
                <p><span className="text-muted">الاسم:</span> {personal.full_name}</p>
                <p><span className="text-muted">الجنس:</span> {personal.gender}</p>
                <p><span className="text-muted">تاريخ الميلاد:</span> {personal.birthday}</p>
                <p><span className="text-muted">الجوال:</span> {personal.phone}</p>
                <p><span className="text-muted">البريد:</span> {personal.email}</p>
                <p><span className="text-muted">الدولة:</span> {personal.country}</p>
              </div>
              <div className="bg-teal-50 rounded-xl p-4 space-y-1">
                <p className="font-medium text-teal-700 mb-2">أسئلة الاختيار</p>
                {(questions?.mcq || []).map((q) => (
                  <p key={q.id}>
                    <span className="text-muted">{q.question}:</span> {mcqAnswers[`q${q.id}`] || '—'}
                  </p>
                ))}
              </div>
              <div className="bg-teal-50 rounded-xl p-4 space-y-2">
                <p className="font-medium text-teal-700 mb-2">الأسئلة المفتوحة</p>
                {(questions?.open || []).map((q, idx) => (
                  <div key={idx}>
                    <p className="text-muted">{q}</p>
                    <p className="text-ink whitespace-pre-wrap mt-1">{openAnswers[`q${idx + 1}`] || '—'}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {error && <p className="text-brick-500 text-sm mt-4">{error}</p>}

        <div className="flex justify-between mt-8 gap-3">
          <Button variant="secondary" onClick={goBack} disabled={stepIndex === 0 || loading}>
            السابق
          </Button>

          {stepIndex < STEPS.length - 1 ? (
            <Button onClick={goNext}>التالي</Button>
          ) : (
            <Button onClick={handleFinalSubmit} disabled={loading}>
              {loading ? 'جارٍ الإرسال...' : 'إرسال الطلب'}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}
