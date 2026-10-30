from django.contrib import admin

from .models import Application, Candidate, JobOpening, Skill, StageChange


class StageChangeInline(admin.TabularInline):
    model = StageChange
    extra = 0
    fields = ["from_stage", "to_stage", "changed_by", "changed_at"]
    readonly_fields = fields
    can_delete = False


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "source", "archived", "created_at"]
    list_filter = ["archived", "source"]
    search_fields = ["first_name", "last_name", "email"]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ["title", "department", "location", "status", "created_at"]
    list_filter = ["status", "department"]
    search_fields = ["title", "department", "location"]
    filter_horizontal = ["skills"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["candidate", "job", "stage", "created_at"]
    list_filter = ["stage", "job"]
    search_fields = ["candidate__first_name", "candidate__last_name", "candidate__email"]
    list_select_related = ["candidate", "job"]
    inlines = [StageChangeInline]


@admin.register(StageChange)
class StageChangeAdmin(admin.ModelAdmin):
    list_display = ["application", "from_stage", "to_stage", "changed_by", "changed_at"]
    list_filter = ["to_stage"]
    list_select_related = ["application__candidate", "application__job", "changed_by"]
