from django.conf import settings
from django.db import models, transaction
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone


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


class ApplicationQuerySet(models.QuerySet):
    def with_stage_details(self):
        """Annotate `stage_since`, when the current stage began, and `left_from`,
        the stage before the latest move (where a Rejected or Withdrawn one left off)."""
        latest = StageChange.objects.filter(application=models.OuterRef("pk")).order_by(
            "-changed_at", "-pk"
        )
        return self.annotate(
            stage_since=models.Subquery(latest.values("changed_at")[:1]),
            left_from=models.Subquery(latest.values("from_stage")[:1]),
        )


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
    FINISHED_STAGES = [Stage.HIRED, Stage.REJECTED, Stage.WITHDRAWN]

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey(JobOpening, on_delete=models.PROTECT, related_name="applications")
    stage = models.CharField(max_length=20, choices=Stage, default=Stage.APPLIED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ApplicationQuerySet.as_manager()

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

    def get_absolute_url(self):
        return reverse("hiring:application_detail", args=[self.pk])

    @classmethod
    def start(cls, *, candidate, job, by):
        """Create an application at Applied together with its initial history entry."""
        with transaction.atomic():
            application = cls.objects.create(candidate=candidate, job=job)
            application.stage_changes.create(to_stage=cls.Stage.APPLIED, changed_by=by)
        return application

    @property
    def left_from_display(self):
        """For Rejected or Withdrawn, the stage it left from; needs `with_stage_details()`."""
        if self.stage in (self.Stage.REJECTED, self.Stage.WITHDRAWN) and self.left_from:
            return self.Stage(self.left_from).label
        return ""

    @property
    def available_moves(self):
        return allowed_moves(self.stage)

    def move_to(self, to_stage, *, by):
        """Move to `to_stage` and record the history entry, or raise InvalidMove.

        The update only matches while the stored stage is still the one we checked,
        so a concurrent move from the same stage can't also succeed.
        """
        if to_stage not in self.available_moves:
            raise InvalidMove(f"Can't move from {self.get_stage_display()} to {to_stage!r}.")
        with transaction.atomic():
            moved = Application.objects.filter(pk=self.pk, stage=self.stage).update(
                stage=to_stage, updated_at=timezone.now()
            )
            if not moved:
                raise InvalidMove("This application was moved by someone else.")
            self.stage_changes.create(from_stage=self.stage, to_stage=to_stage, changed_by=by)
        self.refresh_from_db()


class InvalidMove(Exception):
    pass


PIPELINE = [*Application.ACTIVE_STAGES, Application.Stage.HIRED]


def allowed_moves(stage):
    """Return the stages an application at `stage` may move to.

    From an active stage: one step forward, one step back (if any), Rejected and
    Withdrawn. Hired, Rejected and Withdrawn are final and allow no moves.
    """
    if stage not in PIPELINE[:-1]:
        return []
    index = PIPELINE.index(stage)
    moves = [PIPELINE[index + 1]]
    if index > 0:
        moves.append(PIPELINE[index - 1])
    return moves + [Application.Stage.REJECTED, Application.Stage.WITHDRAWN]


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
