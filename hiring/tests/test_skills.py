import pytest
from django.db import IntegrityError
from django.urls import reverse

from hiring.models import Skill

pytestmark = pytest.mark.django_db


def test_adding_skill_matching_existing_name_in_any_case_is_refused(staff_client):
    Skill.objects.create(name="Python")

    response = staff_client.post(reverse("hiring:skill_list"), {"name": "python"})

    assert response.status_code == 200
    assert "already exists" in response.content.decode()
    assert list(Skill.objects.values_list("name", flat=True)) == ["Python"]


def test_deleting_skill_asks_for_confirmation_then_removes_it(staff_client):
    skill = Skill.objects.create(name="Python")
    url = reverse("hiring:skill_delete", args=[skill.pk])

    confirm = staff_client.get(url)

    assert confirm.status_code == 200
    assert "Python" in confirm.content.decode()
    assert Skill.objects.filter(pk=skill.pk).exists()

    response = staff_client.post(url)

    assert response.status_code == 302
    assert response["Location"] == reverse("hiring:skill_list")
    assert not Skill.objects.filter(pk=skill.pk).exists()


def test_adding_skill_lists_it_in_name_order(staff_client):
    Skill.objects.create(name="SQL")

    response = staff_client.post(reverse("hiring:skill_list"), {"name": "django"}, follow=True)

    assert response.redirect_chain[-1][0] == reverse("hiring:skill_list")
    assert [s.name for s in response.context["skills"]] == ["django", "SQL"]


def test_blank_skill_name_is_refused(staff_client):
    response = staff_client.post(reverse("hiring:skill_list"), {"name": "  "})

    assert response.status_code == 200
    assert not Skill.objects.exists()


def test_database_refuses_case_insensitive_duplicate_name():
    Skill.objects.create(name="Python")

    with pytest.raises(IntegrityError):
        Skill.objects.create(name="PYTHON")


def test_skill_list_offers_delete_for_deletable_skills(staff_client):
    skill = Skill.objects.create(name="Python")

    response = staff_client.get(reverse("hiring:skill_list"))

    assert skill.can_delete()
    assert f'href="{reverse("hiring:skill_delete", args=[skill.pk])}"' in response.content.decode()


def test_delete_view_refuses_skill_that_cannot_be_deleted(staff_client, monkeypatch):
    skill = Skill.objects.create(name="Python")
    monkeypatch.setattr(Skill, "can_delete", lambda self: False)
    url = reverse("hiring:skill_delete", args=[skill.pk])

    page = staff_client.get(url)
    response = staff_client.post(url)

    assert page.status_code == 409
    assert "Delete skill" not in page.content.decode()
    assert response.status_code == 409
    assert Skill.objects.filter(pk=skill.pk).exists()


def test_deleting_unknown_skill_returns_404(staff_client):
    assert staff_client.post(reverse("hiring:skill_delete", args=[999])).status_code == 404


@pytest.mark.parametrize("name", ["skill_list", "skill_delete"])
def test_skill_pages_require_login(client, name):
    args = [Skill.objects.create(name="Python").pk] if name == "skill_delete" else []

    response = client.get(reverse(f"hiring:{name}", args=args))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


def test_sidebar_links_to_skills(staff_client):
    response = staff_client.get(reverse("hiring:skill_list"))

    assert f'href="{reverse("hiring:skill_list")}" class="menu-active"' in (
        response.content.decode()
    )
