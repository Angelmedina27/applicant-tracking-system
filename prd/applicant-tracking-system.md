# PRD: Applicant Tracking System

## Problem Statement

Our employees who handle hiring have no shared, reliable place to track candidates and job openings. Candidates arrive from job boards, referrals, career fairs and other channels, and staff need to record who they are, which jobs they are being considered for, and where each person stands in the hiring process. Without a single system:

- The same person can be logged twice, or considered twice for the same job.
- Nobody can tell at a glance how many people are in Screening, Interview or Offer for a given job.
- When someone is moved, rejected or hired, there is no record of who made that call or when.
- There are no agreed rules for what happens when a job closes, when a candidate should be cleaned out of the list, or when a record created by mistake can be removed.

Candidates never use this system. It is an internal tool for staff only.

## Solution

An internal Django web application where logged-in staff can:

- Log candidates with their contact details and how they found us. Each candidate is identified by a unique email address.
- Create and edit job openings, tag them with skills, and toggle them between Open and Closed.
- Add a candidate to a job as an application, from either the job page or the candidate page. A candidate can have at most one application per job.
- Work each job's hiring pipeline from a single job page. The page shows stage counts, filter tabs and a table of applicants, and each row has buttons for only the moves allowed from that applicant's current stage. Clicking a move updates the pipeline section in place with HTMX, with no full page reload.
- Open any application to see its full stage history: who moved it, from where, to where, and when.
- Archive candidates who are done with us, and delete records only when they were created by mistake and nothing depends on them.

The stage rules are deliberately strict so the data stays trustworthy. Applications move one step forward or one step back, or to Rejected or Withdrawn from any active stage. Hired, Rejected and Withdrawn are final.

## User Stories

### Access

1. As a staff member, I want to log in with my own account, so that only employees can see hiring data.
2. As a staff member, I want every page to require login, so that candidate information is never visible to the public.
3. As a staff member, I want to log out, so that nobody else can use my session on a shared computer.
4. As a superuser, I want to create staff accounts in the Django admin, so that new hiring team members can get access.
5. As a superuser, I want to deactivate a departed employee's account instead of deleting it, so that they can no longer log in but their name stays on the history entries they created.

### Navigation and layout

6. As a staff member, I want a sidebar with links to Pipeline, Jobs, Candidates and Skills, so that I can reach every area of the app quickly.
7. As a staff member, I want the sidebar to list each job with its count of active applications, so that I can jump straight to a job's pipeline and see which jobs need attention.
8. As a staff member on a phone, I want the sidebar to collapse into a menu button, so that the app is usable on a small screen.

### Candidates

9. As a staff member, I want to log a new candidate with first name, last name, email, and optionally phone, a LinkedIn or portfolio URL, and notes, so that we have their basic details on file.
10. As a staff member, I want to record a candidate's source from a fixed list (Job Board, Referral, Company Website, Recruiter Outreach, Career Fair, Other), so that we can see where our candidates come from.
11. As a staff member, I want an optional "source details" field, so that I can note specifics like which job board or who referred them.
12. As a staff member, I want the system to refuse a candidate whose email already exists (ignoring upper and lower case), so that the same person is never logged twice.
13. As a staff member, I want to be told when I enter an existing candidate's email, with a link to that candidate, so that I can go to the existing record instead.
14. As a staff member, I want to edit a candidate's details, so that I can correct typos or update contact information, with the same unique-email rule enforced.
15. As a staff member, I want to see a list of candidates, so that I can find people we have logged.
16. As a staff member, I want to search the candidate list by name or email, so that I can find a specific person quickly.
17. As a staff member, I want a candidate's page to show all of their applications and the current stage of each, so that I can see everything they are being considered for.
18. As a staff member, I want to archive a candidate, so that people we are finished with no longer clutter the candidate list.
19. As a staff member, I want archiving to be blocked while the candidate has any active application, with an explanation of how many are active, so that nobody is hidden while still moving through a pipeline.
20. As a staff member, I want archived candidates hidden from the default list but shown when I choose "Show archived", so that I can still find them when needed.
21. As a staff member, I want to unarchive a candidate, so that I can bring them back if they become relevant again.
22. As a staff member, I want archived candidates to be excluded from new applications, so that they must be unarchived first and archived people stay out of pipelines.
23. As a superuser, I want to permanently delete a candidate in the Django admin, along with their applications and stage history, after a confirmation page that lists everything to be removed, so that I can handle a privacy request.

