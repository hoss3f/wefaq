// frontend/src/pages/RegisterPage.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import config from '../config.json'
import Card from '../components/Card'
import Button from '../components/Button'
import FormField from '../components/FormField'
import ProgressSteps from '../components/ProgressSteps'
import { getQuestions, registerUser, saveAnswers } from '../services/userService'

const STEPS = config.registrationSteps

export default function RegisterPage() {
  const navigate = useNavigate()
  const [stepIndex, setStepIndex] = useState(0)
  const [questions, setQuestions] = useState(null)
  const [personal, setPersonal] = useState({})
  const [mcqAnswers, setMcqAnswers] = useState({})
  const [openAnswers, setOpenAnswers] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [resultCode, setResultCode] = useState(null)

  useEffect(() => {
    getQuestions()
      .then((data) => setQuestions(data.questions))
      .catch(() => setError('تعذر تحميل الأسئلة، حاول تحديث الصفحة'))
  }, [])

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
      const missing = config.personalFields.filter((f) => f.required && !personal[f.name])
      if (missing.length > 0) {
        setError('الرجاء تعبئة جميع الحقول المطلوبة')
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
      const registerRes = await registerUser(personal)
      const userId = registerRes.user.id

      await saveAnswers(userId, mcqAnswers, openAnswers)

      setResultCode(registerRes.user.code)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (resultCode) {
    return (
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <Card>
          <h1 className="font-display text-2xl text-teal-700 mb-4">تم إرسال طلبك بنجاح</h1>
          <p className="text-muted mb-4">احتفظ بهذا الكود لتسجيل الدخول لاحقاً ومتابعة حالة طلبك</p>
          <p className="text-3xl font-bold text-gold-700 mb-6">{resultCode}</p>
          <Button onClick={() => navigate('/login')} className="w-full">
            الذهاب لتسجيل الدخول
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <ProgressSteps steps={STEPS} currentIndex={stepIndex} />

      <Card>
        {stepIndex === 0 && (
          <div>
            <h2 className="font-display text-xl text-teal-700 mb-4">البيانات الشخصية</h2>
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
                      className={`px-4 py-2 rounded-xl border text-sm
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
              تأكد من صحة بياناتك قبل الإرسال. سيراجع فريقنا طلبك خلال أيام قليلة.
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

        <div className="flex justify-between mt-8">
          <Button variant="secondary" onClick={goBack} disabled={stepIndex === 0}>
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
