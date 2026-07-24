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
- Configure the official SMTP credentials and real email addresses for every `signataire` before production use.
- Establish the AMLACS export process that places each official PDF in `pv_documents/official/` using the filename contract in `PV_STORAGE.md`.

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
- Replaced PV template/DOCX/LibreOffice generation with retrieval of the official AMLACS PDF from a private directory.
- Added `PV_DOCUMENT_ROOT` with sibling private folders: `official/` for AMLACS PDFs and `signed/` for Extranet-created signed copies.
- Added `affectations.0005_replace_generated_pv_with_amlacs_pdf_storage`, replacing template/DOCX metadata with source filename/hash and signed PDF metadata.
- Added PDF integrity checks: the source file hash is recorded when OTP is requested, and a changed source PDF cannot be signed with that OTP.
- Added `PyMuPDF==1.27.1` to stamp the signed copy with the electronic-signature line while leaving the official AMLACS source unchanged.
- Removed the unused PV DOCX template and documented the private storage and filename contract in `PV_STORAGE.md`.
- Migrated the existing signed test/audit PDFs into `pv_documents/signed/`.
- Validation passed: `manage.py check`, `manage.py makemigrations --check --dry-run`, and 18 affectations tests.

### 2026-07-21

- Added French/Arabic Extranet localization with a persistent language selector, Arabic right-to-left layout, and Arabic translations for login, dashboard, dossier/PV, OTP, and user-management workflows.
- Restricted the `signataire` dossier list and direct dossier access to dossiers whose PV status is `Signé par DR`; consultation and organism-admin users keep access to all dossiers in their administration.
- Removed the obsolete `generated_documents/` directory, including legacy generated DOCX/PDF test artifacts.
- Removed the unused `LIBREOFFICE_PATH` setting and the obsolete `generated_documents/` Git ignore rule.
- The active PV workflow now exclusively retrieves official AMLACS PDFs from `pv_documents/official/` and creates signed copies in `pv_documents/signed/`.
- Historical migration and progress entries remain as an audit trail; no active code uses the previous DOCX-generation workflow.

### 2026-07-23

- Rebuilt the Extranet UI around a shared, responsive public-administration design system.
- Consolidated page structure, navigation, language controls, forms, tables, statuses, messages, empty states, and footer styling into a common layout and stylesheet.
- Polished login, dashboard, dossier list/detail, PV signing, and beneficiary user-management screens without changing permissions or business workflows.
- Extended Arabic translations for all new interface labels and verified right-to-left behavior.
- Verified desktop and mobile layouts at 1440px and 390px with no page-level horizontal overflow.
- Validation passed: 31 tests, `manage.py check`, static asset discovery, and migration consistency check.
- Integrated the supplied bilingual Ministry of Economy and Finance logo into the shared Extranet header and login screen.
- Adapted the interface palette to the logo's institutional navy and turquoise while preserving the restrained public-administration layout.
- Added localized accessible logo text and verified the image at desktop and mobile sizes without distortion or horizontal overflow.
- Refined the ministry/product header lockup with a centered turquoise divider so the Extranet identity aligns clearly beside the logo.
- Strengthened the visual hierarchy across headings, supporting text, navigation, buttons, forms, tables, and service links using distinct institutional and neutral colors.
- Validation passed: 12 account/UI tests, 19 affectations/PV tests, `manage.py check`, and authenticated desktop visual review.
- Rebalanced the interface palette by moving page, section, form, and table headings to charcoal and reserving ministry blue for branding, links, active navigation, and primary actions.
- Replaced the minimal signed-PV footer with a professional electronic-signature attestation containing the signer name, account identifier, optional function, beneficiary administration, Morocco-local date and time, OTP method, and reproducible signature reference.
- The attestation is placed in newly appended space below the official AMLACS page, preserving the source document's content and coordinates without overlap.
- Validation passed: 19 affectations/PV tests, `manage.py check`, migration consistency check, extracted-text assertions, and visual PDF review.
- Added five fresh `Signé par DR` signature-test dossiers to the unmanaged AMLACS source table: three for Education Nationale and two for Enseignement Supérieur Et De La Recherche Scientifique.
- Added matching private official test PDFs (`12.pdf` through `16.pdf`) under `pv_documents/official/`.
- Confirmed `signataire_education` and `signataire_pv_test` are active signataires with signing permission and both deliver OTP codes to `belayachisouhayl1@gmail.com`.
- Added live signed-PDF integrity verification against both SHA-256 values stored on `PvAffectation` and `SignatureOtpPv`.
- Added a DDE-admin integrity column with `Valide`, `Falsifié`, `Fichier manquant`, `Non vérifiable`, and `Non signé` states, plus a view-permitted bulk verification action.
- Altered or unverifiable signed PDFs no longer expose a viewing link in Django Admin, and the protected DDE document view blocks access when integrity fails.
- Validation passed: all 19 affectations/PV tests, including sign, verify, tamper, admin detection, bulk verification, and access blocking. No migration was required.
- Current integrity audit: recent signed PV records `4` and `5` are valid; historical signed records `1`, `2`, and `3` have no signed file in private storage and are reported as `Fichier manquant`.
- Replaced the verbose French signed-PV attestation with a concise Arabic footer containing only the signataire's first and last name, beneficiary administration, and Morocco-local signature date.
- The footer prefers the Arabic user and administration fields and falls back to their existing names when Arabic data is not yet populated.
- Bundled Noto Naskh Arabic under `document_assets/fonts/` so connected right-to-left Arabic text renders consistently in signed PDFs.
- Validation passed: all 19 affectations/PV tests, `manage.py check`, migration consistency check, and visual PDF review with a long Arabic administration name. No migration was required.
- Diagnosed two manual signatures produced by a stale port `8000` process that still held the removed French footer implementation in memory.
- Reset only the disposable `TEST-OTP-*` PV, OTP, and signature-proof records for source dossiers `12` through `16`; their imported source rows and official AMLACS PDFs remain untouched and ready for retesting.
- Cleared project bytecode caches and restarted port `8000` with an isolated empty cache, forcing the Arabic-only footer implementation to load directly from source.
- Revalidation passed: all 19 affectations/PV tests, `manage.py check`, and migration consistency check.
- Found and terminated twelve overlapping Django `runserver` processes, including the original pre-Arabic worker that continued serving OTP signature requests from memory.
- Reset the affected disposable test signature and removed every remaining French-stamped test PDF from private signed storage.
- Started one clean `127.0.0.1:8000 --noreload` server and verified it through a real HTTP OTP-signature request: footer height `84`, no legacy French markers, and visually correct Arabic rendering.

