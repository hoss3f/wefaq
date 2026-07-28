---
name: wefaq-project
description: >-
  Complete technical knowledge base for the WEFAQ (وِفاق) matchmaking platform.
  Use when working on this repo: backend Flask APIs, React frontend, database
  models, onboarding flow, admin panel, JSON sync, or any feature change.
  Gives an AI full awareness of every file, its role, and implementation logic.
---

# WEFAQ (وِفاق) — Full Project for AI Assistants

This document is the **authoritative technical map** of the WEFAQ codebase.
If you are an AI (ChatGPT, Cursor, Claude, etc.), treat this as your system
manual: architecture, every file’s role, business rules, and how pieces connect.

---

## 1. What the product is

**WEFAQ** is a respectful Islamic matchmaking platform (Arabic UI, RTL).

- Applicants do **not** self-register freely in production UX.
- An **admin generates a user code**; the applicant logs in with that code.
- On **first login**, the applicant must complete: personal profile → MCQ → open essays → review → submit.
- After submit, status becomes `reviewing`; the user dashboard shows full application details.
- Admins review applications, change status, and leave notes (internal or visible to the user).
- A **Super Admin** manages other admins; creating/deleting admins syncs `admins.json`.

**Stack**
- Backend: Python 3, Flask, Flask-SQLAlchemy, Flask-CORS, SQLite, Werkzeug password hashing
- Frontend: React 18, React Router 6, Vite 5, Tailwind CSS 3
- Aux data: JSON files under `backend/data/` (seed + sync mirrors)

**Default ports**
- API: `http://localhost:5000` (prefix `/api`)
- UI: `http://localhost:5173`

**Default Super Admin (dev only)**
- Email: `super@wefaq.com`
- Password: `SuperAdmin@2026`
- Seeded from `backend/data/admins.json` on first app start if missing in DB

---

## 2. High-level architecture

```
Browser (React)
    │  fetch JSON
    ▼
frontend/src/services/*  →  config.apiBaseUrl = http://localhost:5000/api
    │
    ▼
Flask Blueprints (auth / user / admin / notifications)
    │
    ├── SQLAlchemy models → SQLite (backend/instance/wefaq.db)
    └── utils sync helpers → backend/data/*.json
```

**Auth model (current):** no JWT/session server-side. Frontend stores:
- `localStorage.wefaq_user` after user login
- `localStorage.wefaq_admin` after admin login  
Sensitive admin actions pass `admin_id` in query/body; Super Admin checks use DB flags (`is_super_admin`).

---

## 3. Core domain concepts & business rules

### User statuses
`pending` → `reviewing` → `approved` | `rejected`

- Admin-generated code user starts as `pending` with optional/default name.
- Completing application (`POST /users/<id>/complete` or answers save) sets `reviewing`.
- Admin status change creates a `Notification` for the user.

### Placeholder name
Constant `DEFAULT_USER_NAME = 'متقدم جديد'` in `config.py`.

- Used when generating a code with empty `full_name`.
- Treated as **not a real name**: `is_placeholder_name()` / `user_needs_onboarding()`.
- UI shows it as **placeholder text**, not as a filled value the user must clear.

### Onboarding detection (`user_needs_onboarding`)
Returns `true` if any of:
- Missing real name (empty or placeholder), email, phone, birthday, gender, country
- Missing MCQ answers (no row or empty `q1`)

Returned on login and `GET /users/<id>` as `needs_onboarding`.

### First-time code flow
1. Admin: `POST /admin/users/generate-code`
2. User: `POST /auth/user-login` → `needs_onboarding: true`
3. Frontend navigates to `/complete-application`
4. User: `POST /users/<id>/complete` with `{ personal, mcq, open }`
5. Frontend navigates to `/dashboard` with full details

### Notes visibility
`AdminNote.is_visible_to_user`:
- `false` = internal (admin only)
- `true` = shown on user dashboard via `visible_notes` in `GET /users/<id>`

### Super Admin powers
- `GET /admin/admins?admin_id=`
- `DELETE /admin/users/<id>` / `DELETE /admin/admins/<id>`
- Cannot delete self or another super admin
- Create admin via `POST /admin/create` (also syncs JSON)

---

## 4. Database schema (SQLAlchemy)

Defined in `backend/models.py`. Shared `db = SQLAlchemy()`.

| Table | Model | Purpose |
|-------|--------|---------|
| `users` | `User` | Applicant; unique `code`; profile fields; `status`; timestamps |
| `mcq_answers` | `MCQAnswer` | One row per user; `q1`–`q4` short strings |
| `open_answers` | `OpenAnswer` | One row per user; `q1`–`q4` text essays |
| `admins` | `Admin` | Staff; `email` unique; `password_hash`; `is_super_admin`; `is_active` |
| `admin_notes` | `AdminNote` | Note on a user by an admin; `is_visible_to_user` |
| `notifications` | `Notification` | Messages to user and/or admin; `is_read` |

