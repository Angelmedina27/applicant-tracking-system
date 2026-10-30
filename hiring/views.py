from django.db import IntegrityError
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ApplicationForm, CandidateForm, JobOpeningForm, SkillForm
from .models import Application, Candidate, InvalidMove, JobOpening, Skill


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
    current = _pipeline_filter(request.GET.get("stage"))
    return render(request, "hiring/job_detail.html", _pipeline_context(job, current))


PIPELINE_FILTERS = {
    "active": Application.ACTIVE_STAGES,
    **{stage.value: [stage] for stage in Application.ACTIVE_STAGES},
    "finished": Application.FINISHED_STAGES,
}


def _pipeline_filter(value):
    """Return the requested pipeline filter, falling back to Active when unknown."""
    return value if value in PIPELINE_FILTERS else "active"


def _pipeline_context(job, current):
    applications = (
        job.applications.filter(stage__in=PIPELINE_FILTERS[current])
        .select_related("candidate")
        .with_stage_details()
    )
    stage_counts = dict(job.applications.order_by().values_list("stage").annotate(Count("pk")))
    cards = [
        {"value": stage.value, "label": stage.label, "count": stage_counts.get(stage, 0)}
        for stage in Application.ACTIVE_STAGES
    ]
    total = sum(stage_counts.values())
    active = sum(card["count"] for card in cards)
    finished = total - active
    tabs = [
        {"value": "active", "label": "Active", "count": active},
        *cards,
        {"value": "finished", "label": "Finished", "count": finished},
    ]
    for tab in tabs:
        tab["selected"] = tab["value"] == current
    return {
        "job": job,
        "applications": applications,
        "cards": cards,
        "tabs": tabs,
        "total": total,
        "current": current,
    }


def job_edit(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    form = JobOpeningForm(request.POST or None, instance=job)
    if form.is_valid():
        form.save()
        return redirect(job)
    return render(request, "hiring/job_form.html", {"form": form, "job": job})


def job_status(request, pk):
    """Confirm and save a job's new status. Applications are never touched."""
    job = get_object_or_404(JobOpening.objects.with_active_count(), pk=pk)
    if request.method == "POST":
        status = request.POST.get("status", "")
        if status not in JobOpening.Status.values:
            return HttpResponseBadRequest("Unknown status.")
        job.status = status
        job.save(update_fields=["status", "updated_at"])
        return redirect(job)
    return render(request, "hiring/job_status.html", {"job": job})


def application_create_for_job(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    form = ApplicationForm(request.POST or None, job=job)
    return _create_application(request, form, job, {"job": job})


def application_create_for_candidate(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = ApplicationForm(request.POST or None, candidate=candidate)
    return _create_application(request, form, candidate, {"candidate": candidate})


def _create_application(request, form, fixed, context):
    """Shared by both entry points; `fixed` is the job or candidate to return to."""
    if form.is_valid():
        try:
            Application.start(
                candidate=form.instance.candidate, job=form.instance.job, by=request.user
            )
        except IntegrityError:
            form.add_error(form.choice_name, "This candidate has already applied to this job.")
        else:
            return redirect(fixed)
    context |= {
        "form": form,
        "choice": form[form.choice_name],
        "has_choices": form.fields[form.choice_name].queryset.exists(),
    }
    return render(request, "hiring/application_form.html", context)


def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    return render(request, "hiring/application_detail.html", _application_context(application))


def _application_context(application):
    """Re-read the application with its stage details for the stage panel and timeline."""
    application = (
        Application.objects.select_related("candidate", "job")
        .with_stage_details()
        .get(pk=application.pk)
    )
    stage_changes = application.stage_changes.select_related("changed_by")
    return {"application": application, "stage_changes": stage_changes}


@require_POST
def application_move(request, pk):
    application = get_object_or_404(Application.objects.select_related("job"), pk=pk)
    to_stage = request.POST.get("to_stage", "")
    if to_stage not in Application.Stage.values:
        return HttpResponseBadRequest("Unknown stage.")
    try:
        application.move_to(to_stage, by=request.user)
    except InvalidMove as error:
        return HttpResponse(str(error), status=409)
    if request.POST.get("return_to") == "application":
        if not request.headers.get("HX-Request"):
            return redirect(application)
        return render(request, "hiring/_application_stage.html", _application_context(application))
    current = _pipeline_filter(request.POST.get("stage"))
    if not request.headers.get("HX-Request"):
        url = application.job.get_absolute_url()
        return redirect(url if current == "active" else f"{url}?stage={current}")
    return render(request, "hiring/_pipeline.html", _pipeline_context(application.job, current))


def candidate_list(request):
    query = request.GET.get("q", "").strip()
    show_archived = request.GET.get("archived") == "1"
    candidates = Candidate.objects.all()
    if not show_archived:
        candidates = candidates.filter(archived=False)
    if query:
        candidates = candidates.annotate(
            search_name=Concat("first_name", Value(" "), "last_name")
        ).filter(Q(search_name__icontains=query) | Q(email__icontains=query))
    return render(
        request,
        "hiring/candidate_list.html",
        {"candidates": candidates, "query": query, "show_archived": show_archived},
    )


def candidate_create(request):
    form = CandidateForm(request.POST or None)
    if form.is_valid():
        candidate = form.save()
        return redirect(candidate)
    return render(request, "hiring/candidate_form.html", {"form": form})


def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    applications = candidate.applications.select_related("job").with_stage_details()
    return render(
        request,
        "hiring/candidate_detail.html",
        {"candidate": candidate, "applications": applications},
    )


def candidate_edit(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = CandidateForm(request.POST or None, instance=candidate)
    if form.is_valid():
        form.save()
        return redirect(candidate)
    return render(request, "hiring/candidate_form.html", {"form": form, "candidate": candidate})


def candidate_archive(request, pk):
    """Confirm and archive a candidate, refused while any application is active."""
    candidate = get_object_or_404(Candidate, pk=pk)
    if candidate.archived:
        return redirect(candidate)
    context = {"candidate": candidate, "active_count": candidate.active_application_count()}
    if context["active_count"]:
        return render(request, "hiring/candidate_archive.html", context, status=409)
    if request.method == "POST":
        candidate.archived = True
        candidate.save(update_fields=["archived", "updated_at"])
        return redirect(candidate)
    return render(request, "hiring/candidate_archive.html", context)


@require_POST
def candidate_unarchive(request, pk):
    """Unarchiving is always allowed."""
    candidate = get_object_or_404(Candidate, pk=pk)
    candidate.archived = False
    candidate.save(update_fields=["archived", "updated_at"])
    return redirect(candidate)


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
