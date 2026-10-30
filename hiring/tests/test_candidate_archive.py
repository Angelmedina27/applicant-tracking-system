import pytest
from django.urls import reverse

from hiring.models import Application, Candidate, StageChange

Stage = Application.Stage

pytestmark = pytest.mark.django_db


def test_archiving_is_blocked_while_candidate_has_active_applications(
    staff_client, staff_user, make_job, make_candidate
):
    candidate = make_candidate()
    for title, path in [
        ("Backend Engineer", []),
        ("Data Analyst", [Stage.SCREENING, Stage.INTERVIEW]),
        ("Designer", [Stage.REJECTED]),
    ]:
        application = Application.start(
            candidate=candidate, job=make_job(title=title), by=staff_user
        )
        for stage in path:
            application.move_to(stage, by=staff_user)
    url = reverse("hiring:candidate_archive", args=[candidate.pk])

    blocked = staff_client.post(url)

    candidate.refresh_from_db()
    assert blocked.status_code == 409
    assert "2 applications are still active" in blocked.content.decode()
    assert not candidate.archived

    for application in candidate.applications.filter(stage__in=Application.ACTIVE_STAGES):
        application.move_to(Stage.WITHDRAWN, by=staff_user)

    allowed = staff_client.post(url)

    candidate.refresh_from_db()
    assert allowed.status_code == 302
    assert allowed["Location"] == candidate.get_absolute_url()
    assert candidate.archived


def test_candidate_list_hides_archived_unless_show_archived_is_chosen(staff_client, make_candidate):
    make_candidate(first_name="Ada", last_name="Lovelace", email="ada@example.com")
    make_candidate(first_name="Grace", last_name="Hopper", email="grace@example.com", archived=True)
    url = reverse("hiring:candidate_list")

    default = staff_client.get(url)
    with_archived = staff_client.get(url, {"archived": "1"})

    assert [c.full_name for c in default.context["candidates"]] == ["Ada Lovelace"]
    assert [c.full_name for c in with_archived.context["candidates"]] == [
        "Grace Hopper",
        "Ada Lovelace",
    ]


def test_archived_candidate_is_not_offered_and_a_stale_submit_is_refused(
    staff_client, make_job, make_candidate
):
    job = make_job()
    active = make_candidate()
    archived = make_candidate(
        first_name="Grace", last_name="Hopper", email="grace@example.com", archived=True
    )
    url = reverse("hiring:application_create_for_job", args=[job.pk])

    choices = list(staff_client.get(url).context["form"].fields["candidate"].queryset)
    stale = staff_client.post(url, {"candidate": archived.pk})

    assert choices == [active]
    assert stale.status_code == 200
    assert stale.context["form"].errors["candidate"]
    assert not Application.objects.exists()
    assert not StageChange.objects.exists()


def test_candidate_without_applications_gets_confirm_page_and_can_be_archived(
    staff_client, make_candidate
):
    candidate = make_candidate()
    url = reverse("hiring:candidate_archive", args=[candidate.pk])

    html = staff_client.get(url).content.decode()

    assert "Archive candidate" in html
    assert f'href="{candidate.get_absolute_url()}" class="btn btn-ghost">Cancel' in html
    assert not Candidate.objects.get().archived

    staff_client.post(url)

    assert Candidate.objects.get().archived


def test_archive_page_refuses_with_singular_count_on_get(
    staff_client, staff_user, make_job, make_candidate
):
    candidate = make_candidate()
    Application.start(candidate=candidate, job=make_job(), by=staff_user)

    response = staff_client.get(reverse("hiring:candidate_archive", args=[candidate.pk]))

    html = response.content.decode()
    assert response.status_code == 409
    assert "1 application is still active" in html
    assert "Archive candidate" not in html


def test_archiving_an_archived_candidate_just_returns_to_them(staff_client, make_candidate):
    candidate = make_candidate(archived=True)

    response = staff_client.post(reverse("hiring:candidate_archive", args=[candidate.pk]))

    assert response.status_code == 302
    assert response["Location"] == candidate.get_absolute_url()


