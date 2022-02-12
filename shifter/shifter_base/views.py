from django.shortcuts import render


def index(request):
    return render(request, "shifter_base/index.html")
