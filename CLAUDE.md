# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Shifter is a self-hosted file-sharing web app built with Django and Tailwind CSS. Users can upload files with expiry dates, share download links, and manage their uploads. Files are automatically deleted when they expire.

## Development Commands

### Initial Setup

```bash
# Build and start development containers
docker compose -f docker/dev/docker-compose.dev.yml up --build

# Access the app at http://127.0.0.1:8000
# Frontend dev server (HMR) runs at http://localhost:5173
```

### Running Tests

```bash
# Run all tests (Django + Frontend)
docker compose -f docker/dev/docker-compose.test.yml build
docker compose -f docker/dev/docker-compose.test.yml run shifter          # Django tests
docker compose -f docker/dev/docker-compose.test.yml run frontend-tests   # Frontend JS tests
docker compose -f docker/dev/docker-compose.test.yml down

# Run specific Django test
docker compose -f docker/dev/docker-compose.dev.yml exec shifter python manage.py test shifter_files.tests.test_models.FileUploadModelTestCase

# Run frontend tests with watch mode (requires entering container)
docker compose -f docker/dev/docker-compose.dev.yml exec shifter npm run dev -- --run
```

### Code Quality and Linting

```bash
# Before running these commands, ensure you have built and started the development containers:
docker compose -f docker/dev/docker-compose.dev.yml up --build

# Ruff linting (configured in pyproject.toml: line-length=79, extends E/F/I)
docker compose -f docker/dev/docker-compose.dev.yml exec shifter ruff check .

# Auto-fix linting issues
docker compose -f docker/dev/docker-compose.dev.yml exec shifter ruff check --fix .
```

### Running Production Mode

```bash
# Build and start production containers
docker compose -f docker/docker-compose.yml up --build
```

### Other Common Commands

```bash
# Build frontend assets
docker compose -f docker/dev/docker-compose.dev.yml exec shifter npm run build

# Django shell
docker compose -f docker/dev/docker-compose.dev.yml exec shifter python manage.py shell

# Create migrations
docker compose -f docker/dev/docker-compose.dev.yml exec shifter python manage.py makemigrations

# Apply migrations
docker compose -f docker/dev/docker-compose.dev.yml exec shifter python manage.py migrate

# Manual expired file cleanup
docker compose -f docker/dev/docker-compose.dev.yml exec shifter python manage.py cleanupexpired

# Sync settings from Django config to database
docker compose -f docker/dev/docker-compose.dev.yml exec shifter python manage.py createsettings
```

## Architecture Overview

### Django Apps Structure

All the source code is contained within the `shifter/` directory. The project is structured as a standard Django project with the following apps:

**Three main Django apps:**

1. **shifter_auth** - Custom email-based authentication

   - User model uses email instead of username (settings.AUTH_USER_MODEL = "shifter_auth.User")
   - First-time setup flow creates initial admin user
   - Middleware enforces setup completion and password changes
   - Staff users can create additional user accounts

2. **shifter_files** - Core file upload/download functionality

   - File upload with expiry date validation
   - Public download landing pages (no auth required)
   - Expired files and abandoned uploads are deleted by scheduled background tasks
   - Files stored in media/uploads/ with unique hex identifiers

3. **shifter_site_settings** - Dynamic site configuration
   - Settings stored in database with defaults from settings.SITE_SETTINGS
   - Configurable: max file size, default/max expiry offsets
   - System information dashboard (uptime, active files, storage)

### Frontend Architecture (Vite + Django Integration)

**Build System:**

- Vite 7.3 with three entry points (vite.config.js):
  - `shifter.js` - Global scripts (Alpine.js, datetime handling, clipboard)
  - `upload.jsx` - Upload page React island (FilePond picker + chunked uploader, see `assets/js/upload/`)
  - `site-settings.js` - Admin settings interface
- Dev mode: Vite HMR on localhost:5173, Django on localhost:8000
- Production: Vite builds to `./static/` (preserves existing files with emptyOutDir: false)
- Output structure: `js/[name]-bundle.js` and `css/[name].css`

**React islands (incremental migration from Alpine):**

- Pages opt in with `{{ props|json_script:"<id>" }}` plus
  `<div data-react-island="Component" data-props-id="<id>">`; the page's Vite
  entry calls `mountIslands({ Component })` from `assets/js/react/mount.jsx`
- Views build island props in Python (e.g. `FileUploadView.get_upload_props`)
- `assets/js/react/api.js` provides `apiFetch` (CSRF header, Django form errors)
- `{% vite_react_refresh %}` in `base.html` enables Fast Refresh in dev
- Component tests use Vitest + Testing Library (`tests/**/*.test.jsx`)

**Key Libraries:**

- **Alpine.js 3.15** - Lightweight reactive framework for UI interactions
  - Custom Alpine components: `clipboardNotification`, `localizedTime`, `localizedDateTimeInput`
