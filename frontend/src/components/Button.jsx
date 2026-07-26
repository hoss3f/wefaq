// frontend/src/components/Button.jsx
export default function Button({ children, onClick, type = 'button', variant = 'primary', disabled = false, className = '' }) {
  const base = 'px-6 py-3 rounded-xl font-medium transition-colors duration-150 focus-visible:outline-2'
  const variants = {
    primary: 'bg-teal-600 text-linen hover:bg-teal-700 disabled:bg-teal-100 disabled:text-muted',
    secondary: 'bg-transparent border border-teal-600 text-teal-600 hover:bg-teal-50',
    danger: 'bg-brick-500 text-linen hover:bg-brick-500/90'
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  )
}
