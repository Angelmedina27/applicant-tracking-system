from django.db import IntegrityError
from django.db.models import Max, Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ApplicationForm, CandidateForm, JobOpeningForm, SkillForm
from .models import Application, Candidate, JobOpening, Skill


def job_list(request):
    jobs = JobOpening.objects.with_active_count()
    return render(request, "hiring/job_list.html", {"jobs": jobs})


def job_create(request):
    form = JobOpeningForm(request.POST or None)
    if form.is_valid():
        job = form.save()
        return redirect(job)
    return render(request, "hiring/job_form.html", {"form": form})


def job_detail(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    applications = job.applications.select_related("candidate").annotate(
        stage_since=Max("stage_changes__changed_at")
    )
    return render(request, "hiring/job_detail.html", {"job": job, "applications": applications})


def job_edit(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    form = JobOpeningForm(request.POST or None, instance=job)
    if form.is_valid():
        form.save()
        return redirect(job)
    return render(request, "hiring/job_form.html", {"form": form, "job": job})


def application_create_for_job(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    form = ApplicationForm(request.POST or None, job=job)
    if form.is_valid():
        try:
            Application.start(candidate=form.cleaned_data["candidate"], job=job, by=request.user)
        except IntegrityError:
            form.add_error("candidate", "This candidate has already applied to this job.")
        else:
            return redirect(job)
    has_choices = form.fields["candidate"].queryset.exists()
    return render(
        request,
        "hiring/application_form.html",
        {"form": form, "job": job, "has_choices": has_choices},
    )


def candidate_list(request):
    query = request.GET.get("q", "").strip()
    candidates = Candidate.objects.all()
    if query:
        candidates = candidates.annotate(
            search_name=Concat("first_name", Value(" "), "last_name")
        ).filter(Q(search_name__icontains=query) | Q(email__icontains=query))
    return render(request, "hiring/candidate_list.html", {"candidates": candidates, "query": query})


def candidate_create(request):
    form = CandidateForm(request.POST or None)
    if form.is_valid():
        candidate = form.save()
        return redirect(candidate)
    return render(request, "hiring/candidate_form.html", {"form": form})


def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    return render(request, "hiring/candidate_detail.html", {"candidate": candidate})


def candidate_edit(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = CandidateForm(request.POST or None, instance=candidate)
    if form.is_valid():
        form.save()
        return redirect(candidate)
    return render(request, "hiring/candidate_form.html", {"form": form, "candidate": candidate})


def skill_list(request):
    form = SkillForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("hiring:skill_list")
    return render(request, "hiring/skill_list.html", {"skills": Skill.objects.all(), "form": form})


def skill_delete(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    if not skill.can_delete():
        return render(request, "hiring/skill_confirm_delete.html", {"skill": skill}, status=409)
    if request.method == "POST":
        skill.delete()
        return redirect("hiring:skill_list")
    return render(request, "hiring/skill_confirm_delete.html", {"skill": skill})
