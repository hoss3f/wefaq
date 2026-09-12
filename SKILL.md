---
name: wefaq-project-library
description: >-
  Complete technical knowledge base for the WEFAQ (وِفاق) matchmaking platform.
  Use when working on this repo: backend Flask APIs, React frontend, PostgreSQL
  models, onboarding wizard, matching engine, admin panel, or any feature change.
  Gives an AI full awareness of every file, its role, and implementation logic.
---

# WEFAQ (وِفاق) — Full Project Library for AI Assistants

This document is the **authoritative technical map** of the WEFAQ codebase.
If you are an AI coding agent, treat this as your system manual: architecture,
every file's role, business rules, current bugs, and how the pieces connect.

> **Read §9 (gotchas) and §13 (recent changes) before writing any code.** Several
> parts of the repo are mid-migration and the code does not match older docs.

---

## 1. Project overview

**WEFAQ** is a respectful Islamic ("halal") matchmaking platform. Arabic UI, RTL throughout.

**Target users:** applicants seeking marriage (invited by code), plus admins/supervisors who review them.

**Core functionality**
- Applicants do **not** self-register in the intended production UX.
- An **admin generates a user code**; the applicant logs in with that code alone (no password).
- On **first login**, the applicant works through a **dynamic, one-question-at-a-time onboarding wizard** (Typeform-style, driven by `questions.json`'s `onboarding` config) covering personal data, an extended profile, partner preferences, compatibility MCQs, and 4 open essays → submit.
- After submit the status becomes `reviewing`; a welcome email is attempted; the user dashboard shows the full application.
- Admins review applications, change status, leave notes (internal or user-visible), assign/reassign cases, and see **rule-based (non-AI) compatibility suggestions** for each applicant.
- Once an admin sets a user to `approved`, that user is routed to a **candidate browsing screen** (`/matches`) showing privacy-safe, opposite-gender candidate cards ranked by compatibility percentage.
- A **Super Admin** manages other admins.

**Default ports**
- API: `http://localhost:5000` (prefix `/api`)
- UI: `http://localhost:5173`

**Default Super Admin (dev only)** — `super@wefaq.com` / `SuperAdmin@2026`, defined in `backend/models/data/admins.json`. It is **only** inserted by the manual `seed_database()` call (see §5), not automatically at boot.

---

## 2. High-level architecture

```
Browser (React 18 + Vite + Tailwind)
    │  fetch JSON / multipart
    ▼
frontend/src/services/*  →  BASE_URL = VITE_API_BASE_URL || config.apiBaseUrl
    │                         (default http://localhost:5000/api)
    ▼
Flask blueprints (auth / user / admin / notification / matching)
    │
    ├── security.py            auth+authorization decorators, input sanitation
    ├── models/ (package)      SQLAlchemy ORM → PostgreSQL (DATABASE_URL)
    ├── services/matching_service.py   read-only compatibility scoring
    ├── utils.py               hashing, codes, photos, email, JSON sync, activity log
    ├── models/data/*.json     question bank (+ legacy admin/user JSON mirrors)
    └── uploads/               applicant photos, served at GET /uploads/<filename>
```

**Persistence:** PostgreSQL is the **only** database. `backend/config.py` raises `RuntimeError` at import if `DATABASE_URL` is not set. There is no SQLite fallback, and `backend/instance/` now holds only `logs/system.log`.

**Auth model:** no JWT, no server sessions. The frontend stores:
- `localStorage.wefaq_user` after user login (`{id, code, full_name, status, needs_onboarding, photo_url}`)
- `localStorage.wefaq_admin` after admin login (`{id, full_name, email, city, is_super_admin}`)

`buildAuthHeaders()` in `frontend/src/services/api.js` attaches `X-Admin-Id` and `X-User-Code` to **every** request (JSON and multipart). Server-side, `backend/security.py` centralizes the checks: `admin_required` / `super_admin_required` decorators, `get_active_admin`, `get_active_super_admin`, `get_user_by_code`, `can_read_user`, `require_user_self`, `can_access_notification`.

**Two authorization patterns coexist** — see §9.2.

---

## 3. Core domain concepts & business rules

### User statuses
`pending` → `reviewing` → `approved` | `rejected`

- Admin-generated code user starts as `pending` with a placeholder name.
- Completing the application (`POST /users/<id>/complete` or `POST /users/<id>/answers`) sets `reviewing`.
- An admin status change creates a `Notification` row for the user and an `ActivityLog` entry.
- `approved` unlocks the `/matches` candidate browser for that user.

### Placeholder name
`DEFAULT_USER_NAME = 'متقدم جديد'` in `config.py`.
- Used when generating a code with an empty `full_name`.
- Treated as **not a real name**: `is_placeholder_name()` / `user_needs_onboarding()`; rejected by `_apply_personal_data` and `PUT /users/<id>`.
- The UI renders it as placeholder text, never as a pre-filled value the user must clear (`displayName()` helper in `CompleteApplicationPage.jsx` and `UserDashboardPage.jsx`).

### Onboarding detection (`user_needs_onboarding`, `utils.py`)
Returns `true` if **any** of:
- Real name missing/placeholder, or `birthday`, `gender`, `country` missing on `User`
- `UserProfile.details` is missing any of: `nationality`, `profession`, `marital_status`, `marriage_timeline`, `height`, `weight`
- No `OpenAnswer` row, or any of `q1`–`q4` is empty

It **does not check `MCQAnswer`** — a user can be fully onboarded with zero MCQ answers. Returned on login and `GET /users/<id>` as `needs_onboarding`.

### Dynamic onboarding wizard (`questions.json` → `onboarding`)
`backend/models/data/questions.json` has an `onboarding` object driving `CompleteApplicationPage.jsx` as a single-question-per-screen flow.

- `onboarding.ui` — Arabic microcopy (`continue`, `submit`, `submitting`, `back`, `progress`, `validation_error`, `loading`, `open_placeholder`)
- `onboarding.other_option` — label for the free-text "other" choice in `search` fields
- `onboarding.steps[]` — ordered question definitions. Each has `key`, `type`, `title`, `required`, optional `description` / `placeholder` / `options` / `suffix`, and optional `storage`.

**Step `type` values handled by `renderQuestion()`:** `gender`, `text`, `contact`, `date`, `search`, `choice`, `chips`, `number`, `slider`, `textarea`, `preferences`. Anything else falls through to a plain text input.

**`storage` routing** (the `getValue`/`setValue` pair in `CompleteApplicationPage.jsx`):
| `storage` | Destination |
|---|---|
| `"personal"` | local `personal` state → `User` columns (`full_name`, `birthday`, `gender`, `country`, `phone`, `email`) |
| `"mcq"` | local `mcqAnswers` state → `MCQAnswer` |
| *(omitted)* | local `details` state → `UserProfile.details[key]` |

**Special step types**
- `contact` — one screen for phone + email. A country dial-code `<select>` (from the step's `country_codes[]`, e.g. `{code:"+974", name:"قطر"}`) beside the phone input, plus an email input. It has a dedicated branch in `renderQuestion()` (not the generic `getValue`/`setValue` path) because it writes two `personal` keys: `phone` is the dial code concatenated with the digits, `email` is written directly. Phone is required; email is optional. On load, an existing `user.phone` is split back into code + number by the `phoneParsed` effect.
- `preferences` — nested `fields[]` (dual-range sliders, chips, search) for partner preferences (age min/max, marital preference, ethnicity preference, height min/max, nationality preference). All stored in `UserProfile.details` under each field's `key` (or `min_key`/`max_key` for ranges). Range defaults are pre-seeded into `details` on load. **These preferences are collected but not yet consumed by the matching engine.**
- `show_if` — array of `{key, equals}` rules ANDed together, evaluated against `details` only (e.g. `graduation_date` shows when `profession == "طالب"`; `kids_count` when previously married **and** has children).

**Steps appended at runtime by the page (not in `onboarding.steps`):**
1. One `choice` step per `questions.json` `mcq` entry that has `"matching": true`, with `storage: "mcq"` and key `q{id}`.
2. One `textarea` step per `questions.json` `open` entry (key `open_{n}`, `openNumber` set) → `OpenAnswer.q1`–`q4`.

Submit calls `completeApplication(userId, { ...personal, profile_details: details }, mcqAnswers, answers)` → `POST /users/<id>/complete`.

> ⚠️ **No `mcq` entry in the current `questions.json` carries `"matching": true`**, so today the wizard appends zero MCQ steps and `MCQAnswer` stays empty for wizard users. See §9.3.

### Compatibility matching (rewritten — percentage based)
`backend/services/matching_service.py` is fully data-driven and MCQ-only:

- `matching_questions()` → the `questions.json` `mcq` entries where `matching is True`. **Python constants no longer define the inputs; the question bank does.**
- `_answer_for(answer_row, question)` reads `MCQAnswer.answers[key]` first, falling back to the legacy `q1`–`q4` column. `key` is the question's `answer_key` or `q{id}`.
- `score_mcq_similarity(a, b)` → equal-weight exact-match percentage over questions **both** users answered; unanswered questions are "not applicable" and excluded from the denominator. Returns `percentage`, `matching_answers`, `total_applicable_questions`, `configured_questions`, `breakdown`.
- `score_pair(a, b)` → `{compatibility_percentage, total_score (== percentage), max_score: 100, eligible, mandatory_passed, stages: {mcq}}`. **Opposite gender is the only gate** (`user_a.gender != user_b.gender`).
- `_candidate_summary(user, private=False)` → `gender`, `country`, `age`, `nationality`, `profession`, `marital_status`, `marriage_timeline`, `height`, `profile_description` (the user's `OpenAnswer.q1`). When `private=False` it also includes `id` and `status`. **It never includes `full_name`, `code`, or `photo`.**
- `find_matches_for_user(user, candidates, ...)` → filters to the opposite gender, scores, filters by `min_score`, sorts descending, truncates to `limit`.

**Removed in the rewrite:** eligibility scoring (country/age points), open-answer keyword similarity, `confidence_label`, `compute_age` is kept but the 30/40/30 point model is gone.

### Notes visibility
`AdminNote.is_visible_to_user`: `false` = internal (admin only); `true` = shown on the user dashboard via `visible_notes` in `GET /users/<id>`.

### Super Admin powers
- `GET /admin/admins?admin_id=` (full admin list; other admins get names only)
- `POST /admin/create` (create non-super admin; also syncs `admins.json`)
- `DELETE /admin/admins/<id>` — cannot delete self or another super admin
- `scope=by_admin` filtering in the admin dashboard

### Admin powers (any active admin)
- `DELETE /admin/users/<id>` — delete applicants
- `PUT /admin/users/<id>/status`, add/list notes, reassign own cases
- `GET /admin/users/<id>/matches`, `GET /admin/matches/pair`

---

## 4. Technology stack

| Layer | Tech |
|---|---|
| Language (backend) | Python 3.10+ |
| Backend framework | Flask 3.1.3 |
| ORM | Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.x) |
| Database | **PostgreSQL only** (`psycopg2-binary` 2.9.11) |
| CORS | Flask-CORS 6.0.5 |
| Passwords | Werkzeug 3.1.3 (`generate_password_hash` / `check_password_hash`) |
| Env config | python-dotenv 1.1.1 (loads `backend/.env`) |
| Email | stdlib `smtplib` + `email.mime` |
| Frontend | React 18.3, React Router 6.26, Vite 5.4 |
| Styling | Tailwind CSS 3.4 + PostCSS + autoprefixer |
| Fonts | Aref Ruqaa (display), Tajawal (body) |

No test runner, linter, or type checker is configured in either `package.json` or the Python deps. `backend/test_system.py` is a hand-rolled script (currently broken — §9.8).

---

## 5. Backend file library

### `backend/app.py`
- `create_app()`: builds the Flask app, sets `SQLALCHEMY_DATABASE_URI` / `SECRET_KEY`, registers CORS **once** on `/api/*` (allowing `Content-Type`, `X-Admin-Id`, `X-User-Code`; `supports_credentials` only when `CORS_ORIGINS != '*'`), `db.init_app`, `register_routes`, a static `GET /uploads/<path:filename>` route, then `db.create_all()` + `ensure_schema_compatibility()`.
- `ensure_schema_compatibility()`: the project's **only** migration mechanism — runs `ALTER TABLE mcq_answers ADD COLUMN IF NOT EXISTS answers JSON` so databases created before the JSON-answers change keep working. Add further forward-compatible `ALTER`s here rather than introducing a migration tool.
- `seed_database()`: one-off JSON → PostgreSQL import for admins (super admin + `admins[]`, hashing each password) and users (by `code`, skipping existing). **It is commented out in `__main__`** — nothing seeds automatically at boot. Call it manually once against a fresh database.
- `test_db_connection()`: prints admin/user counts at startup.
- Module scope creates `app = create_app()`, so any WSGI runner can import `app`.

### `backend/config.py`
- `BASE_DIR`, then `load_dotenv(backend/.env)`.
- `DATA_DIR` — defaults to **`backend/models/data`** (override `WEFAQ_DATA_DIR`); `INSTANCE_DIR` (`WEFAQ_INSTANCE_DIR`), `UPLOAD_DIR` (`WEFAQ_UPLOAD_DIR`); all created with `os.makedirs`.
- `LOGS_DIR` / `SYSTEM_LOG_FILE` → `instance/logs/system.log` (plain text, separate from the `activity_logs` table).
- `ALLOWED_PHOTO_EXTENSIONS = {jpg, jpeg, png, webp}`.
- `SQLALCHEMY_DATABASE_URI` from `DATABASE_URL`; **raises `RuntimeError` if unset**; rewrites a `postgres://` prefix to `postgresql://` for SQLAlchemy 2.x (Neon/Supabase/Vercel style URLs).
- `SECRET_KEY`, `CORS_ORIGINS` (`WEFAQ_CORS_ORIGINS`, default `*`), `TESTING` (`WEFAQ_TESTING`), `DEFAULT_USER_NAME`.

### `backend/models/` (package — was a single `models.py`)
```
models/__init__.py              re-exports db + all 8 models
models/db_schemes/__init__.py   imports each model module
models/db_schemes/base.py       db = SQLAlchemy()   ← the single shared instance
models/db_schemes/user.py       User + UserProfile
models/db_schemes/mcq_answer.py MCQAnswer
models/db_schemes/open_answer.py OpenAnswer
models/db_schemes/admin.py      Admin
models/db_schemes/admin_note.py AdminNote
models/db_schemes/notification.py Notification
models/db_schemes/activity_log.py ActivityLog
models/data/                    admins.json · questions.json · users.json
```
Import models as `from models import db, User, ...` — never reach into `db_schemes` from outside the package. A new table = a new module in `db_schemes/` + an entry in **both** `__init__.py` files. Full schema in §12.

### `backend/security.py`
- `EMAIL_RE`, caps: `MAX_NAME_LEN=100`, `MAX_PHONE_LEN=20`, `MAX_EMAIL_LEN=50`, `MAX_NOTE_LEN=2000`, `MAX_TEXT_LEN=5000`, `MIN_ADMIN_PASSWORD_LEN=8`.
- Credential extraction: `_admin_id_from_request()` (header `X-Admin-Id` → query `admin_id` → JSON body `admin_id`), `get_user_code_from_request()` (header `X-User-Code` → JSON body `code`).
- Lookups: `get_active_admin`, `get_active_super_admin`, `get_user_by_code`.
- Decorators: `admin_required`, `super_admin_required` (used by `matching_routes.py` only).
- Authorization helpers returning `(obj, error_response)`: `can_read_user(user_id)` (owner via code **or** any admin), `require_user_self(user_id)` (owner only, no admin override), `can_access_notification(notification)`.
- Sanitation: `sanitize_text`, `validate_email`, `validate_admin_password`.

### `backend/utils.py`
- JSON IO: `read_json_file` / `write_json_file` (UTF-8, `ensure_ascii=False`) against `DATA_DIR`.
- Loaders: `load_admins`, `load_questions`, `load_users`.
- Passwords: `hash_password` / `verify_password`.
- Photos: `photo_url_for(photo_path)` (absolute URL from `WEFAQ_PUBLIC_BASE_URL` or the current request host), `save_user_photo(file_storage)` → `({uuid4hex}.{ext}, None)` or `(None, error_message)`.
- `generate_user_code(User)` → next unique `USER###` from the **highest existing number** (not the row count — avoids collisions after deletes), then loops until free.
- `is_placeholder_name`, `user_needs_onboarding(user, mcq_answer=None)` (§3; the `mcq_answer` argument is accepted but unused).
- JSON mirrors: `sync_user_to_json` (now also mirrors `profile_details`, `mcq_answers` — preferring `MCQAnswer.answers` — and `open_answers`), `remove_user_from_json`, `_normalize_admins_file`, `sync_admin_to_json(admin, plain_password=...)`, `remove_admin_from_json(email)`.
- Email: `send_welcome_email(user)` — Arabic/RTL HTML welcome mail over `smtplib` using `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`. No-ops silently when `user.email` is empty or SMTP env vars are incomplete, and swallows/logs send failures, so submitting an application never fails because of email.
- Activity logging: `log_activity(admin_id, user_id, action_type, details)` — adds an `ActivityLog` row **and** appends a line to `SYSTEM_LOG_FILE`; the **caller** owns `db.session.commit()`.

### `backend/services/matching_service.py`
Pure read-only functions, no DB writes. Exports: `compute_age`, `matching_questions`, `score_mcq_similarity`, `score_pair`, `find_matches_for_user`, `_candidate_summary`. See §3 for the algorithm.

### `backend/routes/__init__.py`
`register_routes(app)` registers five blueprints: `auth_bp`, `user_bp`, `admin_bp`, `notification_bp`, `matching_bp`.

### `backend/routes/auth_routes.py` — prefix `/api/auth`
- `POST /user-login` — body `{code}` → `{id, code, full_name, status, needs_onboarding, photo_url}`.
- `POST /admin-login` — body `{email, password}` → admin payload incl. `is_super_admin`; rejects inactive accounts with 403.

### `backend/routes/user_routes.py` — prefix `/api`
- `GET /questions` — the whole `questions.json` (`mcq`, `open`, `onboarding`).
- `POST /users/register` — legacy self-register. **Buggy, see §9.5.**
- `POST /users/<id>/answers` — upserts MCQ/open via `_upsert_answers`, sets `reviewing`, syncs JSON.
- `POST /users/<id>/complete` — **primary first-login completion.** Body `{personal: {...+profile_details}, mcq, open}`. Validates the personal fields and the six required `profile_details` keys via `_apply_personal_data`, requires all four open answers, upserts `MCQAnswer`/`OpenAnswer`, sets `reviewing`, syncs JSON, fires `send_welcome_email`, returns the user + `mcq_answers` + `profile_details` + `open_answers` with `needs_onboarding: false`.
- `GET /users/<id>` — profile + `mcq_answers` (legacy `q1`–`q4` columns only) + `profile_details` + `open_answers` + `visible_notes` + `needs_onboarding`.
- `PUT /users/<id>` — updates `UPDATABLE_FIELDS` (`full_name`, `phone`, `email`, `gender`, `country`, `guardian_phone`, `guardian_relation`) plus `birthday`; rejects the placeholder name.
- Helpers: `_parse_birthday`, `_apply_personal_data` (also upserts `UserProfile.details`), `_upsert_answers` (writes the `answers` JSON dict **and** mirrors `q1`–`q4` columns), `_parse_registration_data`, `_user_payload`.
- **None of these routes are auth-decorated** — see §9.1.

### `backend/routes/admin_routes.py` — prefix `/api/admin`
- `GET /users` — filters: `status`, `scope=all|mine`, `requesting_admin_id`, `assigned_admin_id` (super admin only), `education` (MCQ `q1`), `financial` (MCQ `q2`). Uses `joinedload(User.assigned_admin)` to avoid N+1. Returns `photo_url`; **the list payload omits `assigned_admin_name`** (only `_user_list_item`, used by `/assign`'s response, includes it).
- `PUT /users/<id>/status` — sets status + optional reason, creates a `Notification`, logs `status_change`. **`sync_user_to_json` is commented out.**
- `POST /users/<id>/notes` — adds a note, logs `note_added` (records only the visibility flag, never the note text). `GET /users/<id>/notes` — all notes with `admin_name`.
- `PUT /users/<id>/assign` — body `{admin_id, target_admin_id}`; only a super admin or the current `assigned_admin_id` may reassign; validates the target is active; logs `assignment`; returns `_user_list_item`. **`sync_user_to_json` is commented out.**
- `GET /logs?admin_id=&filter_admin_id=&user_id=&date_from=&date_to=` — activity log, newest first, with `admin_name`/`user_name`.
- `POST /create` — create a non-super admin (requires a super admin's `admin_id`); `sync_admin_to_json` with the plaintext password; logs `admin_created`.
- `GET /admins?admin_id=` — super admin gets full records; other admins get `{id, full_name}` only (for the assignment dropdown).
- `DELETE /users/<id>` — any active admin; logs `user_deleted` with code/name first; `remove_user_from_json`.
- `DELETE /admins/<id>` — super admin only; blocks self and other super admins; `remove_admin_from_json`.
- `POST /users/generate-code` — optional `full_name` + `admin_id`; auto-assigns the case to the creator and logs it; `IntegrityError` → 409. **`sync_user_to_json` is commented out.**
- `_require_super_admin(admin_id)` / `_require_active_admin(admin_id)` — local duplicates of `security.py` helpers (§9.2).

### `backend/routes/matching_routes.py` — prefix `/api/admin`
- `GET /public/users/<id>/matches` — **user-facing.** `require_user_self` (needs `X-User-Code`), rejects non-`approved` users with 403, matches only against other `approved` users, `limit=100`, `private=True` so candidate summaries carry no id/status/name.
- `GET /users/<id>/matches` (`@admin_required`) — ranked matches for one user. Query params: `status` (comma-separated, default `approved,reviewing`, validated against the four valid statuses), `min_score` (float), `limit` (1–100, default 20), `include_ineligible`.
- `GET /matches/pair` (`@admin_required`) — full breakdown for two users (`user_a`, `user_b`).

### `backend/routes/notification_routes.py` — prefix `/api/notifications`
- `GET /user/<id>` — notifications newest first. `PUT /<id>/read` — mark read. Neither is auth-checked (§9.1).

### `backend/models/data/questions.json`
- `mcq[]` — `{id, question, options[]}`; optionally `"matching": true` and `"answer_key"` to enrol a question in compatibility scoring **and** in the onboarding wizard. Ids 1–4 also map to the legacy `MCQAnswer.q1`–`q4` columns.
- `open[]` — 4 essay prompts; index+1 → `OpenAnswer.q1`–`q4`.
- `onboarding` — `{ui, other_option, steps[]}` (§3). This is where the bulk of the applicant experience is configured.

### `backend/models/data/admins.json`, `users.json`
Legacy seed/mirror files. `admins.json` is `{super_admin: {...}, admins: [...]}` with plaintext passwords; `users.json` is a flat array keyed by `code`. **Both are currently invalid JSON — see §9.6.** PostgreSQL is the source of truth; these files are on their way out (§13).

### `backend/uploads/`
Applicant photos, random UUID-hex filenames, served publicly at `GET /uploads/<filename>`.

### `backend/test_system.py`
Standalone integration suite (`python test_system.py` from `backend/`). **Currently broken — see §9.8.**

---

## 6. Frontend file library

### Entry & config
| File | Role |
|---|---|
| `frontend/index.html` | HTML shell; mounts `#root` |
| `frontend/src/main.jsx` | `createRoot`, imports `index.css`, renders `<App />` |
| `frontend/src/App.jsx` | `BrowserRouter`, `<Navbar />`, route table |
| `frontend/src/config.json` | `appName`, `appTagline`, `apiBaseUrl`, `registrationSteps`, `personalFields`, `statusLabels` |
| `frontend/src/index.css` | Tajawal/Aref Ruqaa fonts, linen background, `.mashrabiya-bg`, focus-visible, reduced-motion, and the `.single-range` / `.dual-range` slider styling used by the wizard |
| `frontend/tailwind.config.js` | Brand colors, display/body fonts, mashrabiya SVG background |
| `frontend/vite.config.js` | React plugin; dev server port 5173 |
| `frontend/postcss.config.js` | Tailwind + autoprefixer |
| `frontend/package.json` | scripts: `dev`, `build`, `preview` only |

### Routing (`App.jsx`)
| Path | Page | Logic |
|---|---|---|
| `/` | `HomePage` | Marketing hero; redirects an `approved` session to `/matches`; CTAs → `/login` and `/admin/login` |
| `/login` | `UserLoginPage` | Code login → `needs_onboarding` ? `/complete-application` : `approved` ? `/matches` : `/dashboard` |
| `/complete-application` | `CompleteApplicationPage` | Dynamic one-question-at-a-time wizard |
| `/register` | `RegisterPage` | Legacy 4-step self-register wizard — not linked from any page |
| `/dashboard` | `UserDashboardPage` | Needs onboarding → wizard; `approved` → `/matches`; else the application dashboard |
| `/account` | `UserDashboardPage` | Same component; the `/account` path **suppresses** the approved→`/matches` redirect so approved users can still edit their profile |
| `/matches` | `MatchingPage` | Approved-only candidate browser |
| `/admin/login` | `AdminLoginPage` | Email/password → `wefaq_admin` → `/admin/dashboard` |
| `/admin/dashboard` | `AdminDashboardPage` | Users, filters, notes, assignment, matches, code generation, Super Admin tab |

### Services
| File | Role |
|---|---|
| `services/api.js` | `apiGet`/`apiPost`/`apiPut`/`apiDelete` + `apiPostForm` (multipart); `buildAuthHeaders()` attaches `X-Admin-Id`/`X-User-Code` on **all** calls; `buildPhotoUrl()` resolves a relative upload path against the API host minus `/api`; throws `Error(message)` on non-OK. `BASE_URL` honours `VITE_API_BASE_URL` before `config.apiBaseUrl`. |
| `services/authService.js` | `loginUser`, `loginAdmin` |
| `services/userService.js` | `getQuestions`, `registerUser` (multipart), `saveAnswers`, `completeApplication`, `getUser`, `updateUser`, `getUserNotifications` |
| `services/adminService.js` | `listUsers`, `updateUserStatus`, `assignUserCase`, `getActivityLogs`, `addNote`/`getNotes`, `generateUserCode`, `listAdmins`, `deleteUser`/`deleteAdmin`, `createAdmin` |
| `services/matchingService.js` | `getMatchesForUser(userId, {status, minScore, limit, includeIneligible})`, `scoreUserPair(a, b)`, `getMyMatches(userId)` → `/admin/public/users/<id>/matches` |

### Components
| File | Role |
|---|---|
| `Button.jsx` | Primary/secondary styled button |
| `Card.jsx` | Content panel wrapper |
| `FormField.jsx` | Config-driven field (`text`/`select`/`date`/…); used by `RegisterPage` and the `UserDashboardPage` edit form — **not** by `CompleteApplicationPage` |
| `ProgressSteps.jsx` | Step circles + progress lines — `RegisterPage` only |
| `StatusBadge.jsx` | Colored label from `config.statusLabels` |
| `NotificationList.jsx` | Notification list renderer |
| `Navbar.jsx` | Brand + user-login links (global, on every route) |
| `MashrabiyaDivider.jsx` | Decorative band |

### Pages — logic summary

**`HomePage.jsx`** — hero + three feature cards; on mount, an `approved` `wefaq_user` session is redirected to `/matches`.

**`UserLoginPage.jsx`** — posts the code, stores `wefaq_user`, three-way branch on `needs_onboarding` / `approved`.

**`CompleteApplicationPage.jsx`** — the largest piece of applicant UX. Loads the session user + `getQuestions()`; bails to `/dashboard` if already complete. Builds its step list in a `useMemo`: `onboarding.steps` filtered by `show_if`, then matching-flagged MCQ steps, then one step per open question. Holds four separate state buckets — `personal`, `details`, `mcqAnswers`, `answers` — routed by each step's `storage`. Inline helper components defined in this file: `ChoiceCards` (cards or chips), `SearchSelector` (filterable list with an "other" free-text branch), `RangeField` (dual-range slider), `SliderField` (single-range slider). `nameValidation()` enforces an Arabic/Latin name pattern on `full_name`. `valid()` gates the Continue button per step type. Submit → `completeApplication` → rewrite `wefaq_user` with `needs_onboarding: false` → `/dashboard`.

**`RegisterPage.jsx`** — legacy 4-step wizard (`config.personalFields` + photo upload + the flat `mcq`/`open` arrays) → `registerUser` (multipart) → `saveAnswers`. Creates a **new** code rather than completing an existing one, and never creates a `UserProfile`, so such a user stays `needs_onboarding: true`. Unlinked from the UI.

**`UserDashboardPage.jsx`** — parallel fetch of user, notifications and questions. Redirects to the wizard when onboarding is incomplete, and to `/matches` when `approved` **unless** the path is `/account`. Shows the submission timeline (`created_at` + 3 days expected response), an editable profile form (`FormField` + `config.personalFields` → `PUT /users/<id>`), visible admin notes, notifications, and the full MCQ/open answer summary.

**`MatchingPage.jsx`** *(new)* — approved-only candidate browser. Reads the session, redirects unless `status === 'approved'`, then `getMyMatches`. Renders one candidate at a time as a card: compatibility percentage in a large teal header with a deliberate "الصورة مخفية" (photo hidden) placeholder, a grid of the privacy-safe fields in `PROFILE_FIELDS` (age, nationality, country, profession, marital status, marriage timeline), the `profile_description` blurb, "التالي" cycling through the list, plus **local-only** "اهتمام" (interest) and "حفظ" (save) toggles. Those two toggles are `useState` only — **no persistence and no backend endpoint exists for them yet.**

**`AdminLoginPage.jsx`** — admin credentials → `wefaq_admin` in localStorage.

**`AdminDashboardPage.jsx`** — the admin console:
- Status filter buttons; client-side gender/country/age filters (`AGE_FILTERS`, `calcAge`); server-side scope (`all`/`mine`/`by_admin`), education and financial filters.
- Generate code (passes `admin_id`, so the case auto-assigns to the creator) and shows the new code.
- User table: `UserAvatar` (photo via `buildPhotoUrl`, else the initial letter), inline assignable-admin dropdown (editable only when `canAssignUser` — super admin or the current case owner), status select, notes link, delete with confirm.
- Detail panel (`openUserDetail`): full profile + MCQ/open answers + notes, and a "المطابقات المقترحة" section that calls `getMatchesForUser(id, {limit: 15, status: 'approved,reviewing'})`, renders each candidate as an expandable row, and lets you jump into a candidate's own detail panel. **This block still renders the pre-rewrite score shape — see §9.4.**
- Activity log panel and the Super Admin tab (create admin form, admin list, delete with confirm).

---

## 7. End-to-end flows

### A) Generate code → first login → wizard → dashboard → matches
```
AdminDashboard generateUserCode('', adminId)
  → POST /admin/users/generate-code
  → User(code, full_name='متقدم جديد', status='pending', assigned_admin_id=creator)

UserLoginPage loginUser(code)
  → needs_onboarding true → /complete-application

CompleteApplicationPage (onboarding.steps → matching MCQs → open questions)
  → POST /users/:id/complete { personal: {...+profile_details}, mcq, open }
  → UserProfile + MCQAnswer + OpenAnswer upserted, status='reviewing',
    welcome email attempted → /dashboard

Admin sets status 'approved'  → Notification row for the user
Next user login / dashboard visit → redirected to /matches (MatchingPage)
  → GET /admin/public/users/:id/matches  (X-User-Code, approved-only, private summaries)
```

### B) Legacy self-register flow (unlinked)
```
RegisterPage → POST /users/register (multipart) → POST /users/:id/answers
  → no UserProfile is created, so needs_onboarding stays true
```

### C) Admin review + matching
```
listUsers → openUserDetail → getMatchesForUser (ranked opposite-gender candidates)
updateUserStatus → Notification + ActivityLog('status_change')
addNote(..., isVisibleToUser=true) → surfaces in the user's visible_notes
assignUserCase → ActivityLog('assignment')
```

### D) Super Admin manages admins
```
POST /admin/create        → Admin row + sync_admin_to_json → admins.json admins[] grows
DELETE /admin/admins/:id  → Admin row deleted + remove_admin_from_json
```

---

## 8. State, data & design system

### Frontend state
No Redux/Context/global store — every page owns its state with `useState`/`useEffect`, and cross-page state lives in **localStorage** plus the API.

| localStorage key | Written by | Shape | Read by |
|---|---|---|---|
| `wefaq_user` | `UserLoginPage`, `CompleteApplicationPage`, `UserDashboardPage` | `{id, code, full_name, status, needs_onboarding, photo_url?}` | every user page, `buildAuthHeaders()` (`X-User-Code`) |
| `wefaq_admin` | `AdminLoginPage` | `{id, full_name, email, city, is_super_admin}` | `AdminDashboardPage`, `buildAuthHeaders()` (`X-Admin-Id`) |

Both are cleared on logout. `buildAuthHeaders()` wraps its reads in try/catch so malformed session data degrades to an unauthenticated request rather than throwing.

**Keep `wefaq_user.status` fresh.** Three separate redirects (`HomePage`, `UserLoginPage`, `MatchingPage`) branch on the cached `status`, while `UserDashboardPage` branches on the freshly-fetched one. Any new write of `wefaq_user` must include `status`, or approved users will stop being routed to `/matches`.

### Content/data loading
- Questions are **always** fetched from the API (`GET /api/questions` → `getQuestions()`), never imported from JSON on the client. `CompleteApplicationPage`, `UserDashboardPage` and `AdminDashboardPage` each fetch them independently.
- `frontend/src/config.json` is a static ESM import — it holds only UI config (form fields, step labels, status labels, API base URL), never applicant data.
- There are no dynamic `import()` loaders and no client-side content directory.

### Design system constraints
Preserve the existing brand tokens from `tailwind.config.js`:
- linen `#FAF8F4`, ink `#22302C`, muted `#6B7B76`, teal 600 `#1F4741` / 700 `#173B36`, gold 500 `#C9A15A`, brick 500 `#B4543A`
- Fonts: display `Aref Ruqaa`, body `Tajawal`
- `rounded-xl`/`rounded-2xl` inputs and cards, Arabic copy, `dir="rtl"` layout

Do not introduce a generic purple/cream AI theme. Note that only the shades listed in `tailwind.config.js` exist — `brick` has just `100` and `500`, so classes like `brick-600`/`brick-50` (used in `AdminDashboardPage`'s `matchScoreColor`) silently produce no style.

---

## 9. Important implementation gotchas

1. **Most endpoints are unauthenticated.** Only `matching_routes.py` uses the `security.py` decorators. Everything in `user_routes.py` and `notification_routes.py`, and `GET /admin/users` + `GET /admin/users/<id>/notes` in `admin_routes.py`, perform **no** authorization check at all — anyone who can reach the API can read or modify any applicant by id. The `security.py` helpers (`can_read_user`, `require_user_self`) exist for this but are not wired up outside matching. Treat this as a known hole; when touching one of those routes, adding the right decorator is an improvement, not a regression — but check `test_system.py`'s IDOR tests, which assume protection that is not currently applied.
2. **Dual authorization patterns.** `admin_routes.py` has its own `_require_active_admin` / `_require_super_admin` reading `admin_id` from the JSON body or query, duplicating `security.py`'s `get_active_admin` / `get_active_super_admin`. Prefer `security.py` for new endpoints; match the surrounding file for a small patch.
3. **No question is flagged for matching.** `matching_questions()` returns only `questions.json` `mcq` entries with `"matching": true`, and today none have it. Consequences: the onboarding wizard appends zero MCQ steps, `MCQAnswer` rows stay empty for wizard users, and every compatibility score is `0.0%` with `total_applicable_questions: 0`. **To turn matching on, add `"matching": true` to the relevant `mcq` entries in `questions.json`** — no code change is needed.
4. **The admin matches UI is stale relative to the matching rewrite.** `AdminDashboardPage.jsx` (~lines 775–835) still reads `m.stages.eligibility.score`/`30`, `m.stages.mcq.score`/`40`, `m.stages.open_answers.score`/`30`, `m.confidence.ar`, `m.candidate.full_name` and `m.candidate.code`. The current API returns `compatibility_percentage`, `total_score` (a percentage), `stages.mcq.{percentage, matching_answers, total_applicable_questions, breakdown}`, and a `_candidate_summary` with **no name, code or confidence**. The panel therefore shows blank names and `0/30`, `0/40`, `0/30`. Fix the JSX to the new shape (and add `full_name`/`code` to the non-private branch of `_candidate_summary` if the admin view needs them) rather than reverting the service.
5. **`register_user` in `user_routes.py` is still broken.** `data, photo_file = _parse_registration_data()` is immediately followed by `data = request.get_json() or {}`, discarding the multipart parse — so the photo-upload path never sees its fields (and a multipart request yields `None`, then a 400). It also indexes `data['phone']` without a presence check (`KeyError` → 500) and stores `data['email']` unvalidated even though it validated into a local `email`. `POST /users/register` is only reachable from the unlinked `/register` page; fix it before relying on it.
6. **`models/data/users.json` and `admins.json` are currently invalid JSON.** `users.json` contains three unresolved git merge conflict blocks (`<<<<<<< HEAD:backend/data/users.json` … `>>>>>>> origin/main:backend/models/data/users.json` at lines ~710, ~783, ~1015); `admins.json` has a trailing comma after the last `admins[]` entry. Any code path calling `load_users()`/`load_admins()` therefore raises `JSONDecodeError` — that includes `sync_user_to_json` (still live in `POST /users/register`, `POST /users/<id>/answers`, `POST /users/<id>/complete`, `PUT /users/<id>`), `remove_user_from_json` (`DELETE /admin/users/<id>`), `sync_admin_to_json` (`POST /admin/create`) and `seed_database()`. **Completing an application will 500 until these files are repaired or the sync calls are removed.** Given the JSON-retirement direction (§13), removing the sync calls is the better fix.
7. **`create_all()` does not migrate.** PostgreSQL columns added to a model will not appear on an existing database. Either drop/recreate the schema in dev, or add an idempotent `ALTER TABLE ... IF NOT EXISTS` to `ensure_schema_compatibility()` in `app.py`, which is the pattern already used for `mcq_answers.answers`.
8. **`test_system.py` cannot run as-is.** It copies `backend/data/admins.json` and `backend/data/questions.json`, but that directory moved to `backend/models/data/`; it sets `WEFAQ_DATA_DIR`/`WEFAQ_INSTANCE_DIR` but never `DATABASE_URL`, so importing `config` raises `RuntimeError`; and its isolation assumed a throwaway SQLite file, which no longer exists. Its matching tests also assert the old 30/40/30 shape. Fixing it means pointing at the new data path and pointing `DATABASE_URL` at a disposable test database.
9. **JSON sync is half-removed.** `sync_user_to_json` is commented out in `PUT /admin/users/<id>/status`, `PUT /admin/users/<id>/assign` and `POST /admin/users/generate-code`, but still active in `user_routes.py` and in the delete path. Do not "restore" the commented calls — the project is retiring the mirrors (§13).
10. **Nothing seeds at boot.** `seed_super_admin()` and `seed_users_from_json()` are gone; `seed_database()` is commented out in `__main__`. A fresh database has **no admin account** until you uncomment and run it once (or insert a row manually).
11. **MCQ answers live in two places.** `_upsert_answers` writes the flexible `MCQAnswer.answers` JSON dict **and** mirrors keys `q1`–`q4` into the legacy columns. `_answer_for` in the matching service reads `answers` first and falls back to the columns; `GET /users/<id>` and `POST /users/<id>/complete` return **only** the legacy columns. A question with an `answer_key` outside `q1`–`q4` will be scored correctly but will not appear in those API responses or on the user dashboard.
12. **Open answers are no longer scored.** `score_pair` deliberately excludes them; `OpenAnswer.q1` is reused as the candidate's public `profile_description` on the matching card.
13. **Partner preferences are collected but unused.** The `preferences` wizard step writes age/height ranges and marital/ethnicity/nationality preferences into `UserProfile.details`; the matching engine ignores all of them.
14. **`/matches` interest and save buttons are local-only.** They are `useState` toggles in `MatchingPage.jsx` with no persistence, no API and no DB table. Implementing them means new model + route + service, not just wiring a handler.
15. **User codes** — `generate_user_code` must keep using the max existing `USER###` number, not `query.count()`, or deleted users cause duplicate-code errors.
16. **Windows console** — Arabic `print()` output may need `PYTHONIOENCODING=utf-8`.
17. **JSON plaintext passwords** in `admins.json` are a seed convenience, never a security model.
18. **CORS** defaults to `*` via `WEFAQ_CORS_ORIGINS`. (The old double-registration bug is fixed — CORS is now registered once.)
19. **README drift** — the README's structure tree lists `frontend/test_phase3.mjs` and `frontend/test_onboarding_and_admin.mjs`, which do not exist in the repo.

---

## 10. How an AI should modify this project

1. **Extend, don't fork.** Prefer adding to the existing routes/services/pages over building a parallel stack.
2. **Change onboarding through `questions.json` first.** `CompleteApplicationPage.jsx` renders generically off `type`/`storage`/`show_if`, so adding, reordering or conditioning a question needs **no** frontend code. Only a genuinely new `type` requires a new branch in `renderQuestion()` (and usually a matching `valid()` case).
3. **Turn compatibility questions on with data**, not code: add `"matching": true` (and optionally `"answer_key"`) to `mcq` entries. That single flag drives both the wizard steps and the scoring.
4. **New personal field?** Decide the storage first: a first-class `User` column (add to `models/db_schemes/user.py`, `REQUIRED_FIELDS`/`UPDATABLE_FIELDS`, `_user_payload`, and give the wizard step `storage: "personal"`) versus a `UserProfile.details` key (JSON, no migration, just a wizard step). Prefer `details` unless you need to filter or index on it.
5. **New DB column** → update the model module, add an idempotent `ALTER` to `ensure_schema_compatibility()` in `app.py`, and update §12 here.
6. **New table** → new module in `models/db_schemes/`, exported from **both** `db_schemes/__init__.py` and `models/__init__.py`.
7. **New endpoint** → blueprint file under `routes/`, registered in `routes/__init__.py`, and protect it with `security.py` decorators (`@admin_required` / `@super_admin_required` / `require_user_self`) rather than inventing another local helper.
8. **Changing onboarding gating** → update `user_needs_onboarding` **and** the frontend redirects together (`UserLoginPage`, `UserDashboardPage`, `CompleteApplicationPage`), and consider both flows (the wizard and the legacy `/register`).
9. **After any API shape change** → update the matching `services/*.js` wrapper *and* every consuming page. §9.4 is exactly what happens when this step is skipped.
10. **Keep Arabic UX strings** consistent in tone; user-visible copy for the wizard belongs in `questions.json`'s `onboarding.ui`, not hardcoded in JSX.
11. **Don't add JSON mirror writes.** New write paths should touch PostgreSQL only (§13).
12. **Update this `SKILL.md`** whenever architecture, file roles or the schema change — including §12.

---

## 11. Quick file index (all first-party source)

```
README.md                          Human-facing project overview
SKILL.md                           This AI library (you are here)
requirements.txt                   Python deps (root)
backend/requirements.txt           Same deps for backend-local installs
backend/app.py                     Flask app factory + seed + upload serving
backend/config.py                  Paths, SQLite URI, upload/log dirs, DEFAULT_USER_NAME
backend/models.py                  ORM schema (incl. UserProfile)
backend/security.py                Auth/authorization decorators + input sanitation
backend/utils.py                   Hashing, codes, JSON sync, onboarding helpers, photo I/O
backend/services/matching_service.py  Rule-based compatibility scoring (read-only)
backend/test_system.py             Isolated integration test suite
backend/data/admins.json           Super admin seed + admins list
backend/data/questions.json        MCQ + open question bank + dynamic onboarding config
backend/data/users.json            Synced users mirror
backend/uploads/                   Applicant photo files
backend/routes/__init__.py         Blueprint registration (5 blueprints)
backend/routes/auth_routes.py      User/admin login
backend/routes/user_routes.py      Questions, register, complete, CRUD user
backend/routes/admin_routes.py     Users admin ops, notes, assignment, codes, admins CRUD
backend/routes/matching_routes.py  Compatibility match endpoints (admin-only)
backend/routes/notification_routes.py  User notifications
frontend/src/App.jsx               Routes
frontend/src/main.jsx              React bootstrap
frontend/src/config.json           API URL + legacy form/step config
frontend/src/index.css             Global styles
frontend/src/pages/*               Screens listed above
frontend/src/components/*          Reusable UI
frontend/src/services/*            API clients (incl. matchingService.js)
```

---

*Last aligned with the dynamic one-question-at-a-time onboarding wizard (questions.json `onboarding` config), `UserProfile` extended-profile storage, photo upload support, the rule-based matching/compatibility engine and its admin UI, and `security.py` centralized auth helpers.*

---

## 12. Full Database & Data Storage Reference

This section is the complete, low-level reference for **every place data is stored**, **what type each field is**, and **how the pieces relate** — for both applicant users and admins.

### 12.1 Storage layers overview

WEFAQ persists data across **three separate storage layers**, all under `backend/`:

| Layer | Location | Technology | Role |
|---|---|---|---|
| Primary DB | `DATABASE_URL` | **PostgreSQL** via Flask-SQLAlchemy | Sole source of truth for users, admins, answers, notes, notifications, logs |
| Question bank | `backend/models/data/questions.json` | JSON, UTF-8 | Drives the onboarding wizard and the matching inputs. **Keep this file.** |
| Legacy JSON mirrors | `backend/models/data/{admins,users}.json` | JSON, UTF-8 | Historical seed/mirror; being retired (§13); currently invalid (§9.6) |
| File uploads | `backend/uploads/` | Filesystem, UUID-hex names | Applicant photos (`User.photo_path`) |
| System log | `backend/instance/logs/system.log` | Plain text | Line-per-action mirror of `activity_logs` |

### 12.2 Tables

#### `users` (`User`, `models/db_schemes/user.py`)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | Integer, PK | — | |
| `code` | String(20), unique, **indexed** | No | Login credential, e.g. `USER007` |
| `full_name` | String(100) | No | Placeholder `متقدم جديد` until onboarding |
| `phone` | String(20) | Yes | Dial code + number, written as one string by the `contact` step |
| `email` | String(100) | Yes | |
| `birthday` | Date | Yes | Age source for matching |
| `gender` | String(10) | Yes | `ذكر` / `أنثى` — the matching gate |
| `guardian_phone` | String(20) | Yes | Wali contact |
| `guardian_relation` | String(50) | Yes | |
| `photo_path` | String(200) | Yes | Filename under `uploads/` |
| `country` | String(50) | Yes | Residence country (Arabic label from the wizard) |
| `status` | String(20), **indexed** | default `pending` | `pending`→`reviewing`→`approved`\|`rejected` |
| `status_reason` | Text | Yes | Admin reason on status change |
| `assigned_admin_id` | Integer, FK `admins.id` | Yes | Case owner |
| `created_at` / `updated_at` | DateTime | | `utcnow`, `updated_at` on update |

Relationships (all `cascade='all, delete-orphan'`): `profile` (1:1), `mcq_answers` (1:1), `open_answers` (1:1), `notes`, `notifications`; plus `assigned_admin`. `activity_logs.user_id` uses `ondelete='SET NULL'` so the audit trail survives user deletion.

#### `user_profiles` (`UserProfile`)
| Column | Type | Notes |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | Integer, FK `users.id`, unique | 1:1 |
| `details` | **JSON**, not null, default `{}` | All flexible onboarding data |
| `updated_at` | DateTime | onupdate `utcnow` |

`details` keys currently written by the wizard: `nationality`, `profession`, `graduation_date`, `marital_status`, `has_children`, `kids_count`, `marriage_timeline`, `height`, `weight`, `chronic_diseases`, `chronic_disease_details`, `disability`, `disability_details`, and the preference keys `age_min`, `age_max`, `height_min`, `height_max`, `marital_preference`, `ethnicity_preference`, `nationality_preference`. The six required for onboarding completion are `nationality`, `profession`, `marital_status`, `marriage_timeline`, `height`, `weight`.

#### `mcq_answers` (`MCQAnswer`)
| Column | Type | Meaning |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | Integer, FK `users.id` | 1:1 |
| `answers` | **JSON**, not null, default `{}` | Flexible `{answer_key: value}` map — the forward-looking store |
| `q1` | String(50) | Education level (legacy column; drives the admin `education` filter) |
| `q2` | String(50) | Financial level (legacy; drives the admin `financial` filter) |
| `q3` | String(50) | Cross-country marriage preference (legacy) |
| `q4` | String(50) | Most important trait (legacy) |

Both stores are written together by `_upsert_answers` (§9.11).

#### `open_answers` (`OpenAnswer`)
`id`, `user_id` (FK, 1:1), `q1`–`q4` Text — self-description, partner expectations, 5-year vision, additional conditions. `q1` doubles as the public `profile_description` on match cards.

#### `admins` (`Admin`)
`id`; `full_name` String(100); `phone` String(20); `email` String(100) unique **indexed**; `city` String(50); `password_hash` String(200) (Werkzeug, never plaintext in the DB); `is_super_admin` Boolean default `False`; `is_active` Boolean default `True` (inactive → rejected at login and by the admin decorators); `created_at` DateTime.

#### `admin_notes` (`AdminNote`)
`id`; `user_id` FK; `admin_id` FK (author); `note_text` Text; `is_visible_to_user` Boolean default `False`; `created_at`/`updated_at`.

#### `notifications` (`Notification`)
`id`; `user_id` FK nullable; `admin_id` FK nullable; `message` Text; `is_read` Boolean default `False`; `created_at`.

#### `activity_logs` (`ActivityLog`)
`id`; `admin_id` FK not null (actor); `user_id` FK nullable `ondelete='SET NULL'`; `action_type` String(30) — observed values `status_change`, `note_added`, `assignment`, `user_deleted`, `admin_created`, `admin_deleted`; `details` Text; `created_at`.

### 12.3 Entity relationships
```
Admin (1) ──< User (many)            [assigned_admin_id]
Admin (1) ──< AdminNote (many)       [author]
Admin (1) ──< Notification (many)    [recipient admin]
Admin (1) ──< ActivityLog (many)     [actor]

User (1) ──1 UserProfile             [cascade delete]
User (1) ──1 MCQAnswer               [cascade delete]
User (1) ──1 OpenAnswer              [cascade delete]
User (1) ──< AdminNote (many)        [cascade delete]
User (1) ──< Notification (many)     [cascade delete]
User (1) ──< ActivityLog (many)      [SET NULL on delete — log row survives]
```

### 12.4 Uploads
UUID-hex filenames (not user-controlled, so no traversal/overwrite risk), extension-checked server-side against `{jpg, jpeg, png, webp}`, served at `GET /uploads/<filename>`. `User.photo_path` holds the filename; `photo_url_for()` builds the absolute URL and `buildPhotoUrl()` mirrors that on the client.

### 12.5 Auth & sensitivity model
- **Admin passwords**: Werkzeug-hashed in `admins.password_hash`; never plaintext in the DB (but see the JSON mirror caveat).
- **User login**: passwordless — the unique `code` alone, presented as `X-User-Code` or a `code` body field.
- **No sessions/JWT**: identity is re-sent on every request from localStorage.
- **Input sanitation**: `sanitize_text` strips null bytes and truncates to the `security.py` caps; `validate_email` enforces `EMAIL_RE` and lowercases; `validate_admin_password` enforces 8+ characters.
- **Known non-production-grade points**: most routes unauthenticated (§9.1), plaintext passwords in `admins.json`, a hardcoded `SECRET_KEY` fallback, `CORS_ORIGINS='*'` by default, no rate limiting on the code-login endpoint.

### 12.6 Runtime data flow
```
App import → config.py loads backend/.env, requires DATABASE_URL
App boot   → db.create_all()                  # creates missing tables only
           → ensure_schema_compatibility()     # idempotent ALTERs
           (no automatic seeding)

Write paths → SQLAlchemy commit to PostgreSQL
            → log_activity() on admin actions  # ActivityLog row + system.log line
            → sync_user_to_json() only on the user_routes/delete paths (being retired)
```

---

## 13. Recent changes / new features

Everything below is newer than the previous revision of this document.

1. **PostgreSQL migration completed; SQLite removed.** `DATABASE_URL` is mandatory (`config.py` raises without it) and `postgres://` is rewritten to `postgresql://`. `backend/instance/wefaq.db` no longer exists as a concept; `instance/` holds only `logs/`. `psycopg2-binary` and `python-dotenv` were added to both `requirements.txt` files.
2. **`models.py` became the `models/` package**, split into `models/db_schemes/*.py` (one module per table, sharing `base.py`'s `db`). **`backend/data/` moved to `backend/models/data/`**, and `config.DATA_DIR` now points there.
3. **`MCQAnswer.answers` JSON column added**, with the legacy `q1`–`q4` columns kept in sync for compatibility. `app.py`'s new `ensure_schema_compatibility()` adds the column to pre-existing databases at boot — this is now the project's migration mechanism.
4. **The matching engine was rewritten** as a data-driven, percentage-based, MCQ-only comparison. `questions.json` decides which questions count (`"matching": true`), unanswered questions are excluded from the denominator, opposite gender is the sole gate, and the old 30/40/30 eligibility + open-answer + confidence model was deleted.
5. **New user-facing matching experience:** `GET /api/admin/public/users/<id>/matches` (self-auth via `X-User-Code`, approved-only, privacy-safe summaries with no name/code/photo) plus the new **`MatchingPage.jsx` at `/matches`** — a one-card-at-a-time candidate browser with the compatibility percentage, a hidden-photo placeholder, and local-only interest/save toggles.
6. **Approved users are routed to `/matches`** from `HomePage`, `UserLoginPage` and `UserDashboardPage`. The new **`/account` route** renders `UserDashboardPage` while suppressing that redirect, so approved users can still edit their profile.
7. **The onboarding wizard now collects MCQ answers.** It appends a `choice` step for every matching-flagged `mcq` question (`storage: "mcq"`) and passes real `mcqAnswers` to `completeApplication` — the old hardcoded `mcq: {}` is gone. A `slider` step type and `SliderField` component were also added, alongside the existing `contact` (dial code + phone + email) step.
8. **The `api.js` auth-header bug is fixed.** `X-Admin-Id`/`X-User-Code` are now sent on all JSON requests, not just multipart.
9. **CORS is registered once** (the old unconditional `origins: "*"` second registration is gone), so `WEFAQ_CORS_ORIGINS` is now respected.
10. **Performance work:** indexes on `users.code`, `users.status` and `admins.email`; `joinedload(User.assigned_admin)` in `GET /admin/users` to remove an N+1.
11. **JSON mirrors are being retired.** Boot-time seeding (`seed_super_admin`, `seed_users_from_json`) was replaced by a manual, commented-out `seed_database()`, and `sync_user_to_json` was commented out of the status, assign and generate-code routes. `questions.json` stays; `admins.json`/`users.json` are on the way out. Do not add new mirror writes.
12. **Known breakages introduced along the way** — read §9.3 (no question flagged for matching), §9.4 (stale admin match UI), §9.6 (both JSON mirrors are syntactically invalid, which 500s the live sync paths) and §9.8 (`test_system.py` points at the old data path and has no test database).
