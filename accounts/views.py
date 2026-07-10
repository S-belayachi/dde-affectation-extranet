from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import capability_required
from .forms import (
    MANAGED_ORGANISM_ROLES,
    OrganismUserCreateForm,
    OrganismUserUpdateForm,
)


User = get_user_model()


@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")


def _managed_organism_users(request):
    return (
        User.objects
        .filter(
            administration=request.user.administration,
            role__in=MANAGED_ORGANISM_ROLES,
        )
        .exclude(pk=request.user.pk)
        .order_by("last_name", "first_name", "username")
    )


@capability_required("can_manage_organism_users")
def organism_user_list(request):
    users = _managed_organism_users(request)
    return render(
        request,
        "accounts/organism_user_list.html",
        {
            "managed_users": users,
            "administration": request.user.administration,
        },
    )


@capability_required("can_manage_organism_users")
def organism_user_create(request):
    if request.method == "POST":
        form = OrganismUserCreateForm(
            request.POST,
            administration=request.user.administration,
        )
        if form.is_valid():
            form.save()
            return redirect("accounts:organism_user_list")
    else:
        form = OrganismUserCreateForm(administration=request.user.administration)

    return render(
        request,
        "accounts/organism_user_form.html",
        {
            "form": form,
            "form_title": "Ajouter un utilisateur",
            "submit_label": "Creer l'utilisateur",
        },
    )


@capability_required("can_manage_organism_users")
def organism_user_update(request, user_id):
    managed_user = get_object_or_404(_managed_organism_users(request), pk=user_id)

    if request.method == "POST":
        form = OrganismUserUpdateForm(
            request.POST,
            instance=managed_user,
            administration=request.user.administration,
        )
        if form.is_valid():
            form.save()
            return redirect("accounts:organism_user_list")
    else:
        form = OrganismUserUpdateForm(
            instance=managed_user,
            administration=request.user.administration,
        )

    return render(
        request,
        "accounts/organism_user_form.html",
        {
            "form": form,
            "form_title": "Modifier un utilisateur",
            "submit_label": "Enregistrer",
            "managed_user": managed_user,
        },
    )
