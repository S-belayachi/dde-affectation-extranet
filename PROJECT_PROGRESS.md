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
- [ ] Create the first DDE superuser and verify Django Admin access.
- [ ] Add dossier list filtered by `request.user.administration.nom`.
- [ ] Add role helpers or decorators for `consultation`, `signataire`, `admin_organisme`, and `admin_dde`.
- [ ] Add user-management pages for `admin_organisme` to manage users from only their own administration.
- [ ] Add tests for login, logout, dashboard protection, and organization-based access control.
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

## Completed Fixes

- Created the project progress tracker.
- Made the imported DDE/AMLACS source table admin view-only.
- Cleaned generated model noise without changing model fields or migrations.
- Added a dependency manifest for reproducible local setup.
- Completed final verification after cleanup.
- Added the Extranet authentication foundation.
- Added local `.env` support for consistent development database configuration.
- Created the initial beneficiary administration records needed to link users to organisms.

## Future Work

- Complete official details for beneficiary administrations: codes, Arabic names, addresses, contact emails, and phone numbers.
- Build Extranet login, dashboard, dossier list, and dossier detail pages.
- Add OTP-based PV signature workflow later with full traceability.
