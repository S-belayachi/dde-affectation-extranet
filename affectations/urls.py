from django.urls import path

from . import views


app_name = "affectations"

urlpatterns = [
    path("dossiers/", views.dossier_list, name="dossier_list"),
    path("dossiers/<int:import_id>/", views.dossier_detail, name="dossier_detail"),
    path("dossiers/<int:import_id>/pv/", views.pv_pdf, name="pv_pdf"),
    path(
        "supervision/pvs/<int:pv_id>/document-signe/",
        views.dde_signed_pv_pdf,
        name="dde_signed_pv_pdf",
    ),
    path(
        "dossiers/<int:import_id>/pv/otp/request/",
        views.pv_otp_request,
        name="pv_otp_request",
    ),
    path(
        "dossiers/<int:import_id>/pv/otp/verify/",
        views.pv_otp_verify,
        name="pv_otp_verify",
    ),
]
