from django.db import models
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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("hiring:job_detail", args=[self.pk])
