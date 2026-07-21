# Project Progress

## Current Objective

Clean and harden the early Django MVP setup for the DDE affectation Extranet while keeping the imported DDE/AMLACS source table read-only and unmanaged.

## Todo List

- [x] Create this progress file and record the initial inspection state.
- [x] Harden `TableFaitAffectationDatalab` in Django Admin as truly read-only.
- [x] Clean generated model noise in `affectations/models.py` without changing fields.
- [x] Add `requirements.txt` from the working project virtual environment.
- [x] Run final verification and record remaining future work.

## Authentication And User Management Todo

- [x] Add Extranet authentication foundation: login/logout routes, redirect settings, and a protected dashboard placeholder.
- [x] Create beneficiary administrations in Django Admin so users can be linked to their organism.
- [x] Create the first DDE superuser and verify Django Admin access.
- [x] Add dossier list filtered by `request.user.administration.nom`.
- [x] Add role helpers or decorators for `consultation`, `signataire`, `admin_organisme`, and `admin_dde`.
- [x] Add user-management pages for `admin_organisme` to manage users from only their own administration.
- [x] Add tests for login, logout, dashboard protection, and organization-based access control.
- [x] Add OTP-based PV signature workflow with traceability.

## Initial Inspection

- Project apps are present: `accounts`, `affectations`, and `config`.
- `AUTH_USER_MODEL = 'accounts.CustomUser'` is configured.
- `TableFaitAffectationDatalab` maps to `table_fait_affectation_datalab` with `managed = False`.
- `AdministrationBeneficiaire` and `CustomUser` are present.
- Django Admin registrations are split between `accounts/admin.py` and `affectations/admin.py`.
- Validation using the project virtual environment passed:
  - `.\.venv\Scripts\python.exe manage.py check`
  - `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`
- Migrations are applied in the configured database.
- The imported table `table_fait_affectation_datalab` exists and is readable through the ORM.
- `AdministrationBeneficiaire` currently has no rows.

## Validation Commands

Use the project virtual environment for Django commands:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py showmigrations
```

## Known Risks

- The imported source table must never be managed, recreated, altered, or deleted by Django.
- Admin access to the imported source table must remain view-only.
- Future dossier filtering depends on matching `CustomUser.administration.nom` with `TableFaitAffectationDatalab.administration_beneficiaire`.
- Commands should be run through `.venv`; the global Python environment may not have the PostgreSQL driver installed.

## Progress Log

### 2026-07-10

- Created `PROJECT_PROGRESS.md` as the project cleanup and advancement tracker.
- Hardened `TableFaitAffectationDatalabAdmin` so imported source rows can be viewed but not added, changed, or deleted through Django Admin.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Cleaned the generated `inspectdb` header in `affectations/models.py` and removed the duplicate `models` import.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Added `requirements.txt` from the working `.venv` dependencies.
- Final validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Final validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Final validation passed: `.\.venv\Scripts\python.exe manage.py showmigrations`.
- Confirmed ORM read access to `table_fait_affectation_datalab`; first row sample: `1503/198008/31`, `Education Nationale`, `PV établi`, `Validé`.
- Added the first Extranet authentication foundation:
  - login page at `/login/`
  - logout route at `/logout/`
  - protected dashboard placeholder at `/`
  - redirect settings in `config/settings.py`
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`; no changes detected, with a PostgreSQL credential warning because environment variables are not currently loaded.
- Smoke test passed: unauthenticated `/` redirects to `/login/?next=/`, and `/login/` returns HTTP 200.
- Added local `.env` loading in `config/settings.py` and created the ignored development `.env` file so Django commands can use the PostgreSQL credentials consistently.
- Created 3 `AdministrationBeneficiaire` records from distinct imported source names:
  - `Education Nationale`
  - `Enseignement Supérieur Et De La Recherche Scientifique`
  - `Jeunesse Et Sports`
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Confirmed all 3 distinct source administration names now match structured `AdministrationBeneficiaire.nom` values.
- Normalized the existing `admin` superuser as the first DDE admin account:
  - role: `admin_dde`
  - staff: true
  - superuser: true
  - active: true
  - administration: empty, because it is an internal DDE admin account
- Verified Django Admin access using the normalized `admin` account:
  - `/admin/` returned HTTP 200
  - `/admin/accounts/customuser/` returned HTTP 200
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Added the protected dossier list page:
  - `/dossiers/`
  - exact filter: `TableFaitAffectationDatalab.administration_beneficiaire = request.user.administration.nom`
  - users without an administration see an empty state instead of all dossiers
  - dashboard link: `Consulter mes dossiers`
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Smoke test passed:
  - anonymous `/dossiers/` redirects to `/login/?next=/dossiers/`
  - a user linked to `Education Nationale` gets HTTP 200 and sees its filtered list
  - the internal `admin_dde` account gets HTTP 200 with an empty Extranet dossier state
  - temporary smoke-test user was removed after validation
