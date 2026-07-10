You are assisting me inside my IDE on a Django + PostgreSQL internship project.

For now, your task is only to understand the full context, inspect the project structure and existing code, and be ready to assist me later. Do not build new features yet. Do not modify files unless I explicitly ask you to. Do not run or suggest destructive commands unless I ask for implementation help later.

Project context:
I am doing an IT development internship at the Moroccan Ministère de l’Économie et des Finances, specifically at the Direction des Domaines de l’État (DDE). The project is an MVP Extranet web application related only to the “procédure d’affectation” of State private-domain properties to public beneficiary administrations.

Business meaning:
The DDE manages State private-domain real estate. In the procedure d’affectation, the DDE puts a State-owned property at the disposal of a public administration so it can build or operate a public facility such as a school, hospital, administrative building, etc. The property remains State property; ownership is not transferred. The beneficiary administration needs to consult the advancement of its concerned dossiers d’affectation through an Extranet and perform an OTP-based electronic signature at a specific stage, most likely the PV d’affectation stage.

Important workflow of the affectation procedure:

1. Accord budgétaire / approval of the affectation request.
2. Dossier opened in AMLACS.
3. Recherche / enquête foncière about the property.
4. Expertise / property valuation.
5. Règlement or prélèvement de la contre-valeur.
6. Preparation of the PV d’affectation.
7. Signature of the PV d’affectation by the beneficiary administration.
8. Affectation becomes active.
9. Later follow-up: constat de réalisation.
10. Later follow-up: constat d’utilisation.
11. Possible désaffectation.
12. Possible clôture du dossier.

Application goal:
Build an MVP Extranet where employees of beneficiary public administrations can authenticate, consult only the dossiers d’affectation that concern their own administration, see the different states/advancement of each dossier, access the PV d’affectation when available, and eventually sign electronically using an OTP mechanism. The system must keep traceability: who signed, which dossier, which document, when, and whether OTP was verified.

Current technical stack:

* Python 3.13
* Django
* PostgreSQL 17
* psycopg
* pgAdmin for database inspection
* Windows development environment
* Project folder: affectation_extranet
* Django project/config package: config
* Django app for business data: affectations
* Django app for custom users: accounts

Current database situation:
Originally, I thought I would work with a live view of the big AMLACS database, but the DDE instead provided an extracted big table generated from multiple joined tables. I imported this table into PostgreSQL. The imported table is the source table for dossier data and should be treated as read-only/source data.

Imported PostgreSQL table:
table_fait_affectation_datalab

This table has fields similar to:

* import_id
* dr
* delegation
* num_dossier
* type_affectation
* date_ouverture_dossier
* denomination_projet
* administration_beneficiaire
* nature_sommier
* num_id
* trn
* num_trn
* indice_trn
* numero_construction
* nature_construction
* superficie_concernee
* montant_affectation
* statut_dossier
* date_resultat_enquete
* mobilisable
* superficie_proposee
* num_pv_expertise
* date_expertise
* montant_expertise
* date_pcv
* montant_total_regle
* num_fiche
* date_emission_fiche
* date_virement
* montant_fiche
* numero_pv
* type_pv
* date_envoi_pva_dr
* statut_pv
* constat_realisation
* date_constat_realisation
* constat_utilisation
* objet_utilisation
* date_constat_utilisation
* type_desaffectation
* motif_desaffectation
* date_cloture
* motif_cloture

Django model for the imported table:
The model is named TableFaitAffectationDatalab and has:
class Meta:
managed = False
db_table = 'table_fait_affectation_datalab'

This is very important. Do not make Django manage, recreate, or alter this imported table. It represents source DDE/AMLACS data.

New Django-managed business table:
AdministrationBeneficiaire

It should represent the beneficiary public administrations that will have employees using the Extranet.

Fields wanted:

* nom: name in French, unique
* nom_ar: name in Arabic
* code
* adresse_fr: address in French
* adresse_ar: address in Arabic
* email_contact
* telephone
* active
* created_at

Important note about link between imported table and AdministrationBeneficiaire:
The imported table contains a text field named administration_beneficiaire. The AdministrationBeneficiaire table contains a structured administration record. There is currently no real ForeignKey between them. The link is logical by matching:
table_fait_affectation_datalab.administration_beneficiaire
with:
AdministrationBeneficiaire.nom