Relationships use `cascade='all, delete-orphan'` so deleting a user removes answers, notes, notifications.

**Schema changes in development:** delete `backend/instance/wefaq.db` and restart; `db.create_all()` recreates tables; Super Admin is re-seeded.

---

## 5. Backend file 

### `backend/app.py`
- Factory `create_app()`: config, CORS (`/api/*`), `db.init_app`, `register_routes`, `db.create_all()`, `seed_super_admin()`.
- `seed_super_admin()`: reads `admins.json` → `super_admin`; creates Admin with hashed password if email not in DB.
- `__main__`: optional JSON load printout, then `app.run(debug=True)`.

### `backend/config.py`
- Paths: `BASE_DIR`, `DATA_DIR`, `INSTANCE_DIR` (ensures instance folder exists).
- `SQLALCHEMY_DATABASE_URI` → SQLite file `instance/wefaq.db`.
- `SECRET_KEY` (dev placeholder).
- `DEFAULT_USER_NAME = 'متقدم جديد'`.

### `backend/models.py`
- All ORM tables (see schema above).
- `AdminNote.is_visible_to_user` default `False`.

### `backend/utils.py`
- JSON IO: `read_json_file` / `write_json_file` (UTF-8).
- Loaders: `load_admins`, `load_questions`, `load_users`.
- Passwords: `hash_password` / `verify_password` (Werkzeug).
- `generate_user_code(User)` → next unique `USER###` from **highest existing number** (not row count; avoids collisions after deletes).
- `is_placeholder_name`, `user_needs_onboarding`.
- User JSON sync: `sync_user_to_json`, `remove_user_from_json`.
- Admin JSON sync: `_normalize_admins_file` (strips any legacy `code` on super_admin), `sync_admin_to_json(admin, plain_password=...)`, `remove_admin_from_json(email)`.
  - Super admin lives under key `super_admin`.
  - Regular admins in array `admins` with plaintext password stored **only at create time** (mirror of seed style; not production-safe).

### `backend/routes/__init__.py`
- Imports blueprints; `register_routes(app)` registers all four.

### `backend/routes/auth_routes.py` — prefix `/api/auth`
- `POST /user-login`: body `{ code }` → user payload + `needs_onboarding`.
- `POST /admin-login`: body `{ email, password }` → admin payload including `is_super_admin`; rejects inactive.

### `backend/routes/user_routes.py` — prefix `/api`
- `GET /questions`: from `questions.json`.
- `POST /users/register`: full registration (used less in UX; still valid API); rejects placeholder name.
- `POST /users/<id>/answers`: upsert MCQ/Open; set status `reviewing`; sync JSON.
- `POST /users/<id>/complete`: **primary first-login completion** — validate personal + all MCQ q1–q4, upsert answers, `reviewing`, return user + answers with `needs_onboarding: false`.
- `GET /users/<id>`: profile + answers + `visible_notes` + `needs_onboarding`.
- `PUT /users/<id>`: update personal fields; reject placeholder name for `full_name`.
- Helpers: `_parse_birthday`, `_apply_personal_data`, `_upsert_answers`, `_user_payload`.

### `backend/routes/admin_routes.py` — prefix `/api/admin`
- `GET /users`: list users (optional `?status=`); includes `birthday`, `created_at` for client filters.
- `PUT /users/<id>/status`: set status + optional reason; create user notification.
- `POST/GET /users/<id>/notes`: add note with `is_visible_to_user`; list notes with `admin_name`.
- `POST /create`: create non-super admin; `sync_admin_to_json` with plaintext password.
- `GET /admins?admin_id=`: Super Admin only.
- `DELETE /users/<id>`: Super Admin; also `remove_user_from_json`.
- `DELETE /admins/<id>`: Super Admin; block self/super; `remove_admin_from_json`.
- `POST /users/generate-code`: optional name → default `DEFAULT_USER_NAME`; sync user JSON.
- `_require_super_admin(admin_id)` helper.

### `backend/routes/notification_routes.py` — prefix `/api/notifications`
- `GET /user/<id>`: list notifications newest first.
- `PUT /<id>/read`: mark read.

### `backend/data/admins.json`
```json
{
  "super_admin": { "full_name", "phone", "email", "city", "password" },
  "admins": [ { "full_name", "phone", "email", "city", "password" } ]
}
```
No admin login `code` field.

