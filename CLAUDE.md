# Applicant Tracking System

An internal Django web app where logged-in staff track candidates, job openings and each application's hiring stage. Candidates never use it.

## Stack

- Python + Django, SQLite
- uv for package management and running commands
- Tailwind CSS + DaisyUI via django-tailwind-cli
- HTMX for in-page interactions
- Ruff for linting and formatting
- pytest + pytest-django

## Architecture decisions (from the PRD)

- One Django project package `config` and one app `hiring` that owns all domain models.
- Every hiring view requires login. All active staff have equal permissions; accounts are created and deactivated (never deleted) by a superuser in the Django admin.
- One pure function defines the allowed stage moves. Templates and the move endpoint both use it and must never disagree.
- A stage change and its StageChange history entry are saved in one database transaction.
- HTMX moves are POST-only with CSRF, re-render a single partial, and a refused move returns a 4xx and changes nothing.

## References

- PRD: `prd/applicant-tracking-system.md`
- Implementation plan: `plans/applicant-tracking-system.md`
- Prototypes: `prototypes/` (throwaway references only; never promote into production code)