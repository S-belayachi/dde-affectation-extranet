# Overall idea

L’Extranet est un MVP complémentaire à AMLACS, destiné aux administrations publiques bénéficiaires. Il leur permet de consulter de manière sécurisée l’avancement de leurs dossiers d’affectation, de visualiser les différents états de la procédure, d’accéder au PV d’affectation lorsqu’il est prêt, et de le signer électroniquement à l’aide d’un OTP. L’Extranet doit s’appuyer sur une grande table generee a partir de plusieurs tables jointes issue d’AMLACS, tout en enregistrant la signature OTP et sa traçabilité, sans exposer directement la base interne d’AMLACS.



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



# PV personalization architecture

1. Store the original PV Word template
   pv_affectation_template.docx

2. For each dossier, Django prepares a context
   dossier + administration + business rules

3. docxtpl generates a personalized DOCX

4. Convert DOCX to PDF

5. Store both files privately using Django FileField

6. Show only the PDF to the administration at "signé par DR"

7. After OTP signature, block PDF access for that administration



# PV repartition des taches

PV template
→ general structure of the document

PV context builder
→ prepares values

PV rules
→ decides which paragraphs/fields appear

PV clause blocks
→ optional text sections inserted depending on case



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



# DB new fields

LibelleAdministration
AdresseAdmiEnArabe
NomAdministration
AdresseAdmiParent
NomAdmiParent
QualiteBenefic



# Flux fonctionnel global

┌─────────────────────────────────────────────────────────────┐
│                         AMLACS                              │
│                                                             │
│  Données du dossier + règles métier + données foncières     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Le PV atteint l’état :
                               │ « Signé par DR »
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Service de génération AMLACS                 │
│                                                             │
│  Déclenche une seule génération officielle du PV            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Appel du moteur BIRT
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                           BIRT                              │
│                                                             │
│  - Exécute les règles du fichier .rptdesign                 │
│  - Récupère les données du dossier                          │
│  - Applique les conditions métier                           │
│  - Génère le PV officiel au format PDF                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ PDF généré
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Archivage du document officiel                 │
│                                                             │
│  - Identifiant unique du document                           │
│  - Numéro de version                                        │
│  - Empreinte SHA-256                                        │
│  - Date de génération                                       │
│  - Version du modèle BIRT                                   │
│  - Statut : PRÊT POUR L’EXTRANET                            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Publication sécurisée
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         EXTRANET                            │
│                                                             │
│  L’Extranet récupère le PDF et ses métadonnées              │
│  sans recalculer le document                                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Contrôle d’accès
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           Administration publique bénéficiaire             │
│                                                             │
│  - Utilisateur authentifié                                  │
│  - Appartient à l’administration concernée                  │
│  - Possède le rôle de signataire                            │
│  - Peut consulter le PV                                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Consultation du PDF
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Validation par OTP                       │
│                                                             │
│  - Envoi du code OTP par e-mail                             │
│  - Vérification du code                                     │
│  - Nouvelle vérification des autorisations                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ OTP valide
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            Enregistrement de la signature                  │
│                                                             │
│  La signature est liée à :                                  │
│  - l’utilisateur                                             │
│  - l’administration bénéficiaire                            │
│  - l’identifiant du PV                                      │
│  - la version exacte du PDF                                 │
│  - l’empreinte SHA-256                                      │
│  - la date et l’heure                                       │
│  - l’adresse IP et le navigateur                            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Signature terminée
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Blocage de l’accès au document                 │
│                                                             │
│  - Le bouton « Consulter le PV » disparaît                  │
│  - Le bouton « Signer » disparaît                           │
│  - L’accès direct au PDF retourne une interdiction          │
│  - Seul le statut de signature reste visible                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Synchronisation
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         AMLACS                              │
│                                                             │
│  Statut mis à jour :                                        │
│  « Signé par l’administration bénéficiaire »                │
└─────────────────────────────────────────────────────────────┘



# Architecture technique par composants


┌────────────────────────── AMLACS ────────────────────────────┐
│                                                              │
│  Base de données AMLACS                                      │
│        │                                                     │
│        ▼                                                     │
│  Gestion du workflow du dossier                              │
│        │                                                     │
│        ▼                                                     │
│  Passage à l’état « Signé par DR »                           │
│        │                                                     │
│        ▼                                                     │
│  Service de génération du PV                                 │
│        │                                                     │
│        ▼                                                     │
│  Moteur BIRT + fichier .rptdesign                            │
│        │                                                     │
│        ▼                                                     │
│  Génération du PDF officiel                                  │
│                                                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               │ API sécurisée,
                               │ table d’échange
                               │ ou stockage privé
                               ▼
