// frontend/src/pages/AdminDashboardPage.jsx
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'
import config from '../config.json'
import {
  listUsers,
  updateUserStatus,
  addNote,
  getNotes,
  generateUserCode,
  listAdmins,
  deleteUser,
  deleteAdmin,
  createAdmin,
  assignUserCase
} from '../services/adminService'
import { getUser, getQuestions } from '../services/userService'

const STATUS_FILTERS = ['all', 'pending', 'reviewing', 'approved', 'rejected']
const AGE_FILTERS = [
  { key: 'all', label: 'كل الأعمار' },
  { key: 'under25', label: 'أقل من 25' },
  { key: '25to35', label: '25–35' },
  { key: 'over35', label: 'أكبر من 35' }
]
const SCOPE_FILTERS = [
  { key: 'all', label: 'كل الحالات' },
  { key: 'mine', label: 'حالاتي فقط' },
  { key: 'by_admin', label: 'تصفية حسب المسؤول' }
]
const EDUCATION_OPTIONS = ['ثانوي', 'دبلوم', 'بكالوريوس', 'ماجستير', 'دكتوراه']
const FINANCIAL_OPTIONS = ['بسيط', 'متوسط', 'مرتفع', 'لا يهم']

function calcAge(birthday) {
  if (!birthday) return null
  const birth = new Date(birthday)
  if (Number.isNaN(birth.getTime())) return null
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const m = today.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age -= 1
  return age
}

function matchesAgeFilter(birthday, ageFilter) {
  if (ageFilter === 'all') return true
  const age = calcAge(birthday)
  if (age === null) return false
  if (ageFilter === 'under25') return age < 25
  if (ageFilter === '25to35') return age >= 25 && age <= 35
  if (ageFilter === 'over35') return age > 35
  return true
}

const EMPTY_ADMIN_FORM = {
  full_name: '',
  phone: '',
  email: '',
  city: '',
  password: ''
}

