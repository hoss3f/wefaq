// frontend/src/components/NotificationList.jsx

/** قائمة إشعارات بسيطة تُعرض في لوحة تحكم المستخدم */
export default function NotificationList({ notifications }) {
  if (!notifications || notifications.length === 0) {
    return <p className="text-muted text-sm">لا توجد إشعارات حتى الآن.</p>
  }

  return (
    <ul className="space-y-3">
      {notifications.map((n) => (
        <li
          key={n.id}
          className={`p-3 rounded-xl border text-sm ${n.is_read ? 'border-teal-100 text-muted' : 'border-gold-300 bg-gold-100/40 text-ink'}`}
        >
          {n.message}
        </li>
      ))}
    </ul>
  )
}
