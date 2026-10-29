from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "hiring"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="hiring:job_list"), name="home"),
    path("jobs/", views.job_list, name="job_list"),
    path("candidates/", views.candidate_list, name="candidate_list"),
    path("candidates/new/", views.candidate_create, name="candidate_create"),
    path("candidates/<int:pk>/", views.candidate_detail, name="candidate_detail"),
    path("candidates/<int:pk>/edit/", views.candidate_edit, name="candidate_edit"),
    path("skills/", views.skill_list, name="skill_list"),
    path("skills/<int:pk>/delete/", views.skill_delete, name="skill_delete"),
]