### 2026-07-24

- Kept OTP verification and the concise Arabic signature footer as the beneficiary-signing workflow.
- Added an invisible PAdES-B-B cryptographic signature to each newly signed PDF using `pyHanko`; no visible `DDE Extranet Test` label or signature box is added.
- Added a development-only in-memory self-signed certificate whose subject contains the signataire's real first and last name and beneficiary administration.
- Added persistent PAdES audit metadata to `SignatureOtpPv`: profile, PDF signature field, certificate subject, serial number, and SHA-256 fingerprint.
- Strengthened DDE Admin integrity verification to require the stored PDF hashes, expected certificate fingerprint, intact PAdES signature, full-file coverage, and no later PDF modification.
- Required real first and last names when an organism administrator creates or updates a signataire.
- Added and applied migration `affectations.0006_signatureotppv_pades_certificate_fingerprint_sha256_and_more`; only the managed signature-proof table changed.
- Confirmed a real incremental content edit invalidates PAdES and is blocked by the protected DDE signed-document view.
- Validation passed: all 32 account/PV tests, `manage.py check`, migration consistency check, PAdES metadata inspection, and visual PDF review.
- Existing signed PDFs were not re-signed automatically; records without PAdES proof are intentionally reported as non-verifiable.
- Extended the Arabic signed-PV footer with the Morocco-local signature time using `على الساعة HH:MM:SS`.
- Reinitialized testable PV records `11` and `13` for signature retesting: removed their OTP rows, signature proofs, signed metadata, signed PDFs, backup, and tampered copy while preserving official AMLACS sources `14.pdf` and `13.pdf`.
- Added the managed `Delegation` table with unique `code`, unique `nom`, and required `adresse`.
- Added the exclusive `signataire_delegation` account role and nullable `CustomUser.delegation` relationship; database and model validation prevent mixing delegation authority with a beneficiary administration.
- Added `can_sign_pv_dr` while preserving beneficiary `can_sign_pv` and internal `admin_dde` supervision as separate capabilities.
- Delegation accounts can authenticate and see a delegation-aware bilingual dashboard, but beneficiary dossier and OTP routes remain hidden and return `403` until the DR-specific workflow is implemented.
- Registered delegations and delegation account fields in Django Admin.
- Added and applied migrations `affectations.0007_delegation` and `accounts.0002_customuser_delegation_alter_customuser_role_and_more`; the unmanaged AMLACS source table was not altered.
- Validation passed: all 34 account/PV tests, `manage.py check`, and migration consistency check.
- Added required `Delegation.email` and exposed it in delegation search/list management in Django Admin.
- Added role-aware `CustomUser.otp_email`: beneficiary signers use their account email, while delegation signers use the institutional delegation email.
- Added and applied migration `affectations.0008_delegation_email`.
- Revalidated delegation and beneficiary OTP routing; all 34 account/PV tests, `manage.py check`, and migration consistency check pass.
- Created four delegation test records from real non-test values in the unmanaged AMLACS source table: `Agadir`, `Rabat`, `Essaouira`, and `Casablanca`.
- Created active `signataire_delegation` test accounts `delegation_agadir`, `delegation_rabat`, `delegation_essaouira`, and `delegation_casablanca`; all use the configured test mailbox for OTP and pass authentication/capability checks.
- Generated stable test codes `DEL-AGADIR`, `DEL-RABAT`, `DEL-ESSAOUIRA`, and `DEL-CASABLANCA`; addresses are explicitly marked for later completion because the imported source table has no delegation address field.
- Added a dedicated delegation dossier section at `/delegation/dossiers/`, visible in delegation navigation and dashboard services.
- Delegation dossier access is filtered by exact imported delegation name and exact PV status `Validé`; beneficiary dossier details and signature routes remain isolated.
- Verified the real `delegation_agadir` account sees only eligible dossier `1503/198008/31`; already-signed Agadir dossiers and other delegations are excluded.
- Added permission tests proving beneficiary and `admin_dde` users cannot access the delegation list.
- Validation passed: all 36 account/PV/delegation tests, `manage.py check`, and migration consistency check. No migration was required.
- Implemented the complete delegation/DR signature stage for source dossiers
  whose exact PV status is `Validé`.