### `backend/data/questions.json`
- `mcq`: array of `{ id, question, options[] }` (ids 1–4 map to `q1`–`q4`).
- `open`: array of 4 question strings (index+1 → `q1`–`q4`).

### `backend/data/users.json`
- Mirror list of users for convenience/backup sync; source of truth for runtime is SQLite.

### `backend/instance/wefaq.db`
- Runtime SQLite DB (gitignored typically).

### `backend/requirements.txt` and root `requirements.txt`
- Should list: Flask, Flask-CORS, Flask-SQLAlchemy, Werkzeug (explicit for password helpers).

---

## 6. Frontend file 

### Entry & config
| File | Role |
|------|------|
| `frontend/index.html` | HTML shell; mounts `#root` |
| `frontend/src/main.jsx` | `createRoot`, imports `index.css`, renders `<App />` |
| `frontend/src/App.jsx` | `BrowserRouter` + routes (see routing table) |
| `frontend/src/config.json` | `apiBaseUrl`, `registrationSteps`, `personalFields` (incl. full_name placeholder), `statusLabels` |
| `frontend/src/index.css` | Tajawal/Aref Ruqaa fonts, linen background, mashrabiya utility, focus-visible, reduced-motion |
| `frontend/tailwind.config.js` | Brand colors: linen, ink, muted, teal, gold, brick; display/body fonts; mashrabiya SVG pattern |
| `frontend/vite.config.js` | React plugin; dev server port 5173 |
| `frontend/postcss.config.js` | Tailwind + autoprefixer |
| `frontend/package.json` | scripts: `dev`, `build`, `preview` |

### Routing (`App.jsx`)
| Path | Page | Logic |
|------|------|--------|
| `/` | `HomePage` | Branding; CTA **دخول بالكود** → `/login`; **دخول الإداريين** → `/admin/login` |
| `/login` | `UserLoginPage` | Code login; if `needs_onboarding` → `/complete-application` else `/dashboard` |
| `/complete-application` | `CompleteApplicationPage` | Wizard for first-time code users |
| `/register` | `RegisterPage` | Legacy/self-register wizard (API register + answers); not primary home CTA |
| `/dashboard` | `UserDashboardPage` | If still needs onboarding → redirect complete; else profile + answers + notes |
| `/admin/login` | `AdminLoginPage` | Email/password → store admin → `/admin/dashboard` |
| `/admin/dashboard` | `AdminDashboardPage` | Users, filters, notes, code gen; Super Admin tab for admins |

### Services
| File | Role |
|------|------|
| `services/api.js` | Shared `fetch` wrapper; throws `Error(message)` on non-OK; exports GET/POST/PUT/DELETE |
| `services/authService.js` | `loginUser`, `loginAdmin` |
| `services/userService.js` | questions, register, answers, **completeApplication**, getUser, updateUser, notifications |
| `services/adminService.js` | listUsers, updateUserStatus, addNote/getNotes, generateUserCode, listAdmins, deleteUser/Admin, createAdmin |

### Components
| File | Role |
|------|------|
| `Button.jsx` | Primary/secondary styled button |
| `Card.jsx` | Content panel wrapper |
| `FormField.jsx` | Dynamic field from config (`text`/`select`/`date`/…); supports `placeholder` |
| `ProgressSteps.jsx` | Step circles + **connecting progress lines** + “step X of N” |
| `StatusBadge.jsx` | Colored label from `config.statusLabels` |
| `NotificationList.jsx` | Renders notification list |
| `Navbar.jsx` | Brand + links to user login |
| `MashrabiyaDivider.jsx` | Decorative mashrabiya band |

### Pages — logic summary

**`HomePage.jsx`**  
Marketing hero; two CTAs with distinct routes (user vs admin).

**`UserLoginPage.jsx`**  
Posts code; saves `wefaq_user`; branches on `needs_onboarding`.

**`CompleteApplicationPage.jsx`**  
Loads session user + questions; if already complete → dashboard.  
Steps 0–3 from `registrationSteps`.  
Prefills personal data but clears placeholder name to empty + placeholder UI.  
Validates required personal + all MCQ before advancing.  
Review step shows personal + MCQ + **open essays**.  
Submit → `completeApplication` → dashboard with `justCompleted` state.

**`RegisterPage.jsx`**  
Similar wizard but creates a **new** user via `registerUser` then `saveAnswers` (not the code-onboarding path).

**`UserDashboardPage.jsx`**  
Parallel fetch: user, notifications, questions.  
Shows timeline (created_at, +3 days expected response), editable profile, visible admin notes, full MCQ/open application details.