- **FilePond 4.32** - Drag-and-drop file uploads with size validation
- **client-zip** - Streaming client-side zip of multiple files
- **Tailwind CSS 4.1** + **Flowbite 4.0** - Styling and components
- **django-vite** - Template tags for HMR and asset loading: `{% vite_asset %}`, `{% vite_hmr_client %}`

### File Upload Flow

1. FilePond is used only as the file picker (client-side size validation)
2. Multiple files are zipped on the fly with client-zip (streamed, never
   held in memory; `predictLength` gives the exact size up front)
3. Chunked upload API (`shifter_files/api.py`, session auth + CSRF header):
   - `POST /api/uploads` validates filename, size and expiry
     (`ChunkedUploadInitForm`) and creates a `ChunkedUpload`
   - `PUT /api/uploads/<id>/chunk` appends one chunk (`X-Upload-Offset`
     header, at most `UPLOAD_CHUNK_SIZE` bytes) to a temp file under
     `media/chunked_uploads/`; out-of-order offsets get 409 with `received`
   - `POST /api/uploads/<id>/complete` moves the file into `media/uploads/`,
     creates the FileUpload and returns `redirect_url`; the MD5 is filled in
     afterwards by the `calculate_file_hash` background task
   - `DELETE /api/uploads/<id>` aborts
4. The browser retries failed chunks with backoff and shows progress
5. Abandoned uploads are removed by the `delete_stale_chunked_upload` task
   once untouched for `CHUNKED_UPLOAD_MAX_AGE_HOURS`
6. User receives shareable download link at `/download/<hex>/`

### File Download and Expiry

- **Public landing page:** `/download/<hex>/` - Shows filename/size, no auth required
- **Direct download:** `/f/<hex>/` - Sends file as attachment
- Both check `FileUpload.is_expired()` before serving (404 if expired)
- With `X_ACCEL_REDIRECT_PREFIX` set, `/f/<hex>/` returns an empty response
  with an `X-Accel-Redirect` header and the proxy sends the file (see
  `docs/PROXY_DOWNLOADS.md`)
- **Deletion:** Users can soft-delete by setting expiry_datetime to now
- **Expiry deletion:** saving a FileUpload (post_save signal in
  `shifter_files/signals.py`) schedules a `delete_expired_file` task to run at
  its `expiry_datetime`; changing or clearing the expiry, or deleting the file,
  replaces or cancels it. The task re-checks `is_expired()` before deleting
  - Pre-delete signal removes actual file from storage
  - Can be triggered manually via `/api/cleanup-files` (staff only) or `manage.py cleanupexpired`

### Database Models

```
User (shifter_auth.User extends AbstractUser)
├── email (unique, USERNAME_FIELD)
├── change_password_on_login (boolean)
└── files (reverse FK from FileUpload)

FileUpload (shifter_files)
├── owner (FK → User, null=True)
├── filename, upload_datetime, expiry_datetime
├── file_content (FileField → media/uploads/)
├── file_hex (unique, 32-char hex for URLs)
└── Methods: is_expired(), get_expired_files(), delete_expired_files()

SiteSetting (shifter_site_settings)
├── name (unique), value
└── get_setting(name) → value or settings.SITE_SETTINGS default
```

### Key API Endpoints

| Endpoint              | Auth     | Purpose                                         |
| --------------------- | -------- | ----------------------------------------------- |
| `/`                   | Required | Upload page (uploads use `/api/uploads`)        |
| `/files`              | Required | User's file list (paginated by 10) with search  |
| `/files/<hex>`        | Required | File details with shareable link                |
| `/download/<hex>`     | Public   | Download landing page                           |
| `/f/<hex>`            | Public   | Direct file download                            |
| `/files/<hex>/delete` | Required | Soft-delete file                                |
| `/api/cleanup-files`  | Staff    | Manual cleanup trigger                          |
| `/api/prune-task-results` | Staff | Delete finished background task records    |
| `/auth/setup`         | Special  | First-time admin setup (only if no users exist) |
| `/auth/new-user`      | Staff    | Create new user                                 |
| `/site-settings`      | Staff    | Admin configuration                             |

### Time Zone Handling

- Server stores all datetimes in UTC
- JavaScript converts to local time for display
- Form inputs use `datetime-local` with calculated min/max offsets
- Configured via TIMEZONE env var (defaults to UTC)

### Background Tasks