### Jobs and skills

24. As a staff member, I want to create a job opening with title, department, location and description, so that we can start hiring for it.
25. As a staff member, I want to edit a job opening, so that I can keep its details accurate.
26. As a staff member, I want to tag a job with skills using checkboxes, so that it is clear what the role requires.
27. As a staff member, I want one skill to be usable on many jobs, so that we don't duplicate skills like "Python" or "SQL".
28. As a staff member, I want to view, add and delete skills on a Skills page, so that the skill list stays tidy.
29. As a staff member, I want skill names to be unique regardless of upper and lower case, so that "python" and "Python" don't become two skills.
30. As a staff member, I want to delete a skill only when no job uses it, so that removing a skill never silently changes existing jobs.
31. As a staff member, I want to see a list of jobs with their status and active-application counts, so that I know which postings are open and which still have people in progress.
32. As a staff member, I want to close a job, so that no new applications can be added to it.
33. As a staff member, I want a warning showing how many applications are still active when I close a job, so that I know there are people still in progress.
34. As a staff member, I want applications on a closed job to keep moving through their stages, so that interviews and offers already underway can be finished.
35. As a staff member, I want to reopen a closed job, so that a job closed by mistake or paused can accept applications again.
36. As a staff member, I want to delete a job only when it has no applications, so that a job created by mistake can be removed without losing any hiring history.

### Applications

37. As a staff member on a job's page, I want to add an application by picking a candidate, so that I can add people while working that job's pipeline.
38. As a staff member on a candidate's page, I want to apply them to a job by picking a job, so that I can place someone right after logging them.
39. As a staff member, I want the application form to only offer valid choices (open jobs, unarchived candidates, and no job the candidate already applied to), so that I can't pick something that will be rejected.
40. As a staff member, I want the system to refuse a second application by the same candidate for the same job, even if two people submit at once, so that the one-application-per-job rule always holds.
41. As a staff member, I want the system to re-check on submit that the job is still open and the candidate is not archived, so that stale forms can't break the rules.
42. As a staff member, I want every new application to start at Applied and record that as its first history entry, so that every timeline starts at the beginning.
43. As a staff member, I want to delete an application only while it is still at Applied and has never been moved, so that an application added to the wrong job can be removed without losing real history.

### Pipeline and stage moves

44. As a staff member, I want each job's page to show a count card for each active stage (Applied, Screening, Interview, Final Review, Offer), so that I can see the shape of the pipeline at a glance.
45. As a staff member, I want filter tabs for Active, each individual stage, and Finished (Hired, Rejected, Withdrawn), each with a count, so that I can focus on one group of applicants.
46. As a staff member, I want clicking a stage count card to apply that stage's filter, so that I can drill in with one click.
47. As a staff member, I want a table of applications showing candidate name and email, source, current stage and time in that stage, so that I can see who needs attention.
48. As a staff member, I want Rejected and Withdrawn applications to show which stage they left from, so that I know how far they got.
49. As a staff member, I want each row to show buttons for only the moves allowed from its current stage, so that I can't attempt an invalid move.
50. As a staff member, I want to advance an application one stage forward, so that I can progress a candidate through hiring.
51. As a staff member, I want to move an application one stage back, so that I can undo an accidental advance.
52. As a staff member, I want to reject or withdraw an application from any active stage, so that I can end the process at any point.
53. As a staff member, I want Hired, Rejected and Withdrawn to be final, with no move buttons, so that finished outcomes can't be changed by accident.
54. As a staff member, I want stages to be impossible to skip, so that every applicant's history follows the real process.
55. As a staff member, I want a move to update the counts, tabs and table in place without reloading the whole browser page, so that I can work through many applicants quickly.
56. As a staff member, I want the current filter tab to stay selected after a move, and a moved applicant to disappear from a single-stage tab they no longer belong to, so that the view stays accurate.
57. As a staff member, I want the server to refuse a move that isn't allowed, even if submitted directly or from an outdated page, without changing anything, so that the rules can't be bypassed.

### Stage history

