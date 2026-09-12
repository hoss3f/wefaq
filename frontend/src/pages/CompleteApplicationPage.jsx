import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getQuestions, getUser, completeApplication } from '../services/userService'
import { NumericRangeSlider, NumericSlider } from '../components/NumericSlider'

const PLACEHOLDER_NAME = 'متقدم جديد'
function displayName(name) {
  if (!name || name.trim() === PLACEHOLDER_NAME) return ''
  return name
}

function ChoiceCards({ options, value, onChange, chips = false }) {
  return <div className={chips ? 'flex flex-wrap gap-2' : 'space-y-3'}>{options.map((item) => <button key={item} type="button" onClick={() => onChange(item)} className={chips ? `rounded-full border px-4 py-2 font-medium transition-colors ${value === item ? 'border-teal-600 bg-teal-600 text-linen' : 'border-teal-100 bg-white text-ink hover:bg-teal-50'}` : `flex min-h-20 w-full items-center justify-between rounded-2xl border-2 px-5 text-right transition-colors ${value === item ? 'border-gold-500 bg-gold-100/40 text-teal-700' : 'border-teal-100 bg-white text-ink hover:border-teal-300'}`}><b>{item}</b>{!chips && <span className={`h-6 w-6 rounded-full border ${value === item ? 'border-teal-600 bg-teal-600 shadow-[inset_0_0_0_5px_#FAF8F4]' : 'border-teal-300'}`} />}</button>)}</div>
}

function SearchSelector({ question, value, onChange, otherOption }) {
  const [query, setQuery] = useState('')
  const isCustom = !!value && !(question.options || []).includes(value)
  const [customMode, setCustomMode] = useState(isCustom)
  const showCustomInput = customMode || isCustom
  const matches = (question.options || []).filter((item) => item.toLowerCase().includes(query.trim().toLowerCase()))
  const choices = [...matches.filter((item) => item !== otherOption), otherOption]
  function pick(item) {
    if (item === otherOption) {
      setCustomMode(true)
      if (!isCustom) onChange('')
    } else {
      setCustomMode(false)
      onChange(item)
    }
  }
  return <div><div className="flex items-center gap-3 border-b border-teal-100 py-3 text-muted"><span className="text-2xl">⌕</span><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder={question.placeholder} className="w-full bg-transparent text-lg outline-none placeholder:text-muted/70" /></div><div className="mt-5 max-h-80 space-y-1 overflow-y-auto">{choices.map((item) => <button key={item} type="button" onClick={() => pick(item)} className={`flex w-full items-center justify-between rounded-xl px-3 py-3 text-right text-lg transition-colors ${(value === item || (item === otherOption && showCustomInput)) ? 'bg-teal-50 font-bold text-teal-700' : 'text-ink hover:bg-linen'}`}>{item}<span className={`h-5 w-5 rounded-md border ${(value === item || (item === otherOption && showCustomInput)) ? 'border-gold-500 bg-gold-500' : 'border-teal-100'}`} /></button>)}</div>{showCustomInput && <input autoFocus value={value || ''} onChange={(event) => onChange(event.target.value)} placeholder={otherOption} className="mt-4 w-full border-b-2 border-teal-100 bg-transparent py-3 text-lg outline-none focus:border-gold-500" />}</div>
}

function RangeField({ field, details, setDetail }) {
  return <NumericRangeSlider label={field.title} minimum={field.min} maximum={field.max} minValue={details[field.min_key] ?? field.default_min} maxValue={details[field.max_key] ?? field.default_max} onMinChange={(value) => setDetail(field.min_key, value)} onMaxChange={(value) => setDetail(field.max_key, value)} unit={field.unit} />
}

