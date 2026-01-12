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
   - Background cron job cleanup every 15 minutes (configurable via EXPIRED_FILE_CLEANUP_SCHEDULE)
   - Files stored in media/uploads/ with unique hex identifiers

3. **shifter_site_settings** - Dynamic site configuration
   - Settings stored in database with defaults from settings.SITE_SETTINGS
   - Configurable: max file size, default/max expiry offsets
   - System information dashboard (uptime, active files, storage)

### Frontend Architecture (Vite + Django Integration)

**Build System:**

- Vite 7.3 with three entry points (vite.config.js):
  - `shifter.js` - Global scripts (Alpine.js, datetime handling, clipboard)
  - `filepond.js` - File upload handling
  - `site-settings.js` - Admin settings interface
- Dev mode: Vite HMR on localhost:5173, Django on localhost:8000
- Production: Vite builds to `./static/` (preserves existing files with emptyOutDir: false)
- Output structure: `js/[name]-bundle.js` and `css/[name].css`

**Key Libraries:**

- **Alpine.js 3.15** - Lightweight reactive framework for UI interactions
  - Custom Alpine components: `clipboardNotification`, `localizedTime`, `localizedDateTimeInput`
  - Alpine stores manage upload state
- **FilePond 4.32** - Drag-and-drop file uploads with size validation
- **JSZip 3.10** - Client-side multi-file compression (automatic)
- **Tailwind CSS 4.1** + **Flowbite 4.0** - Styling and components
- **django-vite** - Template tags for HMR and asset loading: `{% vite_asset %}`, `{% vite_hmr_client %}`

### File Upload Flow

1. FilePond dropzone with client-side validation (size from settings, expiry bounds)
2. Multiple files automatically combined into ZIP by JSZip
3. POST to same URL with file + expiry datetime (ISO format) + CSRF token
4. `FileUploadView.form_valid()` validates and stores:
   - Generates 32-char hex UUID for unique file reference
   - Saves to `media/uploads/` with hex appended to filename
   - Creates FileUpload model instance with owner FK
5. Returns JSON redirect to file details page
6. User receives shareable download link at `/download/<hex>/`

### File Download and Expiry

- **Public landing page:** `/download/<hex>/` - Shows filename/size, no auth required
- **Direct download:** `/f/<hex>/` - Sends file as attachment
- Both check `FileUpload.is_expired()` before serving (404 if expired)
- **Deletion:** Users can soft-delete by setting expiry_datetime to now
- **Cron cleanup:** `shifter_files.cron.delete_expired_files` runs every 15 minutes
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
| `/`                   | Required | Upload form (GET) and submission (POST)         |
| `/files`              | Required | User's file list (paginated by 10) with search  |
| `/files/<hex>`        | Required | File details with shareable link                |
| `/download/<hex>`     | Public   | Download landing page                           |
| `/f/<hex>`            | Public   | Direct file download                            |
| `/files/<hex>/delete` | Required | Soft-delete file                                |
| `/api/cleanup-files`  | Staff    | Manual cleanup trigger                          |
| `/auth/setup`         | Special  | First-time admin setup (only if no users exist) |
| `/auth/new-user`      | Staff    | Create new user                                 |
| `/site-settings`      | Staff    | Admin configuration                             |

### Time Zone Handling

- Server stores all datetimes in UTC
- JavaScript converts to local time for display
- Form inputs use `datetime-local` with calculated min/max offsets
- Configured via TIMEZONE env var (defaults to UTC)

### Background Tasks

- **django-crontab** handles scheduled tasks
- Single cron job: delete expired files (settings.CRONJOBS)
- Schedule via EXPIRED_FILE_CLEANUP_SCHEDULE env var (default: `*/15 * * * *`)
- Crontab added and crond started in Docker entrypoint.sh

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
- EXPIRED_FILE_CLEANUP_SCHEDULE (cron format, default: `*/15 * * * *`)
- DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD (dev only)
- TIMEZONE (default: UTC)

# Git Guidance

- Use feature branches for new features/bugfixes
- Write descriptive commit messages using conventional commit messages
- **IMPORTANT: Do NOT push the code to remote, or raise a pull request until the user has reviewed the code locally**
- Open pull requests for code review before merging to main
- When raising pull requests relating to issues, ensure the pull request will close the issue (e.g. "Closes #123" in description)
- Use the GH cli for interfacing with GitHub
- Co-sign commits as Claude

# Development Guidance

When implementing a feature or fixing a bug, please attempt to use test driven development (TDD) where it makes sense. Write tests that cover the new functionality or bug fix first, then implement the code to make the tests pass. This helps ensure code quality and prevents regressions.