For the MVP, filtering dossiers can be done by comparing the logged-in user’s administration.nom with the imported table’s administration_beneficiaire text field. Later, if a stable administration code is provided, use the code instead of name matching.

Custom user model:
I want to use a custom user model instead of Django’s default auth.User because each Extranet user belongs to an administration bénéficiaire and has business-specific fields.

The app accounts should contain CustomUser extending AbstractUser.

CustomUser should include:

* inherited Django fields: username, password, first_name, last_name, email, is_active, is_staff, is_superuser, groups, permissions
* nom_ar
* prenom_ar
* administration: ForeignKey to AdministrationBeneficiaire, nullable for DDE internal admins if needed
* role with choices:

  * consultation: Consultation uniquement
  * signataire: Signataire
  * admin_organisme: Administrateur organisme
  * admin_dde: Administrateur DDE
* fonction
* telephone
* cin
* matricule
* peut_signer: boolean

settings.py should include:
AUTH_USER_MODEL = 'accounts.CustomUser'

Expected user logic:

* DDE admin users can access Django Admin and create beneficiary administrations and users.
* Normal beneficiary employees should not use Django Admin; they will use the Extranet.
* Each beneficiary employee must see only dossiers related to their administration.
* Users with role consultation can only consult.
* Users with role signataire and peut_signer=True can later sign the PV using OTP.
* Users with role admin_organisme may later manage users of their own administration.
* Users with role admin_dde are internal DDE admin users.

Current admin goal:
First, create an administrator interface using Django Admin:

* Register AdministrationBeneficiaire.
* Register CustomUser using UserAdmin.
* Keep TableFaitAffectationDatalab visible in admin as read-only.
* In the table list, show only important summary columns like import_id, num_dossier, administration_beneficiaire, type_affectation, statut_dossier, statut_pv.
* In the detail page, group all dossier fields into sections:

  * Informations générales
  * Bien concerné
  * Expertise et règlement
  * PV d’affectation
  * Constats
  * Désaffectation / clôture

Important development instructions:

* For now, only inspect and understand the current project. Do not implement changes yet.
* Before changing files later, inspect the current project structure and existing code.
* Do not delete or modify the imported PostgreSQL table table_fait_affectation_datalab.
* Do not remove managed = False from TableFaitAffectationDatalab.
* Do not use the old ProfilUtilisateur model if we are using CustomUser.
* Keep user-related admin code in accounts/admin.py.
* Keep affectation/business-data admin code in affectations/admin.py.
* Keep AdministrationBeneficiaire in affectations/models.py.
* Keep CustomUser in accounts/models.py.
* Avoid circular migrations.
* If migrations are already messy because of earlier experiments, explain the situation first and suggest a clean migration reset only for Django-managed app tables, never for the imported DDE source table.
* Use clear French labels in admin where appropriate.
* Explain every observation and recommendation clearly.
* Prefer small, safe steps.
* When I later ask for implementation, tell me exactly which commands to run:
  python manage.py check
  python manage.py makemigrations
  python manage.py migrate
  python manage.py createsuperuser
  python manage.py runserver

Near-term things to understand, not implement yet:

1. Verify mentally how settings.py should contain accounts and affectations in INSTALLED_APPS and AUTH_USER_MODEL = 'accounts.CustomUser'.
2. Understand that affectations/models.py should contain TableFaitAffectationDatalab with managed=False and AdministrationBeneficiaire.
3. Understand that accounts/models.py should contain CustomUser extending AbstractUser.
4. Understand that accounts/admin.py should register CustomUser correctly using UserAdmin.
5. Understand that affectations/admin.py should register AdministrationBeneficiaire and TableFaitAffectationDatalab correctly.
6. Understand possible migration issues if old models like ProfilUtilisateur existed before.
7. Understand that the first DDE admin superuser will later be created for Django Admin.
8. Understand that Django Admin is only the first administrator interface for managing users and data.
9. Understand that the real Extranet pages will be built later:

   * login
   * dashboard
   * dossier list filtered by user administration
   * dossier detail page
   * later OTP signature workflow

When helping me, act like a senior Django developer and internship mentor. For now, focus only on understanding the project, the current architecture, the DDE business context, and the relationships between the database, Django models, admin, users, and future Extranet logic. Wait for my next instructions before making or suggesting concrete implementation steps.
