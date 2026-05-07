from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, "dashboard/home.html")


def health(request):
    return JsonResponse({"status": "ok", "app": "Carta Arcanum"})
