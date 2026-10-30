# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-10-29 — Implemented Phase 9 (close and reopen jobs)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 9`
2. Yes I approve them *(TDD behaviors: posting `status=closed` closes an open job, redirects to its page and leaves every application's stage and history unchanged; posting `status=open` reopens a closed job; the close confirmation shows how many applications are still active, counting only active stages)*
3. Yes, I approve them *(RED test for behavior 1)*
4. Yes, move onto behavior 2
5. Yes, I approve it *(RED test for behavior 2)*
6. Yes, move onto behavior 3
7. Yes, I approve it *(RED test for behavior 3)*
8. Yes, continue with the rest of phase 9
9. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - New route `/jobs/<pk>/status/` (`job_status` view):
    - GET shows a confirmation page;
    - POST saves the posted target status (`open` or `closed`) and redirects to the job page;
    - any other value returns 400 and changes nothing.
  - The view loads the job through `JobOpening.objects.with_active_count()`, the same count as the job list and sidebar, and never touches applications.
  - `job_status.html`:
    - When closing, it explains that existing applications can still be moved and shows a warning such as "2 applications are still active". The wording is singular for one, and the page says "No applications are active" when there are none.
    - When reopening, it just asks for confirmation.
    - Both versions have breadcrumbs and Cancel.
  - The job page has a "Close job" or "Reopen job" button. A closed job shows an info notice saying it can't take new applications but existing ones can still be moved. "Add application" was already hidden on closed jobs. Pipeline stays highlighted in the sidebar on the status page.
  - Three TDD behaviors went red → green, and ten normal test functions (13 test cases) cover:
    - unknown and missing status;
    - the close page's button, Cancel link and "none active" text;
    - the singular warning;
    - the reopen page having no warning;
    - the job page's Close/Reopen links and the closed notice;
    - a reopened job accepting applications again;
    - the sidebar highlight;
    - the 404;
    - login required for GET and POST.
  - Moves on a closed job were already tested in Phase 7, and the closed-job submit refusal in Phase 5, so they weren't re-tested.
  - All 141 tests, Ruff lint and Ruff format pass, and no migration was needed. I verified the phase manually in the browser.
- **Deviations:**
  - I approved everything as proposed and asked no follow-up questions.
  - Claude made choices that aren't in the plan:
    - The POST carries the target status instead of toggling, so a double-submit can't flip the job back.
    - Reopening also goes through the confirmation page.
    - An unknown status gets a 400.
    - The wording of the closed-job notice and the warning.
- **Sideways:**
  - Behavior 1's GREEN deliberately set every job to Closed regardless of the posted value. That was the minimum the test needed, and it left behavior 2 (reopen) a real assertion failure at RED.
  - After behavior 2, the view saved `request.POST["status"]` without validation. Claude flagged this gap, and it was closed in the normal tests with the 400 check.
  - Behavior 3 matches the full sentence "2 applications are still active" rather than the bare number, because the sidebar already shows the same count for the job.
  - Ruff reformatted the new test file once. There were no lint errors.

## 2026-10-29 — Implemented Phase 8 (pipeline counts, filters and application timeline)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 8`
2. Yes, I approve *(TDD behaviors: the count cards and filter tabs show correct counts, with Finished = Hired + Rejected + Withdrawn; a move keeps the selected filter and drops an applicant who no longer belongs in it; the application page shows the full stage history, newest first)*
3. Yes, I approve *(RED test for behavior 1)*
4. Yes, I approve *(behavior 1 green; continue to behavior 2)*
5. Yes, I approve *(RED test for behavior 2)*
6. Yes, I approve *(behavior 2 green; continue to behavior 3)*
7. Yes, I approve go ahead and make it pass *(RED test for behavior 3)*
8. Yes, I approve go ahead with the rest of the phase
9. It passed *(manual browser verification)*

### Summary
- **Outcome:**
  - `_pipeline_context(job, current)` runs one grouped stage-count query and builds five count cards (Applied → Offer) plus tabs for Active, each stage and Finished. A `PIPELINE_FILTERS` map gives each filter's stages, and an unknown `?stage=` value falls back to Active. Cards and tabs link to `?stage=<filter>`.
  - `Application.FINISHED_STAGES` was added next to `ACTIVE_STAGES`.
  - Each move form sends the current filter as a hidden `stage` field. The move endpoint re-renders the pipeline section with that filter. A non-HTMX move redirects to `?stage=<filter>`, or to the plain job URL for Active.
  - The new `ApplicationQuerySet.with_stage_details()` annotates `stage_since` and `left_from` (the latest change's from-stage) using subqueries. It replaces three copies of the old `Max(...)` annotation. `Application.left_from_display` shows "from <stage>" for Rejected and Withdrawn on the job, candidate and application pages.
  - New page `/applications/<pk>/`:
    - candidate and job cards;
    - a stage panel with the current stage, time in stage and move buttons;
    - a newest-first timeline with "From → To" or "Created at Applied", who made the change (full name, or username if none) and the local time.
  - A move on the application page posts `return_to=application` and re-renders `_application_stage.html` (the stage panel and timeline) in place.
  - The move buttons moved into a shared `_move_buttons.html` partial, used by both pages. The stage badges on the job and candidate pages link to the application page, and Pipeline in the sidebar is highlighted on application pages.
  - Three TDD behaviors went red → green, and eight normal tests cover:
    - the card links;
    - the default and unknown filters;
    - the Finished tab with "left from";
    - the application page's content;
    - the HTMX move and the non-HTMX move from the application page;
    - login required;
    - links from the job and candidate pages to the application page.
  - All 126 tests, Ruff lint and Ruff format pass, and no migration was needed. I verified the phase manually in the browser.
- **Deviations:**
  - I approved everything as proposed and asked no follow-up questions.
  - Claude made choices that aren't in the plan:
    - The job page now defaults to the Active tab, so finished applications appear only under Finished.
    - The `return_to=application` field tells the move endpoint which partial to send back.
    - Links to the application page are on the stage badges.
    - The table's empty state reads "No applications in this filter." when the job does have applications.
- **Sideways:**
  - Claude edited files with Python scripts that used the Windows default encoding, so a search string containing `→` didn't match and the `get_absolute_url` edit silently failed. Behavior 3's test then failed with an `AttributeError` instead of an assertion. Claude checked that the earlier edits were intact, redid the edit with UTF-8, and got a proper assertion failure at RED.
  - Behavior 2 made one existing test weaker: "Hired rows show no move buttons" passed only because Hired rows are no longer on the default page. The new Finished-tab test covers it properly.
  - An existing Phase 7 test checked the exact list of rendered templates and broke when the shared button partial was added. It was changed to check only the top-level template.
  - Ruff flagged a `zip()` call without `strict=`, and two files needed formatting. Both were fixed before the final run.

## 2026-10-29 — Implemented Phase 7 (stage moves via HTMX on the job page)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 7`
2. Yes, I approve *(TDD behaviors: the transition function returns the right moves for every stage; an allowed move updates the stage, writes a `StageChange` with the right user and from/to stages, and returns the pipeline partial; a disallowed or malformed move returns a 4xx and changes nothing. HTMX is vendored into `assets/js/` instead of loaded from a CDN)*
3. Yes, I approve *(RED test for behavior 1)*
4. Yes, I approve *(behavior 1 green; continue to the endpoint, partial and HTMX)*
5. Yes, I approve *(RED test for behavior 2)*
6. Yes, I approve continue to behavior 3
7. Yes, I approve *(RED test for behavior 3)*
8. Yes, I approve *(continue with the remaining tests and Ruff)*
9. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - `allowed_moves(stage)` in `hiring/models.py` is the one pure transition function. It works from a `PIPELINE` list (Applied → … → Offer → Hired) and returns forward, back (if any), Rejected and Withdrawn for active stages, and nothing for final stages.
  - `Application.available_moves` exposes those moves to templates. `Application.move_to(to_stage, by=)` raises `InvalidMove` for a disallowed move. Otherwise it saves the stage change and its `StageChange` in one transaction.
  - The stage update is conditional on the stored stage still matching (`filter(pk, stage).update(...)`), so the second of two simultaneous moves is refused instead of writing duplicate history.
  - New POST-only route `/applications/<pk>/move/`:
    - a value that isn't a stage returns 400;
    - a move that isn't allowed returns 409;
    - an HTMX request gets back the `_pipeline.html` partial;
    - a plain form post redirects to the job page.
  - The job page's applications table moved into `hiring/_pipeline.html` (`<section id="pipeline">`, swapped with `outerHTML`). Each row has a form with only its allowed buttons: "Advance to X", "Back to X", Reject and Withdraw. Finished rows show "Final". A refused move pops an alert and leaves the table untouched.
  - HTMX 2.0.4 is downloaded to `assets/js/htmx.min.js` and loaded in `base.html`. `<body>` sets `hx-headers` with the CSRF token.
  - Three TDD behaviors went red → green, with 18 parametrized cases. Seven normal tests cover:
    - GET returning 405;
    - login required;
    - the non-HTMX redirect;
    - the stale concurrent move;
    - moves on a closed job;
    - row buttons for Applied and Hired rows;
    - forward and back buttons mid-pipeline.
  - All 115 tests, Ruff lint and Ruff format pass, and no migration was needed. I verified the phase manually in the browser.
- **Deviations:**
  - I approved everything as proposed and asked no follow-up questions.
  - Claude made choices that aren't in the plan:
    - Refusal status codes: 400 for an unknown stage, 409 for a disallowed one.
    - The concurrent-move guard.
    - The non-HTMX redirect fallback.
    - The `alert()` on a refused move.
    - The button labels and the "Final" placeholder.
    - Vendoring HTMX instead of using a CDN.
- **Sideways:**
  - After behavior 1, Claude wrote the full `move_to` validation and the view's error handling before writing behavior 2's test. That would have made behaviors 2 and 3 pass without ever going red. Claude caught it, cut `move_to` back to a stub and removed the view validation, so both behaviors got a real assertion failure at RED.
  - The first view draft used `request.htmx`, which needs django-htmx (not installed). It was replaced with a check of the `HX-Request` header in the same cleanup.
  - A first draft of the mid-pipeline button test rendered the partial with a bare `RequestFactory` request. That crashed in the sidebar context processor (no `request.user`). It was rewritten to load the real job page through the logged-in client.

## 2026-10-29 — Implemented Phase 6 (apply from the candidate page)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 6`
2. Yes, I approve *(TDD behaviors: applying from the candidate page creates the application at Applied with exactly one initial `StageChange` recording the user, then returns to the candidate page; the job choices exclude closed and already-applied jobs, and a stale submit naming one is refused without writing anything; the candidate page lists each of their applications with job and current stage, and no one else's)*
3. Yes, I approve it *(RED test for behavior 1)*
4. Yes, move on to behavior
5. Yes, I approve it *(RED test for behavior 2)*
6. Yes, move on to behavior 3
7. Yes, I approve it *(RED test for behavior 3)*
8. Yes continue with the rest of phase 6
9. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - The shared `ApplicationForm` now takes either `job=` (pick a candidate, as in Phase 5) or `candidate=` (pick a job). It drops the fixed field and exposes `choice_name` for the one left to pick.
  - In candidate mode, the job choices are open jobs the candidate hasn't applied to, labelled "Title (Department, Location)". A stale choice shows "That job can't be chosen. It may be closed, or the candidate already applied to it."
  - Both views go through one `_create_application` helper. It calls `Application.start`, turns an `IntegrityError` into an error on the chosen field, and redirects back to the fixed job or candidate.
  - The new route `/candidates/<pk>/apply/` reuses `application_form.html`. The template now has breadcrumbs, heading, empty-state text, submit label and Cancel target for each entry point. When no jobs are left, it links to "Create a job".
  - The candidate page has an "Apply to job" button and an Applications table with job (linked, with department and location), stage badge and time in stage, or "No applications yet." The sidebar keeps "Candidates" highlighted on the apply page.
  - Three TDD behaviors went red → green. Nine normal tests cover:
    - both entry points using the same form class;
    - job labels and the Cancel link;
    - the no-jobs page;
    - a blank submit;
    - the simultaneous-submit race landing on the job field;
    - the Apply button and empty state;
    - the sidebar highlight;
    - login required and the 404.
  - All 90 tests, Ruff lint and Ruff format pass, and no migration was needed. I verified the phase manually in the browser.
- **Deviations:**
  - I approved everything as proposed and asked no follow-up questions.
  - Excluding archived candidates is still left to Phase 10. Until then, an archived candidate can be applied from their own page.
  - Claude made choices that aren't in the plan:
    - The job label format and the invalid-choice message.
    - One shared template with per-entry-point branches, rather than two templates.
    - A time-in-stage column on the candidate page.
    - On the candidate side, closed jobs are refused by the choice queryset. The form's `clean()` closed-job check still applies only when the job is fixed.
- **Sideways:**
  - Behavior 1's scaffolding deliberately left the job queryset unfiltered and the POST unsaved, so behaviors 1 and 2 each got a real assertion failure at RED.
  - The first draft of the generalized form template had a stray empty `{% with %}` line and a duplicated Cancel button. It was rewritten before any test ran.
  - Behavior 3's first draft checked job links across the whole page, and those checks passed on their own because the sidebar links every job. Claude spotted this and narrowed the assertions to `<main>` before presenting the RED test.
  - Ruff flagged one 101-character line in the new error message. The string was split, and lint was rerun clean.

## 2026-10-29 — Implemented Phase 5 (add an application from the job page)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 5`
2. Yes I approve *(TDD behaviors: adding an application from the job page creates it at Applied with exactly one initial `StageChange` recording the user; a duplicate is refused at the form and at the database; a submit against a closed job is refused and creates nothing)*
3. Yes, I approve it *(RED test for behavior 1)*
4. Yes, move on to behavior 2
5. Yes, I approve it *(RED test for behavior 2)*
6. Yes, move on to behavior 3
7. Yes, I approve it *(RED test for behavior 3)*
8. Yes, continue with the rest of phase 5
9. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - The `Application` model links a candidate (CASCADE) and a job (PROTECT), and has a stage from the eight-choice `Stage` list (default Applied), an `ACTIVE_STAGES` list and timestamps. It has a `UniqueConstraint` on (candidate, job).
  - The `StageChange` model has application (CASCADE), a blank-able `from_stage`, `to_stage`, `changed_by` user (PROTECT) and `changed_at`. Both models are in migration `0004_application_stagechange`.
  - `Application.start(candidate=, job=, by=)` creates the application and its initial `StageChange` in one `transaction.atomic()`.
  - The shared `ApplicationForm` (job fixed for now) lists only candidates without an application to that job, labelled "Name (email)". Its `clean()` refuses closed jobs. The view turns an `IntegrityError` from a simultaneous submit into a candidate-field error.
  - `/jobs/<pk>/applications/new/` shows the form, a closed-job warning, or a "no candidates available" hint.
  - The job page has an "Add application" button only while the job is Open, and an applications table with name, email, source, stage and time in stage. Time in stage comes from the newest `StageChange`.
  - `JobOpening.objects.with_active_count()` annotates `active_count`. The job list has a new Active column, and a `sidebar_jobs` context processor lists every job with its count under Pipeline, highlighting the current job.
  - Three TDD behaviors went red → green. Fifteen normal tests cover:
    - the simultaneous-submit race;
    - choice labels;
    - the closed-job and no-candidates form pages, and the closed message showing once;
    - a blank candidate submit;
    - the Add button showing only on open jobs;
    - the table contents and time in stage (from the latest change), and its empty state;
    - active counts on the list and sidebar, with finished stages left out;
    - the sidebar on other pages and the current-job highlight;
    - login required and the 404;
    - the `on_delete` rules.
  - All 78 tests, Ruff lint and Ruff format pass. I verified the phase manually in the browser.
- **Deviations:**
  - I approved everything as proposed and asked no follow-up questions.
  - Excluding archived candidates from the choices was left to Phase 10, as the plan says, even though the `archived` flag already exists.
  - Claude made choices that aren't in the plan:
    - Creation lives in an `Application.start` classmethod rather than in `form.save()`.
    - A stale choice shows "That candidate can't be added. They may have already applied to this job." instead of Django's default invalid-choice message.
    - The sidebar dims closed jobs, and the Pipeline link is also active on the add-application page.
    - Time in stage is computed from `Max(stage_changes__changed_at)` rather than stored on the application.
- **Sideways:**
  - The models were scaffolded without the unique constraint so behavior 2 got a real red. Migration `0004` was then deleted and regenerated with the constraint. It was never committed.
  - Behavior 2's form-level assertions already passed at RED, because the scaffolded candidate queryset refuses a stale choice. Only the database assertion was red, and Claude said so when presenting it.
  - Claude's first try at adding `Application.start` used a Python string replace that silently missed on the CRLF file with a non-ASCII `→`. The GREEN run failed with an `AttributeError`, and the change was redone with the Edit tool.
  - A first fix to the form template left an empty `{% if %}` branch and then an invalid `{% with %}` line. The template was rewritten in full, with `has_choices` passed from the view.
  - A bash heredoc holding the normal tests failed to parse and wrote nothing, so the test file was written with the Write tool instead.
  - One normal test posted `{}`, which the `request.POST or None` pattern treats as an unbound form. It was changed to post `{"candidate": ""}`, as a browser does.

## 2026-10-29 — Implemented Phase 4 (jobs CRUD with skills)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 4`
2. Yes I approve them. *(TDD behaviors: creating a job with checked skills saves it as Open with exactly those skills and goes to its job page; a skill used by a job can't be deleted; editing a job replaces its skills with the checked ones)*
3. Yes, I approve it. *(RED test for behavior 1)*
4. Yes, move on to behavior 2
5. Yes, i approve it *(RED test for behavior 2)*
6. Yes, move on to behavior 3
7. Yes, I approve it *(RED test for behavior 3)*
8. Yes, continue with the rest of phase 4
9. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - The `JobOpening` model has title, department, location, description, an Open/Closed `status` that defaults to Open, a `skills` many-to-many (`related_name="jobs"`) and timestamps. Migration `0003_jobopening`.
  - `JobOpeningForm` has the four core fields plus skill checkboxes. Status isn't on the form, so a new job is always Open.
  - Pages:
    - `/jobs/` lists title, department, location and a status badge, with links and a "New job" button.
    - `/jobs/new/` and `/jobs/<pk>/edit/` show the form.
    - `/jobs/<pk>/` shows the job header, status, skills, description and an Edit action.
  - `Skill.can_delete()` now returns true only when no job uses the skill, which replaces the Phase 3 stub. The Skills page shows "In use", and the delete view refuses with a 409.
  - Added a `make_job` fixture. Three TDD behaviors went red → green. Fifteen normal test functions (18 test cases) cover:
    - the status being ignored on create;
    - required fields;
    - skill checkboxes and the empty-skills hint;
    - the pre-filled edit form;
    - unchecking every skill;
    - the list and job pages;
    - 404s and login required;
    - the sidebar.
  - All 60 tests, Ruff lint and Ruff format pass. I verified the phase manually in the browser.
- **Deviations:**
  - I approved everything as proposed and asked no follow-up questions.
  - Claude made choices that aren't in the plan:
    - The sidebar highlights Jobs on the list, new and edit pages, and Pipeline on a job's own page, since that page becomes the pipeline. Both links still point to the job list.
    - The status badge is a shared `_job_status_badge.html` partial.
    - Job pages show location as well as the department.
- **Sideways:**
  - Behavior 1's status assertion passed before GREEN, because the model's `status` default was part of the scaffolding. Only the skills assertion was red. Claude said so when presenting the RED.
  - Behavior 3 needed a deliberately thin scaffold (an edit view that showed the form but ignored POST) to get a real red, because Django's `ModelForm` replaces M2M sets on its own. Claude flagged in advance that GREEN would be a few lines.
  - The first version of two normal tests checked `"Open" in html`, which the base layout's `aria-label="Open menu"` always satisfies. Claude caught this before running the feedback loops and changed the checks to match the badge text (`>Open</span>`).
  - Claude's first attempt to add this entry missed its anchor in PROMPTS.md because of wrong indentation, and it was redone.

## 2026-10-29 — Implemented Phase 3 (Skills page)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 3`
2. Yes I approve them *(TDD behaviors: adding a skill whose name matches an existing one in any case is refused; deleting a skill asks for confirmation, then removes it)*
3. Yes, I approve it *(RED test for behavior 1)*
4. Yes, move onto behavior 2
5. Yes, I approve it *(RED test for behavior 2)*
6. Yes, continue with the rest of phase 3
7. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - The `Skill` model is ordered by name ignoring case. Migration `0002_skill` includes a `UniqueConstraint(Lower("name"))`.
  - `SkillForm.clean_name` refuses a duplicate name in any letter case, the same way `clean_email` does for candidates.
  - The `/skills/` page lists skills and has an inline add form. `/skills/<pk>/delete/` shows a confirmation page and deletes on POST. The sidebar's Skills link is now live.
  - `Skill.can_delete()` always returns True until jobs exist. The list shows Delete only when it's true, and the delete view returns a 409 and changes nothing when it's false.
  - Two TDD behaviors went red → green. Eight normal test functions (nine test cases) cover:
    - name ordering;
    - blank names;
    - the DB-level duplicate;
    - the Delete link;
    - the refused delete (with `can_delete` faked to False);
    - the 404 for an unknown skill;
    - login required on both pages;
    - the active sidebar link.
  - All 39 tests, Ruff lint and Ruff format pass. I verified the phase manually in the browser.
- **Deviations:**
  - Claude chose only two TDD behaviors instead of three. A test of `can_delete` refusing needs jobs, and the plan leaves that test to Phase 4.
  - I approved everything as proposed and asked no follow-up questions.
  - Claude made two choices that aren't in the plan:
    - a refused delete returns 409 with an explanation page;
    - the refusal test fakes `can_delete` with `monkeypatch`, so the view's guard is tested now rather than waiting for Phase 4.
  - As in Phase 2, behavior 1's GREEN added the database constraint as well as the form check, which went beyond the minimum the test needed. Claude stated this in the plan I approved.
- **Sideways:**
  - The model was scaffolded without the constraint, so the RED failed on an assertion (302 instead of 200). Migration `0002_skill` was then deleted and regenerated with the constraint. It was never committed.
  - Ruff's E501 flagged the `SkillForm` widget line at 106 characters, and Claude wrapped it.

## 2026-10-29 — Implemented Phase 2 (candidates: log, list, edit and search)

### Prompts
1. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 2`
2. I approve them. *(TDD behaviors: case-insensitive duplicate email refused on create with a link to the existing candidate; edit keeps its own email but refuses another candidate's; list search by partial name or email)*
3. Yes, I approve it. *(RED test for behavior 1)*
4. Yes, move on to behavior 2
5. Yes, I approve it. *(RED test for behavior 2)*
6. Yes, move onto behavior 3
7. Yes, I approve the test. *(RED test for behavior 3)*
8. Yes add full-name matching and continue with phase 2
9. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - The `Candidate` model has a fixed six-choice `source`, an `archived` flag and timestamps. Migration `0001_initial` includes a `UniqueConstraint(Lower("email"))`.
  - `CandidateForm.clean_email` refuses a case-insensitive duplicate, ignoring the candidate being edited. It keeps the match on the form, so the template can show a "Go to *Name* instead" link.
  - There are candidate list, create, detail and edit pages, and the sidebar's Candidates link is now live.
  - The list search matches part of a first name, last name, full name or email, ignoring letter case.
  - Added a `make_candidate` factory fixture.
  - Three TDD behaviors went red → green. Ten normal test functions (19 test cases with parametrization) cover create/detail, the six source choices, the DB-level duplicate, the pre-filled edit form, the 404, login required on all four pages, and the active sidebar link.
  - All 28 tests, Ruff lint and Ruff format pass. I verified the phase manually in the browser.
- **Deviations:**
  - After behavior 3 went green, Claude pointed out that searching a full name ("Ada Lovelace") matched nothing, because each field was matched separately. I chose to add full-name matching, with a `"ada love"` test case.
  - Behavior 1's GREEN added the database constraint as well as the form check. That went beyond the minimum the test needed, but Claude stated it in the plan I approved.
  - Claude kept the duplicate link out of the error-message HTML. The form keeps the matched candidate, and the template renders the link, so no `mark_safe` is needed.
- **Sideways:**
  - Behavior 1's form check deliberately didn't leave out the candidate being edited. That gap was what made behavior 2's test go red (200 instead of 302).
  - `0001_initial` was generated before the constraint existed, so Claude deleted and regenerated it. It was never committed.
  - The first full-name annotation was named `full_name` and clashed with the model property ("property … has no setter"), so it was renamed `search_name`.
  - Ruff's DJ012 flagged `get_absolute_url` placed after a custom property, so the model was reordered.

## 2026-10-29 — Wrote CLAUDE.md and implemented Phase 1 (project skeleton, login, app shell)

### Prompts
1. Create the initial CLAUDE.md for this project. *(about 20–30 lines: one-line description, stack and package manager, durable PRD architecture decisions, pointers to the PRD, plan and prototypes; no commands, predicted paths, URL or testing conventions, business rules or new conventions)*
2. `/implement @prd/applicant-tracking-system.md @plans/applicant-tracking-system.md implement Phase 1`
3. Yes I approve them. *(TDD behaviors: anonymous job list redirects to login; `/` redirects to the job list)*
4. Yes, I approve it. *(RED test for behavior 1)*
5. Switch to the middleware option. *(replace per-view `@login_required` with Django's `LoginRequiredMiddleware`)*
6. Yes, I approve it. *(RED test for behavior 2)*
7. Yes continue with the rest of phase 1
8. It passed. *(manual browser verification)*

### Summary
- **Outcome:**
  - Wrote a 26-line `CLAUDE.md` (committed separately as `cbf1e9a`).
  - Phase 1 built:
    - uv project on Python 3.14, Django 6.1, the `config` package and the `hiring` app.
    - Tailwind + DaisyUI via django-tailwind-cli (CLI pinned to 2.10.34, `corporate` theme).
    - Ruff and pytest + pytest-django, with `staff_user` and `staff_client` fixtures.
  - Login is required site-wide through `LoginRequiredMiddleware`. Login and logout use Django's auth views, and logout is POST-only.
  - Variant A sidebar layout, collapsing to a ☰ drawer on small screens. `/` redirects to a placeholder job list.
  - Two TDD behaviors went red → green. Seven normal tests cover the login page, login landing, inactive users, the sidebar and logout form, POST-only logout, ending the session, and the admin's own login.
  - All 9 tests, Ruff lint and Ruff format pass. I verified the phase manually in the browser.
- **Deviations:**
  - After behavior 1 went green with `@login_required`, Claude pointed out that the decorator only protects views that remember to use it. I chose its recommended switch to `LoginRequiredMiddleware`.
  - Claude asked whether `config`/`hiring` in CLAUDE.md counted as "predicted structure". I didn't answer, so the bullet stayed.
  - Candidates and Skills appear in the sidebar but are disabled, because their pages arrive in Phases 2 and 3. Claude decided this; it is not in the plan.
- **Sideways:**
  - The first RED for behavior 1 failed with a 404 because `/jobs/` didn't exist yet. Claude treated that as missing scaffolding, added an unprotected route, and got a real red (200 instead of 302) before asking for approval.
  - The first login template used DaisyUI 4 classes (`form-control`, `input-bordered`) that DaisyUI 5 removed. Claude caught this before building and switched to `fieldset`.
  - Ruff flagged unused imports in the `startapp` stubs (`models.py`, `admin.py`), and Claude emptied them.
  - Git Bash mangled `/` in the curl output during the dev-server smoke test. This was cosmetic, and the redirects were correct.
  - Claude's first attempt to add this entry missed its anchor in PROMPTS.md because of wrong indentation, and it was redone.

## 2026-10-29 — Grilled the project idea, prototyped stage rules and pipeline UI, wrote the PRD

### Prompts
1. `/grill-me @project-idea.md`
2. A *(Q1 access: all staff have equal access)*
3. A *(Q2 candidate identity: email required and unique)*
4. A *(Q3 source: on the Candidate, from a fixed list)*
5. A *(Q4 skills: plain many-to-many)*
6. `/prototype can you prototype the hiring stage transition rules from the latest question in our grill?` *(Q5)*
7. Go with option C *(Q5 stage moves: one step forward/back, Rejected/Withdrawn from any active stage, final stages locked)*
8. B *(Q6 history: a StageChange record for every move)*
9. A *(Q7 closing a job: only blocks new applications)*
10. A *(Q8 reopening jobs: free Open ↔ Closed toggle)*
11. B *(Q9 candidate lifecycle: archive in the app, hard delete in the admin only)*
12. A *(Q10 archiving: blocked while the candidate has active applications)*
13. `/prototype build 3 structurally different variants for our main tracking pipeline dashboard screen` *(Q11)*
14. Go with option A *(Q11 layout: Variant A, sidebar + table)*
15. C *(Q12 creating applications: from both the job page and the candidate page, one shared form)*
16. B *(Q13 deletes: only when nothing depends on the record)*
17. A *(Q14 on_delete: cascade candidate → applications → history; protect users)*
18. A *(Q15 project structure: one `hiring` app)*
19. A *(Q16 tests: pytest + pytest-django)*
20. C *(Q17 HTMX move: re-render the whole pipeline section)*
21. `/to-prd`
22. Write this session log to PROMPTS.md according to its instructions.

### Summary
- **Outcome:**
  - Resolved 17 design questions covering every requirement in `project-idea.md`.
  - Built two throwaway prototypes:
    - `prototypes/stage-transitions.html`: compares the four stage-rule options with walkthroughs.
    - `prototypes/pipeline-dashboard.html`: three layout variants in Tailwind + DaisyUI.
  - Wrote `prd/applicant-tracking-system.md`, with 62 user stories, implementation decisions and out-of-scope items.
  - No application code was written. Nothing from this session is committed yet.
- **Deviations:**
  - Every answer matched the recommended option. There were no overrides.
  - Twice, instead of answering directly, I asked for a prototype (Q5 stage rules, Q11 pipeline screen) and then chose from it. Both choices matched the recommendation.
  - Some decisions were defaults Claude assumed rather than ones I explicitly answered. They're written into the PRD and should be checked:
    - skills managed on a Skills page and picked with checkboxes;
    - candidate search by name or email;
    - a disallowed move returns an error and changes nothing;
    - an application detail page that holds the history timeline;
    - the default candidate and job fields.
- **Sideways:**
  - Node.js isn't installed, so the stage-rules prototype's logic couldn't be checked with a script. The walkthrough outcomes were traced by hand instead.
  - The dashboard prototype was never opened in a browser during the session, so it hasn't been visually checked.
  - Claude spotted and fixed a sloppy button-ordering sort in the board variant before handing the prototype over.
  - The Q11 question listed options A–D, while the prototype labelled its variants A–C. "Option A" meant the sidebar + table layout in both, so the answer was unambiguous.