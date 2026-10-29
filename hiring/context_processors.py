from .models import JobOpening


def sidebar_jobs(request):
    if not request.user.is_authenticated:
        return {}
    return {"sidebar_jobs": JobOpening.objects.with_active_count()}
