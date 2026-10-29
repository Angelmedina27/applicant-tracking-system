from django.shortcuts import render


def job_list(request):
    return render(request, "hiring/job_list.html")
