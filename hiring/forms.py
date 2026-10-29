from django import forms

from .models import Candidate


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