**`AdminLoginPage.jsx`**  
Admin credentials → `wefaq_admin` localStorage.

**`AdminDashboardPage.jsx`**  
- Status filter buttons + client-side gender/country/age filters (age from birthday).  
- Generate code: single input placeholder `متقدم جديد`, one generate button (empty → backend default name).  
- User table: click name → full detail card (getUser + questions); status select; notes panel; Super Admin delete.  
- Notes: author name, internal vs visible checkbox.  
- Super Admin tab: create admin form, list admins, delete with confirm.

---

## 7. End-to-end flows (for implementers)

### A) Generate code → first login → complete → dashboard
```
AdminDashboard generateUserCode('')
  → POST /admin/users/generate-code { full_name: "" }
  → User(code, full_name="متقدم جديد", status=pending)

UserLoginPage loginUser(code)
  → needs_onboarding true → /complete-application

CompleteApplicationPage
  → POST /users/:id/complete { personal, mcq, open }
  → status reviewing, needs_onboarding false → /dashboard
```

### B) Admin reviews
```
listUsers → updateUserStatus → Notification created
addNote(..., isVisibleToUser=true) → appears in user visible_notes
```

### C) Super Admin creates admin
```
POST /admin/create → DB insert + sync_admin_to_json → admins.json admins[] grows
DELETE /admin/admins/:id → DB delete + remove_admin_from_json
```

---

## 8. Design system constraints

When changing UI, **preserve** existing brand tokens:
- Background linen `#FAF8F4`, ink `#22302C`, teal primary `#1F4741`, gold accent `#C9A15A`, brick errors `#B4543A`
- Fonts: display `Aref Ruqaa`, body `Tajawal`
- Rounded-xl inputs/cards; Arabic copy; RTL layout assumed by browser `dir`/CSS

Do not invent a new purple/cream AI-generic theme unless explicitly asked.

---

## 9. Important implementation gotchas

1. **SQLite schema**: `create_all()` does not migrate; delete DB file after model column adds in dev.
2. **Windows console**: Arabic `print` may need `PYTHONIOENCODING=utf-8`.
3. **MCQ key mapping**: question `id` from JSON → answer key `q{id}` (q1…q4).
4. **Open answers**: array index `i` → `q{i+1}`.
5. **User codes**: `generate_user_code` must use max existing `USER###` number, not `query.count()`, or deleted users cause duplicate-code 500 errors on generate.
6. **No server sessions**: never assume auth beyond what frontend sends (`admin_id`, user id in URL).
7. **Register vs Complete**: `/register` creates a new code; `/complete-application` fills an **existing** code user.
8. **JSON passwords**: stored for seed/sync convenience only — not a security model for production.
9. **CORS**: enabled for all origins on `/api/*` in development.

---

## 10. How an AI should modify this project

1. Prefer extending existing routes/services/pages over new parallel stacks.
2. Keep Arabic UX strings consistent with current tone.
3. If adding a DB column: update `models.py`, document here, and note DB reset for local SQLite.
4. If adding admin CRUD that should persist outside DB: update `utils` JSON sync.
5. If changing onboarding rules: update `user_needs_onboarding` **and** frontend redirects together.
6. After API changes: update matching `*Service.js` and the consuming page.
7. Update this `SKILL.md` when architecture or file roles change.

---

## 11. Quick file index (all first-party source)

```
README.md                          Human-facing project overview
SKILL.md                           This AI library (you are here)
requirements.txt                   Python deps (root)
backend/requirements.txt           Same deps for backend-local installs
backend/app.py                     Flask app factory + seed
backend/config.py                  Paths, SQLite URI, DEFAULT_USER_NAME
backend/models.py                  ORM schema
backend/utils.py                   Hashing, codes, JSON sync, onboarding helpers
backend/data/admins.json           Super admin seed + admins list
backend/data/questions.json        MCQ + open question bank
backend/data/users.json            Synced users mirror
backend/routes/__init__.py         Blueprint registration
backend/routes/auth_routes.py      User/admin login
backend/routes/user_routes.py      Questions, register, complete, CRUD user
backend/routes/admin_routes.py     Users admin ops, notes, codes, admins CRUD
backend/routes/notification_routes.py  User notifications
frontend/src/App.jsx               Routes
frontend/src/main.jsx              React bootstrap
frontend/src/config.json           API URL + form/step config
frontend/src/index.css             Global styles
frontend/src/pages/*               Screens listed above
frontend/src/components/*          Reusable UI
frontend/src/services/*            API clients
```

---

*Last aligned with the codebase after admin/user enhancements, first-login onboarding, progress tracker, admin JSON sync, and home CTAs (user code vs admin login).*