- **django.tasks** (built into Django 6) with the **django-tasks-db** backend
  (settings.TASKS) runs one-off work outside requests, e.g.
  `shifter_files.tasks.calculate_file_hash`
  - Tasks are stored in the database and run by `python manage.py db_worker`
  - entrypoint.sh starts the worker in the same container (restarting it if
    it exits) unless RUN_TASK_WORKER=0 or TEST_MODE is set
  - Enqueue with `transaction.on_commit` (see `schedule_file_hash`) so the
    worker never runs before the row it needs is committed
  - On startup entrypoint.sh runs `manage.py rescheduletasks`, which
    re-queues work that may have been lost (e.g. a hash task interrupted
    when the container stopped and left marked RUNNING) and schedules a
    deletion for any file with an expiry but no waiting deletion, a stale
    check for any unfinished upload without one, and the daily prune if
    none is waiting
  - Tasks queued with `.using(run_after=...)` show as "Scheduled" in the
    Task Log and aren't counted as Queued Tasks
  - Finished task records are deleted from the Site Settings page
    ("Prune Task History", `/api/prune-task-results`)
  - Site Settings > Maintenance has a collapsed Task Log of the latest 50
    tasks by scheduled time, future ones first (`shifter_files.tasks.get_task_log`)
  - Site Information shows Queued Tasks and Failed Tasks tiles, and Copy Site
    Info includes task counts (`shifter_files.tasks.get_task_stats`)
  - Tests: `shifter_files.tests.helpers.immediate_tasks` plus
    `self.captureOnCommitCallbacks(execute=True)` runs tasks inline
- Scheduled work also uses tasks (there is no cron):
  - `delete_expired_file` runs at each file's expiry
  - `delete_stale_chunked_upload` runs when an unfinished upload would go
    stale and reschedules itself if chunks arrived since
  - `prune_old_task_results` runs daily, deleting finished task records older
    than TASK_RESULT_MAX_AGE_DAYS and records stuck RUNNING for over a day

### Static Files and Asset Pipeline

**Development:**

- Vite dev server provides HMR at localhost:5173
- Django templates use `{% vite_asset 'shifter.js' %}` etc.
- Static files in `./static/` (images, icons) served directly

**Production:**

1. npm install && npm run build (vite build)
2. Vite outputs to `./static/` with manifest.json
3. python manage.py collectstatic --no-input --clear
4. WhiteNoise serves from `/app/static_root/` with compression

### Settings Management

- Defaults defined in `settings.SITE_SETTINGS` dict
- Database values override defaults (via SiteSetting model)
- Settings form dynamically generated from config metadata
- Includes validation (min/max values) and tooltips
- Sync defaults to DB with `manage.py createsettings`

## Important Patterns

### Security

- All forms require CSRF tokens (validated by middleware)
- File access controlled by ownership check (users only see their files)
- Staff-only endpoints use `UserPassesTestMixin`
- Email-based auth prevents username enumeration
- Password validation on creation and changes

### Database Configuration

- Supports SQLite (default) and PostgreSQL
- Set via DATABASE env var (`sqlite` or `postgres`)
- PostgreSQL requires: SQL_DATABASE, SQL_HOST, SQL_USER, SQL_PASSWORD
- Connection configured in settings.py lines 110-143

### Middleware Order (Important!)

1. SecurityMiddleware
2. WhiteNoiseMiddleware (must be early for static files)
3. SessionMiddleware
4. CommonMiddleware
5. CsrfViewMiddleware
6. AuthenticationMiddleware
7. **ensure_first_time_setup_completed** (redirects to /auth/setup if no users)
8. **ensure_password_changed** (forces password change for new users)
9. MessagesMiddleware
10. ClickjackingMiddleware

## Testing Notes

- Django tests use `--parallel` flag in test compose
- Frontend tests run with Vitest in jsdom environment
- Setup file: `tests/setup.js`
- Test mode sets TEST_MODE=1 and DJANGO_LOG_LEVEL=OFF
- Tests use `.env EXAMPLE` file (not .env.dev)

## Environment Variables

Key variables in `.env` or `.env.dev`:

- DEBUG (0/1)
- SECRET_KEY
- SHIFTER_URL (sets ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS)
- DATABASE (sqlite/postgres)
- TASK_RESULT_MAX_AGE_DAYS (default: 7; finished task records are pruned after this)
- DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD (dev only)
- TIMEZONE (default: UTC)
- RUN_TASK_WORKER (default: 1; run the task worker in this container)
- X_ACCEL_REDIRECT_PREFIX (default: empty; hand downloads to the reverse proxy)

## Development Guidelines
- Whenever you make a change, ensure there is proper test coverage for it.
- When fixing a bug, write a test that reproduces the bug before fixing it.
- Break changes up into small, focused commits with clear messages.

## Git Workflow Guidelines
- ALWAYS use feature branches for new features or significant changes (`git switch -c feature/your-feature-name`)
- If you are on main, create a new branch for your work before making changes (`git switch -c feature/your-feature-name`)
- Keep commits small and focused, with clear messages
- Use semantic commit messages (e.g., `feat: add form field to change username`, `fix: resolve path traversal issue in file download view`)
- **IMPORTANT: Do NOT push the code to remote, or raise a pull request until the user has reviewed the code locally**
- Open pull requests for code review before merging to main
- Ensure all tests pass and code is linted before merging.
- When raising a PR, do not include a test plan section.
- When raising pull requests relating to issues, ensure the pull request will close the issue (e.g. "Closes #123" in description)
- Use the GH cli for interfacing with GitHub
- Co-sign commits as Claude
