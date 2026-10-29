import pytest
from django.db import IntegrityError
from django.urls import reverse

from hiring.models import Candidate

pytestmark = pytest.mark.django_db


def candidate_data(**overrides):
    return {
        "first_name": "Grace",
        "last_name": "Hopper",
        "email": "grace@example.com",
        "source": Candidate.Source.JOB_BOARD,
    } | overrides


def test_create_refuses_email_matching_existing_candidate_in_any_case(staff_client, make_candidate):
    existing = make_candidate(email="ada@example.com")

    response = staff_client.post(
        reverse("hiring:candidate_create"), candidate_data(email="ADA@Example.com")
    )

    assert response.status_code == 200
    assert Candidate.objects.count() == 1
    assert "already exists" in response.content.decode()
    assert f'href="{existing.get_absolute_url()}"' in response.content.decode()


def test_edit_keeps_own_email_but_refuses_another_candidates_email(staff_client, make_candidate):
    ada = make_candidate(email="ada@example.com")
    grace = make_candidate(first_name="Grace", last_name="Hopper", email="grace@example.com")
    url = reverse("hiring:candidate_edit", args=[ada.pk])

    kept = staff_client.post(url, candidate_data(first_name="Augusta", email="ADA@example.com"))

    assert kept.status_code == 302
    ada.refresh_from_db()
    assert ada.first_name == "Augusta"

    taken = staff_client.post(url, candidate_data(email="Grace@Example.com"))

    assert taken.status_code == 200
    assert f'href="{grace.get_absolute_url()}"' in taken.content.decode()
    ada.refresh_from_db()
    assert ada.email == "ADA@example.com"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", ["Grace Hopper", "Ada Lovelace", "Alan Turing"]),
        ("GRA", ["Grace Hopper"]),
        ("love", ["Ada Lovelace"]),
        ("bletchley", ["Alan Turing"]),
        ("ada love", ["Ada Lovelace"]),
        ("a", ["Grace Hopper", "Ada Lovelace", "Alan Turing"]),
        ("nobody", []),
    ],
)
def test_candidate_list_search_matches_partial_name_or_email(
    staff_client, make_candidate, query, expected
):
    make_candidate(first_name="Ada", last_name="Lovelace", email="ada@example.com")
    make_candidate(first_name="Grace", last_name="Hopper", email="grace@navy.mil")
    make_candidate(first_name="Alan", last_name="Turing", email="alan@bletchley.org")

    response = staff_client.get(reverse("hiring:candidate_list"), {"q": query})

    assert [c.full_name for c in response.context["candidates"]] == expected


def test_create_saves_candidate_and_shows_detail(staff_client):
    data = candidate_data(
        phone="555-0100",
        url="https://linkedin.com/in/grace",
        source=Candidate.Source.REFERRAL,
        source_details="Referred by Alan",
        notes="Strong compiler background.",
    )

    response = staff_client.post(reverse("hiring:candidate_create"), data, follow=True)

    candidate = Candidate.objects.get()
    assert response.redirect_chain[-1][0] == candidate.get_absolute_url()
    assert not candidate.archived
    html = response.content.decode()
    for text in ("Grace Hopper", "grace@example.com", "555-0100", "Referral", "Referred by Alan"):
        assert text in html


def test_source_is_limited_to_the_six_choices(staff_client):
    form = staff_client.get(reverse("hiring:candidate_create")).context["form"]
    labels = [label for value, label in form.fields["source"].choices if value]

    assert labels == [
        "Job Board",
        "Referral",
        "Company Website",
        "Recruiter Outreach",
        "Career Fair",
        "Other",
    ]

    response = staff_client.post(reverse("hiring:candidate_create"), candidate_data(source="tv"))

    assert response.status_code == 200
    assert not Candidate.objects.exists()


def test_database_refuses_case_insensitive_duplicate_email(make_candidate):
    make_candidate(email="ada@example.com")

    with pytest.raises(IntegrityError):
        make_candidate(email="Ada@Example.COM")


def test_edit_form_is_prefilled(staff_client, make_candidate):
    ada = make_candidate()

    response = staff_client.get(reverse("hiring:candidate_edit", args=[ada.pk]))

    assert response.status_code == 200
    assert 'value="ada@example.com"' in response.content.decode()


def test_unknown_candidate_returns_404(staff_client):
    assert staff_client.get(reverse("hiring:candidate_detail", args=[999])).status_code == 404


@pytest.mark.parametrize(
    "name", ["candidate_list", "candidate_create", "candidate_detail", "candidate_edit"]
)
def test_candidate_pages_require_login(client, make_candidate, name):
    args = [make_candidate().pk] if name in ("candidate_detail", "candidate_edit") else []

    response = client.get(reverse(f"hiring:{name}", args=args))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


def test_sidebar_links_to_candidates(staff_client):
    response = staff_client.get(reverse("hiring:candidate_list"))

    assert f'href="{reverse("hiring:candidate_list")}" class="menu-active"' in (
        response.content.decode()
    )
