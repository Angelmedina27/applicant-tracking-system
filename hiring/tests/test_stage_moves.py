import pytest
from django.urls import reverse

from hiring.models import Application, InvalidMove, JobOpening, allowed_moves

Stage = Application.Stage


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        (Stage.APPLIED, [Stage.SCREENING, Stage.REJECTED, Stage.WITHDRAWN]),
        (Stage.SCREENING, [Stage.INTERVIEW, Stage.APPLIED, Stage.REJECTED, Stage.WITHDRAWN]),
        (Stage.INTERVIEW, [Stage.FINAL_REVIEW, Stage.SCREENING, Stage.REJECTED, Stage.WITHDRAWN]),
        (Stage.FINAL_REVIEW, [Stage.OFFER, Stage.INTERVIEW, Stage.REJECTED, Stage.WITHDRAWN]),
        (Stage.OFFER, [Stage.HIRED, Stage.FINAL_REVIEW, Stage.REJECTED, Stage.WITHDRAWN]),
        (Stage.HIRED, []),
        (Stage.REJECTED, []),
        (Stage.WITHDRAWN, []),
    ],
)
def test_allowed_moves_for_every_stage(stage, expected):
    assert allowed_moves(stage) == expected


def move(client, application, to_stage):
    return client.post(
        reverse("hiring:application_move", args=[application.pk]),
        {"to_stage": to_stage},
        headers={"HX-Request": "true"},
    )


@pytest.mark.django_db
def test_allowed_move_updates_stage_records_history_and_returns_pipeline_section(
    staff_client, staff_user, make_job, make_candidate
):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)

    response = move(staff_client, application, Stage.SCREENING)

    application.refresh_from_db()
    assert application.stage == Stage.SCREENING
    latest = application.stage_changes.first()
    assert application.stage_changes.count() == 2
    assert (latest.from_stage, latest.to_stage) == (Stage.APPLIED, Stage.SCREENING)
    assert latest.changed_by == staff_user
    assert response.status_code == 200
    assert [t.name for t in response.templates] == ["hiring/_pipeline.html"]
    html = response.content.decode()
    assert '<section id="pipeline"' in html
    assert ">Screening</span>" in html
    assert "<html" not in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("stage", "to_stage"),
    [
        (Stage.APPLIED, Stage.INTERVIEW),
        (Stage.INTERVIEW, Stage.APPLIED),
        (Stage.OFFER, Stage.APPLIED),
        (Stage.HIRED, Stage.OFFER),
        (Stage.REJECTED, Stage.APPLIED),
        (Stage.WITHDRAWN, Stage.SCREENING),
        (Stage.APPLIED, Stage.APPLIED),
        (Stage.APPLIED, "promoted"),
        (Stage.APPLIED, ""),
    ],
)
def test_disallowed_move_is_refused_and_changes_nothing(
    staff_client, staff_user, make_job, make_candidate, stage, to_stage
):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    Application.objects.filter(pk=application.pk).update(stage=stage)

    response = move(staff_client, application, to_stage)

    assert 400 <= response.status_code < 500
    application.refresh_from_db()
    assert application.stage == stage
    assert application.stage_changes.count() == 1


@pytest.mark.django_db
def test_move_endpoint_rejects_get(staff_client, staff_user, make_job, make_candidate):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)

    response = staff_client.get(reverse("hiring:application_move", args=[application.pk]))

    assert response.status_code == 405
    application.refresh_from_db()
    assert application.stage == Stage.APPLIED


@pytest.mark.django_db
def test_move_endpoint_requires_login(client, staff_user, make_job, make_candidate):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)

    response = move(client, application, Stage.SCREENING)

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))
    application.refresh_from_db()
    assert application.stage == Stage.APPLIED
    assert application.stage_changes.count() == 1


@pytest.mark.django_db
def test_move_without_htmx_redirects_to_job_page(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    application = Application.start(candidate=make_candidate(), job=job, by=staff_user)

    response = staff_client.post(
        reverse("hiring:application_move", args=[application.pk]), {"to_stage": Stage.SCREENING}
    )

    assert response.status_code == 302
    assert response["Location"] == job.get_absolute_url()
    application.refresh_from_db()
    assert application.stage == Stage.SCREENING


@pytest.mark.django_db
def test_stale_move_after_concurrent_move_is_refused(staff_user, make_job, make_candidate):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    stale = Application.objects.get(pk=application.pk)
    application.move_to(Stage.SCREENING, by=staff_user)

    with pytest.raises(InvalidMove):
        stale.move_to(Stage.SCREENING, by=staff_user)

    application.refresh_from_db()
    assert application.stage == Stage.SCREENING
    assert application.stage_changes.count() == 2


@pytest.mark.django_db
def test_applications_on_closed_job_can_still_be_moved(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    application = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    job.status = JobOpening.Status.CLOSED
    job.save()

    response = move(staff_client, application, Stage.SCREENING)

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.stage == Stage.SCREENING


@pytest.mark.django_db
def test_job_page_rows_show_only_allowed_move_buttons(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    active = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    hired = Application.start(
        candidate=make_candidate(first_name="Grace", email="grace@example.com"),
        job=job,
        by=staff_user,
    )
    Application.objects.filter(pk=hired.pk).update(stage=Stage.HIRED)

    html = staff_client.get(job.get_absolute_url()).content.decode()

    active_url = reverse("hiring:application_move", args=[active.pk])
    hired_url = reverse("hiring:application_move", args=[hired.pk])
    assert f'hx-post="{active_url}"' in html
    assert f'hx-post="{hired_url}"' not in html
    for stage in (Stage.SCREENING, Stage.REJECTED, Stage.WITHDRAWN):
        assert f'name="to_stage" value="{stage}"' in html
    for stage in (Stage.APPLIED, Stage.INTERVIEW, Stage.HIRED):
        assert f'name="to_stage" value="{stage}"' not in html
    assert ">Advance to Screening</button>" in html
    assert "Back to" not in html
    assert 'hx-target="#pipeline"' in html


@pytest.mark.django_db
def test_mid_pipeline_row_offers_forward_and_back_buttons(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    application = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    Application.objects.filter(pk=application.pk).update(stage=Stage.INTERVIEW)

    html = staff_client.get(job.get_absolute_url()).content.decode()

    assert ">Advance to Final Review</button>" in html
    assert ">Back to Screening</button>" in html
