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
- [ ] Later: add OTP-based PV signature workflow with traceability.

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

## Future Work

- Complete official details for beneficiary administrations: codes, Arabic names, addresses, contact emails, and phone numbers.
- Build Extranet login, dashboard, dossier list, and dossier detail pages.
- Add OTP-based PV signature workflow later with full traceability.
