// frontend/src/pages/UserLoginPage.jsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import { loginUser } from '../services/authService'

export default function UserLoginPage() {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginUser(code.trim())
      localStorage.setItem('wefaq_user', JSON.stringify(data.user))
      if (data.user.needs_onboarding) {
        navigate('/complete-application', { replace: true })
      } else {
        navigate('/dashboard', { replace: true })
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-6 py-16">
      <Card>
        <h1 className="font-display text-2xl text-teal-700 mb-2">تسجيل الدخول</h1>
        <p className="text-muted text-sm mb-6">
          أدخل الكود الذي استلمته من فريق وِفاق. إن كانت هذه أول مرة تستخدمه،
          ستُطلب منك تعبئة بياناتك ثم الأسئلة لإكمال الطلب.
        </p>

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="مثال: USER001"
            className="w-full rounded-xl border border-teal-100 px-4 py-3 bg-linen mb-4 focus-visible:outline-2 focus-visible:outline-gold-500"
            required
            autoFocus
          />
          {error && <p className="text-brick-500 text-sm mb-4">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? 'جارٍ التحقق...' : 'دخول'}
          </Button>
        </form>

        <p className="text-sm text-muted mt-6 text-center">
          <Link to="/admin/login" className="text-teal-600">دخول الإداريين</Link>
        </p>
      </Card>
    </div>
  )
}
