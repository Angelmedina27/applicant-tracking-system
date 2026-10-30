import pytest
from django.db.models import ProtectedError
from django.urls import reverse

from hiring.models import Application, Candidate, JobOpening, StageChange

pytestmark = pytest.mark.django_db


def test_job_with_applications_cannot_be_deleted(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    Application.start(candidate=make_candidate(), job=job, by=staff_user)
    url = reverse("hiring:job_delete", args=[job.pk])

    page = staff_client.get(job.get_absolute_url()).content.decode()

    assert f'href="{url}"' not in page

    confirm = staff_client.get(url)

    assert confirm.status_code == 409
    assert "Delete job" not in confirm.content.decode()

    response = staff_client.post(url)

    assert response.status_code == 409
    assert JobOpening.objects.filter(pk=job.pk).exists()
    assert job.applications.count() == 1


def test_application_moved_back_to_applied_cannot_be_deleted(
    staff_client, staff_user, make_job, make_candidate
):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    application.move_to(Application.Stage.SCREENING, by=staff_user)
    application.move_to(Application.Stage.APPLIED, by=staff_user)
    url = reverse("hiring:application_delete", args=[application.pk])

    page = staff_client.get(application.get_absolute_url()).content.decode()

    assert f'href="{url}"' not in page

    confirm = staff_client.get(url)

    assert confirm.status_code == 409
    assert "Delete application" not in confirm.content.decode()

    response = staff_client.post(url)

    assert response.status_code == 409
    assert Application.objects.filter(pk=application.pk).exists()
    assert application.stage_changes.count() == 3


def test_admin_candidate_delete_confirms_then_cascades_to_applications_and_history(
    client, admin_user, staff_user, make_job, make_candidate
):
    candidate = make_candidate()
    application = Application.start(candidate=candidate, job=make_job(), by=staff_user)
    application.move_to(Application.Stage.SCREENING, by=staff_user)
    client.force_login(admin_user)
    url = f"/admin/hiring/candidate/{candidate.pk}/delete/"

    confirm = client.get(url)

    assert confirm.status_code == 200
    assert "Applications: 1" in confirm.content.decode()
    assert "Stage changes: 2" in confirm.content.decode()

    response = client.post(url, {"post": "yes"})

    assert response.status_code == 302
    assert not Candidate.objects.filter(pk=candidate.pk).exists()
    assert not Application.objects.exists()
    assert not StageChange.objects.exists()


def test_deleting_a_job_without_applications_asks_for_confirmation_then_removes_it(
    staff_client, make_job
):
    job = make_job()
    url = reverse("hiring:job_delete", args=[job.pk])

    page = staff_client.get(job.get_absolute_url()).content.decode()
    confirm = staff_client.get(url)

    assert f'href="{url}"' in page
    assert confirm.status_code == 200
    assert "Delete job" in confirm.content.decode()
    assert JobOpening.objects.filter(pk=job.pk).exists()

    response = staff_client.post(url)

    assert response.status_code == 302
    assert response["Location"] == reverse("hiring:job_list")
    assert not JobOpening.objects.filter(pk=job.pk).exists()


def test_job_with_only_finished_applications_cannot_be_deleted(
    staff_user, make_job, make_candidate
):
    job = make_job()
    application = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    application.move_to(Application.Stage.WITHDRAWN, by=staff_user)

    assert not job.can_delete()


def test_deleting_an_unmoved_application_asks_for_confirmation_then_removes_it(
    staff_client, staff_user, make_job, make_candidate
):
    candidate = make_candidate()
    job = make_job()
    application = Application.start(candidate=candidate, job=job, by=staff_user)
    url = reverse("hiring:application_delete", args=[application.pk])

    page = staff_client.get(application.get_absolute_url()).content.decode()
    confirm = staff_client.get(url)

    assert f'href="{url}"' in page
    assert confirm.status_code == 200
    assert "Delete application" in confirm.content.decode()

    response = staff_client.post(url)

    assert response.status_code == 302
    assert response["Location"] == job.get_absolute_url()
    assert not Application.objects.filter(pk=application.pk).exists()
    assert not StageChange.objects.exists()
    assert Candidate.objects.filter(pk=candidate.pk).exists()
    assert JobOpening.objects.filter(pk=job.pk).exists()


@pytest.mark.parametrize(
    "stage", [Application.Stage.SCREENING, Application.Stage.REJECTED, Application.Stage.WITHDRAWN]
)
def test_application_that_left_applied_cannot_be_deleted(
    staff_user, make_job, make_candidate, stage
):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    application.move_to(stage, by=staff_user)

    assert not application.can_delete()


def test_moving_an_application_removes_its_delete_link(
    staff_client, staff_user, make_job, make_candidate
):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    url = reverse("hiring:application_delete", args=[application.pk])

    response = staff_client.post(
        reverse("hiring:application_move", args=[application.pk]),
        {"to_stage": Application.Stage.SCREENING, "return_to": "application"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert f'href="{url}"' not in response.content.decode()


@pytest.mark.parametrize("name", ["job_delete", "application_delete"])
def test_delete_pages_require_login(client, staff_user, make_job, make_candidate, name):
    job = make_job()
    application = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    pk = job.pk if name == "job_delete" else application.pk

    response = client.post(reverse(f"hiring:{name}", args=[pk]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))
    assert Application.objects.filter(pk=application.pk).exists()


@pytest.mark.parametrize("name", ["job_delete", "application_delete"])
def test_deleting_unknown_record_returns_404(staff_client, name):
    assert staff_client.post(reverse(f"hiring:{name}", args=[999])).status_code == 404


def test_user_referenced_by_history_cannot_be_deleted(staff_user, make_job, make_candidate):
    Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)

    with pytest.raises(ProtectedError):
        staff_user.delete()


def test_admin_refuses_to_delete_a_user_with_history(
    client, admin_user, staff_user, make_job, make_candidate
):
    Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    client.force_login(admin_user)
    url = reverse("admin:auth_user_delete", args=[staff_user.pk])

    confirm = client.get(url)
    client.post(url, {"post": "yes"})

    assert "would require deleting the following protected related objects" in (
        confirm.content.decode()
    )
    assert type(staff_user).objects.filter(pk=staff_user.pk).exists()


def test_deactivated_user_cannot_log_in_but_stays_on_history(
    client, staff_user, make_job, make_candidate
):
    staff_user.first_name, staff_user.last_name = "Grace", "Hopper"
    staff_user.save()
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    staff_user.is_active = False
    staff_user.save()

    assert not client.login(username="staff", password="staff-pass-123")

    viewer = type(staff_user).objects.create_user(username="viewer", password="viewer-pass-123")
    client.force_login(viewer)
    page = client.get(application.get_absolute_url()).content.decode()

    assert "Grace Hopper" in page