58. As a staff member, I want every stage move to be recorded with who made it, the from and to stages, and when, so that we have an audit trail.
59. As a staff member, I want an application detail page that shows the candidate, the job, the current stage and its move buttons, so that I can manage one application in depth.
60. As a staff member, I want the application detail page to show a timeline of all stage changes, newest first, so that I can see exactly how the application progressed and who made each decision.
61. As a staff member, I want a move made on the application detail page to update the stage panel and timeline in place, so that I see the result immediately.
62. As a staff member, I want a stage change and its history entry to be saved together or not at all, so that the history never disagrees with the current stage.

## Implementation Decisions

### Technology

- Python and Django, using SQLite as the database.
- uv for dependency management and running commands.
- Tailwind CSS with DaisyUI, integrated through django-tailwind-cli.
- HTMX for in-page interactions (stage moves).
- Ruff for linting and formatting.
- pytest with pytest-django for automated tests, with shared setup in fixtures (e.g. a logged-in staff client, a job, a candidate at a given stage).

### Project structure

- One Django project package named `config` for settings and root URL routing.
- One Django app named `hiring` containing all domain models, forms, views, templates and tests. Views and tests may be split into several modules inside the app if they grow, but models stay in this one app.
- Login and logout use Django's built-in authentication views. Every hiring view requires login.

### Authentication and permissions

- All active staff accounts have equal permissions inside the app. There are no roles or per-job access rules.
- Accounts are created by a superuser in the Django admin.
- Staff users are never deleted, only deactivated. The history model protects user records from deletion.

### Models

- **Candidate**
  - First name, last name, email (required, unique, compared case-insensitively), optional phone, optional URL (LinkedIn or portfolio), optional notes.
  - Source as a fixed choice list (Job Board, Referral, Company Website, Recruiter Outreach, Career Fair, Other), plus optional source details text.
  - An archived flag, and created/updated timestamps.
  - Exposes a "has active applications" check used for the archive rule.
- **Skill**
  - Name, unique and compared case-insensitively.
  - Exposes a "can delete" check (true only when no job uses it).
- **JobOpening**
  - Title, department, location, description, status (Open or Closed), and created/updated timestamps.
  - A plain many-to-many link to Skill.
  - Exposes an active-application count and a "can delete" check (true only when it has no applications).
- **Application**
  - Links one Candidate and one JobOpening, with a stage and timestamps.
  - A database-level unique constraint on (candidate, job).
  - Stage choices: Applied, Screening, Interview, Final Review, Offer, Hired, Rejected, Withdrawn.
  - "Active" means Applied through Offer. "Finished" means Hired, Rejected or Withdrawn.
  - Exposes a "can delete" check (true only when the stage is Applied and the only history entry is the initial one).
- **StageChange**
  - Records application, from-stage (empty for the initial entry), to-stage, the staff user who made the change, and a timestamp.

### Delete behaviour (on_delete)

- Application → Candidate: cascade. This is only reachable through the Django admin, since the app has no candidate delete.
- Application → JobOpening: protect.
- Skills linked to jobs: protected from deletion in the app by the "can delete" rule.
- StageChange → Application: cascade.
- StageChange → User: protect.

### Stage transition rules

- A single pure function returns the allowed next stages for a given current stage. From any active stage these are:
  - the next pipeline stage;
  - the previous pipeline stage, if any;
  - Rejected;
  - Withdrawn.
- Hired, Rejected and Withdrawn have no allowed moves.
- Templates use this function to decide which buttons to render, and the move view uses it to accept or refuse a request. They are never allowed to disagree.
- Pipeline order: Applied → Screening → Interview → Final Review → Offer → Hired.
- Performing a move updates the application's stage and creates a StageChange in one database transaction.
- Creating an application writes an initial StageChange (no from-stage, to Applied) in the same transaction.

### Job lifecycle rules

- Closing a job changes only its status and has no effect on existing applications, which can still be moved.
- New applications can't be created for a closed job.
- Jobs can be toggled freely between Open and Closed.
- The close action shows the number of active applications as a warning.
- Jobs can be deleted only when they have no applications, behind a confirmation page.

### Candidate lifecycle rules

- Candidates can be edited at any time, with email uniqueness enforced.
- Candidates can be archived only when they have no active applications, and can be unarchived at any time.
- Archived candidates are excluded from the default list and from application form choices. A "Show archived" filter reveals them.
- There is no candidate delete in the app. Superusers delete through the Django admin, where the cascade and Django's confirmation page apply.