- Added role and capability helpers on `CustomUser`:
  - `has_role`
  - `is_consultation_user`
  - `is_signataire`
  - `is_admin_organisme`
  - `is_admin_dde`
  - `can_consult_dossiers`
  - `can_sign_pv`
  - `can_manage_organism_users`
- Added reusable decorators in `accounts/decorators.py`:
  - `role_required`
  - `capability_required`
- Updated the dossier list to use `request.user.can_consult_dossiers` before showing filtered source dossiers.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Smoke test passed for the four roles, and temporary smoke-test users were removed after validation.
- Added organism user-management pages for `admin_organisme`:
  - `/utilisateurs/` list page
  - `/utilisateurs/ajouter/` create page
  - `/utilisateurs/<id>/modifier/` edit page
  - dashboard link visible only when `request.user.can_manage_organism_users` is true
- User-management safety rules:
  - managed users are limited to the current admin's `administration`
  - `admin_dde` accounts cannot be created or edited through these organism pages
  - `is_staff`, `is_superuser`, and `administration` are forced server-side
  - the current `admin_organisme` account is excluded from its own management list
  - `peut_signer` is kept only for `signataire` users
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Smoke test passed:
  - `admin_organisme` can list same-administration users
  - `admin_organisme` can create a same-administration signataire user
  - `admin_organisme` can edit a same-administration user
  - cross-administration edit returns HTTP 404
  - non-admin-organisme access returns HTTP 403
  - temporary smoke-test users were removed after validation
- Added automated tests for authentication and access control:
  - dashboard requires login
  - login redirects to dashboard
  - logout redirects to login
  - `admin_organisme` sees only same-administration users
  - non-`admin_organisme` access to user management is forbidden
  - organism user creation forces the current administration and non-staff flags
  - organism user update is limited to the same administration
  - cross-administration user edit returns HTTP 404
  - dossier list requires login
  - beneficiary users see only dossiers matching their administration name
  - `admin_dde` does not receive all beneficiary dossiers in the Extranet list
- Test validation passed: `.\.venv\Scripts\python.exe manage.py test` ran 11 tests successfully.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Created three development Extranet test users linked to `Education Nationale`:
  - `consult_education`, role `consultation`
  - `signataire_education`, role `signataire`, `peut_signer=True`
  - `admin_org_education`, role `admin_organisme`
- Verified the test users are active, non-staff, non-superuser accounts and that `consult_education` can log in successfully.
- Blocked internal DDE admin accounts from the beneficiary Extranet:
  - added `CustomUser.can_access_extranet`
  - added `ExtranetAuthenticationForm` for `/login/`
  - applied `can_access_extranet` to the dashboard and dossier list
  - kept Django Admin authentication separate for `admin_dde`
- Improved the login template so it shows specific form-level access errors.
- Test validation passed: `.\.venv\Scripts\python.exe manage.py test` ran 14 tests successfully.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Confirmed the real `admin` account has `can_access_extranet=False` and receives HTTP 403 on `/` and `/dossiers/`.
- Implemented the PV d'affectation workflow:
  - managed PV metadata model: `PvAffectation`
  - hashed OTP model: `OtpCode`
  - signature proof/audit model: `SignatureOtpPv`
  - grouped PV key based on administration, dossier number, and PV number
  - ready status rule: `Signé par DR`
  - protected dossier detail page at `/dossiers/<import_id>/`
  - protected PDF view at `/dossiers/<import_id>/pv/`
  - OTP request and verification views
  - DDE admin supervision through read-only Django Admin records
  - beneficiary signing restricted to `can_access_extranet` and `can_sign_pv`
  - PDF access blocked after successful OTP signature
- Added document settings:
  - `DOCUMENT_TEMPLATE_ROOT`
  - `GENERATED_DOCUMENT_ROOT`
  - `LIBREOFFICE_PATH`
  - PV OTP expiry/attempt settings
- Added `document_templates/pv_affectation/pv_affectation_template.docx` with non-confidential placeholders.
- Added `generated_documents/` to `.gitignore`.
- Added `docxtpl` and related document dependencies to `requirements.txt`.
- Applied migration `affectations.0002_pvaffectation_otpcode_signatureotppv`.
- Test validation passed: `.\.venv\Scripts\python.exe manage.py test` ran 26 tests successfully.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Note: LibreOffice is now configured locally; the development-only PDF fallback remains available only while `DEBUG=True` if conversion is unavailable.
- Configured local LibreOffice path in the ignored `.env` file:
  - `C:\Program Files\LibreOffice\program\soffice.exe`
