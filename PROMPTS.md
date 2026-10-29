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