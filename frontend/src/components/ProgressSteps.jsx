// frontend/src/components/ProgressSteps.jsx

/** شريط مراحل مع خطوط تقدّم تربط الخطوات أثناء تعبئة الطلب */
export default function ProgressSteps({ steps, currentIndex }) {
  return (
    <div className="mb-8">
      <ol className="flex items-center w-full">
        {steps.map((step, index) => {
          const isDone = index < currentIndex
          const isActive = index === currentIndex
          const isLast = index === steps.length - 1

          return (
            <li key={step.key} className={`flex items-center ${isLast ? '' : 'flex-1'}`}>
              <div className="flex flex-col items-center min-w-[4.5rem]">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all duration-300
                    ${isDone
                      ? 'bg-teal-600 text-linen border-teal-600'
                      : isActive
                        ? 'bg-gold-500 text-ink border-gold-500 shadow-sm scale-110'
                        : 'bg-linen text-muted border-teal-100'}`}
                >
                  {isDone ? '✓' : index + 1}
                </div>
                <span className={`text-[11px] mt-2 text-center leading-snug max-w-[5.5rem]
                  ${isActive ? 'text-ink font-medium' : 'text-muted'}`}>
                  {step.label}
                </span>
              </div>

              {!isLast && (
                <div
                  className={`flex-1 h-0.5 mx-1 mb-6 rounded-full transition-colors duration-500
                    ${index < currentIndex ? 'bg-teal-600' : 'bg-teal-100'}`}
                  aria-hidden
                />
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
