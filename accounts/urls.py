from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import ExtranetAuthenticationForm


app_name = "accounts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("utilisateurs/", views.organism_user_list, name="organism_user_list"),
    path(
        "utilisateurs/ajouter/",
        views.organism_user_create,
        name="organism_user_create",
    ),
    path(
        "utilisateurs/<int:user_id>/modifier/",
        views.organism_user_update,
        name="organism_user_update",
    ),
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=ExtranetAuthenticationForm,
            template_name="accounts/login.html",
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]