function MultiSearchSelector({ question, value, onChange }) {
  const [query, setQuery] = useState('')
  const selected = Array.isArray(value) ? value : value ? [value] : []
  const matches = (question.options || []).filter((item) => item.toLowerCase().includes(query.trim().toLowerCase()))
  function toggle(item) {
    if (item === 'لا يهم') return onChange(selected.includes(item) ? [] : [item])
    const withoutNeutral = selected.filter((entry) => entry !== 'لا يهم')
    onChange(withoutNeutral.includes(item) ? withoutNeutral.filter((entry) => entry !== item) : [...withoutNeutral, item])
  }
  return <div>
    {selected.length > 0 && <div className="mb-4 flex flex-wrap gap-2">{selected.map((item) => <button key={item} type="button" onClick={() => toggle(item)} className="rounded-full bg-teal-600 px-3 py-2 text-sm font-medium text-linen">{item} ×</button>)}</div>}
    <div className="flex items-center gap-3 border-b border-teal-100 py-3 text-muted"><span className="text-2xl">⌕</span><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder={question.placeholder} className="w-full bg-transparent text-lg outline-none placeholder:text-muted/70" /></div>
    <div className="mt-4 max-h-72 space-y-1 overflow-y-auto">{matches.map((item) => { const checked = selected.includes(item); return <button key={item} type="button" onClick={() => toggle(item)} className={`flex min-h-12 w-full items-center justify-between rounded-xl px-3 text-right transition-colors ${checked ? 'bg-teal-50 font-bold text-teal-700' : 'text-ink hover:bg-linen'}`}><span>{item}</span><span className={`flex h-6 w-6 items-center justify-center rounded-md border ${checked ? 'border-gold-500 bg-gold-500 text-white' : 'border-teal-100'}`}>{checked ? '✓' : ''}</span></button> })}</div>
  </div>
}

function SliderField({ question, value, onChange }) {
  return <NumericSlider label={question.title} minimum={question.min} maximum={question.max} value={value ?? question.default ?? question.min} onChange={(selected) => onChange(question, selected)} unit={question.suffix} />
}

function clampValue(value, minimum, maximum, fallback) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? Math.min(Math.max(numeric, minimum), maximum) : fallback
}

