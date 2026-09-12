function clamp(value, minimum, maximum) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? Math.min(Math.max(numeric, minimum), maximum) : minimum
}

function RangeInput({ ariaLabel, minimum, maximum, value, onChange }) {
  return <input
    aria-label={ariaLabel}
    type="range"
    min={minimum}
    max={maximum}
    step="1"
    value={value}
    onChange={(event) => onChange(Number(event.target.value))}
  />
}

/** تحكم رقمي موحّد للقيم المفردة والنطاقات، مع تثبيت الاتجاه لتفادي عكس السحب في RTL. */
export function NumericSlider({ label, minimum, maximum, value, onChange, unit }) {
  const selected = clamp(value, minimum, maximum)

  return <div className="rounded-2xl bg-teal-50 p-5">
    <div className="mb-5 text-center">
      <strong className="text-4xl text-teal-700">{selected}</strong>
      {unit && <span className="mr-2 text-lg text-muted">{unit}</span>}
    </div>
    <div dir="ltr" className="single-range">
      <RangeInput ariaLabel={label} minimum={minimum} maximum={maximum} value={selected} onChange={onChange} />
    </div>
    <div className="mt-3 flex justify-between text-sm text-muted" dir="ltr">
      <span>{minimum} {unit}</span><span>{maximum} {unit}</span>
    </div>
  </div>
}

export function NumericRangeSlider({ label, minimum, maximum, minValue, maxValue, onMinChange, onMaxChange, unit }) {
  const lower = clamp(minValue, minimum, maximum)
  const upper = Math.max(lower, clamp(maxValue, minimum, maximum))
  const span = maximum - minimum || 1
  const lowerPosition = ((lower - minimum) / span) * 100
  const upperPosition = ((upper - minimum) / span) * 100

  return <div className="rounded-2xl bg-teal-50 p-5">
    <div className="mb-5 flex flex-wrap justify-between gap-2 font-bold text-teal-700">
      <span>الحد الأدنى: {lower} {unit}</span>
      <span>الحد الأقصى: {upper} {unit}</span>
    </div>
    <div dir="ltr" className="dual-range dual-range--mirrored" style={{ '--range-start': `${lowerPosition}%`, '--range-end': `${upperPosition}%` }}>
      <div className="dual-range__track" aria-hidden="true" />
      <RangeInput ariaLabel={`الحد الأدنى لـ${label}`} minimum={minimum} maximum={maximum} value={lower} onChange={(next) => onMinChange(Math.min(next, upper))} />
      <RangeInput ariaLabel={`الحد الأقصى لـ${label}`} minimum={minimum} maximum={maximum} value={upper} onChange={(next) => onMaxChange(Math.max(next, lower))} />
    </div>
    <div className="mt-3 flex justify-between text-sm text-muted" dir="ltr">
      <span>{maximum} {unit}</span><span>{minimum} {unit}</span>
    </div>
  </div>
}
