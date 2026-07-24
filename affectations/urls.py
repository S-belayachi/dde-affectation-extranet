from django.urls import path

from . import views


app_name = "affectations"

urlpatterns = [
    path(
        "delegation/dossiers/",
        views.delegation_dossier_list,
        name="delegation_dossier_list",
    ),
    path(
        "delegation/dossiers/<int:import_id>/",
        views.delegation_dossier_detail,
        name="delegation_dossier_detail",
    ),
    path(
        "delegation/dossiers/<int:import_id>/pv/",
        views.delegation_pv_pdf,
        name="delegation_pv_pdf",
    ),
    path(
        "delegation/dossiers/<int:import_id>/pv/otp/request/",
        views.delegation_pv_otp_request,
        name="delegation_pv_otp_request",
    ),
    path(
        "delegation/dossiers/<int:import_id>/pv/otp/verify/",
        views.delegation_pv_otp_verify,
        name="delegation_pv_otp_verify",
    ),
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
