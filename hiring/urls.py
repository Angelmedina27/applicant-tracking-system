from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "hiring"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="hiring:job_list"), name="home"),
    path("jobs/", views.job_list, name="job_list"),
]