export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const [admin, setAdmin] = useState(null)
  const [users, setUsers] = useState([])
  const [filter, setFilter] = useState('all')
  const [genderFilter, setGenderFilter] = useState('all')
  const [countryFilter, setCountryFilter] = useState('all')
  const [ageFilter, setAgeFilter] = useState('all')
  const [scopeFilter, setScopeFilter] = useState('all')
  const [assignedAdminFilter, setAssignedAdminFilter] = useState('')
  const [educationFilter, setEducationFilter] = useState('')
  const [financialFilter, setFinancialFilter] = useState('')
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [notes, setNotes] = useState([])
  const [noteText, setNoteText] = useState('')
  const [noteVisibleToUser, setNoteVisibleToUser] = useState(false)
  const [error, setError] = useState('')
  const [newUserName, setNewUserName] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [generating, setGenerating] = useState(false)
  const [panelTab, setPanelTab] = useState('users')
  const [userDetail, setUserDetail] = useState(null)
  const [questions, setQuestions] = useState(null)
  const [admins, setAdmins] = useState([])
  const [adminForm, setAdminForm] = useState(EMPTY_ADMIN_FORM)
  const [creatingAdmin, setCreatingAdmin] = useState(false)
  const [assigningUserId, setAssigningUserId] = useState(null)

  useEffect(() => {
    const stored = localStorage.getItem('wefaq_admin')
    if (!stored) {
      navigate('/admin/login')
      return
    }
    setAdmin(JSON.parse(stored))
  }, [navigate])

  useEffect(() => {
    getQuestions()
      .then((data) => setQuestions(data.questions))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!admin) return
    if (!admin.is_super_admin && scopeFilter === 'by_admin') {
      setScopeFilter('all')
      setAssignedAdminFilter('')
    }
  }, [admin, scopeFilter])

  useEffect(() => {
    if (!admin) return
    listAdmins(admin.id)
      .then((data) => setAdmins(data.admins))
      .catch(() => {})
  }, [admin])

  async function refreshUsers() {
    const params = {
      status: filter === 'all' ? undefined : filter,
      education: educationFilter || undefined,
      financial: financialFilter || undefined,
      requestingAdminId: admin.id
    }
    if (scopeFilter === 'mine') {
      params.scope = 'mine'
    } else if (scopeFilter === 'by_admin' && assignedAdminFilter && admin.is_super_admin) {
      params.assignedAdminId = Number(assignedAdminFilter)
    }
    const data = await listUsers(params)
    setUsers(data.users)
  }

  useEffect(() => {
    if (!admin) return
    refreshUsers().catch(() => setError('تعذر جلب قائمة المستخدمين'))
  }, [admin, filter, scopeFilter, assignedAdminFilter, educationFilter, financialFilter])

  useEffect(() => {
    if (!admin?.is_super_admin || panelTab !== 'admins') return
    listAdmins(admin.id)
      .then((data) => setAdmins(data.admins))
      .catch((err) => setError(err.message))
  }, [admin, panelTab])

  const countries = useMemo(() => {
    const set = new Set(users.map((u) => u.country).filter(Boolean))
    return Array.from(set).sort()
  }, [users])

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      if (genderFilter !== 'all' && u.gender !== genderFilter) return false
      if (countryFilter !== 'all' && u.country !== countryFilter) return false
      if (!matchesAgeFilter(u.birthday, ageFilter)) return false
      return true
    })
  }, [users, genderFilter, countryFilter, ageFilter])

  const visibleScopeFilters = useMemo(() => {
    if (admin?.is_super_admin) return SCOPE_FILTERS
    return SCOPE_FILTERS.filter((s) => s.key !== 'by_admin')
  }, [admin])

  function canAssignUser(user) {
    if (!admin) return false
    if (admin.is_super_admin) return true
    return user.assigned_admin_id === admin.id
  }

  function openUserNotes(userId) {
    setSelectedUserId(userId)
    getNotes(userId)
      .then((data) => setNotes(data.notes))
      .catch(() => setNotes([]))
  }

  async function openUserDetail(userId) {
    setError('')
    setSelectedUserId(userId)
    try {
      const [detail, notesData] = await Promise.all([getUser(userId), getNotes(userId)])
      setUserDetail(detail)
      setNotes(notesData.notes)
    } catch (err) {
      setError(err.message || 'تعذر جلب تفاصيل المستخدم')
    }
  }

  async function handleStatusChange(userId, newStatus) {
    try {
      await updateUserStatus(userId, newStatus, admin.id)
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, status: newStatus } : u)))
      if (userDetail?.user?.id === userId) {
        setUserDetail((prev) => prev ? { ...prev, user: { ...prev.user, status: newStatus } } : prev)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleAddNote() {
    if (!noteText.trim() || !selectedUserId) return
    try {
      await addNote(selectedUserId, admin.id, noteText.trim(), noteVisibleToUser)
      setNoteText('')
      setNoteVisibleToUser(false)
      openUserNotes(selectedUserId)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleGenerateCode() {
    setGenerating(true)
    setError('')
    try {
      const res = await generateUserCode(newUserName.trim(), admin.id)
      setGeneratedCode(res.user.code)
      setNewUserName('')
      await refreshUsers()
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  async function handleAssignCase(userId, targetAdminId) {
    if (!userId || !targetAdminId) return
    setAssigningUserId(userId)
    setError('')
    try {
      const res = await assignUserCase(userId, admin.id, Number(targetAdminId))
      setUsers((prev) => prev.map((u) => (u.id === userId ? res.user : u)))
      await refreshUsers()
    } catch (err) {
      setError(err.message)
    } finally {
      setAssigningUserId(null)
    }
  }

  async function handleDeleteUser(userId, userName) {
    if (!window.confirm(`هل أنت متأكد من حذف المستخدم "${userName}"؟`)) return
    try {
      await deleteUser(userId, admin.id)
      if (selectedUserId === userId) {
        setSelectedUserId(null)
        setNotes([])
        setUserDetail(null)
      }
      await refreshUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleCreateAdmin(e) {
    e.preventDefault()
    setCreatingAdmin(true)
    setError('')
    try {
      await createAdmin({ ...adminForm, admin_id: admin.id })
      setAdminForm(EMPTY_ADMIN_FORM)
      const data = await listAdmins(admin.id)
      setAdmins(data.admins)
    } catch (err) {
      setError(err.message)
    } finally {
      setCreatingAdmin(false)
    }
  }

  async function handleDeleteAdmin(targetId, name) {
    if (!window.confirm(`هل أنت متأكد من حذف الإداري "${name}"؟`)) return
    try {
      await deleteAdmin(targetId, admin.id)
      const data = await listAdmins(admin.id)
      setAdmins(data.admins)
    } catch (err) {
      setError(err.message)
    }
  }

  function handleLogout() {
    localStorage.removeItem('wefaq_admin')
    navigate('/admin/login')
  }

  if (!admin) return null

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display text-2xl text-teal-700">لوحة تحكم الإداري</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">{admin.full_name}</span>
          <Button variant="secondary" onClick={handleLogout}>تسجيل الخروج</Button>
        </div>
      </div>

      {admin.is_super_admin && (
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setPanelTab('users')}
            className={`px-4 py-2 rounded-xl text-sm border
              ${panelTab === 'users' ? 'bg-teal-600 text-linen border-teal-600' : 'border-teal-100 text-ink hover:bg-teal-50'}`}
          >
            المستخدمون
          </button>
          <button
            onClick={() => setPanelTab('admins')}
            className={`px-4 py-2 rounded-xl text-sm border
              ${panelTab === 'admins' ? 'bg-teal-600 text-linen border-teal-600' : 'border-teal-100 text-ink hover:bg-teal-50'}`}
          >
            إدارة الإداريين
          </button>
        </div>
      )}

      {error && <p className="text-brick-500 text-sm mb-4">{error}</p>}

      {panelTab === 'admins' && admin.is_super_admin ? (
        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <h2 className="font-display text-lg text-teal-700 mb-4">إضافة إداري جديد</h2>
            <form onSubmit={handleCreateAdmin} className="space-y-3">
              {[
                { key: 'full_name', label: 'الاسم الكامل', type: 'text' },
                { key: 'phone', label: 'رقم الجوال', type: 'tel' },
                { key: 'email', label: 'البريد الإلكتروني', type: 'email' },
                { key: 'city', label: 'المدينة', type: 'text' },
                { key: 'password', label: 'كلمة المرور', type: 'password' }
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-sm text-muted mb-1">{field.label}</label>
                  <input
                    type={field.type}
                    required
                    value={adminForm[field.key]}
                    onChange={(e) => setAdminForm((prev) => ({ ...prev, [field.key]: e.target.value }))}
                    className="w-full rounded-xl border border-teal-100 px-4 py-3 bg-linen focus-visible:outline-2 focus-visible:outline-gold-500"
                  />
                </div>
              ))}
              <Button type="submit" className="w-full" disabled={creatingAdmin}>
                {creatingAdmin ? 'جارٍ الإنشاء...' : 'إنشاء حساب إداري'}
              </Button>
            </form>
          </Card>

          <Card>
            <h2 className="font-display text-lg text-teal-700 mb-4">قائمة الإداريين</h2>
            <ul className="space-y-3">
              {admins.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 border-b border-teal-50 pb-3">
                  <div>
                    <p className="text-sm text-ink">{a.full_name}</p>
                    <p className="text-xs text-muted">{a.email} — {a.city}</p>
                    {a.is_super_admin && <p className="text-xs text-gold-700 mt-1">مدير عام</p>}
                  </div>
                  {!a.is_super_admin && a.id !== admin.id && (
                    <button
                      onClick={() => handleDeleteAdmin(a.id, a.full_name)}
                      className="text-brick-500 text-sm hover:underline"
                    >
                      حذف
                    </button>
                  )}
                </li>
              ))}
              {admins.length === 0 && <p className="text-muted text-sm">لا يوجد إداريون</p>}
            </ul>
          </Card>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2 mb-6">
            {STATUS_FILTERS.map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={`px-3 py-2 rounded-xl text-sm border whitespace-nowrap
                  ${filter === status ? 'bg-teal-600 text-linen border-teal-600' : 'border-teal-100 text-ink hover:bg-teal-50'}`}
              >
                {status === 'all' ? 'الكل' : config.statusLabels[status]}
              </button>
            ))}
            <select
              value={genderFilter}
              onChange={(e) => setGenderFilter(e.target.value)}
              className="rounded-xl border border-teal-100 px-3 py-2 bg-linen text-sm"
            >
              <option value="all">كل الأجناس</option>
              <option value="ذكر">ذكر</option>
              <option value="أنثى">أنثى</option>
            </select>
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="rounded-xl border border-teal-100 px-3 py-2 bg-linen text-sm"
            >
              <option value="all">كل الدول</option>
              {countries.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <select
              value={ageFilter}
              onChange={(e) => setAgeFilter(e.target.value)}
              className="rounded-xl border border-teal-100 px-3 py-2 bg-linen text-sm"
            >
              {AGE_FILTERS.map((a) => (
                <option key={a.key} value={a.key}>{a.label}</option>
              ))}
            </select>
            {visibleScopeFilters.map((s) => (
              <button
                key={s.key}
                onClick={() => {
                  setScopeFilter(s.key)
                  if (s.key !== 'by_admin') setAssignedAdminFilter('')
                }}
                className={`px-3 py-2 rounded-xl text-sm border whitespace-nowrap
                  ${scopeFilter === s.key ? 'bg-teal-600 text-linen border-teal-600' : 'border-teal-100 text-ink hover:bg-teal-50'}`}
              >
                {s.label}
              </button>
            ))}
            {admin.is_super_admin && scopeFilter === 'by_admin' && (
              <select
                value={assignedAdminFilter}
                onChange={(e) => setAssignedAdminFilter(e.target.value)}
                className="rounded-xl border border-teal-100 px-3 py-2 bg-linen text-sm"
              >
                <option value="">اختر المسؤول</option>
                {admins.map((a) => (
                  <option key={a.id} value={a.id}>{a.full_name}</option>
                ))}
              </select>
            )}
            <select
              value={educationFilter}
              onChange={(e) => setEducationFilter(e.target.value)}
              className="rounded-xl border border-teal-100 px-3 py-2 bg-linen text-sm"
            >
              <option value="">المستوى التعليمي</option>
              {EDUCATION_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
            <select
              value={financialFilter}
              onChange={(e) => setFinancialFilter(e.target.value)}
              className="rounded-xl border border-teal-100 px-3 py-2 bg-linen text-sm"
            >
              <option value="">المستوى المادي</option>
              {FINANCIAL_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>

          <Card className="mb-6">
            <h2 className="font-display text-lg text-teal-700 mb-3">توليد كود مستخدم جديد</h2>
            <p className="text-muted text-sm mb-4">
              أدخل اسم المتقدم إن رغبت، أو اترك الحقل فارغاً ليُحفظ كـ «متقدم جديد»، ثم ولّد الكود.
            </p>
            <div className="flex gap-3 items-start flex-wrap">
              <input
                type="text"
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                placeholder="متقدم جديد"
                className="flex-1 min-w-[220px] rounded-xl border border-teal-100 px-4 py-3 bg-linen focus-visible:outline-2 focus-visible:outline-gold-500"
              />
              <Button onClick={handleGenerateCode} disabled={generating}>
                {generating ? 'جارٍ التوليد...' : 'توليد الكود'}
              </Button>
            </div>
            {generatedCode && (
              <p className="mt-3 text-sm text-ink">
                الكود الجديد: <span className="font-bold text-gold-700">{generatedCode}</span>
              </p>
            )}
          </Card>

          <div className="grid md:grid-cols-3 gap-6">
            <Card className="md:col-span-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted border-b border-teal-100">
                    <th className="text-right py-2">الاسم</th>
                    <th className="text-right py-2">الكود</th>
                    <th className="text-right py-2">المسؤول</th>
                    <th className="text-right py-2">الحالة</th>
                    <th className="text-right py-2">إجراء</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((u) => (
                    <tr key={u.id} className="border-b border-teal-50">
                      <td className="py-3">
                        <button
                          onClick={() => openUserDetail(u.id)}
                          className="text-teal-700 hover:underline text-right"
                        >
                          {u.full_name}
                        </button>
                      </td>
                      <td className="py-3">{u.code}</td>
                      <td className="py-3">
                        {canAssignUser(u) ? (
                          <select
                            value={u.assigned_admin_id ? String(u.assigned_admin_id) : ''}
                            onChange={(e) => {
                              const nextId = e.target.value
                              if (nextId && Number(nextId) !== u.assigned_admin_id) {
                                handleAssignCase(u.id, nextId)
                              }
                            }}
                            disabled={assigningUserId === u.id}
                            className="w-full min-w-[120px] max-w-[160px] border border-teal-100 rounded-lg px-2 py-1 text-sm bg-linen disabled:opacity-60"
                          >
                            <option value="">—</option>
                            {admins.map((a) => (
                              <option key={a.id} value={a.id}>{a.full_name}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-muted">{u.assigned_admin_name || '—'}</span>
                        )}
                      </td>
                      <td className="py-3"><StatusBadge status={u.status} /></td>
                      <td className="py-3 whitespace-nowrap">
                        <div className="inline-flex flex-row flex-nowrap items-center gap-2">
                          <select
                            value={u.status}
                            onChange={(e) => handleStatusChange(u.id, e.target.value)}
                            className="shrink-0 border border-teal-100 rounded-lg px-2 py-1 text-sm bg-linen"
                          >
                            {Object.keys(config.statusLabels).map((s) => (
                              <option key={s} value={s}>{config.statusLabels[s]}</option>
                            ))}
                          </select>
                          <button
                            onClick={() => openUserNotes(u.id)}
                            className="shrink-0 text-teal-600 text-sm hover:underline"
                          >
                            الملاحظات
                          </button>
                          <button
                            onClick={() => handleDeleteUser(u.id, u.full_name)}
                            className="shrink-0 text-brick-500 text-sm hover:underline"
                          >
                            حذف
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredUsers.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-muted">لا يوجد طلبات ضمن هذا التصنيف</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </Card>

            <Card>
              <h2 className="font-display text-lg text-teal-700 mb-4">الملاحظات</h2>
              {!selectedUserId ? (
                <p className="text-muted text-sm">اختر مستخدماً لعرض ملاحظاته</p>
              ) : (
                <>
                  <ul className="space-y-2 mb-4 max-h-48 overflow-y-auto">
                    {notes.map((n) => (
                      <li key={n.id} className="text-sm bg-teal-50 rounded-lg p-2">
                        <p>{n.note_text}</p>
                        <p className="text-xs text-muted mt-1">
                          {n.admin_name || 'إداري'}
                          {' · '}
                          {n.is_visible_to_user ? 'مرئية للمستخدم' : 'داخلية'}
                        </p>
                      </li>
                    ))}
                    {notes.length === 0 && <p className="text-muted text-sm">لا توجد ملاحظات بعد</p>}
                  </ul>
                  <textarea
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    rows={2}
                    placeholder="أضف ملاحظة..."
                    className="w-full rounded-xl border border-teal-100 px-3 py-2 bg-linen mb-2"
                  />
                  <label className="flex items-center gap-2 text-sm text-muted mb-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={noteVisibleToUser}
                      onChange={(e) => setNoteVisibleToUser(e.target.checked)}
                      className="accent-teal-600"
                    />
                    إظهار الملاحظة للمستخدم
                  </label>
                  <Button onClick={handleAddNote} className="w-full">إضافة الملاحظة</Button>
                </>
              )}
            </Card>
          </div>

          {userDetail && (
            <Card className="mt-6">
              <div className="flex items-start justify-between mb-4 gap-3">
                <div>
                  <h2 className="font-display text-lg text-teal-700">تفاصيل المتقدم</h2>
                  <p className="text-sm text-muted mt-1">
                    {userDetail.user.full_name} — {userDetail.user.code}
                  </p>
                </div>
                <button
                  onClick={() => setUserDetail(null)}
                  className="text-sm text-muted hover:text-ink"
                >
                  إغلاق
                </button>
              </div>

              <div className="grid sm:grid-cols-2 gap-3 text-sm mb-6">
                <p><span className="text-muted">الجنس:</span> {userDetail.user.gender || '—'}</p>
                <p><span className="text-muted">الدولة:</span> {userDetail.user.country || '—'}</p>
                <p><span className="text-muted">تاريخ الميلاد:</span> {userDetail.user.birthday || '—'}</p>
                <p><span className="text-muted">العمر:</span> {calcAge(userDetail.user.birthday) ?? '—'}</p>
                <p><span className="text-muted">الجوال:</span> {userDetail.user.phone || '—'}</p>
                <p><span className="text-muted">البريد:</span> {userDetail.user.email || '—'}</p>
                <p><span className="text-muted">ولي الأمر:</span> {userDetail.user.guardian_relation || '—'}</p>
                <p><span className="text-muted">جوال ولي الأمر:</span> {userDetail.user.guardian_phone || '—'}</p>
                <p><span className="text-muted">تاريخ التقديم:</span> {userDetail.user.created_at ? new Date(userDetail.user.created_at).toLocaleString('ar') : '—'}</p>
                <p className="flex items-center gap-2">
                  <span className="text-muted">الحالة:</span>
                  <StatusBadge status={userDetail.user.status} />
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-display text-base text-teal-700 mb-3">إجابات الاختيار</h3>
                  {userDetail.mcq_answers ? (
                    <ul className="space-y-2 text-sm">
                      {(questions?.mcq || []).map((q, idx) => {
                        const key = `q${idx + 1}`
                        return (
                          <li key={key} className="bg-teal-50 rounded-lg p-3">
                            <p className="text-muted mb-1">{q.question}</p>
                            <p className="text-ink">{userDetail.mcq_answers[key] || '—'}</p>
                          </li>
                        )
                      })}
                      {!questions?.mcq && Object.entries(userDetail.mcq_answers).map(([key, val]) => (
                        <li key={key} className="bg-teal-50 rounded-lg p-3">
                          <p className="text-muted mb-1">{key}</p>
                          <p className="text-ink">{val || '—'}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted text-sm">لا توجد إجابات اختيار بعد</p>
                  )}
                </div>

                <div>
                  <h3 className="font-display text-base text-teal-700 mb-3">الإجابات المفتوحة</h3>
                  {userDetail.open_answers ? (
                    <ul className="space-y-2 text-sm">
                      {(questions?.open || []).map((q, idx) => {
                        const key = `q${idx + 1}`
                        return (
                          <li key={key} className="bg-teal-50 rounded-lg p-3">
                            <p className="text-muted mb-1">{q}</p>
                            <p className="text-ink whitespace-pre-wrap">{userDetail.open_answers[key] || '—'}</p>
                          </li>
                        )
                      })}
                      {!questions?.open && Object.entries(userDetail.open_answers).map(([key, val]) => (
                        <li key={key} className="bg-teal-50 rounded-lg p-3">
                          <p className="text-muted mb-1">{key}</p>
                          <p className="text-ink whitespace-pre-wrap">{val || '—'}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-muted text-sm">لا توجد إجابات مفتوحة بعد</p>
                  )}
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
