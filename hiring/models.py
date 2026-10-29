from django.conf import settings
from django.db import models, transaction
from django.db.models.functions import Lower
from django.urls import reverse


class Candidate(models.Model):
    class Source(models.TextChoices):
        JOB_BOARD = "job_board", "Job Board"
        REFERRAL = "referral", "Referral"
        COMPANY_WEBSITE = "company_website", "Company Website"
        RECRUITER_OUTREACH = "recruiter_outreach", "Recruiter Outreach"
        CAREER_FAIR = "career_fair", "Career Fair"
        OTHER = "other", "Other"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    url = models.URLField("LinkedIn or portfolio URL", blank=True)
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=Source)
    source_details = models.CharField(max_length=200, blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_candidate_email_ci",
                violation_error_message="A candidate with this email already exists.",
            ),
        ]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("hiring:candidate_detail", args=[self.pk])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Skill(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = [Lower("name")]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_skill_name_ci",
                violation_error_message="A skill with this name already exists.",
            ),
        ]

    def __str__(self):
        return self.name

    def can_delete(self):
        return not self.jobs.exists()


class JobOpeningQuerySet(models.QuerySet):
    def with_active_count(self):
        """Annotate each job with `active_count`, its number of active applications."""
        return self.annotate(
            active_count=models.Count(
                "applications",
                filter=models.Q(applications__stage__in=Application.ACTIVE_STAGES),
            )
        )


class JobOpening(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=Status, default=Status.OPEN)
    skills = models.ManyToManyField(Skill, blank=True, related_name="jobs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = JobOpeningQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("hiring:job_detail", args=[self.pk])


class Application(models.Model):
    class Stage(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        INTERVIEW = "interview", "Interview"
        FINAL_REVIEW = "final_review", "Final Review"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    ACTIVE_STAGES = [
        Stage.APPLIED,
        Stage.SCREENING,
        Stage.INTERVIEW,
        Stage.FINAL_REVIEW,
        Stage.OFFER,
    ]

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey(JobOpening, on_delete=models.PROTECT, related_name="applications")
    stage = models.CharField(max_length=20, choices=Stage, default=Stage.APPLIED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job"],
                name="unique_application_per_job",
                violation_error_message="This candidate has already applied to this job.",
            ),
        ]

    def __str__(self):
        return f"{self.candidate} → {self.job}"

    @classmethod
    def start(cls, *, candidate, job, by):
        """Create an application at Applied together with its initial history entry."""
        with transaction.atomic():
            application = cls.objects.create(candidate=candidate, job=job)
            application.stage_changes.create(to_stage=cls.Stage.APPLIED, changed_by=by)
        return application


class StageChange(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="stage_changes"
    )
    from_stage = models.CharField(max_length=20, choices=Application.Stage, blank=True)
    to_stage = models.CharField(max_length=20, choices=Application.Stage)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stage_changes"
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at", "-pk"]

    def __str__(self):
        return f"{self.application}: {self.from_stage or '—'} → {self.to_stage}"
