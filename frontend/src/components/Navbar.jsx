// frontend/src/components/Navbar.jsx
import { Link } from 'react-router-dom'
import config from '../config.json'

export default function Navbar() {
  return (
    <header className="border-b border-teal-100 bg-linen/80 backdrop-blur">
      <div className="max-w-5xl mx-auto flex items-center justify-between px-6 py-4">
        <Link to="/" className="font-display text-2xl text-teal-700">
          {config.appName}
        </Link>
        <nav className="flex items-center gap-4 text-sm font-medium">
          <Link to="/login" className="text-ink hover:text-teal-600">تسجيل الدخول</Link>
          <Link to="/login" className="text-linen bg-teal-600 px-4 py-2 rounded-xl hover:bg-teal-700">
            دخول بالكود
          </Link>
        </nav>
      </div>
    </header>
  )
}