def test_unarchiving_restores_candidate_to_default_list(staff_client, make_candidate):
    candidate = make_candidate(archived=True)

    response = staff_client.post(reverse("hiring:candidate_unarchive", args=[candidate.pk]))

    assert response.status_code == 302
    assert response["Location"] == candidate.get_absolute_url()
    listed = staff_client.get(reverse("hiring:candidate_list")).context["candidates"]
    assert list(listed) == [candidate]


def test_unarchive_is_allowed_even_with_active_applications(
    staff_client, staff_user, make_job, make_candidate
):
    candidate = make_candidate()
    Application.start(candidate=candidate, job=make_job(), by=staff_user)
    Candidate.objects.filter(pk=candidate.pk).update(archived=True)

    staff_client.post(reverse("hiring:candidate_unarchive", args=[candidate.pk]))

    assert not Candidate.objects.get().archived


def test_unarchive_rejects_get(staff_client, make_candidate):
    candidate = make_candidate(archived=True)

    response = staff_client.get(reverse("hiring:candidate_unarchive", args=[candidate.pk]))

    assert response.status_code == 405
    assert Candidate.objects.get().archived


def test_archived_candidate_cannot_be_applied_from_candidate_page(
    staff_client, make_job, make_candidate
):
    job = make_job()
    candidate = make_candidate(archived=True)
    url = reverse("hiring:application_create_for_candidate", args=[candidate.pk])

    page = staff_client.get(url).content.decode()
    stale = staff_client.post(url, {"job": job.pk})

    assert "This candidate is archived" in page
    assert ">Apply to job</button>" not in page
    assert stale.status_code == 200
    assert "This candidate is archived" in " ".join(stale.context["form"].non_field_errors())
    assert not Application.objects.exists()
    assert not StageChange.objects.exists()


def test_candidate_page_offers_archive_when_not_archived(staff_client, make_candidate):
    candidate = make_candidate()

    html = staff_client.get(candidate.get_absolute_url()).content.decode()

    assert f'href="{reverse("hiring:candidate_archive", args=[candidate.pk])}"' in html
    assert reverse("hiring:application_create_for_candidate", args=[candidate.pk]) in html
    assert reverse("hiring:candidate_unarchive", args=[candidate.pk]) not in html
    assert ">Archived</span>" not in html


def test_archived_candidate_page_shows_badge_and_unarchive_but_no_apply(
    staff_client, make_candidate
):
    candidate = make_candidate(archived=True)

    html = staff_client.get(candidate.get_absolute_url()).content.decode()

    assert ">Archived</span>" in html
    assert f'action="{reverse("hiring:candidate_unarchive", args=[candidate.pk])}"' in html
    assert reverse("hiring:candidate_archive", args=[candidate.pk]) not in html
    assert reverse("hiring:application_create_for_candidate", args=[candidate.pk]) not in html


def test_show_archived_checkbox_reflects_filter_and_combines_with_search(
    staff_client, make_candidate
):
    make_candidate(first_name="Ada", last_name="Lovelace", email="ada@example.com", archived=True)
    make_candidate(first_name="Alan", last_name="Turing", email="alan@example.com")
    url = reverse("hiring:candidate_list")

    default = staff_client.get(url, {"q": "ada"})
    with_archived = staff_client.get(url, {"q": "ada", "archived": "1"})

    assert list(default.context["candidates"]) == []
    assert 'value="1" class="checkbox checkbox-sm" onchange="this.form.submit()" >' in (
        default.content.decode()
    )
    assert [c.full_name for c in with_archived.context["candidates"]] == ["Ada Lovelace"]
    assert "checked" in with_archived.content.decode()
    assert ">Archived</span>" in with_archived.content.decode()


@pytest.mark.parametrize("name", ["candidate_archive", "candidate_unarchive"])
def test_unknown_candidate_returns_404(staff_client, name):
    assert staff_client.post(reverse(f"hiring:{name}", args=[999])).status_code == 404


@pytest.mark.parametrize(
    ("name", "archived"), [("candidate_archive", False), ("candidate_unarchive", True)]
)
def test_archive_actions_require_login(client, make_candidate, name, archived):
    candidate = make_candidate(archived=archived)

    response = client.post(reverse(f"hiring:{name}", args=[candidate.pk]))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))
    assert Candidate.objects.get().archived == archived
