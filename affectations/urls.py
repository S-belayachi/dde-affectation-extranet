from django.urls import path

from . import views


app_name = "affectations"

urlpatterns = [
    path("dossiers/", views.dossier_list, name="dossier_list"),
]
