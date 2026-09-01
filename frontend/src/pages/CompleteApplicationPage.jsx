import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getQuestions, getUser, completeApplication } from '../services/userService'

function ChoiceCards({ options, value, onChange, chips = false }) {
  return <div className={chips ? 'flex flex-wrap gap-2' : 'space-y-3'}>{options.map((item) => <button key={item} type="button" onClick={() => onChange(item)} className={chips ? `rounded-full border px-4 py-2 font-medium transition-colors ${value === item ? 'border-teal-600 bg-teal-600 text-linen' : 'border-teal-100 bg-white text-ink hover:bg-teal-50'}` : `flex min-h-20 w-full items-center justify-between rounded-2xl border-2 px-5 text-right transition-colors ${value === item ? 'border-gold-500 bg-gold-100/40 text-teal-700' : 'border-teal-100 bg-white text-ink hover:border-teal-300'}`}><b>{item}</b>{!chips && <span className={`h-6 w-6 rounded-full border ${value === item ? 'border-teal-600 bg-teal-600 shadow-[inset_0_0_0_5px_#FAF8F4]' : 'border-teal-300'}`} />}</button>)}</div>
}

function SearchSelector({ question, value, onChange, otherOption }) {
  const [query, setQuery] = useState('')
  const matches = (question.options || []).filter((item) => item.toLowerCase().includes(query.trim().toLowerCase()))
  const choices = [...matches.filter((item) => item !== otherOption), otherOption]
  return <div><div className="flex items-center gap-3 border-b border-teal-100 py-3 text-muted"><span className="text-2xl">⌕</span><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder={question.placeholder} className="w-full bg-transparent text-lg outline-none placeholder:text-muted/70" /></div><div className="mt-5 max-h-80 space-y-1 overflow-y-auto">{choices.map((item) => <button key={item} type="button" onClick={() => onChange(item)} className={`flex w-full items-center justify-between rounded-xl px-3 py-3 text-right text-lg transition-colors ${value === item ? 'bg-teal-50 font-bold text-teal-700' : 'text-ink hover:bg-linen'}`}>{item}<span className={`h-5 w-5 rounded-md border ${value === item ? 'border-gold-500 bg-gold-500' : 'border-teal-100'}`} /></button>)}</div></div>
}

function RangeField({ field, details, setDetail }) {
  const min = details[field.min_key] ?? field.default_min
  const max = details[field.max_key] ?? field.default_max
  const range = field.max - field.min
  return <div className="rounded-2xl bg-teal-50 p-5"><div className="mb-5 flex justify-between font-bold text-teal-700"><span>الحد الأدنى: {min} {field.unit}</span><span>الحد الأقصى: {max} {field.unit}</span></div><div dir="ltr" className="dual-range" style={{ '--min': `${((min - field.min) / range) * 100}%`, '--max': `${((max - field.min) / range) * 100}%` }}><div className="dual-range__track" /><input aria-label="الحد الأدنى للعمر" type="range" min={field.min} max={field.max} value={min} onChange={(event) => setDetail(field.min_key, Math.min(+event.target.value, max))} /><input aria-label="الحد الأقصى للعمر" type="range" min={field.min} max={field.max} value={max} onChange={(event) => setDetail(field.max_key, Math.max(+event.target.value, min))} /></div></div>
}

function SliderField({ question, value, onChange }) {
  const selected = Number(value || question.default || question.min)
  return <div className="rounded-2xl bg-teal-50 p-5"><div className="mb-5 text-center"><strong className="text-4xl text-teal-700">{selected}</strong><span className="mr-2 text-lg text-muted">{question.suffix}</span></div><div dir="ltr" className="single-range"><input aria-label={question.title} type="range" min={question.min} max={question.max} value={selected} onChange={(event) => onChange(question, +event.target.value)} /></div><div className="mt-3 flex justify-between text-sm text-muted"><span>{question.min} {question.suffix}</span><span>{question.max} {question.suffix}</span></div></div>
}

