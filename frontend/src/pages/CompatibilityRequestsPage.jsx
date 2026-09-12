import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ApprovedUserNav from '../components/ApprovedUserNav'
import Button from '../components/Button'
import { getCompatibilityRequests, respondToCompatibilityRequest } from '../services/matchInteractionService'

const STATUS = {
  pending: ['قيد الانتظار', 'bg-gold-100 text-gold-700'],
  accepted: ['تم القبول', 'bg-teal-50 text-teal-700'],
  declined: ['تم الرفض', 'bg-brick-100 text-brick-500'],
  withdrawn: ['تم سحب الطلب', 'bg-teal-50 text-muted'],
}

function formatDate(value) {
  return new Date(value).toLocaleDateString('ar', { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function CompatibilityRequestsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('incoming')
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const session = JSON.parse(localStorage.getItem('wefaq_user') || 'null')
    if (!session) return navigate('/login', { replace: true })
    if (session.status !== 'approved') return navigate('/dashboard', { replace: true })
    getCompatibilityRequests().then(setData).catch((err) => setError(err.message))
  }, [navigate])

  async function respond(item, status) {
    setBusyId(item.id)
    setError('')
    try {
      const result = await respondToCompatibilityRequest(item.id, status)
      setData((current) => ({
        ...current,
        [status === 'withdrawn' ? 'sent' : 'incoming']: current[status === 'withdrawn' ? 'sent' : 'incoming'].map((entry) => entry.id === item.id ? result.request : entry),
      }))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  const items = data?.[tab] || []
  return (
    <main dir="rtl" className="mx-auto max-w-2xl px-4 pb-28 pt-7 sm:px-6">
      <header>
        <p className="text-sm text-muted">إدارة التواصل باحترام وخصوصية</p>
        <h1 className="mt-1 font-display text-3xl text-teal-700">طلبات التوافق</h1>
      </header>

      <div className="mt-6 grid grid-cols-2 rounded-2xl bg-teal-50 p-1.5" role="tablist" aria-label="أنواع الطلبات">
        <TabButton active={tab === 'incoming'} onClick={() => setTab('incoming')}>الواردة {data ? `(${data.incoming.length})` : ''}</TabButton>
        <TabButton active={tab === 'sent'} onClick={() => setTab('sent')}>المرسلة {data ? `(${data.sent.length})` : ''}</TabButton>
      </div>

      {error && <p className="mt-4 rounded-xl bg-brick-100 px-4 py-3 text-sm text-brick-500">{error}</p>}
      {!data ? <p className="py-16 text-center text-muted">جاري تحميل الطلبات...</p> : items.length === 0 ? (
        <div className="py-16 text-center"><p className="font-display text-xl text-teal-700">لا توجد طلبات {tab === 'incoming' ? 'واردة' : 'مرسلة'} حتى الآن.</p><p className="mt-2 text-sm text-muted">ستظهر الطلبات هنا مع الحفاظ على خصوصية الطرفين.</p></div>
      ) : (
        <div className="mt-5 space-y-3">
          {items.map((item) => <RequestItem key={item.id} item={item} incoming={tab === 'incoming'} busy={busyId === item.id} onRespond={respond} onOpen={() => item.available && navigate(`/matches?candidate=${item.candidate.candidate_ref}`)} />)}
        </div>
      )}
      <ApprovedUserNav />
    </main>
  )
}

function TabButton({ active, onClick, children }) {
  return <button type="button" role="tab" aria-selected={active} onClick={onClick} className={`min-h-11 rounded-xl text-sm font-medium ${active ? 'bg-white text-teal-700 shadow-sm' : 'text-muted'}`}>{children}</button>
}

function RequestItem({ item, incoming, busy, onRespond, onOpen }) {
  const [label, style] = STATUS[item.status] || STATUS.pending
  return (
    <article className="rounded-2xl border border-teal-100 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-xl text-teal-700">{item.available ? 'مرشح متوافق' : 'مرشح غير متاح'}</h2>
          <p className="mt-1 text-xs text-muted">{incoming ? 'طلب وارد' : 'طلب مرسل'} · {formatDate(item.created_at)}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${style}`}>{label}</span>
      </div>
      {item.available && <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink"><span>{item.candidate.age} سنة</span><span>{item.candidate.country || 'بلد الإقامة غير محدد'}</span><span>{item.candidate.profession || 'المهنة غير محددة'}</span>{item.compatibility_percentage != null && <span className="text-gold-700">توافق {item.compatibility_percentage}%</span>}</div>}
      {!item.available && <p className="mt-3 text-sm text-muted">لم يعد الملف متاحاً للعرض.</p>}
      <div className="mt-4 flex flex-wrap gap-2">
        {item.available && <Button variant="secondary" className="px-4 py-2 text-sm" onClick={onOpen}>عرض الملف</Button>}
        {incoming && item.status === 'pending' && <>
          <Button className="px-4 py-2 text-sm" disabled={busy} onClick={() => onRespond(item, 'accepted')}>قبول</Button>
          <Button variant="danger" className="px-4 py-2 text-sm" disabled={busy} onClick={() => onRespond(item, 'declined')}>رفض</Button>
        </>}
        {!incoming && item.status === 'pending' && <Button variant="danger" className="px-4 py-2 text-sm" disabled={busy} onClick={() => onRespond(item, 'withdrawn')}>سحب الطلب</Button>}
      </div>
    </article>
  )
}