- Added protected delegation dossier detail, PDF consultation, OTP request, and
  OTP verification routes under `/delegation/dossiers/<import_id>/`.
- Added separate managed DR evidence storage: `PvAffectation` DR state,
  `DrOtpCode`, and `SignatureOtpPvDr`. No write is made to the unmanaged AMLACS
  source table.
- Added private `pv_documents/dr_signed/` storage and a concise Arabic footer
  followed by an invisible PAdES-B-B signature for the delegation signataire.
- After the DR signature, the dossier leaves the delegation queue and becomes
  eligible for the matching beneficiary signataire even while the imported
  source row remains `Validé`.
- Applied migration `affectations.0009_pvaffectation_delegation_and_more`.
- Fixed PostgreSQL row locking in DR OTP verification by avoiding an outer join
  on the nullable delegation relationship.
- Validation passed: all 40 tests, `manage.py check`, migration consistency
  check, real-account permission check, and an authenticated render check for
  all three Agadir signing controls.
- Known test-data prerequisite: real Agadir source dossier import ID `1`
  (`1503/198008/31`) has no official AMLACS PDF in private storage yet. Place
  it at `pv_documents/official/1.pdf` before requesting its OTP.
- Corrected the final PV chain so beneficiary signing starts from the
  delegation-signed PDF in `dr_signed/`, not from the original AMLACS PDF.
- The DR stage now reserves a second footer area. Beneficiary OTP verification
  adds the Arabic beneficiary footer as a visible signature appearance and
  appends a second PAdES-B-B signature incrementally.
- The final PDF in `signed/` contains both embedded fields:
  `DrSignature_<pv_id>` and `BeneficiarySignature_<pv_id>`.
- Final integrity verification now validates the final SHA-256 evidence, the
  beneficiary signature over the complete file, and the delegation signature
  over its earlier revision with only the later signature update permitted.
- A rendered QA sample confirmed correct footer order, spacing, Arabic
  legibility, and separate delegation/beneficiary signature areas.
- Validation passed: all 40 tests, `manage.py check`, migration consistency
  check, dual-certificate validation, and final PDF visual review.
- Replaced the delegation PDF debug 404 with a document-aware dossier state.
  When the AMLACS PDF is missing, consultation and OTP controls are hidden and
  the page displays the exact expected filename.
- Confirmed dossier import ID `8` (`603/200626/31`, delegation `Essaouira`)
  expects `pv_documents/official/8.pdf`; the private official directory
  currently contains only `12.pdf` through `16.pdf`.
- Validation passed: all 5 delegation-flow tests, `manage.py check`, and the
  migration consistency check. No migration was required.
- Generated clearly marked local test PDFs for missing source import IDs `1`
  through `11` under `pv_documents/official/`; existing PDFs `12` through `16`
  were preserved.
- Every one of the 16 source dossiers now resolves through the official-PV
  service using its `<import_id>.pdf` filename.
- Visually verified test PDF `8.pdf` and confirmed protected consultation
  returns HTTP 200 `application/pdf` for the real Agadir and Essaouira
  delegation accounts.
- Reset test dossier `14` again for manual signing: removed its OTP, signature proof, signed-PV metadata, and signed copy while preserving the `Signé par DR` source row and official AMLACS PDF.
