import itertools
import re

import pytest
from django.urls import reverse
from django.utils.dateformat import format as date_format
from django.utils.timezone import localtime

from hiring.models import Application

Stage = Application.Stage


def counts(html, kind):
    """Map each count card or filter tab (`kind` = "card" or "tab") to its count."""
    pattern = rf'data-{kind}="(\w+)".*?data-count>(\d+)<'
    return {name: int(count) for name, count in re.findall(pattern, html, re.S)}


def selected_tabs(html):
    return re.findall(r'data-tab="(\w+)"[^>]*aria-selected="true"', html)


@pytest.fixture
def make_application(staff_user, make_job, make_candidate):
    numbers = itertools.count(1)

    def make(job, stage):
        n = next(numbers)
        candidate = make_candidate(first_name=f"Cand{n}", email=f"cand{n}@example.com")
        application = Application.start(candidate=candidate, job=job, by=staff_user)
        Application.objects.filter(pk=application.pk).update(stage=stage)
        return application

    return make


@pytest.mark.django_db
def test_count_cards_and_filter_tabs_show_correct_counts(staff_client, make_job, make_application):
    job = make_job()
    for stage in [
        Stage.APPLIED,
        Stage.APPLIED,
        Stage.SCREENING,
        Stage.OFFER,
        Stage.HIRED,
        Stage.REJECTED,
        Stage.WITHDRAWN,
        Stage.WITHDRAWN,
    ]:
        make_application(job, stage)
    make_application(make_job(title="Other job"), Stage.APPLIED)

    html = staff_client.get(job.get_absolute_url()).content.decode()

    assert counts(html, "card") == {
        "applied": 2,
        "screening": 1,
        "interview": 0,
        "final_review": 0,
        "offer": 1,
    }
    assert counts(html, "tab") == {
        "active": 4,
        "applied": 2,
        "screening": 1,
        "interview": 0,
        "final_review": 0,
        "offer": 1,
        "finished": 4,
    }


@pytest.mark.django_db
def test_move_keeps_selected_filter_and_drops_applicant_who_left_it(
    staff_client, make_job, make_application
):
    job = make_job()
    moving = make_application(job, Stage.SCREENING)
    staying = make_application(job, Stage.SCREENING)

    page = staff_client.get(job.get_absolute_url(), {"stage": "screening"}).content.decode()
    assert '<input type="hidden" name="stage" value="screening">' in page

    response = staff_client.post(
        reverse("hiring:application_move", args=[moving.pk]),
        {"to_stage": Stage.INTERVIEW, "stage": "screening"},
        headers={"HX-Request": "true"},
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert selected_tabs(html) == ["screening"]
    assert counts(html, "tab")["screening"] == 1
    assert counts(html, "tab")["interview"] == 1
    assert staying.candidate.email in html
    assert moving.candidate.email not in html


def timeline(html):
    """Return each timeline entry's text, in page order, with tags and extra spaces removed."""
    entries = re.findall(r"<li data-stage-change[^>]*>(.*?)</li>", html, re.S)
    return [" ".join(re.sub(r"<[^>]+>", " ", entry).split()) for entry in entries]


@pytest.mark.django_db
def test_application_page_shows_full_timeline_newest_first(
    staff_client, staff_user, django_user_model, make_job, make_candidate
):
    grace = django_user_model.objects.create_user(
        username="grace", first_name="Grace", last_name="Hopper"
    )
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)
    application.move_to(Stage.SCREENING, by=staff_user)
    application.move_to(Stage.INTERVIEW, by=grace)
    changes = list(application.stage_changes.all())

    html = staff_client.get(application.get_absolute_url()).content.decode()

    entries = timeline(html)
    assert len(entries) == 3
    assert "Screening → Interview" in entries[0]
    assert "Grace Hopper" in entries[0]
    assert "Applied → Screening" in entries[1]
    assert "staff" in entries[1]
    assert "Created at Applied" in entries[2]
    assert "staff" in entries[2]
    for entry, change in zip(entries, changes, strict=True):
        assert date_format(localtime(change.changed_at), "M j, Y, g:i a") in entry


@pytest.mark.django_db
def test_count_card_links_to_its_stage_filter(staff_client, make_job, make_application):
    job = make_job()
    screening = make_application(job, Stage.SCREENING)
    applied = make_application(job, Stage.APPLIED)

    page = staff_client.get(job.get_absolute_url()).content.decode()
    assert f'href="{job.get_absolute_url()}?stage=screening" data-card="screening"' in page

    html = staff_client.get(job.get_absolute_url(), {"stage": "screening"}).content.decode()

    assert selected_tabs(html) == ["screening"]
    assert screening.candidate.email in html
    assert applied.candidate.email not in html


