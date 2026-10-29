import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_anonymous_job_list_redirects_to_login(client):
    response = client.get("/jobs/")

    assert response.status_code == 302
    assert response["Location"] == f"{reverse('login')}?next=/jobs/"


def test_root_redirects_to_job_list(staff_client):
    response = staff_client.get("/")

    assert response.status_code == 302
    assert response["Location"] == reverse("hiring:job_list")


def test_login_page_is_public(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200


def test_staff_can_log_in_and_land_on_job_list(client, staff_user):
    response = client.post(
        reverse("login"), {"username": "staff", "password": "staff-pass-123"}, follow=True
    )

    assert response.redirect_chain[-1][0] == reverse("hiring:job_list")
    assert response.context["user"] == staff_user


def test_inactive_user_cannot_log_in(client, staff_user):
    staff_user.is_active = False
    staff_user.save()

    response = client.post(reverse("login"), {"username": "staff", "password": "staff-pass-123"})

    assert response.status_code == 200
    assert not response.context["user"].is_authenticated


def test_job_list_shows_sidebar_and_logout(staff_client):
    response = staff_client.get(reverse("hiring:job_list"))
    html = response.content.decode()

    assert response.status_code == 200
    for label in ("Pipeline", "Jobs", "Candidates", "Skills"):
        assert label in html
    assert f'action="{reverse("logout")}"' in html


def test_logout_requires_post(staff_client):
    response = staff_client.get(reverse("logout"))

    assert response.status_code == 405


def test_logout_ends_session(staff_client):
    response = staff_client.post(reverse("logout"))

    assert response["Location"] == reverse("login")
    assert staff_client.get(reverse("hiring:job_list")).status_code == 302


def test_admin_uses_its_own_login(client):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")
