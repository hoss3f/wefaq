import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ApprovedUserNav from '../components/ApprovedUserNav'
import Button from '../components/Button'
import CandidateProfileCard from '../components/CandidateProfileCard'
import { getMyMatches } from '../services/matchingService'
import {
  getCompatibilityRequests,
  getSavedCandidates,
  removeSavedCandidate,
  saveCandidate,
  sendCompatibilityRequest,
} from '../services/matchInteractionService'

const REQUEST_LABELS = {
  'sent-pending': 'تم إرسال الطلب',
  'sent-accepted': 'تم قبول الطلب',
  'sent-declined': 'تم الاعتذار عن الطلب',
  'sent-withdrawn': 'تم سحب الطلب',
  'incoming-pending': 'لديك طلب وارد',
  'incoming-accepted': 'طلب مقبول',
  'incoming-declined': 'طلب مرفوض',
  'incoming-withdrawn': 'طلب مسحوب',
}

export default function MatchingPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [matches, setMatches] = useState(null)
  const [index, setIndex] = useState(0)
  const [savedRefs, setSavedRefs] = useState(new Set())
  const [requestStates, setRequestStates] = useState(new Map())
  const [activeOutgoingRef, setActiveOutgoingRef] = useState(null)
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    const session = JSON.parse(localStorage.getItem('wefaq_user') || 'null')
    if (!session) return navigate('/login', { replace: true })
    if (session.status !== 'approved') return navigate('/dashboard', { replace: true })

    Promise.all([getMyMatches(session.id), getSavedCandidates(), getCompatibilityRequests()])
      .then(([matchData, savedData, requestData]) => {
        const nextMatches = matchData.matches || []
        setMatches(nextMatches)
        setSavedRefs(new Set((savedData.saved || []).filter((item) => item.available).map((item) => item.candidate.candidate_ref)))
        const states = new Map()
        ;[...(requestData.incoming || []), ...(requestData.sent || [])].forEach((item) => {
          if (item.available) states.set(item.candidate.candidate_ref, `${item.direction}-${item.status}`)
        })
        setRequestStates(states)
        const activeOutgoing = (requestData.sent || []).find((item) => item.status === 'pending')
        setActiveOutgoingRef(activeOutgoing?.candidate?.candidate_ref ?? activeOutgoing?.candidate_ref ?? null)
        const requestedRef = Number(searchParams.get('candidate'))
        const requestedIndex = nextMatches.findIndex((item) => item.candidate.candidate_ref === requestedRef)
        if (requestedIndex >= 0) setIndex(requestedIndex)
      })
      .catch((err) => setError(err.message))
  }, [navigate, searchParams])

  const match = matches?.[index]
  const candidateRef = match?.candidate?.candidate_ref
  const isSaved = savedRefs.has(candidateRef)
  const requestState = requestStates.get(candidateRef)
  const anotherRequestIsActive = activeOutgoingRef != null && activeOutgoingRef !== candidateRef
  const requestLabel = useMemo(() => anotherRequestIsActive ? 'لديك طلب توافق قيد الانتظار' : REQUEST_LABELS[requestState] || 'إرسال طلب توافق', [anotherRequestIsActive, requestState])

  function next() {
    setIndex((current) => (current + 1) % matches.length)
    setMessage('')
    setError('')
  }

  async function handleRequest() {
    if (anotherRequestIsActive) return navigate('/compatibility-requests')
    if (requestState) {
      if (requestState.startsWith('incoming-')) navigate('/compatibility-requests')
      return
    }
    setBusy('request')
    setMessage('')
    setError('')
    try {
      const data = await sendCompatibilityRequest(candidateRef)
      setRequestStates((current) => new Map(current).set(candidateRef, `${data.request.direction}-${data.request.status}`))
      if (data.request.direction === 'sent' && data.request.status === 'pending') setActiveOutgoingRef(candidateRef)
      setMessage(data.message)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  async function handleSave() {
    setBusy('save')
    setMessage('')
    setError('')
    try {
      if (isSaved) {
        await removeSavedCandidate(candidateRef)
        setSavedRefs((current) => {
          const nextSet = new Set(current)
          nextSet.delete(candidateRef)
          return nextSet
        })
        setMessage('تمت إزالة المرشح من المحفوظات.')
      } else {
        await saveCandidate(candidateRef)
        setSavedRefs((current) => new Set(current).add(candidateRef))
        setMessage('تم حفظ المرشح لتعود إليه لاحقاً.')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  if (error && !matches) return <PageMessage text={error} action={() => navigate('/account')} actionLabel="العودة إلى الحساب" />
  if (!matches) return <p dir="rtl" className="py-20 text-center text-muted">جاري البحث عن المرشحين المناسبين...</p>
  if (!matches.length) return <><PageMessage title="لا توجد نتائج مطابقة حالياً" text="سنظهر لك المرشحين المناسبين عند توفرهم." /><ApprovedUserNav /></>

  return (
    <main dir="rtl" className="mx-auto min-h-full max-w-xl px-4 pb-28 pt-6 sm:px-6">
      <header className="mb-5">
        <p className="text-sm text-muted">مساحة خاصة للمرشحين المعتمدين</p>
        <h1 className="mt-1 font-display text-3xl text-teal-700">المرشحون المناسبون</h1>
      </header>

      <CandidateProfileCard candidate={match.candidate} compatibility={match.has_sufficient_data ? match.compatibility_percentage : null} position={`${index + 1} من ${matches.length}`}>
        {match.compatibility_summary && <p className="mt-4 text-sm leading-6 text-muted">{match.compatibility_summary}</p>}
        {(message || error) && <p role="status" className={`mt-4 rounded-xl px-4 py-3 text-sm ${error ? 'bg-brick-100 text-brick-500' : 'bg-teal-50 text-teal-700'}`}>{error || message}</p>}
        <div className="mt-6 grid grid-cols-2 gap-3">
          <Button onClick={handleRequest} disabled={busy === 'request' || anotherRequestIsActive || (requestState && !requestState.startsWith('incoming-'))} className="min-h-14 px-3">
            {busy === 'request' ? 'جارٍ الإرسال...' : requestLabel}
          </Button>
          <Button variant="secondary" onClick={handleSave} disabled={busy === 'save'} className="min-h-14 px-3">
            {busy === 'save' ? 'جارٍ الحفظ...' : isSaved ? 'إزالة من المحفوظات' : 'حفظ المرشح'}
          </Button>
        </div>
        {activeOutgoingRef != null && <button type="button" onClick={() => navigate('/compatibility-requests')} className="mt-3 min-h-11 w-full rounded-xl bg-gold-100/60 px-4 text-sm font-medium text-gold-700">إدارة الطلب القائم</button>}
        <button type="button" onClick={next} className="mt-3 min-h-12 w-full rounded-xl text-sm font-medium text-muted hover:bg-teal-50">عرض المرشح التالي ←</button>
      </CandidateProfileCard>
      <ApprovedUserNav />
    </main>
  )
}

function PageMessage({ title, text, action, actionLabel }) {
  return <main dir="rtl" className="mx-auto max-w-xl px-6 py-20 text-center"><h1 className="font-display text-2xl text-teal-700">{title}</h1><p className="mt-3 text-muted">{text}</p>{action && <Button variant="secondary" className="mt-5" onClick={action}>{actionLabel}</Button>}</main>
}
