import pytest
from django.urls import reverse

from hiring.models import JobOpening, Skill

pytestmark = pytest.mark.django_db


def test_creating_job_with_checked_skills_saves_it_open_and_goes_to_job_page(staff_client):
    python = Skill.objects.create(name="Python")
    sql = Skill.objects.create(name="SQL")
    Skill.objects.create(name="Figma")

    response = staff_client.post(
        reverse("hiring:job_create"),
        {
            "title": "Backend Engineer",
            "department": "Engineering",
            "location": "Remote",
            "description": "Build APIs.",
            "skills": [python.pk, sql.pk],
        },
    )

    job = JobOpening.objects.get()
    assert response.status_code == 302
    assert response["Location"] == reverse("hiring:job_detail", args=[job.pk])
    assert job.status == JobOpening.Status.OPEN
    assert set(job.skills.values_list("name", flat=True)) == {"Python", "SQL"}


def test_editing_job_replaces_its_skills_with_the_checked_ones(staff_client):
    python = Skill.objects.create(name="Python")
    sql = Skill.objects.create(name="SQL")
    django = Skill.objects.create(name="Django")
    job = JobOpening.objects.create(
        title="Backend Engineer", department="Engineering", location="Remote", description="APIs"
    )
    job.skills.add(python, sql)

    response = staff_client.post(
        reverse("hiring:job_edit", args=[job.pk]),
        {
            "title": "Senior Backend Engineer",
            "department": "Engineering",
            "location": "Remote",
            "description": "APIs",
            "skills": [python.pk, django.pk],
        },
    )

    job.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == reverse("hiring:job_detail", args=[job.pk])
    assert job.title == "Senior Backend Engineer"
    assert set(job.skills.values_list("name", flat=True)) == {"Python", "Django"}


def test_new_job_ignores_a_submitted_status(staff_client):
    staff_client.post(
        reverse("hiring:job_create"),
        {
            "title": "Designer",
            "department": "Design",
            "location": "Berlin",
            "description": "Design things.",
            "status": JobOpening.Status.CLOSED,
        },
    )

    assert JobOpening.objects.get().status == JobOpening.Status.OPEN


@pytest.mark.parametrize("missing", ["title", "department", "location", "description"])
def test_job_form_requires_core_fields(staff_client, missing):
    data = {
        "title": "Designer",
        "department": "Design",
        "location": "Berlin",
        "description": "Design things.",
    }
    data[missing] = ""

    response = staff_client.post(reverse("hiring:job_create"), data)

    assert response.status_code == 200
    assert response.context["form"].errors[missing]
    assert not JobOpening.objects.exists()


def test_job_form_offers_every_skill_as_a_checkbox(staff_client):
    python = Skill.objects.create(name="Python")
    sql = Skill.objects.create(name="SQL")

    html = staff_client.get(reverse("hiring:job_create")).content.decode()

    for skill in (python, sql):
        assert f'type="checkbox" name="skills" value="{skill.pk}"' in html
        assert skill.name in html


def test_job_form_without_skills_points_to_skills_page(staff_client):
    html = staff_client.get(reverse("hiring:job_create")).content.decode()

    assert "No skills yet" in html
    assert f'href="{reverse("hiring:skill_list")}"' in html


def test_edit_form_is_prefilled_with_current_skills_checked(staff_client, make_job):
    python = Skill.objects.create(name="Python")
    Skill.objects.create(name="SQL")
    job = make_job(skills=[python])

    response = staff_client.get(reverse("hiring:job_edit", args=[job.pk]))

    form = response.context["form"]
    assert form["title"].value() == "Backend Engineer"
    assert form["skills"].value() == [python.pk]


def test_unchecking_every_skill_clears_them(staff_client, make_job):
    job = make_job(skills=[Skill.objects.create(name="Python")])

    staff_client.post(
        reverse("hiring:job_edit", args=[job.pk]),
        {
            "title": job.title,
            "department": job.department,
            "location": job.location,
            "description": job.description,
        },
    )

    assert not job.skills.exists()


def test_job_list_shows_title_department_and_status_with_links(staff_client, make_job):
    backend = make_job()
    designer = make_job(title="Designer", department="Design", status=JobOpening.Status.CLOSED)

    html = staff_client.get(reverse("hiring:job_list")).content.decode()

    for job in (backend, designer):
        assert f'href="{job.get_absolute_url()}"' in html
        assert job.title in html
        assert job.department in html
    assert ">Open</span>" in html
    assert ">Closed</span>" in html
    assert "No job openings yet" not in html


def test_job_list_links_to_new_job(staff_client):
    html = staff_client.get(reverse("hiring:job_list")).content.decode()

    assert f'href="{reverse("hiring:job_create")}"' in html
    assert "No job openings yet" in html


def test_job_page_shows_details_skills_and_edit_action(staff_client, make_job):
    job = make_job(skills=[Skill.objects.create(name="Python")])
    Skill.objects.create(name="Figma")

    response = staff_client.get(job.get_absolute_url())
    html = response.content.decode()

    assert response.status_code == 200
    for text in ("Backend Engineer", "Engineering", "Remote", "Build and run our APIs."):
        assert text in html
    assert ">Open</span>" in html
    assert "Python" in html
    assert "Figma" not in html
    assert f'href="{reverse("hiring:job_edit", args=[job.pk])}"' in html


@pytest.mark.parametrize("name", ["job_detail", "job_edit"])
def test_unknown_job_returns_404(staff_client, name):
    assert staff_client.get(reverse(f"hiring:{name}", args=[999])).status_code == 404


@pytest.mark.parametrize("name", ["job_create", "job_detail", "job_edit"])
def test_job_pages_require_login(client, make_job, name):
    args = [] if name == "job_create" else [make_job().pk]

    response = client.get(reverse(f"hiring:{name}", args=args))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


def test_sidebar_marks_jobs_active_on_job_list(staff_client):
    html = staff_client.get(reverse("hiring:job_list")).content.decode()

    assert f'href="{reverse("hiring:job_list")}" class="menu-active">Jobs' in html
