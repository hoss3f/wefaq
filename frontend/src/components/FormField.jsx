// frontend/src/components/FormField.jsx

/**
 * حقل نموذج ديناميكي، يُبنى نوعه (نص، بريد، تاريخ، قائمة) من كائن الحقل القادم من config.json
 */
export default function FormField({ field, value, onChange, error, placeholder }) {
  const baseClasses = 'w-full rounded-xl border border-teal-100 px-4 py-3 bg-linen focus-visible:outline-2 focus-visible:outline-gold-500'
  const hint = placeholder || field.placeholder || ''

  return (
    <label className="block mb-4">
      <span className="block mb-1 text-sm font-medium text-ink">
        {field.label}
        {field.required && <span className="text-brick-500"> *</span>}
      </span>

      {field.type === 'select' ? (
        <select
          className={baseClasses}
          value={value || ''}
          onChange={(e) => onChange(field.name, e.target.value)}
        >
          <option value="" disabled>اختر</option>
          {field.options.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      ) : (
        <input
          type={field.type}
          className={baseClasses}
          value={value || ''}
          placeholder={hint}
          onChange={(e) => onChange(field.name, e.target.value)}
        />
      )}

      {error && <span className="block mt-1 text-sm text-brick-500">{error}</span>}
    </label>
  )
}