function normalizeNumericDetails(questionData, storedDetails) {
  const normalized = { ...storedDetails }
  const steps = questionData.onboarding?.steps || []
  steps.filter((step) => step.type === 'slider').forEach((step) => {
    normalized[step.key] = clampValue(storedDetails[step.key], step.min, step.max, step.default ?? step.min)
  })
  steps.filter((step) => step.type === 'preferences').flatMap((step) => step.fields || []).filter((field) => field.type === 'range').forEach((field) => {
    const lower = clampValue(storedDetails[field.min_key], field.min, field.max, field.default_min)
    const upper = Math.max(lower, clampValue(storedDetails[field.max_key], field.min, field.max, field.default_max))
    normalized[field.min_key] = lower
    normalized[field.max_key] = upper
  })
  if (normalized.nationality_preference && !Array.isArray(normalized.nationality_preference)) {
    normalized.nationality_preference = [normalized.nationality_preference]
  }
  return normalized
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
  const [phoneCode, setPhoneCode] = useState('+974')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [phoneParsed, setPhoneParsed] = useState(false)

  useEffect(() => {
    const session = JSON.parse(localStorage.getItem('wefaq_user') || 'null')
    if (!session) return navigate('/login')
    setUserId(session.id)
    Promise.all([getUser(session.id), getQuestions()]).then(([data, questionData]) => {
      if (!data.user.needs_onboarding) return navigate('/dashboard', { replace: true })
      setPersonal({ full_name: displayName(data.user.full_name), birthday: data.user.birthday || '', gender: data.user.gender || '', country: data.user.country || '', phone: data.user.phone || '', email: data.user.email || '' })
      const preferenceQuestion = questionData.questions.onboarding?.steps.find((item) => item.type === 'preferences')
      const rangeDefaults = Object.fromEntries((preferenceQuestion?.fields || [])
        .filter((field) => field.type === 'range')
        .flatMap((field) => [[field.min_key, field.default_min], [field.max_key, field.default_max]]))
      setDetails(normalizeNumericDetails(questionData.questions, { ...rangeDefaults, ...(data.profile_details || {}) }))
      setMcqAnswers(data.mcq_answers || {})
      setAnswers(data.open_answers || {})
      setQuestionSet(questionData.questions)
    }).catch(() => setError('تعذر تحميل بيانات الطلب'))
  }, [navigate])

  useEffect(() => {
    if (phoneParsed) return
    const contactStep = questionSet?.onboarding?.steps.find((item) => item.type === 'contact')
    if (!contactStep) return
    const raw = personal.phone || ''
    const codes = contactStep.country_codes || []
    const match = codes.find((item) => raw.startsWith(item.code))
    if (match) {
      setPhoneCode(match.code)
      setPhoneNumber(raw.slice(match.code.length))
    } else {
      setPhoneNumber(raw)
    }
    setPhoneParsed(true)
  }, [questionSet, personal, phoneParsed])

  function updatePhone(code, number) {
    setPhoneCode(code)
    setPhoneNumber(number)
    setPersonal((old) => ({ ...old, phone: `${code}${number}`.trim() }))
  }

  const onboarding = questionSet?.onboarding
  const steps = useMemo(() => {
    if (!onboarding) return []
    const ruleMatches = (rule) => {
      const source = rule.storage === 'personal' ? personal : details
      const value = source[rule.key]
      return rule.in ? rule.in.includes(value) : value === rule.equals
    }
    const configured = onboarding.steps.filter((item) => !item.show_if || item.show_if.every(ruleMatches))
    const matching = (questionSet.mcq || []).filter((item) => item.active !== false && item.matching).map((item) => ({
      key: `q${item.id}`, storage: 'mcq', type: 'choice', title: item.question, options: item.options, required: true,
    }))
    const open = (questionSet.open || []).map((title, position) => ({ key: `open_${position + 1}`, type: 'textarea', title, placeholder: onboarding.ui.open_placeholder, required: true, openNumber: position + 1 }))
    const all = [...configured, ...matching, ...open]
    if (!onboarding.flow) return all
    const byFlowKey = new Map(all.map((item) => [item.storage === 'mcq' ? `mcq_${item.key}` : item.key, item]))
    const ordered = onboarding.flow.map((key) => byFlowKey.get(key)).filter(Boolean)
    return [...ordered, ...all.filter((item) => !ordered.includes(item))]
  }, [onboarding, details, personal, questionSet])
  const question = steps[index]
  const ui = onboarding?.ui || {}
  const getValue = (item) => item.storage === 'personal' ? personal[item.key] : item.storage === 'mcq' ? mcqAnswers[item.key] : details[item.key]
  const setValue = (item, value) => {
    if (item.storage === 'personal') setPersonal((old) => ({ ...old, [item.key]: value }))
    else if (item.storage === 'mcq') setMcqAnswers((old) => ({ ...old, [item.key]: value }))
    else setDetails((old) => ({ ...old, [item.key]: value }))
    if (item.key === 'gender' && value !== 'أنثى') setDetails((old) => { const nextDetails = { ...old }; delete nextDetails.polygyny_acceptance; return nextDetails })
    if (item.key === 'full_name') setNameError(nameValidation(value))
  }
  const setDetail = (key, value) => setDetails((old) => ({ ...old, [key]: value }))

  function valid() {
    if (!question?.required) return true
    if (question.type === 'preferences') return question.fields.filter((field) => field.type !== 'range' && !field.optional).every((field) => Array.isArray(details[field.key]) ? details[field.key].length > 0 : !!details[field.key])
    if (question.type === 'contact') return !!phoneNumber?.trim()
    if (question.openNumber) {
      const answer = answers[`q${question.openNumber}`]?.trim() || ''
      return answer.length >= (question.openNumber === 1 ? 20 : 5) && answer.length <= 1500
    }
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
    return <div className="space-y-7">{question.fields.map((field) => <section key={field.key}><b className="text-teal-700">{field.title}</b>{field.description && <p className="mt-1 text-sm text-muted">{field.description}</p>}<div className="mt-3">{field.type === 'range' ? <RangeField field={field} details={details} setDetail={setDetail} /> : field.type === 'chips' ? <ChoiceCards chips options={field.options} value={details[field.key]} onChange={(value) => setDetail(field.key, value)} /> : field.type === 'search' ? <SearchSelector question={field} value={details[field.key]} onChange={(value) => setDetail(field.key, value)} otherOption={onboarding.other_option} /> : field.type === 'multi_search' ? <MultiSearchSelector question={field} value={details[field.key]} onChange={(value) => setDetail(field.key, value)} /> : <input value={details[field.key] || ''} onChange={(event) => setDetail(field.key, event.target.value)} placeholder={field.placeholder} className="w-full border-b border-teal-100 bg-transparent py-3 outline-none focus:border-gold-500" />}</div></section>)}</div>
  }
  function renderQuestion() {
    const value = getValue(question)
    if (question.type === 'gender') return <div className="grid grid-cols-2 gap-4">{question.options.map((option) => <button key={option} type="button" onClick={() => setValue(question, option)} className={`rounded-2xl border-2 p-7 transition-colors ${value === option ? 'border-gold-500 bg-gold-100/50 text-teal-700' : 'border-teal-100 bg-white text-ink hover:border-teal-300'}`}><span className="text-5xl">{option === question.options[0] ? '◐' : '◑'}</span><b className="mt-5 block text-xl">{option}</b></button>)}</div>
    if (question.type === 'choice') return <ChoiceCards options={question.options_by_gender?.[personal.gender] || question.options || []} value={value} onChange={(selected) => setValue(question, selected)} />
    if (question.type === 'chips') return <ChoiceCards chips options={question.options} value={value} onChange={(selected) => setValue(question, selected)} />
    if (question.type === 'search') return <SearchSelector question={question} value={value} onChange={(selected) => setValue(question, selected)} otherOption={onboarding.other_option} />
    if (question.type === 'date') return <input autoFocus type="date" value={value || ''} onChange={(event) => setValue(question, event.target.value)} className="w-full rounded-xl border border-teal-100 bg-white p-5 text-xl outline-none focus:border-gold-500" />
    if (question.type === 'slider') return <SliderField question={question} value={value} onChange={setValue} />
    if (question.type === 'number') return <div className="relative"><input autoFocus type="number" min="1" value={value || ''} onChange={(event) => setValue(question, event.target.value)} className="w-full border-b-2 border-teal-100 bg-transparent py-4 text-5xl font-bold text-teal-700 outline-none focus:border-gold-500" />{question.suffix && <span className="absolute bottom-5 left-0 text-xl text-muted">{question.suffix}</span>}</div>
    if (question.type === 'textarea') return question.openNumber
      ? <div><textarea autoFocus rows="6" minLength={question.openNumber === 1 ? 20 : 5} maxLength="1500" value={answers[`q${question.openNumber}`] || ''} onChange={(event) => setAnswers((old) => ({ ...old, [`q${question.openNumber}`]: event.target.value }))} placeholder={question.openNumber === 1 ? 'اكتب فقرة قصيرة تعبّر عن شخصيتك واهتماماتك...' : question.placeholder} className="w-full border-b-2 border-teal-100 bg-transparent py-3 text-xl leading-relaxed outline-none focus:border-gold-500" /><p className="mt-2 text-left text-xs text-muted">{(answers[`q${question.openNumber}`] || '').length} / 1500</p></div>
      : <textarea autoFocus rows="6" value={value || ''} onChange={(event) => setValue(question, event.target.value)} placeholder={question.placeholder} className="w-full border-b-2 border-teal-100 bg-transparent py-3 text-xl leading-relaxed outline-none focus:border-gold-500" />
    if (question.type === 'preferences') return renderPreferences()
    if (question.type === 'contact') {
      const codes = question.country_codes || []
      return <div className="space-y-8">
        <div>
          <b className="mb-3 block text-teal-700">{question.phone_label}</b>
          <div className="flex items-center gap-3 border-b-2 border-teal-100 focus-within:border-gold-500">
            <select value={phoneCode} onChange={(event) => updatePhone(event.target.value, phoneNumber)} className="bg-transparent py-4 text-lg font-bold text-teal-700 outline-none">
              {codes.map((item) => <option key={item.code} value={item.code}>{item.code} {item.name}</option>)}
            </select>
            <input autoFocus type="tel" value={phoneNumber} onChange={(event) => updatePhone(phoneCode, event.target.value)} placeholder={question.phone_placeholder} className="w-full bg-transparent py-4 text-2xl outline-none placeholder:text-muted/70" />
          </div>
        </div>
        <div>
          <b className="mb-3 block text-teal-700">{question.email_label}</b>
          <input type="email" value={personal.email || ''} onChange={(event) => setPersonal((old) => ({ ...old, email: event.target.value }))} placeholder={question.email_placeholder} className="w-full border-b-2 border-teal-100 bg-transparent py-4 text-2xl outline-none focus:border-gold-500" />
        </div>
      </div>
    }
    return <><input autoFocus value={value || ''} onChange={(event) => setValue(question, event.target.value)} placeholder={question.placeholder || (question.key === 'full_name' ? 'اكتب الاسم الكامل هنا...' : '')} className="w-full border-b-2 border-teal-100 bg-transparent py-4 text-2xl outline-none placeholder:text-muted/60 focus:border-gold-500" />{question.key === 'full_name' && nameError && <p className="mt-3 text-sm text-brick-500">{nameError}</p>}</>
  }

  if (!question) return <p className="py-20 text-center text-muted">{ui.loading || '...'}</p>
  return <main dir="rtl" className="min-h-[calc(100vh-64px)] bg-linen text-ink"><div className="mx-auto flex min-h-[calc(100vh-64px)] max-w-xl flex-col px-6 pb-8 pt-7"><header dir="ltr" className="flex items-center gap-5"><button type="button" aria-label={ui.back} disabled={index === 0} onClick={() => setIndex((current) => Math.max(0, current - 1))} className="text-3xl text-teal-700 disabled:text-teal-100">‹</button><div className="h-1 flex-1 overflow-hidden rounded-full bg-teal-100"><div className="h-full rounded-full bg-gold-500 transition-all" style={{ width: `${((index + 1) / steps.length) * 100}%` }} /></div><span className="font-display text-xl text-teal-700">و</span></header><div className="flex-1 pt-16"><p className="mb-3 text-sm text-muted">{index + 1} {ui.progress} {steps.length}</p><h1 className="font-display text-3xl font-bold leading-tight text-teal-700 sm:text-4xl">{question.title}</h1>{question.description && <p className="mt-3 text-lg leading-relaxed text-muted">{question.description}</p>}<div className={`mt-10 ${error ? 'rounded-2xl ring-2 ring-brick-500 ring-offset-4 ring-offset-linen' : ''}`}>{renderQuestion()}</div>{error && <p className="mt-4 flex items-center gap-2 text-sm font-medium text-brick-500"><span aria-hidden="true">⚠</span>{error}</p>}</div><button type="button" onClick={next} disabled={loading} className="mt-8 w-full rounded-xl bg-teal-600 px-6 py-4 text-lg font-bold text-linen transition-colors hover:bg-teal-700 disabled:bg-teal-100 disabled:text-muted">{loading ? ui.submitting : index === steps.length - 1 ? ui.submit : ui.continue}</button></div></main>
}
