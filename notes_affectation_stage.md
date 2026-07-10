# Overall idea

L’Extranet est un MVP complémentaire à AMLACS, destiné aux administrations publiques bénéficiaires. Il leur permet de consulter de manière sécurisée l’avancement de leurs dossiers d’affectation, de visualiser les différents états de la procédure, d’accéder au PV d’affectation lorsqu’il est prêt, et de le signer électroniquement à l’aide d’un OTP. L’Extranet doit s’appuyer sur une vue contrôlée des données issues d’AMLACS, tout en enregistrant la signature OTP et sa traçabilité, sans exposer directement la base interne d’AMLACS.



# Procédure d’affectation des biens domaniaux aux administrations publiques

1. L’administration demande un bien.
2. La Direction du Budget donne son accord si les crédits existent.
3. La DDE intègre l’accord budgétaire dans AMLACS.
4. La délégation DDE ouvre le dossier d’affectation.
5. La DDE effectue une enquête sur le bien.
6. La DDE évalue la valeur du bien.
7. La contre-valeur est réglée ou prélevée.
8. La DDE prépare le PV d’affectation.
9. Le PV est signé par la DDE et par l’administration bénéficiaire.
10. Le bien devient affecté à cette administration.
11. Plus tard, la DDE vérifie si le projet a été réalisé et si le bien est réellement utilisé.
12. Si le bien n’est pas utilisé ou n’est plus nécessaire, l’affectation peut être arrêtée.



# Workflow d'affectation

1. Accord budgétaire
2. Dossier ouvert dans AMLACS
3. Recherche / enquête foncière
4. Expertise
5. Règlement de la contre-valeur
6. Préparation du PV d’affectation
7. Signature du PV par l’administration bénéficiaire
8. Affectation validée / active
9. Suivi de réalisation
10. Suivi d’utilisation
11. Désaffectation éventuelle
12. Clôture du dossier



# Processus digital du signature du PV par OTP

1. PV préparé dans AMLACS
2. PV visible dans l’Extranet
3. L’administration se connecte
4. L’administration consulte le dossier et le PV
5. Le représentant autorisé clique sur "Signer"
6. Un OTP est envoyé
7. Le représentant saisit l’OTP
8. Le système enregistre la signature
9. La DDE est informée que le PV a été signé



# Questions 

1. Quel document doit être signé à travers l’Extranet ?
- Est-ce uniquement le PV d’affectation, ou aussi le PV d’expertise, le PV modificatif, ou d’autres documents ?

2. À quel statut AMLACS exact le bouton de signature doit-il apparaître ?
- Par exemple : “PV généré”, “PV validé par la DDE”, “en attente de signature administration”.

3. L’Extranet doit-il réécrire dans AMLACS ?
- Après la signature OTP, le statut doit-il être mis à jour dans AMLACS, ou seulement enregistré dans une base propre à l’Extranet ?

4. Quelles données seront exposées dans la vue de base de données ?
- Tu as besoin d’informations comme le numéro du dossier, l’administration, l’état, l’étape, le document PV, les dates et l’indicateur de signature.

5. Qui signe pour l’administration bénéficiaire ?
- Un seul compte ? Plusieurs comptes ? Un représentant légal ? Un administrateur ? Plusieurs signatures possibles ?

6. Quel canal OTP doit être utilisé ?
- Email, SMS, application d’authentification ou OTP interne ?

7. L’administration peut-elle télécharger le PV avant de signer ?

8. L’Extranet doit-il afficher tout le cycle de vie après la signature ?
- Par exemple : réalisation, utilisation, désaffectation, clôture.

# users

- consultation: can consult dossiers if linked to an administration
- signataire: can consult dossiers and can sign later if peut_signer=True
- admin_organisme: can consult dossiers and can manage organism users later
- admin_dde: does not see beneficiary dossiers in the Extranet list


# What is not complete yet if we speak about a production-grade authentication system:

- No password reset flow
- No email verification
- No forced password change on first login
- No account lockout after repeated failed logins
- No audit log for login/logout/user-management actions
- No custom rule blocking admin_dde from Extranet login
- No polished shared layout/base template
- No HTTPS/production security settings yet
- No OTP authentication/signature flow yet
