from django.shortcuts import render

from accounts.decorators import capability_required

from .models import TableFaitAffectationDatalab


@capability_required("can_access_extranet")
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
