# Project Objectives
This is a new Django application named Applicant Tracking System. It is an internal hiring system for our employees to use. Candidates will not log in to this system at all.

# Technology Stack
- Python and Django
- SQLite for the database
- uv for package management
- Tailwind CSS and DaisyUI with django-tailwind-cli
- HTMX for page interactions
- Ruff for linting and formatting
- Automated tests using pytest or Django tests

# Business Requirements
1. The system is internal only for employees handling the hiring process.
2. Staff need to log candidates and their basic details from places like job boards or referrals.
3. Staff need to create and edit job openings, and flag them as open or closed.
4. Candidates can apply to multiple different jobs, but can only have one application per specific job opening.
5. Applications need to follow these exact stages: Applied, Screening, Interview, Final Review, Offer, Hired, Rejected, and Withdrawn.
6. We need to use HTMX so staff can move applicants between stages without refreshing the whole browser page.
7. We need to track skills for each job opening, where one skill can be linked to many different openings.
8. We need to figure out how we want to manage candidate records over time, like editing, archiving, or removing them.
9. We need to decide what happens to open applications when a job posting closes, and if we are allowed to reopen closed jobs.