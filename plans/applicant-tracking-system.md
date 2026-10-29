# Plan: Applicant Tracking System

> Source PRD: `prd/applicant-tracking-system.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: one Django project package `config` (settings, root URLs) and one app `hiring` holding all models, forms, views, templates and tests. App URLs are namespaced `hiring:`.
- **Identifiers**: integer pks in every URL; no slugs (job titles are not unique).
- **URLs**:
  - `/` → redirects to the job list. The sidebar "Pipeline" link also points to the job list.
  - `/accounts/login/`, `/accounts/logout/` — Django's built-in auth views
  - `/admin/` — Django admin (staff accounts, deactivation, candidate hard delete)
  - `/candidates/`, `/candidates/new/`, `/candidates/<pk>/`, `/candidates/<pk>/edit/`, `/candidates/<pk>/archive/`, `/candidates/<pk>/unarchive/`, `/candidates/<pk>/apply/`
  - `/jobs/`, `/jobs/new/`, `/jobs/<pk>/` (pipeline page; `?stage=` filter), `/jobs/<pk>/edit/`, `/jobs/<pk>/status/`, `/jobs/<pk>/delete/`, `/jobs/<pk>/applications/new/`
  - `/applications/<pk>/`, `/applications/<pk>/move/` (POST only), `/applications/<pk>/delete/`
  - `/skills/`, `/skills/<pk>/delete/`
- **Models** (each introduced in the first phase that needs it):
  - `Candidate`: names, email (unique, case-insensitive), optional phone / URL / notes, `source` choice + optional source details, archived flag, timestamps.
  - `Skill`: name (unique, case-insensitive).
  - `JobOpening`: title, department, location, description, status (Open / Closed), timestamps; plain M2M to `Skill`.
  - `Application`: FK `Candidate` (CASCADE), FK `JobOpening` (PROTECT), stage, timestamps; DB unique constraint on (candidate, job).
  - `StageChange`: FK `Application` (CASCADE), from-stage (blank for the initial entry), to-stage, FK `User` (PROTECT), timestamp.
- **Stages**: Applied → Screening → Interview → Final Review → Offer → Hired, plus Rejected and Withdrawn. Active = Applied..Offer; Finished = Hired, Rejected, Withdrawn. One pure function defines the allowed moves, and both the templates and the move endpoint use it.
- **Auth**: every hiring view requires login; all active staff have equal permissions; accounts are created and deactivated by a superuser in the admin.
- **HTMX**: moves are POSTs with CSRF configured for HTMX. Each move re-renders a single partial: the whole pipeline section on the job page, or the stage panel + timeline on the application page. A refused move returns a 4xx and changes nothing.
- **Tooling**: uv, Tailwind + DaisyUI via django-tailwind-cli, Ruff, pytest + pytest-django with shared fixtures.

---

## Phase 1: Project skeleton, login and app shell

**User stories**: 1, 2, 3, 4, 6, 8

### What to build

Set up the project with uv: Django, the `config` package, the `hiring` app, SQLite, Tailwind/DaisyUI, Ruff and pytest. Staff can log in and out using Django's auth views, and every app page requires login. The base layout is the sidebar + table shell (Variant A) with links to Pipeline, Jobs, Candidates and Skills, and it collapses to a menu button on narrow screens. `/` redirects to the job list, which is an empty placeholder page for now. A superuser can create staff accounts in the admin.

### Acceptance criteria

- [ ] `uv run` can start the dev server, run tests and run Ruff
- [ ] Anonymous requests to app pages redirect to the login page
- [ ] A staff user can log in, sees the sidebar layout, and can log out (POST)
- [ ] `/` and the "Pipeline" link both lead to the job list
- [ ] The sidebar collapses into a menu button at phone width
- [ ] Shared pytest fixtures exist, including a logged-in staff client
- [ ] Tests cover login-required behaviour and the root redirect

---

## Phase 2: Candidates — log, list, edit and search

**User stories**: 9, 10, 11, 12, 13, 14, 15, 16

### What to build

Add the `Candidate` model and its migration. Staff can create a candidate (names, email, optional phone/URL/notes, source from the fixed list, optional source details), view the candidate's detail page, edit the candidate, and browse the candidate list with search by name or email. Email is unique regardless of letter case on both create and edit. A duplicate email produces an error with a link to the existing candidate.

### Acceptance criteria

- [ ] Candidates can be created, viewed and edited, and the source is limited to the six choices
- [ ] Creating or editing a candidate with an email that matches another candidate (any letter case) is refused, and the error links to the existing record
- [ ] Editing a candidate keeps its own email without triggering the duplicate error
- [ ] The candidate list shows logged candidates and filters by partial name or email
- [ ] Tests cover email uniqueness (case-insensitive) and search

---

## Phase 3: Skills page

**User stories**: 27, 28, 29, 30

### What to build

Add the `Skill` model. The Skills page lists all skills, has an inline form to add one, and lets staff delete a skill through a confirmation step. Names are unique regardless of letter case. A skill can be deleted only when its "can delete" check passes, meaning no job uses it. Until jobs exist, this check is always true, and Phase 4 adds the test that it blocks deletion once a job uses the skill.

### Acceptance criteria

- [ ] Staff can list, add and delete skills
- [ ] Adding "python" when "Python" exists is refused
- [ ] `Skill` exposes a "can delete" check, and the delete view honours it
- [ ] Tests cover case-insensitive uniqueness and delete

---

## Phase 4: Jobs CRUD with skills

**User stories**: 24, 25, 26, 31

### What to build

Add the `JobOpening` model with its M2M link to `Skill`. Staff can create and edit jobs (title, department, location, description) and tag skills with checkboxes. The job list shows each job's status. The job detail page (`/jobs/<pk>/`) shows a header with the job's status, skills and an edit action, and later phases fill in its pipeline. New jobs start as Open.

### Acceptance criteria

- [ ] Jobs can be created and edited, with skills chosen by checkbox
- [ ] The job list shows title, department and status, and links to each job page
- [ ] The job page shows the job's details and skills
- [ ] A skill used by a job can no longer be deleted on the Skills page
- [ ] Tests cover creating a job with skills and the skill "can delete" rule

---

## Phase 5: Add an application from the job page

**User stories**: 7, 37, 39, 40, 41, 42, 47

### What to build

Add the `Application` and `StageChange` models, including the unique constraint and the `on_delete` rules. From a job page, staff add an application by picking a candidate. The choices are limited to unarchived candidates without an existing application for that job, and only open jobs offer the action. On submit, the form re-checks that the job is open, the candidate isn't archived and there's no duplicate. The new application starts at Applied, and its initial `StageChange` (no from-stage, made by the current user) is written in the same transaction. The job page now shows an applications table with name, email, source, current stage and time in stage. The job list and the sidebar show each job's active-application count.

### Acceptance criteria

- [ ] Adding an application creates it at Applied with exactly one initial `StageChange` recording the user
- [ ] The candidate choices exclude candidates who already applied to this job (archived ones are excluded once Phase 10 adds archiving)
- [ ] A duplicate submit is refused at the form level, and a direct duplicate insert is refused by the database
- [ ] Submitting against a closed job is refused
- [ ] The job page table lists the job's applications with stage and time in stage
- [ ] The sidebar lists jobs with active-application counts, and the job list shows the same counts
- [ ] Tests cover the duplicate rule (form and DB), the closed-job refusal and the initial history entry

---

## Phase 6: Apply from the candidate page

**User stories**: 17, 38

### What to build

The candidate detail page lists all of the candidate's applications with each one's job and current stage, and offers an "apply to job" action. That action uses the same shared application form as Phase 5, with the candidate fixed and the job chosen. Only open jobs the candidate hasn't applied to are offered.

### Acceptance criteria

- [ ] The candidate page shows each application's job and current stage
- [ ] Applying from the candidate page creates the application and its initial history entry
- [ ] The job choices exclude closed jobs and jobs the candidate already applied to
- [ ] Both entry points use the same form and validation
- [ ] Tests cover the candidate-page entry point

---

## Phase 7: Stage moves via HTMX on the job page

**User stories**: 49, 50, 51, 52, 53, 54, 55, 57, 58, 62

### What to build

Add the pure transition function. From any active stage it allows the next pipeline stage, the previous stage (if any), Rejected and Withdrawn. Hired, Rejected and Withdrawn allow no moves. Each table row renders buttons only for the allowed moves. A button sends an HTMX POST to `/applications/<pk>/move/`, which validates the move with the same function. The stage update and its `StageChange` are saved in one transaction. The response re-renders the job page's pipeline section partial in place. A disallowed or malformed move returns a 4xx and changes nothing.

### Acceptance criteria

- [ ] The transition function returns the correct moves for every stage, final stages return none, and no move skips a stage
- [ ] Rows show only the allowed move buttons, and finished rows show none
- [ ] An allowed move updates the stage, writes a `StageChange` with the correct user and from/to stages, and returns the re-rendered section
- [ ] A disallowed move (including one sent directly or from a stale page) returns a 4xx and changes nothing
- [ ] The move endpoint rejects GET and anonymous requests
- [ ] A move doesn't reload the full page in the browser
- [ ] Tests cover the transition function and the move endpoint (allowed, refused, login required)

---

## Phase 8: Pipeline counts, filters and application timeline

**User stories**: 44, 45, 46, 48, 56, 59, 60, 61

### What to build

The pipeline section on the job page gains count cards for each active stage and filter tabs for Active, each stage and Finished, each with a count. Clicking a count card applies that stage's filter. The move request carries the current filter, so after a move the counts, tabs and table re-render together with the same tab selected. An applicant who no longer matches the filter drops out of the table. Rejected and Withdrawn rows show the stage they left from.

Add the application detail page at `/applications/<pk>/`. It shows the candidate, the job, the current stage with its move buttons, and a newest-first timeline of every `StageChange` with who made it, from, to and when. A move made on this page re-renders the stage panel and timeline in place.

### Acceptance criteria

- [ ] Count cards and tab counts are correct, and Finished counts Hired + Rejected + Withdrawn
- [ ] Clicking a count card applies that stage's filter
- [ ] After a move, the selected tab stays the same, and an applicant who no longer belongs in a single-stage tab disappears from it
- [ ] Rejected and Withdrawn rows show the stage they left from
- [ ] The application page shows a full timeline, newest first, including the initial entry
- [ ] A move on the application page updates its stage panel and timeline without a full reload
- [ ] Tests cover filter counts, the filter staying selected after a move, and the timeline content and order

---

## Phase 9: Close and reopen jobs

**User stories**: 32, 33, 34, 35

### What to build

The job page has an open/close action posting to `/jobs/<pk>/status/`. When closing, staff see a warning with the number of active applications. A closed job shows a notice and no "add application" action. Existing applications can still be moved. Staff can reopen a closed job at any time. Closing and reopening never change applications.

### Acceptance criteria

- [ ] Staff can close an open job and reopen a closed job
- [ ] The close action shows the active-application count as a warning
- [ ] Closed jobs show a notice, hide "add application", and refuse application submits
- [ ] Applications on a closed job can still be moved
- [ ] Tests cover close, reopen, and moves on a closed job

---

## Phase 10: Archive and unarchive candidates

**User stories**: 18, 19, 20, 21, 22

### What to build

The candidate page gets archive and unarchive actions. Archiving is refused while the candidate has any active application, and the refusal explains how many are active. Archived candidates are hidden from the default candidate list and shown when "Show archived" is selected. Archived candidates are excluded from application choices and refused on submit. Unarchiving is always allowed.

### Acceptance criteria

- [ ] Archiving a candidate with active applications is blocked, with the active count shown
- [ ] A candidate with only finished applications (or none) can be archived
- [ ] Archived candidates are hidden from the default list and shown with "Show archived"
- [ ] Archived candidates are absent from application choices, and a stale submit naming one is refused
- [ ] Unarchiving restores the candidate to the default list
- [ ] Tests cover the archive block, the list filter and the application refusal

---

## Phase 11: Guarded deletes and admin

**User stories**: 5, 23, 36, 43

### What to build

Job delete is offered only when the job has no applications, and goes through a confirmation page. Application delete is offered only while the application is at Applied with only its initial history entry, also behind a confirmation page. Both views refuse when the "can delete" check is false. Register the models in the Django admin so that a superuser can hard-delete a candidate, and Django's confirmation page lists the cascaded applications and stage history. Staff users who are referenced by history can't be deleted, only deactivated, and a deactivated user can't log in while their name stays on history entries.

### Acceptance criteria

- [ ] A job with no applications can be deleted after confirmation, and a job with applications cannot (no button, and the view refuses)
- [ ] An unmoved Applied application can be deleted after confirmation, and a moved one cannot
- [ ] Admin deletion of a candidate cascades to their applications and stage changes
- [ ] Deleting a user with history is protected, and a deactivated user can't log in and still appears on history entries
- [ ] Tests cover each "can delete" rule and its view