- Verified Django reads `LIBREOFFICE_PATH` and the executable exists.
- Verified real DOCX-to-PDF conversion with a `Signé par DR` dossier; generated PDF exists and has a SHA-256 hash.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run`.
- Test validation passed: `.\.venv\Scripts\python.exe manage.py test` ran 26 tests successfully.
- Created `signataire_pv_test` for manual PV testing:
  - role: `signataire`
  - `peut_signer=True`
  - administration: `Enseignement Supérieur Et De La Recherche Scientifique`
  - eligible dossier: import id `6`, dossier `1003/199204/31`, PV `23/2010/04`, status `Signé par DR`
- Verified `signataire_pv_test` can log in and sees `Consulter le PV` / `Signer par OTP` on dossier `6`.
- Inserted two development-only PV test rows into the imported source table after explicit confirmation:
  - import id `10`, dossier `TEST-PV-DR-001`, administration `Education Nationale`, PV `TEST-PV-001`, ready PV status
  - import id `11`, dossier `TEST-PV-DR-002`, administration `Enseignement Superieur Et De La Recherche Scientifique`, PV `TEST-PV-002`, ready PV status
- Verified both rows are readable through the unmanaged ORM model.
- Verified `signataire_education` can see `Consulter le PV` / `Signer par OTP` on dossier `10`.
- Verified `signataire_pv_test` can see `Consulter le PV` / `Signer par OTP` on dossier `11`.
- Validation passed: `.\.venv\Scripts\python.exe manage.py check`.

## Completed Fixes

- Created the project progress tracker.
- Made the imported DDE/AMLACS source table admin view-only.
- Cleaned generated model noise without changing model fields or migrations.
- Added a dependency manifest for reproducible local setup.
- Completed final verification after cleanup.
- Added the Extranet authentication foundation.
- Added local `.env` support for consistent development database configuration.
- Created the initial beneficiary administration records needed to link users to organisms.
- Normalized and verified the first DDE admin superuser.
- Added the first protected Extranet dossier list filtered by beneficiary administration.
- Added reusable role/capability helpers and decorators for Extranet authorization.
- Added same-administration user-management pages for `admin_organisme`.
- Added automated tests for authentication, dossier filtering, and organism user-management access control.
- Created development Extranet test users for manual role testing.
- Blocked `admin_dde` accounts from beneficiary Extranet login/pages while keeping Django Admin separate.
- Added PV generation, protected PDF consultation, OTP signature, and signature traceability.
- Configured and verified LibreOffice headless conversion locally.
- Created a dedicated signataire account for manual PV testing.
- Created two development-only ready-to-sign PV test dossiers.
- Replaced development-only console OTP handling with configurable SMTP email delivery for PV signatures. Console output is now disabled by default and can only be enabled explicitly while `DEBUG=True`.
- Added OTP request cooldown, explicit invalidation of replaced codes, and fresh permission checks inside the signing transaction.
- Added migration `affectations.0003_otpcode_invalidated_at_otpcode_invalidation_reason`; it changes only the Django-managed OTP table.

## Future Work

- Complete official details for beneficiary administrations: codes, Arabic names, addresses, contact emails, and phone numbers.
- Keep `LIBREOFFICE_PATH` configured per environment for DOCX-to-PDF conversion.
- Configure the official SMTP credentials and real email addresses for every `signataire` before production use.
- Replace the placeholder PV template only after mapping the approved Arabic/French fields in `PV_affectation_editable.docx` to the imported dossier data and structured administration data.

### 2026-07-14

- Reviewed the supplied `PV_affectation_editable.docx` template without changing it or the PV generation code.
- Confirmed it is a one-page Arabic/French PV with official logos and a nine-row property-reference table.
- Confirmed that it contains visual blanks and hard-coded beneficiary wording rather than `docxtpl` placeholders; personalization must be added before it can be used by the generation service.
- LibreOffice rendering exposed malformed placeholder-line glyphs in one Arabic paragraph. This must be corrected and re-rendered before the template is adopted for generated PDFs.
- Added six nullable administration metadata columns directly to the unmanaged source table: `libelle_administration`, `adresse_admi_en_arabe`, `nom_administration`, `adresse_admi_parent`, `nom_admi_parent`, and `qualite_benefic`.
- Added matching read-only fields to `TableFaitAffectationDatalab` and the Django Admin source-record detail view.
- Applied state-only migration `affectations.0004_source_administration_fields_state`; it records the external schema for Django without issuing source-table SQL.
- Validation passed: source fields are readable through the ORM, `manage.py check`, `manage.py makemigrations --check --dry-run`, and 17 affectations tests.
- Added a signed-PV document stamp: after valid OTP verification, the final DOCX/PDF footer reads `Signé électroniquement par <administration beneficiaire>`.
- The final PDF is regenerated before the signature record is saved, so the stored PDF SHA-256 hash proves the stamped version of the document.
- Validation passed: `manage.py check`, `manage.py makemigrations --check --dry-run`, 17 affectations tests, and a LibreOffice visual review of the footer placement.
- Added protected internal DDE access to signed PV PDFs at `/supervision/pvs/<pv_id>/document-signe/`.
- Only `admin_dde` users can open this document; beneficiary users remain blocked after signature. Signed PV entries in Django Admin now include a `Voir le PDF signe` link.
- Validation passed: `manage.py check`, `manage.py makemigrations --check --dry-run`, and 17 affectations tests.
