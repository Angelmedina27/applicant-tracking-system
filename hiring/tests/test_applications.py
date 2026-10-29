from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone

from hiring.forms import ApplicationForm
from hiring.models import Application, Candidate, JobOpening, StageChange

pytestmark = pytest.mark.django_db


def make_application(candidate, job, by, stage=Application.Stage.APPLIED):
    application = Application.start(candidate=candidate, job=job, by=by)
    if stage != Application.Stage.APPLIED:
        application.stage_changes.create(
            from_stage=Application.Stage.APPLIED, to_stage=stage, changed_by=by
        )
        application.stage = stage
        application.save()
    return application


def test_adding_application_from_job_page_starts_at_applied_with_initial_history(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    candidate = make_candidate()

    response = staff_client.post(
        reverse("hiring:application_create_for_job", args=[job.pk]),
        {"candidate": candidate.pk},
    )

    assert response.status_code == 302
    assert response["Location"] == job.get_absolute_url()
    application = Application.objects.get()
    assert application.candidate == candidate
    assert application.job == job
    assert application.stage == Application.Stage.APPLIED
    change = StageChange.objects.get()
    assert change.application == application
    assert change.from_stage == ""
    assert change.to_stage == Application.Stage.APPLIED
    assert change.changed_by == staff_user


def test_duplicate_application_is_refused_by_form_and_database(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    applied = make_candidate()
    fresh = make_candidate(first_name="Grace", last_name="Hopper", email="grace@example.com")
    Application.start(candidate=applied, job=job, by=staff_user)
    url = reverse("hiring:application_create_for_job", args=[job.pk])

    choices = staff_client.get(url).context["form"].fields["candidate"].queryset
    stale = staff_client.post(url, {"candidate": applied.pk})

    assert list(choices) == [fresh]
    assert stale.status_code == 200
    assert stale.context["form"].errors["candidate"]
    assert Application.objects.count() == 1
    assert StageChange.objects.count() == 1
    with pytest.raises(IntegrityError):
        Application.objects.create(candidate=applied, job=job)


def test_submitting_against_a_closed_job_is_refused(staff_client, make_job, make_candidate):
    job = make_job(status=JobOpening.Status.CLOSED)
    candidate = make_candidate()

    response = staff_client.post(
        reverse("hiring:application_create_for_job", args=[job.pk]),
        {"candidate": candidate.pk},
    )

    assert response.status_code == 200
    assert "This job is closed" in " ".join(response.context["form"].non_field_errors())
    assert not Application.objects.exists()
    assert not StageChange.objects.exists()


def test_simultaneous_duplicate_submit_is_refused_without_writing_anything(
    staff_client, staff_user, make_job, make_candidate, monkeypatch
):
    job = make_job()
    candidate = make_candidate()
    original_clean = ApplicationForm.clean

    def clean_then_lose_the_race(form):
        cleaned_data = original_clean(form)
        Application.start(candidate=candidate, job=job, by=staff_user)
        return cleaned_data

    monkeypatch.setattr(ApplicationForm, "clean", clean_then_lose_the_race)

    response = staff_client.post(
        reverse("hiring:application_create_for_job", args=[job.pk]),
        {"candidate": candidate.pk},
    )

    assert response.status_code == 200
    assert response.context["form"].errors["candidate"] == [
        "This candidate has already applied to this job."
    ]
    assert Application.objects.count() == 1
    assert StageChange.objects.count() == 1


def test_application_form_labels_candidates_with_name_and_email(
    staff_client, make_job, make_candidate
):
    job = make_job()
    make_candidate()

    html = staff_client.get(
        reverse("hiring:application_create_for_job", args=[job.pk])
    ).content.decode()

    assert "Ada Lovelace (ada@example.com)" in html
    assert ">Add application</button>" in html


def test_application_form_for_closed_job_shows_notice_and_no_submit(
    staff_client, make_job, make_candidate
):
    job = make_job(status=JobOpening.Status.CLOSED)
    make_candidate()

    html = staff_client.get(
        reverse("hiring:application_create_for_job", args=[job.pk])
    ).content.decode()

    assert "This job is closed" in html
    assert 'name="candidate"' not in html
    assert ">Add application</button>" not in html


def test_application_form_without_available_candidates_points_to_log_one(staff_client, make_job):
    job = make_job()

    html = staff_client.get(
        reverse("hiring:application_create_for_job", args=[job.pk])
    ).content.decode()

    assert "No candidates are available" in html
    assert f'href="{reverse("hiring:candidate_create")}"' in html
    assert ">Add application</button>" not in html


def test_refused_closed_job_submit_shows_the_message_once(staff_client, make_job, make_candidate):
    job = make_job(status=JobOpening.Status.CLOSED)
    candidate = make_candidate()

    html = staff_client.post(
        reverse("hiring:application_create_for_job", args=[job.pk]),
        {"candidate": candidate.pk},
    ).content.decode()

    assert html.count("This job is closed") == 1


def test_submit_without_candidate_is_refused(staff_client, make_job):
    job = make_job()

    response = staff_client.post(
        reverse("hiring:application_create_for_job", args=[job.pk]), {"candidate": ""}
    )

    assert response.status_code == 200
    assert response.context["form"].errors["candidate"]
    assert not Application.objects.exists()


def test_job_page_offers_add_application_only_while_open(staff_client, make_job):
    open_job = make_job()
    closed_job = make_job(title="Designer", status=JobOpening.Status.CLOSED)

    open_html = staff_client.get(open_job.get_absolute_url()).content.decode()
    closed_html = staff_client.get(closed_job.get_absolute_url()).content.decode()

    assert reverse("hiring:application_create_for_job", args=[open_job.pk]) in open_html
    assert reverse("hiring:application_create_for_job", args=[closed_job.pk]) not in closed_html


def test_job_page_lists_its_applications_with_stage_and_time_in_stage(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    other_job = make_job(title="Designer")
    ada = make_candidate()
    grace = make_candidate(
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
        source=Candidate.Source.CAREER_FAIR,
    )
    alan = make_candidate(first_name="Alan", last_name="Turing", email="alan@example.com")
    make_application(ada, job, staff_user)
    make_application(grace, job, staff_user, stage=Application.Stage.SCREENING)
    make_application(alan, other_job, staff_user)
    now = timezone.now()
    StageChange.objects.filter(application__candidate=ada).update(
        changed_at=now - timedelta(days=3)
    )
    grace_changes = StageChange.objects.filter(application__candidate=grace)
    grace_changes.filter(from_stage="").update(changed_at=now - timedelta(days=10))
    grace_changes.exclude(from_stage="").update(changed_at=now - timedelta(days=2))

    html = staff_client.get(job.get_absolute_url()).content.decode()

    for text in ("Ada Lovelace", "ada@example.com", "Referral", "Applied", "3\xa0days"):
        assert text in html
    for text in ("Grace Hopper", "grace@example.com", "Career Fair", "Screening", "2\xa0days"):
        assert text in html
    assert "10\xa0days" not in html
    assert "Alan Turing" not in html
    assert "No applications yet" not in html


def test_job_page_without_applications_says_so(staff_client, make_job):
    html = staff_client.get(make_job().get_absolute_url()).content.decode()

    assert "No applications yet" in html


def test_job_list_and_sidebar_count_only_active_applications(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    empty_job = make_job(title="Designer")
    stages = [
        Application.Stage.APPLIED,
        Application.Stage.OFFER,
        Application.Stage.HIRED,
        Application.Stage.REJECTED,
        Application.Stage.WITHDRAWN,
    ]
    for i, stage in enumerate(stages):
        candidate = make_candidate(email=f"person{i}@example.com")
        make_application(candidate, job, staff_user, stage=stage)

    response = staff_client.get(reverse("hiring:job_list"))

    listed = {j.pk: j.active_count for j in response.context["jobs"]}
    in_sidebar = {j.pk: j.active_count for j in response.context["sidebar_jobs"]}
    assert listed == in_sidebar == {job.pk: 2, empty_job.pk: 0}


def test_sidebar_lists_jobs_on_every_page(staff_client, make_job):
    job = make_job()

    html = staff_client.get(reverse("hiring:candidate_list")).content.decode()

    assert f'href="{job.get_absolute_url()}"' in html
    assert job.title in html


def test_sidebar_marks_current_job(staff_client, make_job):
    job = make_job()
    other = make_job(title="Designer")

    html = staff_client.get(job.get_absolute_url()).content.decode()

    assert f'href="{job.get_absolute_url()}" class="justify-between menu-focus"' in html
    assert f'href="{other.get_absolute_url()}" class="justify-between"' in html


def test_application_form_requires_login(client, make_job):
    url = reverse("hiring:application_create_for_job", args=[make_job().pk])

    response = client.get(url)

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


def test_application_form_for_unknown_job_returns_404(staff_client):
    url = reverse("hiring:application_create_for_job", args=[999])

    assert staff_client.get(url).status_code == 404


def test_delete_rules_protect_jobs_and_users_and_cascade_candidates(
    staff_user, make_job, make_candidate
):
    job = make_job()
    candidate = make_candidate()
    make_application(candidate, job, staff_user)

    with pytest.raises(ProtectedError):
        job.delete()
    with pytest.raises(ProtectedError):
        staff_user.delete()

    candidate.delete()

    assert not Application.objects.exists()
    assert not StageChange.objects.exists()


def test_applying_from_candidate_page_starts_at_applied_with_initial_history(
    staff_client, staff_user, make_job, make_candidate
):
    candidate = make_candidate()
    job = make_job()

    response = staff_client.post(
        reverse("hiring:application_create_for_candidate", args=[candidate.pk]),
        {"job": job.pk},
    )

    assert response.status_code == 302
    assert response["Location"] == candidate.get_absolute_url()
    application = Application.objects.get()
    assert application.candidate == candidate
    assert application.job == job
    assert application.stage == Application.Stage.APPLIED
    change = StageChange.objects.get()
    assert change.application == application
    assert change.from_stage == ""
    assert change.to_stage == Application.Stage.APPLIED
    assert change.changed_by == staff_user


def test_candidate_page_job_choices_exclude_closed_and_already_applied_jobs(
    staff_client, staff_user, make_job, make_candidate
):
    candidate = make_candidate()
    open_job = make_job()
    closed_job = make_job(title="Designer", status=JobOpening.Status.CLOSED)
    applied_job = make_job(title="Data Analyst")
    Application.start(candidate=candidate, job=applied_job, by=staff_user)
    url = reverse("hiring:application_create_for_candidate", args=[candidate.pk])

    choices = staff_client.get(url).context["form"].fields["job"].queryset
    stale_closed = staff_client.post(url, {"job": closed_job.pk})
    stale_applied = staff_client.post(url, {"job": applied_job.pk})

    assert list(choices) == [open_job]
    for stale in (stale_closed, stale_applied):
        assert stale.status_code == 200
        assert stale.context["form"].errors["job"]
    assert Application.objects.count() == 1
    assert StageChange.objects.count() == 1


def test_candidate_page_lists_their_applications_with_job_and_stage(
    staff_client, staff_user, make_job, make_candidate
):
    ada = make_candidate()
    grace = make_candidate(first_name="Grace", last_name="Hopper", email="grace@example.com")
    backend = make_job()
    designer = make_job(title="Designer")
    analyst = make_job(title="Data Analyst")
    make_application(ada, backend, staff_user)
    make_application(ada, designer, staff_user, stage=Application.Stage.SCREENING)
    make_application(grace, analyst, staff_user, stage=Application.Stage.OFFER)

    html = staff_client.get(ada.get_absolute_url()).content.decode()
    main = html.split("<main", 1)[1].split("</main>", 1)[0]

    assert f'href="{backend.get_absolute_url()}"' in main
    assert f'href="{designer.get_absolute_url()}"' in main
    assert "Applied" in main
    assert "Screening" in main
    assert f'href="{analyst.get_absolute_url()}"' not in main
    assert "Offer" not in main


def test_both_entry_points_use_the_shared_application_form(staff_client, make_job, make_candidate):
    job = make_job()
    candidate = make_candidate()

    from_job = staff_client.get(reverse("hiring:application_create_for_job", args=[job.pk]))
    from_candidate = staff_client.get(
        reverse("hiring:application_create_for_candidate", args=[candidate.pk])
    )

    assert type(from_job.context["form"]) is ApplicationForm
    assert type(from_candidate.context["form"]) is ApplicationForm
    assert list(from_job.context["form"].fields) == ["candidate"]
    assert list(from_candidate.context["form"].fields) == ["job"]


def test_candidate_apply_form_labels_jobs_with_department_and_location(
    staff_client, make_job, make_candidate
):
    candidate = make_candidate()
    make_job()

    html = staff_client.get(
        reverse("hiring:application_create_for_candidate", args=[candidate.pk])
    ).content.decode()

    assert "Backend Engineer (Engineering, Remote)" in html
    assert ">Apply to job</button>" in html
    assert f'href="{candidate.get_absolute_url()}" class="btn btn-ghost">Cancel' in html


def test_candidate_apply_form_without_available_jobs_points_to_create_one(
    staff_client, make_job, make_candidate
):
    candidate = make_candidate()
    make_job(status=JobOpening.Status.CLOSED)

    html = staff_client.get(
        reverse("hiring:application_create_for_candidate", args=[candidate.pk])
    ).content.decode()

    assert "No jobs are available" in html
    assert f'href="{reverse("hiring:job_create")}"' in html
    assert 'name="job"' not in html
    assert ">Apply to job</button>" not in html


def test_candidate_apply_submit_without_job_is_refused(staff_client, make_job, make_candidate):
    candidate = make_candidate()
    make_job()

    response = staff_client.post(
        reverse("hiring:application_create_for_candidate", args=[candidate.pk]), {"job": ""}
    )

    assert response.status_code == 200
    assert response.context["form"].errors["job"]
    assert not Application.objects.exists()


def test_simultaneous_duplicate_from_candidate_page_is_refused_on_the_job_field(
    staff_client, staff_user, make_job, make_candidate, monkeypatch
):
    candidate = make_candidate()
    job = make_job()
    original_clean = ApplicationForm.clean

    def clean_then_lose_the_race(form):
        cleaned_data = original_clean(form)
        Application.start(candidate=candidate, job=job, by=staff_user)
        return cleaned_data

    monkeypatch.setattr(ApplicationForm, "clean", clean_then_lose_the_race)

    response = staff_client.post(
        reverse("hiring:application_create_for_candidate", args=[candidate.pk]),
        {"job": job.pk},
    )

    assert response.status_code == 200
    assert response.context["form"].errors["job"] == [
        "This candidate has already applied to this job."
    ]
    assert Application.objects.count() == 1
    assert StageChange.objects.count() == 1


def test_candidate_page_offers_apply_to_job(staff_client, make_candidate):
    candidate = make_candidate()

    html = staff_client.get(candidate.get_absolute_url()).content.decode()

    assert reverse("hiring:application_create_for_candidate", args=[candidate.pk]) in html
    assert "No applications yet" in html


def test_candidate_apply_page_highlights_candidates_in_sidebar(staff_client, make_candidate):
    candidate = make_candidate()

    html = staff_client.get(
        reverse("hiring:application_create_for_candidate", args=[candidate.pk])
    ).content.decode()

    assert 'class="menu-active">Candidates</a>' in html


def test_candidate_apply_form_requires_login(client, make_candidate):
    url = reverse("hiring:application_create_for_candidate", args=[make_candidate().pk])

    response = client.get(url)

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


def test_candidate_apply_form_for_unknown_candidate_returns_404(staff_client):
    url = reverse("hiring:application_create_for_candidate", args=[999])

    assert staff_client.get(url).status_code == 404