@pytest.mark.django_db
def test_default_and_unknown_filters_show_active_applications(
    staff_client, make_job, make_application
):
    job = make_job()
    active = make_application(job, Stage.OFFER)
    hired = make_application(job, Stage.HIRED)

    for params in ({}, {"stage": "bogus"}):
        html = staff_client.get(job.get_absolute_url(), params).content.decode()

        assert selected_tabs(html) == ["active"]
        assert active.candidate.email in html
        assert hired.candidate.email not in html


@pytest.mark.django_db
def test_finished_tab_shows_final_rows_and_where_rejected_and_withdrawn_left_from(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    rejected = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    rejected.move_to(Stage.SCREENING, by=staff_user)
    rejected.move_to(Stage.INTERVIEW, by=staff_user)
    rejected.move_to(Stage.REJECTED, by=staff_user)
    withdrawn = Application.start(
        candidate=make_candidate(first_name="Grace", email="grace@example.com"),
        job=job,
        by=staff_user,
    )
    withdrawn.move_to(Stage.WITHDRAWN, by=staff_user)
    active = Application.start(
        candidate=make_candidate(first_name="Alan", email="alan@example.com"),
        job=job,
        by=staff_user,
    )

    html = staff_client.get(job.get_absolute_url(), {"stage": "finished"}).content.decode()

    assert selected_tabs(html) == ["finished"]
    assert "from Interview" in html
    assert "from Applied" in html
    assert active.candidate.email not in html
    assert 'name="to_stage"' not in html
    assert html.count(">Final</span>") == 2


@pytest.mark.django_db
def test_application_page_shows_candidate_job_stage_and_allowed_moves(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job(title="Data Analyst")
    application = Application.start(candidate=make_candidate(), job=job, by=staff_user)
    application.move_to(Stage.SCREENING, by=staff_user)

    html = staff_client.get(application.get_absolute_url()).content.decode()

    assert "ada@example.com" in html
    assert f'href="{application.candidate.get_absolute_url()}"' in html
    assert f'href="{job.get_absolute_url()}"' in html
    assert "Data Analyst" in html
    assert ">Screening</span>" in html
    assert ">Advance to Interview</button>" in html
    assert ">Back to Applied</button>" in html
    assert 'hx-target="#application-stage"' in html
    assert '<input type="hidden" name="return_to" value="application">' in html


@pytest.mark.django_db
def test_move_from_application_page_returns_stage_panel_and_timeline(
    staff_client, staff_user, make_job, make_candidate
):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)

    response = staff_client.post(
        reverse("hiring:application_move", args=[application.pk]),
        {"to_stage": Stage.REJECTED, "return_to": "application"},
        headers={"HX-Request": "true"},
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert response.templates[0].name == "hiring/_application_stage.html"
    assert "<html" not in html
    assert '<section id="application-stage"' in html
    assert ">Rejected</span>" in html
    assert "from Applied" in html
    assert 'name="to_stage"' not in html
    assert [entry.split(" staff")[0] for entry in timeline(html)] == [
        "Applied → Rejected",
        "Created at Applied",
    ]


@pytest.mark.django_db
def test_move_from_application_page_without_htmx_redirects_back(
    staff_client, staff_user, make_job, make_candidate
):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)

    response = staff_client.post(
        reverse("hiring:application_move", args=[application.pk]),
        {"to_stage": Stage.SCREENING, "return_to": "application"},
    )

    assert response.status_code == 302
    assert response["Location"] == application.get_absolute_url()


@pytest.mark.django_db
def test_application_page_requires_login(client, staff_user, make_job, make_candidate):
    application = Application.start(candidate=make_candidate(), job=make_job(), by=staff_user)

    response = client.get(application.get_absolute_url())

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


@pytest.mark.django_db
def test_job_and_candidate_pages_link_to_the_application(
    staff_client, staff_user, make_job, make_candidate
):
    job = make_job()
    candidate = make_candidate()
    application = Application.start(candidate=candidate, job=job, by=staff_user)

    for page in (job.get_absolute_url(), candidate.get_absolute_url()):
        html = staff_client.get(page).content.decode()
        assert f'href="{application.get_absolute_url()}"' in html
