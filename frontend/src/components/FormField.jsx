// frontend/src/components/FormField.jsx

/**
 * حقل نموذج ديناميكي، يُبنى نوعه (نص، بريد، تاريخ، قائمة) من كائن الحقل القادم من config.json
 */
export default function FormField({ field, value, onChange, error, placeholder }) {
  const baseClasses = 'w-full rounded-xl border border-teal-100 px-4 py-3 bg-linen focus-visible:outline-2 focus-visible:outline-gold-500'
  const hint = placeholder || field.placeholder || ''

  const handleChange = (e) => {
    let newValue = e.target.value
    if (field.type === 'tel') {
      newValue = newValue.replace(/\D/g, '')
    }
    onChange(field.name, newValue)
  }

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
          onChange={handleChange}
        >
          <option value="" disabled>اختر</option>
          {field.options.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      ) : field.type === 'searchable-select' ? (
        <>
          <input
            list={`${field.name}-options`}
            className={baseClasses}
            value={value || ''}
            placeholder={hint}
            onChange={handleChange}
            autoComplete="off"
          />
          <datalist id={`${field.name}-options`}>
            {field.options?.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </>
      ) : (
        <input
          type={field.type}
          className={baseClasses}
          value={value || ''}
          placeholder={hint}
          onChange={handleChange}
          inputMode={field.type === 'tel' ? 'numeric' : undefined}
          pattern={field.type === 'tel' ? '\\d*' : undefined}
        />
      )}

      {error && <span className="block mt-1 text-sm text-brick-500">{error}</span>}
    </label>
  )
}
