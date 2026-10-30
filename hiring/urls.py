from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "hiring"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="hiring:job_list"), name="home"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/new/", views.job_create, name="job_create"),
    path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
    path("jobs/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path(
        "jobs/<int:pk>/applications/new/",
        views.application_create_for_job,
        name="application_create_for_job",
    ),
    path("candidates/", views.candidate_list, name="candidate_list"),
    path("candidates/new/", views.candidate_create, name="candidate_create"),
    path("candidates/<int:pk>/", views.candidate_detail, name="candidate_detail"),
    path("candidates/<int:pk>/edit/", views.candidate_edit, name="candidate_edit"),
    path(
        "candidates/<int:pk>/apply/",
        views.application_create_for_candidate,
        name="application_create_for_candidate",
    ),
    path("applications/<int:pk>/", views.application_detail, name="application_detail"),
    path("applications/<int:pk>/move/", views.application_move, name="application_move"),
    path("skills/", views.skill_list, name="skill_list"),
    path("skills/<int:pk>/delete/", views.skill_delete, name="skill_delete"),
]
