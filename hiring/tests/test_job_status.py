import pytest
from django.urls import reverse

from hiring.models import Application, JobOpening

Stage = Application.Stage

pytestmark = pytest.mark.django_db


def test_closing_a_job_changes_only_its_status(staff_client, staff_user, make_job, make_candidate):
    job = make_job()
    applied = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    interview = Application.start(
        candidate=make_candidate(email="grace@example.com"), job=job, by=staff_user
    )
    interview.move_to(Stage.SCREENING, by=staff_user)
    interview.move_to(Stage.INTERVIEW, by=staff_user)

    response = staff_client.post(
        reverse("hiring:job_status", args=[job.pk]), {"status": JobOpening.Status.CLOSED}
    )

    job.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == job.get_absolute_url()
    assert job.status == JobOpening.Status.CLOSED
    assert dict(job.applications.values_list("pk", "stage")) == {
        applied.pk: Stage.APPLIED,
        interview.pk: Stage.INTERVIEW,
    }
    assert applied.stage_changes.count() == 1
    assert interview.stage_changes.count() == 3


def test_reopening_a_closed_job_makes_it_open_again(staff_client, make_job):
    job = make_job(status=JobOpening.Status.CLOSED)

    response = staff_client.post(
        reverse("hiring:job_status", args=[job.pk]), {"status": JobOpening.Status.OPEN}
    )

    job.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == job.get_absolute_url()
    assert job.status == JobOpening.Status.OPEN


def test_close_confirmation_warns_with_the_active_application_count(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    for name, path in [
        ("ada", []),
        ("grace", [Stage.SCREENING, Stage.INTERVIEW]),
        ("alan", [Stage.REJECTED]),
        ("edsger", [Stage.WITHDRAWN]),
    ]:
        application = Application.start(
            candidate=make_candidate(email=f"{name}@example.com"), job=job, by=staff_user
        )
        for stage in path:
            application.move_to(stage, by=staff_user)

    html = staff_client.get(reverse("hiring:job_status", args=[job.pk])).content.decode()

    assert "2 applications are still active" in html


@pytest.mark.parametrize("status", ["", "archived"])
def test_unknown_status_is_refused_and_changes_nothing(staff_client, make_job, status):
    job = make_job()

    response = staff_client.post(reverse("hiring:job_status", args=[job.pk]), {"status": status})

    job.refresh_from_db()
    assert response.status_code == 400
    assert job.status == JobOpening.Status.OPEN


def test_close_page_offers_close_button_and_says_when_nothing_is_active(staff_client, make_job):
    job = make_job()

    html = staff_client.get(reverse("hiring:job_status", args=[job.pk])).content.decode()

    assert 'name="status" value="closed"' in html
    assert "No applications are active" in html
    assert f'href="{job.get_absolute_url()}" class="btn btn-ghost">Cancel' in html


def test_close_warning_uses_singular_for_one_active_application(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    Application.start(candidate=make_candidate(), job=job, by=staff_user)

    html = staff_client.get(reverse("hiring:job_status", args=[job.pk])).content.decode()

    assert "1 application is still active" in html


def test_reopen_page_offers_reopen_button_without_warning(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    Application.start(candidate=make_candidate(), job=job, by=staff_user)
    job.status = JobOpening.Status.CLOSED
    job.save()

    html = staff_client.get(reverse("hiring:job_status", args=[job.pk])).content.decode()

    assert 'name="status" value="open"' in html
    assert 'value="closed"' not in html
    assert "still active" not in html


def test_open_job_page_links_to_close_without_closed_notice(staff_client, make_job):
    job = make_job()

    html = staff_client.get(job.get_absolute_url()).content.decode()

    assert (
        f'href="{reverse("hiring:job_status", args=[job.pk])}" class="btn btn-sm">Close job' in html
    )
    assert "This job is closed" not in html


def test_closed_job_page_shows_notice_reopen_link_and_no_add_action(staff_client, make_job):
    job = make_job(status=JobOpening.Status.CLOSED)

    html = staff_client.get(job.get_absolute_url()).content.decode()

    assert "This job is closed" in html
    assert (
        f'href="{reverse("hiring:job_status", args=[job.pk])}" class="btn btn-sm">Reopen job'
        in html
    )
    assert reverse("hiring:application_create_for_job", args=[job.pk]) not in html


def test_reopened_job_accepts_new_applications_again(staff_client, make_job, make_candidate):
    job = make_job(status=JobOpening.Status.CLOSED)
    candidate = make_candidate()
    staff_client.post(reverse("hiring:job_status", args=[job.pk]), {"status": "open"})

    staff_client.post(
        reverse("hiring:application_create_for_job", args=[job.pk]), {"candidate": candidate.pk}
    )

    assert job.applications.get().candidate == candidate


def test_status_page_keeps_pipeline_highlighted(staff_client, make_job):
    job = make_job()

    html = staff_client.get(reverse("hiring:job_status", args=[job.pk])).content.decode()

    assert 'class="menu-active">Pipeline' in html


def test_unknown_job_status_page_returns_404(staff_client):
    assert staff_client.get(reverse("hiring:job_status", args=[999])).status_code == 404


@pytest.mark.parametrize("method", ["get", "post"])
def test_job_status_requires_login(client, make_job, method):
    job = make_job()

    response = getattr(client, method)(
        reverse("hiring:job_status", args=[job.pk]), {"status": "closed"}
    )

    job.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))
    assert job.status == JobOpening.Status.OPEN
