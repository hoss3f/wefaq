// frontend/src/pages/AdminLoginPage.jsx
import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import { loginAdmin } from '../services/authService'

const STORAGE_KEY = 'wefaq_admin_credentials'

export default function AdminLoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (!saved) return
      const parsed = JSON.parse(saved)
      if (parsed?.email) setEmail(parsed.email)
      if (parsed?.password) setPassword(parsed.password)
      if (typeof parsed?.rememberMe === 'boolean') setRememberMe(parsed.rememberMe)
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const trimmedEmail = email.trim()
      const trimmedPassword = password
      const data = await loginAdmin(trimmedEmail, trimmedPassword)
      localStorage.setItem('wefaq_admin', JSON.stringify(data.admin))

      if (rememberMe) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
          email: trimmedEmail,
          password: trimmedPassword,
          rememberMe: true
        }))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }

      navigate('/admin/dashboard')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <Card>
        <h1 className="font-display text-2xl text-teal-700 mb-2">دخول الإداريين</h1>
        <p className="text-muted text-sm mb-6">هذه الصفحة مخصصة لفريق المراجعة فقط</p>

        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="البريد الإلكتروني"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-teal-100 px-4 py-3 bg-linen mb-4 focus-visible:outline-2 focus-visible:outline-gold-500"
            required
          />
          <input
            type="password"
            placeholder="كلمة المرور"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-teal-100 px-4 py-3 bg-linen mb-4 focus-visible:outline-2 focus-visible:outline-gold-500"
            required
          />
          <label className="flex items-center gap-2 text-sm text-muted mb-4">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="rounded border-teal-200"
            />
            <span>تذكرني في هذا الجهاز</span>
          </label>
          {error && <p className="text-brick-500 text-sm mb-4">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? 'جارٍ التحقق...' : 'دخول'}
          </Button>
        </form>

        <p className="text-sm text-muted mt-6 text-center">
          <Link to="/login" className="text-teal-600">تسجيل دخول المستخدمين</Link>
        </p>
      </Card>
    </div>
  )
}
