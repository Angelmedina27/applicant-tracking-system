from django import forms

from .models import Application, Candidate, JobOpening, Skill


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "url",
            "source",
            "source_details",
            "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duplicate_candidate = None
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
            else:
                widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = self.cleaned_data["email"]
        self.duplicate_candidate = (
            Candidate.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).first()
        )
        if self.duplicate_candidate:
            raise forms.ValidationError("A candidate with this email already exists.")
        return email


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input w-full", "placeholder": "e.g. Python"})
        }

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Skill.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A skill with this name already exists.")
        return name


class JobOpeningForm(forms.ModelForm):
    class Meta:
        model = JobOpening
        fields = ["title", "department", "location", "description", "skills"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "skills": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                widget.attrs["class"] = "checkbox checkbox-sm"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
            else:
                widget.attrs["class"] = "input w-full"


class ApplicationForm(forms.ModelForm):
    """Shared by both entry points: fix the `job` to pick a candidate, or fix the
    `candidate` to pick a job. `choice_name` names the one field left to pick."""

    class Meta:
        model = Application
        fields = ["candidate", "job"]

    def __init__(self, *args, job=None, candidate=None, **kwargs):
        super().__init__(*args, **kwargs)
        if job is not None:
            self.instance.job = job
            self.choice_name = "candidate"
            del self.fields["job"]
            choice = self.fields["candidate"]
            choice.queryset = Candidate.objects.exclude(applications__job=job)
            choice.label_from_instance = lambda c: f"{c.full_name} ({c.email})"
            choice.error_messages["invalid_choice"] = (
                "That candidate can't be added. They may have already applied to this job."
            )
        else:
            self.instance.candidate = candidate
            self.choice_name = "job"
            del self.fields["candidate"]
            choice = self.fields["job"]
            choice.queryset = JobOpening.objects.filter(status=JobOpening.Status.OPEN).exclude(
                applications__candidate=candidate
            )
            choice.label_from_instance = lambda j: f"{j.title} ({j.department}, {j.location})"
            choice.error_messages["invalid_choice"] = (
                "That job can't be chosen. "
                "It may be closed, or the candidate already applied to it."
            )
        choice.widget.attrs["class"] = "select w-full"

    def clean(self):
        cleaned_data = super().clean()
        if self.choice_name == "candidate" and self.instance.job.status != JobOpening.Status.OPEN:
            raise forms.ValidationError("This job is closed, so it can't take new applications.")
        return cleaned_data