┌────────────────────── Couche d’intégration ──────────────────┐
│                                                              │
│  - Publication du PV                                         │
│  - Métadonnées du document                                   │
│  - Numéro de version                                         │
│  - Empreinte SHA-256                                         │
│  - Statut du document                                        │
│  - Gestion des erreurs et des reprises                       │
│                                                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────── EXTRANET ─────────────────────────────┐
│                                                               │
│  Django                                                       │
│  ├── Authentification                                         │
│  ├── Gestion des administrations bénéficiaires                │
│  ├── Filtrage des dossiers                                    │
│  ├── Contrôle d’accès au PV                                   │
│  ├── Vue protégée du PDF                                      │
│  ├── Service OTP par e-mail                                   │
│  ├── Enregistrement de la signature                           │
│  ├── Journal d’audit                                          │
│  └── Synchronisation du statut vers AMLACS                    │
│                                                               │
│  PostgreSQL Extranet                                          │
│  ├── Utilisateurs                                             │
│  ├── Administrations bénéficiaires                            │
│  ├── Références des PV                                        │
│  ├── Demandes OTP                                             │
│  ├── Signatures                                               │
│  └── Journaux d’audit                                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘



# OTP signature record

> Lorsqu’un PV est signé avec succès par OTP, le système conserve les informations suivantes :
- Le PV concerné.
- Le numéro de dossier et le numéro du PV, via le dossier lié au PV.
- L’utilisateur signataire : son compte Extranet.
- L’administration bénéficiaire du signataire.
- La confirmation que le code OTP a été validé.
- La date et l’heure exactes de la signature.
- L’adresse IP utilisée lors de la signature.
- Le navigateur ou appareil déclaré par le navigateur (user-agent).
- L’empreinte SHA-256 du PDF signé, permettant de prouver l’intégrité exacte du document.
- L’état du PV : signé.
- La date et l’heure de génération du document.
- Le chemin interne du DOCX et du PDF générés, non exposé publiquement.

> Pour le code OTP lui-même, le système conserve :
- Son empreinte cryptographique, jamais le code en clair.
- Sa date de création.
- Sa date d’expiration.
- Le nombre de tentatives.
- Le nombre maximal de tentatives autorisées.
- La date d’utilisation après validation.
- Une éventuelle date et raison d’invalidation si un nouveau code a été demandé.

> Les informations de signature sont réparties dans ces tables :
- affectations_signatureotppv
Preuve principale de signature : PV, utilisateur signataire, administration, validation OTP, date/heure, adresse IP, navigateur et hash SHA-256 du PDF.
- affectations_pvaffectation
État et document du PV : dossier/PV source, chemins internes DOCX/PDF, hash SHA-256, date de génération, is_signed, signed_at.
- affectations_otpcode
Traçabilité OTP : hash du code, création, expiration, tentatives, utilisation et invalidation éventuelle.

> Tables liées pour identifier le contexte :
- accounts_customuser : identité et rôle du signataire.
- affectations_administrationbeneficiaire : administration du signataire.
- table_fait_affectation_datalab : dossier source, numéro de dossier, numéro PV et statut PV. Cette table ne contient pas la signature elle-même.




# workflow

Lors du passage du PV à l’état « Signé par DR », AMLACS génère une version PDF définitive à travers BIRT et l’archive avec un identifiant, un numéro de version et une empreinte SHA-256. Cette version est ensuite mise à disposition de l’Extranet à travers une API sécurisée ou une table d’échange. L’Extranet ne recalcule pas le PV et ne reproduit pas les règles BIRT. Il gère uniquement la consultation contrôlée, la validation OTP, la traçabilité et la remontée du statut de signature vers AMLACS.


AMLACS
  ↓
Le PV devient « Signé par DR »
  ↓
BIRT génère une version PDF définitive
  ↓
Le PDF est archivé avec version + SHA-256 (déposé dans un stockage ou une table d’échange)
  ↓
AMLACS expose le document à travers une API sécurisée
  ↓
L’Extranet récupère le document et ses métadonnées
  ↓
L’administration bénéficiaire le consulte
  ↓
Validation par OTP
  ↓
La signature est liée à la version et au hash du PDF
  ↓
L’accès au PDF est bloqué
  ↓
Le résultat est transmis à AMLACS
