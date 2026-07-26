// frontend/src/components/MashrabiyaDivider.jsx

/**
 * فاصل بصري مستوحى من نقش المشربية التقليدي، الذي كان يتيح الرؤية دون كشف الخصوصية.
 * يُستخدم هنا كرمز للفكرة الأساسية للمشروع: تعارف يحفظ الستر ولا يفرط في الكشف.
 */
export default function MashrabiyaDivider({ className = '' }) {
  return (
    <div className={`h-10 mashrabiya-bg ${className}`} aria-hidden="true" />
  )
}
