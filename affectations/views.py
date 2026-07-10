from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import TableFaitAffectationDatalab


@login_required
def dossier_list(request):
    administration = request.user.administration
    dossiers = TableFaitAffectationDatalab.objects.none()

    if request.user.can_consult_dossiers:
        dossiers = (
            TableFaitAffectationDatalab.objects
            .filter(administration_beneficiaire=administration.nom)
            .order_by("num_dossier", "import_id")
        )

    context = {
        "administration": administration,
        "dossiers": dossiers,
    }
    return render(request, "affectations/dossier_list.html", context)
