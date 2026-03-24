from django.urls import path

from . import views

app_name = "quantai"

urlpatterns = [
    path("", views.index, name="index"),
    path("submit", views.submit, name="submit"),
    path("result/<str:job_id>", views.result, name="result"),
    path("health", views.health, name="health"),
]
