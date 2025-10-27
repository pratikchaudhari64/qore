from django.urls import path

from . import views

urlpatterns = [
    path("", views.root, name="root"),
    path('kiteredirect', views.kite_redirect_handler, name='kite_redirect')
]