### Application creation

- One shared application form, used from two entry points:
  - the job page, where the job is fixed and staff choose a candidate;
  - the candidate page, where the candidate is fixed and staff choose a job.
- Choice lists include only valid options: open jobs, unarchived candidates, and no existing application for that pair.
- On submit, the form re-validates the closed-job, archived-candidate and duplicate rules. The database unique constraint is the final safeguard.
- Applications can be deleted only while their "can delete" check is true, behind a confirmation page.

### Views and pages

- **Job pipeline page:** job header with status, skills and actions (edit, add application, open/close, delete when allowed), a closed-job notice when applicable, stage count cards, filter tabs, and the applications table.
- **Application detail page:** candidate and job info, current stage, move buttons, and the stage history timeline.
- **Other pages:**
  - candidate list, with search by name or email and a "Show archived" filter;
  - candidate detail, with applications and archive/unarchive;
  - candidate create/edit;
  - job list, with status and active counts;
  - job create/edit, with skill checkboxes;
  - Skills page, to list, add and delete skills;
  - confirmation pages for each allowed delete.
- The UI follows the chosen "sidebar + table" layout (Variant A of the dashboard prototype), using DaisyUI components and collapsing to a menu on narrow screens.

### HTMX interaction

- **On the job page:**
  - Each move button sends an HTMX POST to a move endpoint, including the current filter.
  - The target is the wrapper around the whole pipeline section (count cards, tabs and table).
  - The server re-renders that section from a single partial template, keeping the current filter. Counts, tabs and rows are therefore always consistent.
- **On the application detail page:** a move re-renders that page's stage panel and history timeline.
- **Refused moves:** an invalid or disallowed move gets a client-error response and changes nothing.
- Move endpoints accept POST only, require login, and use Django's CSRF protection, configured for HTMX requests.

### Testing focus

- **Stage transition function:** every stage's allowed moves, including that final stages have none and that stages can't be skipped.
- **Move endpoint:**
  - an allowed move updates the stage, writes history with the correct user, and returns the updated section with new counts;
  - a disallowed move is refused and changes nothing;
  - login is required.
- **Application creation:**
  - the duplicate rule, at both form and database level;
  - closed jobs and archived candidates are refused;
  - the initial history entry is written.
- **Lifecycle rules:**
  - archive blocked with active applications;
  - closing and reopening a job;
  - each "can delete" rule and its view.
- **Candidate email:** uniqueness, case-insensitively.

## Out of Scope

- Any candidate-facing features: candidate login, a public job board, application forms for candidates, or emails to candidates.
- Roles, per-job access, or any permission difference between staff members.
- Notes or reasons attached to individual stage moves.
- Reopening Rejected or Withdrawn applications, moving Hired applications, or skipping stages in the app. These are handled, if ever needed, by a superuser in the Django admin.
- Recording when or how often a job was closed or reopened.
- Required vs nice-to-have skills, proficiency levels, or skills on candidates and candidate–job matching.
- A per-application source (source is recorded once, on the candidate).
- Automatic changes to applications when a job closes or a candidate is archived.
- Anonymizing candidates instead of deleting them.
- A kanban board, drag-and-drop, or out-of-band HTMX updates.
- Reporting, analytics, and data import or export.
- File uploads such as resumes.

## Further Notes

- **Known limitations accepted with the stage rules.**
  - A candidate who withdraws or is rejected can't re-enter that job's pipeline, because final stages are locked and only one application per job is allowed.
  - A hire that falls through can't be changed in the app.
  - Both cases need a superuser in the Django admin.
- **Prototypes.** Two throwaway prototypes in the `prototypes` folder informed these decisions. They are references only and must not be promoted into production code.
  - `stage-transitions.html`: the stage rules; option C was chosen.
  - `pipeline-dashboard.html`: the screen layout; Variant A, sidebar + table, was chosen.
- **Possible future upgrades** that the current design leaves room for:
  - a board view, as a template change only, since the move endpoint and rules stay the same;
  - out-of-band count updates for very large pipelines;
  - a timestamp for when a job was closed;
  - an optional note on each stage change.
