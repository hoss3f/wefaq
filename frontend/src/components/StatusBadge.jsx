// frontend/src/components/StatusBadge.jsx
import config from '../config.json'

const STYLES = {
  pending: 'bg-teal-50 text-teal-600',
  reviewing: 'bg-gold-100 text-gold-700',
  approved: 'bg-teal-600 text-linen',
  rejected: 'bg-brick-100 text-brick-500'
}

export default function StatusBadge({ status }) {
  const label = config.statusLabels[status] || status
  const style = STYLES[status] || 'bg-teal-50 text-teal-600'

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${style}`}>
      {label}
    </span>
  )
}
