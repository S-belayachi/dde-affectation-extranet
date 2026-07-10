# Project Progress

## Current Objective

Clean and harden the early Django MVP setup for the DDE affectation Extranet while keeping the imported DDE/AMLACS source table read-only and unmanaged.

## Todo List

- [x] Create this progress file and record the initial inspection state.
- [x] Harden `TableFaitAffectationDatalab` in Django Admin as truly read-only.
- [x] Clean generated model noise in `affectations/models.py` without changing fields.
- [x] Add `requirements.txt` from the working project virtual environment.
- [x] Run final verification and record remaining future work.

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

## Completed Fixes

- Created the project progress tracker.
- Made the imported DDE/AMLACS source table admin view-only.
- Cleaned generated model noise without changing model fields or migrations.
- Added a dependency manifest for reproducible local setup.
- Completed final verification after cleanup.

## Future Work

- Add beneficiary administrations matching imported source names.
- Build Extranet login, dashboard, dossier list, and dossier detail pages.
- Add OTP-based PV signature workflow later with full traceability.