function nameValidation(value) {
  const name = (value || '').trim()
  if (!name) return 'يرجى إدخال الاسم الكامل.'
  if (!/^[\u0621-\u064Aa-zA-Z][\u0621-\u064Aa-zA-Z\s'-]{1,99}$/.test(name)) return 'يرجى إدخال اسم صحيح.'
  return ''
}

export default function CompleteApplicationPage() {
  const navigate = useNavigate()
  const [userId, setUserId] = useState(null)
  const [questionSet, setQuestionSet] = useState(null)
  const [personal, setPersonal] = useState({})
  const [details, setDetails] = useState({})
  const [mcqAnswers, setMcqAnswers] = useState({})
  const [answers, setAnswers] = useState({})
  const [index, setIndex] = useState(0)
  const [error, setError] = useState('')
  const [nameError, setNameError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const session = JSON.parse(localStorage.getItem('wefaq_user') || 'null')
    if (!session) return navigate('/login')
    setUserId(session.id)
    Promise.all([getUser(session.id), getQuestions()]).then(([data, questionData]) => {
      if (!data.user.needs_onboarding) return navigate('/dashboard', { replace: true })
      setPersonal({ full_name: data.user.full_name === 'متقدم جديد' ? '' : data.user.full_name || '', birthday: data.user.birthday || '', gender: data.user.gender || '', country: data.user.country || '' })
      const preferenceQuestion = questionData.questions.onboarding?.steps.find((item) => item.type === 'preferences')
      const rangeDefaults = Object.fromEntries((preferenceQuestion?.fields || [])
        .filter((field) => field.type === 'range')
        .flatMap((field) => [[field.min_key, field.default_min], [field.max_key, field.default_max]]))
      setDetails({ ...rangeDefaults, ...(data.profile_details || {}) })
      setMcqAnswers(data.mcq_answers || {})
      setAnswers(data.open_answers || {})
      setQuestionSet(questionData.questions)
    }).catch(() => setError('تعذر تحميل بيانات الطلب'))
  }, [navigate])

  const onboarding = questionSet?.onboarding
  const steps = useMemo(() => {
    if (!onboarding) return []
    const configured = onboarding.steps.filter((item) => !item.show_if || item.show_if.every((rule) => details[rule.key] === rule.equals))
    const matching = (questionSet.mcq || []).filter((item) => item.matching).map((item) => ({
      key: `q${item.id}`, storage: 'mcq', type: 'choice', title: item.question, options: item.options, required: true,
    }))
    const open = (questionSet.open || []).map((title, position) => ({ key: `open_${position + 1}`, type: 'textarea', title, placeholder: onboarding.ui.open_placeholder, required: true, openNumber: position + 1 }))
    return [...configured, ...matching, ...open]
  }, [onboarding, details, questionSet])
  const question = steps[index]
  const ui = onboarding?.ui || {}
  const getValue = (item) => item.storage === 'personal' ? personal[item.key] : item.storage === 'mcq' ? mcqAnswers[item.key] : details[item.key]
  const setValue = (item, value) => {
    if (item.storage === 'personal') setPersonal((old) => ({ ...old, [item.key]: value }))
    else if (item.storage === 'mcq') setMcqAnswers((old) => ({ ...old, [item.key]: value }))
    else setDetails((old) => ({ ...old, [item.key]: value }))
    if (item.key === 'full_name') setNameError(nameValidation(value))
  }
  const setDetail = (key, value) => setDetails((old) => ({ ...old, [key]: value }))

  function valid() {
    if (!question?.required) return true
    if (question.type === 'preferences') return question.fields.filter((field) => field.type !== 'range').every((field) => !!details[field.key])
    if (question.openNumber) return !!answers[`q${question.openNumber}`]?.trim()
    if (question.key === 'full_name') return !nameValidation(getValue(question))
    return !!getValue(question)?.toString().trim()
  }
  async function submit() {
    setLoading(true)
    try {
      const result = await completeApplication(userId, { ...personal, profile_details: details }, mcqAnswers, answers)
      localStorage.setItem('wefaq_user', JSON.stringify({ id: result.user.id, code: result.user.code, full_name: result.user.full_name, status: result.user.status, needs_onboarding: false }))
      navigate('/dashboard', { replace: true })
    } catch (requestError) { setError(requestError.message) } finally { setLoading(false) }
  }
  function next() {
    if (question?.key === 'full_name') setNameError(nameValidation(getValue(question)))
    if (!valid()) return setError(ui.validation_error)
    setError('')
    if (index === steps.length - 1) return submit()
    setIndex((current) => current + 1)
  }
  function renderPreferences() {
    return <div className="space-y-7">{question.fields.map((field) => <section key={field.key}><b className="text-teal-700">{field.title}</b><div className="mt-3">{field.type === 'range' ? <RangeField field={field} details={details} setDetail={setDetail} /> : field.type === 'chips' ? <ChoiceCards chips options={field.options} value={details[field.key]} onChange={(value) => setDetail(field.key, value)} /> : field.type === 'search' ? <SearchSelector question={field} value={details[field.key]} onChange={(value) => setDetail(field.key, value)} otherOption={onboarding.other_option} /> : <input value={details[field.key] || ''} onChange={(event) => setDetail(field.key, event.target.value)} placeholder={field.placeholder} className="w-full border-b border-teal-100 bg-transparent py-3 outline-none focus:border-gold-500" />}</div></section>)}</div>
  }
  function renderQuestion() {
    const value = getValue(question)
    if (question.type === 'gender') return <div className="grid grid-cols-2 gap-4">{question.options.map((option) => <button key={option} type="button" onClick={() => setValue(question, option)} className={`rounded-2xl border-2 p-7 transition-colors ${value === option ? 'border-gold-500 bg-gold-100/50 text-teal-700' : 'border-teal-100 bg-white text-ink hover:border-teal-300'}`}><span className="text-5xl">{option === question.options[0] ? '◐' : '◑'}</span><b className="mt-5 block text-xl">{option}</b></button>)}</div>
    if (question.type === 'choice') return <ChoiceCards options={question.options} value={value} onChange={(selected) => setValue(question, selected)} />
    if (question.type === 'chips') return <ChoiceCards chips options={question.options} value={value} onChange={(selected) => setValue(question, selected)} />
    if (question.type === 'search') return <SearchSelector question={question} value={value} onChange={(selected) => setValue(question, selected)} otherOption={onboarding.other_option} />
    if (question.type === 'date') return <input autoFocus type="date" value={value || ''} onChange={(event) => setValue(question, event.target.value)} className="w-full rounded-xl border border-teal-100 bg-white p-5 text-xl outline-none focus:border-gold-500" />
    if (question.type === 'slider') return <SliderField question={question} value={value} onChange={setValue} />
    if (question.type === 'number') return <div className="relative"><input autoFocus type="number" min="1" value={value || ''} onChange={(event) => setValue(question, event.target.value)} className="w-full border-b-2 border-teal-100 bg-transparent py-4 text-5xl font-bold text-teal-700 outline-none focus:border-gold-500" />{question.suffix && <span className="absolute bottom-5 left-0 text-xl text-muted">{question.suffix}</span>}</div>
    if (question.type === 'textarea') return <textarea autoFocus rows="6" value={answers[`q${question.openNumber}`] || ''} onChange={(event) => setAnswers((old) => ({ ...old, [`q${question.openNumber}`]: event.target.value }))} placeholder={question.placeholder} className="w-full border-b-2 border-teal-100 bg-transparent py-3 text-xl leading-relaxed outline-none focus:border-gold-500" />
    if (question.type === 'preferences') return renderPreferences()
    return <><input autoFocus value={value || ''} onChange={(event) => setValue(question, event.target.value)} placeholder={question.placeholder || (question.key === 'full_name' ? 'اكتب الاسم الكامل هنا...' : '')} className="w-full border-b-2 border-teal-100 bg-transparent py-4 text-2xl outline-none placeholder:text-muted/60 focus:border-gold-500" />{question.key === 'full_name' && nameError && <p className="mt-3 text-sm text-brick-500">{nameError}</p>}</>
  }

  if (!question) return <p className="py-20 text-center text-muted">{ui.loading || '...'}</p>
  return <main dir="rtl" className="min-h-[calc(100vh-64px)] bg-linen text-ink"><div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-xl flex-col px-6 pb-8 pt-7"><header dir="ltr" className="flex items-center gap-5"><button type="button" aria-label={ui.back} disabled={index === 0} onClick={() => setIndex((current) => Math.max(0, current - 1))} className="text-3xl text-teal-700 disabled:text-teal-100">‹</button><div className="h-1 flex-1 overflow-hidden rounded-full bg-teal-100"><div className="h-full rounded-full bg-gold-500 transition-all" style={{ width: `${((index + 1) / steps.length) * 100}%` }} /></div><span className="font-display text-xl text-teal-700">و</span></header><div className="flex-1 pt-16"><p className="mb-3 text-sm text-muted">{index + 1} {ui.progress} {steps.length}</p><h1 className="font-display text-3xl font-bold leading-tight text-teal-700 sm:text-4xl">{question.title}</h1>{question.description && <p className="mt-3 text-lg leading-relaxed text-muted">{question.description}</p>}<div className="mt-10">{renderQuestion()}</div>{error && <p className="mt-4 text-sm text-brick-500">{error}</p>}</div><button type="button" onClick={next} disabled={loading} className="mt-8 w-full rounded-xl bg-teal-600 px-6 py-4 text-lg font-bold text-linen transition-colors hover:bg-teal-700 disabled:bg-teal-100 disabled:text-muted">{loading ? ui.submitting : index === steps.length - 1 ? ui.submit : ui.continue}</button></div></main>
}
