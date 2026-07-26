// frontend/src/components/Card.jsx
export default function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-teal-100 p-6 ${className}`}>
      {children}
    </div>
  )
}
