# Avocat Yassine — Plateforme de gestion de cabinet d'avocats

Plateforme multi-plateforme (**Web + Desktop + Mobile**) pour la gestion complète d'un cabinet d'avocat marocain, avec synchronisation centrale ↔ locale, intégration **mahakim.ma**, audit complet et bilingue **FR/AR (RTL)**.

> Lecture cible : un développeur (ou Claude Code) qui découvre le projet pour la première fois et doit pouvoir poursuivre le développement de A à Z.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Stack technique](#2-stack-technique)
3. [Architecture](#3-architecture)
4. [Pré-requis & installation](#4-pré-requis--installation)
5. [Structure du dépôt](#5-structure-du-dépôt)
6. [Modèle de données](#6-modèle-de-données)
7. [Modules fonctionnels](#7-modules-fonctionnels)
8. [Authentification & sécurité](#8-authentification--sécurité)
9. [Synchronisation centrale ↔ locale](#9-synchronisation-centrale--locale)
10. [Intégration mahakim.ma](#10-intégration-mahakimma)
11. [Build & distribution](#11-build--distribution)
12. [Imports XLSX](#12-imports-xlsx)
13. [API REST](#13-api-rest)
14. [Tests & smoke tests](#14-tests--smoke-tests)
15. [Conventions](#15-conventions)
16. [Historique & roadmap](#16-historique--roadmap)

---

## 1. Vue d'ensemble

### Objectif métier

Outil unique pour gérer un cabinet d'avocat marocain :

- **Affaires (قضايا)** : suivi complet du cycle de vie (création → audiences → décisions → exécution → archive)
- **Audiences (جلسات)** : calendrier, résultats, mesures judiciaires
- **Parties & avocats** : annuaire, rôles, relations avec affaires
- **Pièces jointes** : documents binaires (procurations, jugements, expertises…)
- **Mahakim.ma** : import automatique des données publiques (numéro/code/année → fiche affaire)
- **Finances** : dépenses & recettes par affaire
- **Tâches & alertes** : échéances, rappels, délais légaux d'avertissement
- **Audit** : traçabilité complète "qui a fait quoi, quand"

### Cibles de déploiement

| Cible    | Statut          | Mode                                  |
|----------|-----------------|---------------------------------------|
| **Web**  | ✓ production    | Django runserver / gunicorn + MySQL central |
| **Desktop (.dmg/.app/.exe)** | ✓ macOS livré, Windows .spec prêt | Django embarqué + SQLite local + sync REST |
| **Android (.apk)** | ✓ signée et installable hors store | Capacitor 6 WebView pointant la web |
| **iOS (.ipa)** | non commencé | Capacitor 6 prêt côté config |
| **PWA**  | ✓ active        | Service worker network-first nav + cache-first assets |

### Multi-langue

- Interface principale en **arabe (RTL)** avec libellés français en frontmatter sur certains modèles.
- Templates de notification, login, audit, etc. tous en arabe.
- PDF officiels avec police **Amiri** (jspdf-autotable) pour rendu arabe propre.

---

## 2. Stack technique

| Couche       | Technologie                                                                 |
|--------------|------------------------------------------------------------------------------|
| Backend      | Python 3.13 · Django 5.1.2 · Django REST Framework 3.16                      |
| Base centrale| MySQL 8 (PyMySQL/mysqlclient)                                                |
| Base locale  | SQLite (mode desktop)                                                         |
| Frontend Web | Bootstrap 5 RTL · jQuery 3 · Select2 · HTMX · Bootstrap Icons                |
| Auth         | django.contrib.auth + django-simplejwt + django-axes (anti-brute force)      |
| Mobile       | Capacitor 6 (downgrade requis car JDK 17 nécessaire vs JDK 21 pour Cap 8)    |
| Desktop      | PyWebView 6.2.1 + PyObjC (macOS) + PyInstaller 6.20                          |
| PDF          | reportlab · xhtml2pdf · arabic-reshaper · python-bidi (rendu arabe)           |
| Excel        | openpyxl · pyexcel-xlsx                                                       |
| WhatsApp/SMS | Twilio Python SDK                                                             |
| IA           | embeddings.py (vector store local pour recherche sémantique des décisions)   |
| Scraping     | Selenium + requests (scraper mahakim.ma)                                      |
| Dev tools    | django-extensions · django-filter · django-environ                            |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       CENTRAL (server)                                │
│  Django 5 + DRF + JWT + MySQL                                         │
│  - API REST /api/* pour mobile, desktop, intégrations                 │
│  - UI Web /auth, /affaires, /audiences, /ref, /audit, /portail        │
│  - Sync engine : Outbox → push, Pull endpoint, LWW conflict           │
│  - File storage : media/pieces/<uuid>/*                               │
└─────────────▲──────────────────────────────▲─────────────────────────┘
              │ REST/JWT                     │ REST/JWT
              │                              │
┌─────────────┴──────────────┐    ┌──────────┴───────────────┐
│  DESKTOP (.dmg / .exe)     │    │  MOBILE (.apk / .ipa)    │
│  PyWebView + Django local  │    │  Capacitor 6 WebView     │
│  SQLite mirror + sync push │    │  → points to central URL │
│  + setup wizard            │    │  + cleartext_traffic     │
└────────────────────────────┘    └──────────────────────────┘
```

### Synchro centrale ↔ desktop

- **Outbox** : chaque modification locale empile une entrée `SyncOutbox` (model, pk, action, payload).
- **Pull** : pull complet de toutes les tables (référentiels d'abord, métier ensuite) avec PRAGMA FK OFF pour éviter les erreurs d'ordre.
- **Push** : envoi de l'Outbox vers `/api/sync/push/`.
- **Files sync** : un ledger `desktop_file_state` track les uploads/downloads des PieceJointe via `/api/files/<uuid>/`.
- **Conflict resolution** : Last-Write-Wins par `updated_at` (UTC).
- **Tombstones** : suppression logique propagée via `is_deleted=True` (jamais de DELETE physique).

---

## 4. Pré-requis & installation

### Pré-requis système

- **Python 3.13** (venv recommandé)
- **MySQL 8** ou MariaDB 10.11+ avec utf8mb4
- **Node 20** + **JDK 17** (pour rebuild mobile)
- **Xcode 16** (pour rebuild desktop macOS) ou **Visual Studio Build Tools** (Windows)
- **Homebrew** (macOS) : `brew install mysql node openjdk@17`

### Installation initiale (Web)

```bash
# 1. Cloner le repo
git clone git@github.com:yacentoselmoudene/avocat_yassine.git
cd avocat_yassine

# 2. Créer un venv et installer les deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configurer .env (NE JAMAIS COMMITER)
cat > .env <<EOF
DEBUG=True
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
DATABASE_URL=mysql://avocat:password@127.0.0.1:3306/avocat_yassine
PORTAIL_COOKIE_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
TWILIO_SID=
TWILIO_TOKEN=
TWILIO_WHATSAPP_FROM=
EOF

# 4. Créer la base MySQL
mysql -u root -p -e "CREATE DATABASE avocat_yassine CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER 'avocat'@'localhost' IDENTIFIED BY 'password';"
mysql -u root -p -e "GRANT ALL ON avocat_yassine.* TO 'avocat'@'localhost';"

# 5. Migrer + créer superuser
python manage.py migrate
python manage.py createsuperuser

# 6. Importer les référentiels juridiques marocains
python manage.py import_juridictions_xlsx       # 32 CA + 160 PI
python manage.py import_codes_affaires_xlsx     # ~540 codes affaire

# 7. Lancer
python manage.py runserver 0.0.0.0:8000
# → http://127.0.0.1:8000/auth/login/
```

### Lancement desktop (PyWebView)

```bash
cd desktop
python launcher.py
# → fenêtre native macOS avec Django embarqué en localhost:port_aléatoire
```

### Rebuild mobile APK

```bash
cd mobile
npm install
# Pointer la WebView vers le bon serveur dans capacitor.config.json
npx cap sync android
cd android
./gradlew assembleRelease
# → app/build/outputs/apk/release/app-release.apk
```

---

## 5. Structure du dépôt

```
avocat_yassine/
├── avocat_yassine/                # Project Django (settings, urls racine, wsgi)
│   ├── settings.py                # MySQL + JWT + axes + corsheaders
│   ├── urls.py                    # racine — include cabinet, auth, ref, api, desktop
│   └── wsgi.py
│
├── avocat_app/                    # APPLICATION PRINCIPALE
│   ├── models.py                  # ~50 modèles (TimeStampedSoftDeleteModel base)
│   ├── forms.py                   # Tous les ModelForm + AffaireForm cascade
│   ├── views.py                   # CRUD principal + APIs JSON
│   ├── views_audit.py             # Audit trail UI (timeline filtrable)
│   ├── views_portail.py           # Portail client externe
│   ├── views_users.py             # CRUD utilisateurs avec ui_perms
│   ├── views_cabinet_params.py    # Paramètres globaux du cabinet
│   ├── views_codes_affaire.py     # CRUD AJAX /ref/codes-affaire/ (Volet 4)
│   ├── views_ref.py               # Refs liste + ref_registry
│   ├── views_ref_generic.py       # RefList/RefCreate générique (slug)
│   ├── views_pwa.py               # manifest.webmanifest + sw.js
│   ├── views_mixins.py            # HTMXModalFormMixin, success_json, etc.
│   ├── ref_registry.py            # Configuration des CRUD de référentiel
│   ├── urls.py                    # Routes principales (/affaires, /api, etc.)
│   ├── urls_ref.py                # Routes /ref/* (codes-affaire avant slug catchall)
│   ├── auth_urls.py               # Auth views (login, password reset)
│   ├── api/                       # DRF endpoints (registry + files_views)
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── files_views.py         # GET/POST /api/files/<uuid>/ pour PieceJointe
│   │   ├── registry.py            # auto-register ViewSets pour tous les modèles
│   │   └── sync_views.py          # /api/sync/push/, /api/sync/pull/
│   ├── management/commands/
│   │   ├── import_juridictions_xlsx.py        # 32 CA + 160 PI
│   │   ├── import_codes_affaires_xlsx.py      # ~540 codes
│   │   ├── import_categories_ca.py            # 55 codes du PDF CA Casa
│   │   └── sync_mahakim.py                    # cron job scraper mahakim.ma
│   ├── migrations/                # 32 migrations cumulées
│   ├── services/
│   │   ├── audit_signals.py       # signals post_save → AuditLog
│   │   ├── auth_signals.py        # logging connexions
│   │   ├── alerts.py              # création auto d'alertes (échéances)
│   │   ├── deadline_alerts.py     # délais légaux (avertissements)
│   │   ├── mahakim_scraper.py     # Selenium scraper du portail public
│   │   ├── ai_client.py           # wrapper Anthropic/OpenAI pour résumés
│   │   ├── embeddings.py          # vector store SQLite pour décisions
│   │   ├── notifier.py            # SMS/WhatsApp via Twilio
│   │   ├── portail_auth.py        # auth séparée pour clients du portail
│   │   ├── token_utils.py         # AuthToken rotation + idle timeout
│   │   ├── twilio_client.py
│   │   └── twilio_security.py
│   ├── sync_signals.py            # suppress_outbox + push automatique
│   └── templatetags/ui_perms.py   # filter |can_see pour droits UI
│
├── desktop/                       # Desktop wrapper
│   ├── launcher.py                # PyWebView main, port aléatoire
│   ├── settings_desktop.py        # Override Django : SQLite + cookies HTTP
│   ├── sync_engine.py             # full_sync = pull → files_pull → push → files_push → pull_post
│   ├── sync_files.py              # Binaires PieceJointe (ledger SQLite)
│   ├── urls.py                    # Routes /desktop/* (status, setup, trigger_sync)
│   ├── views.py                   # setup wizard (validate central + shadow user)
│   ├── context_processors.py      # injecte DESKTOP_MODE dans templates
│   └── avocat_desktop.spec        # PyInstaller spec (templates+static+migrations)
│
├── mobile/                        # Capacitor 6 wrapper
│   ├── capacitor.config.json      # appId=ma.avocatyassine.maktab, cleartext
│   ├── package.json
│   ├── www/index.html             # Page d'accueil RTL avec URL input
│   ├── android/
│   │   ├── app/
│   │   │   ├── build.gradle       # signing conditionnel via signing.properties
│   │   │   ├── release.jks        # 🔒 GITIGNORE — keystore RSA-4096
│   │   │   └── signing.properties # 🔒 GITIGNORE — mots de passe keystore
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       └── res/               # icons adaptatives mdpi→xxxhdpi + splash
│   ├── .gitignore                 # exclut node_modules, build, release.jks, .properties
│   └── INSTALL_ANDROID.md         # guide utilisateur (sideload .apk)
│
├── client_poc/                    # POC client Python offline (CLI)
│   ├── auth.py · sync.py · storage.py · cli.py
│   └── local.sqlite3
│
├── templates/                     # Django templates
│   ├── base.html                  # Layout + navbar + toast + htmx handler
│   ├── auth/                      # login, password_reset (RTL)
│   ├── cabinet/                   # affaire_form.html (wizard 4 étapes)
│   ├── modals/                    # _affaire_form.html (modal cascade)
│   ├── affaires/                  # detail.html avec timeline
│   ├── avocat/                    # listes CRUD
│   ├── ref/                       # codes_affaire.html (CRUD AJAX), libelle_list
│   ├── audit/                     # timeline filtrable
│   ├── portail/                   # interface client (lecture seule)
│   ├── pdf/                       # rendu reportlab/xhtml2pdf
│   ├── _partials/                 # _stepper, _table_filter, _table_pager
│   ├── desktop/setup.html         # 1er lancement : credentials → shadow user
│   └── dashboard/                 # tableaux de bord avocat
│
├── static/                        # CSS, JS, fonts
│   └── pwa/                       # service worker, icons, manifest
│
├── media/                         # 🔒 GITIGNORE (sauf si forcé)
│   ├── pieces/                    # PieceJointe binaires
│   ├── المحاكم الابتدائية مع الاستئناف.xlsx  # 32 CA + PI
│   └── رموز المحاكم.xlsx            # ~540 codes affaire
│
├── releases/                      # Artefacts livrables (binaires)
│   ├── avocat-yassine-v1.0.apk    # APK signée Android
│   └── AvocatDesktop-v1.0.dmg     # DMG macOS drag-and-drop
│
├── dist/                          # 🔒 GITIGNORE — build outputs PyInstaller
├── staticfiles/                   # 🔒 GITIGNORE — collectstatic
├── .env                           # 🔒 GITIGNORE — secrets dev
├── manage.py
├── requirements.txt               # ~120 packages Python
├── CLAUDE.md                      # instructions globales projet (Yassine)
└── PROJECT.md                     # CE FICHIER
```

---

## 6. Modèle de données

### Modèle de base : `TimeStampedSoftDeleteModel`

Tous les modèles métier héritent de cette base définie dans `avocat_app/models.py` :

```python
class TimeStampedSoftDeleteModel(models.Model):
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(User, on_delete=PROTECT, null=True, related_name="+")
    updated_by  = models.ForeignKey(User, on_delete=PROTECT, null=True, related_name="+")
    is_deleted  = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(User, on_delete=SET_NULL, null=True, related_name="+")
```

**Principe absolu** : aucune suppression physique. Tout passe par `is_deleted=True` (soft delete) avec possibilité de désarchivage.

### Référentiels (CRUD générique via `RefList` + `ref_registry`)

- `TypeAffaire`, `StatutAffaire`, `TypeAudience`, `ResultatAudience`
- `TypeMesure`, `StatutMesure`
- `TypeRecours`, `StatutRecours`, `TypeExecution`, `StatutExecution`
- `TypeJuridiction`, `DegreJuridiction`, `Juridiction` (hiérarchique via `TribunalParent`)
- `TypeDepense`, `TypeRecette`
- `TypeAlerte`, `TypeAvertissement` (avec délai légal en jours)
- `RoleUtilisateur`, `StatutTache`
- `Barreau`, `Avocat`
- `CodeCategorieAffaire` (~540 codes) → CRUD dédié `/ref/codes-affaire/`

### Entités métier centrales

```
Affaire ──┬── numero_dossier / code_categorie / annee_dossier  →  reference_tribunal auto
          ├── juridiction  →  Juridiction (CA si is_premiere_instance=False, sinon PI)
          ├── type_affaire, statut_affaire, phase
          ├── avocat_responsable + avocats (M2M via AffaireAvocat)
          ├── parties (M2M via AffairePartie avec rôle)
          ├── audiences (1-N, avec mesures, expertises, décisions)
          ├── recours (1-N : VoieDeRecours → instance d'appel)
          ├── notifications (1-N : signification, citation)
          ├── executions (1-N : Execution avec StatutExecution)
          ├── avertissements (mises en demeure, délais légaux)
          ├── depenses (1-N) + recettes (1-N)
          ├── pieces_jointes (1-N : binaires synchronisés)
          ├── document_requirements (checklist documents requis)
          ├── taches (1-N) + alertes (1-N)
          └── journal_activite (1-N : timeline globale)
```

### Audit (immutable)

- `AuditLog` : `(actor, action, model, pk, before_json, after_json, ip, ua, timestamp)`
- Implémenté via signals `post_save`/`post_delete` dans `audit_signals.py`
- Respecte le contexte `suppress_outbox` (pas d'audit lors d'un pull sync)

### Référentiel `CodeCategorieAffaire` (post Volet 1)

Champs étendus depuis import XLSX :

| Champ             | Exemple              | Description                          |
|-------------------|----------------------|--------------------------------------|
| code              | `1101`               | Code affaire 4 chiffres (unique)     |
| libelle           | `الاستعجالي`         | Libellé de l'affaire                 |
| code_type         | `1100`               | Code chambre groupant                |
| type_libelle      | `مؤسسة الرئيس وغرفة المشورة` | Libellé de la chambre        |
| sous_type         | `ابتدائي` ou `استئنافي` ou texte libre | Niveau juridiction |
| categorie_globale | `civil` / `penal` / `admin` / `commercial` | Famille principale |
| domaine           | `civil` / `famille` / ... | 11 domaines pour filtres UI    |
| niveau            | `premiere_instance` / `appel` / ... | Compatibilité descendante |

---

## 7. Modules fonctionnels

### 7.1 Affaires (cœur métier)

- **Création multi-étapes** : `/affaires/create/` (wizard 4 étapes)
  1. **المراجع** : référence interne + numéro/code/année
  2. **التصنيف والمحكمة** : type + phase + **cascade CA → checkbox 1ère instance → PI** (style mahakim.ma)
  3. **تفاصيل مالية** : date d'ouverture + priorité + valeur litige
  4. **الموضوع** : objet + notes

- **Cascade mahakim.ma** (Volet 2, juin 2026) :
  - Dropdown CA (32 cours d'appel)
  - Checkbox "القضية ابتدائية"
  - Si cochée → dropdown PI filtré via AJAX `/api/juridictions-by-ca/?ca=<id>`
  - Si non cochée → `affaire.juridiction = CA`
  - Validation serveur : la PI choisie doit appartenir à la CA

- **Vérification doublon AJAX** (juin 2026) :
  - Sur blur de `reference_interne` → check existence
  - Sur blur des champs `numero/code/annee` → check triplet
  - Endpoint : `GET /api/affaires/check-duplicate/`

- **Détail affaire** : `/affaires/<uuid>/` avec timeline globale et accès direct à toutes les entités liées.

### 7.2 Audiences

- Création depuis affaire : `/affaires/<uuid>/audiences/new/`
- Calendrier global + filtres
- Saisie du résultat post-audience (modal AJAX)
- Mesures judiciaires associées (`Mesure`, `TypeMesure`, `StatutMesure`)

### 7.3 Référentiels

- `/ref/<slug>/` : interface CRUD générique pour chaque type de référentiel
- Recherche client-side + pagination 25/50/100
- **`/ref/codes-affaire/`** (page dédiée AJAX, Volet 4) :
  - 691 codes en base
  - Recherche libre + 3 filtres (catégorie globale, chambre, sous-type)
  - Pagination 10/25/50
  - Sélection multiple + archivage de masse
  - Modal create/edit AJAX

### 7.4 Portail client

- Auth séparée (`portail_auth.py`) — accès en lecture seule
- Vue de l'affaire publique
- Cookies signés via `PORTAIL_COOKIE_SECRET`

### 7.5 Audit trail

- `/audit/` : timeline chronologique
- Filtres : utilisateur, action, modèle, période
- Lecture seule (les entrées ne sont jamais modifiables ni supprimables)

### 7.6 Documents requis (PDF mahakim.ma)

- Modèle `DocumentRequirement` : liste configurable par type d'affaire
- Sur la fiche affaire : boutons "Upload" et "View" par document requis
- Stockage dans `media/pieces/<uuid>/`

### 7.7 Notifications externes

- WhatsApp via Twilio API (`whatsapp_bot.py`)
- Templates de messages : `WhatsAppTemplate` avec variables `{{client}}`, `{{tribunal}}`, etc.
- Logs envoyés : `WhatsAppMessage`

### 7.8 Synchronisation desktop

- `Trigger sync` : bouton dans la navbar mode desktop
- Lance `full_sync()` : pull → files_pull → push → files_push → pull_post
- Affiche `pending_changes` (nombre d'entrées Outbox en attente)

---

## 8. Authentification & sécurité

### Web

- Django auth standard, vue `/auth/login/`
- `django-axes` : 5 échecs → blocage 30 min
- Reset password : email-less, par admin (sécurité Maroc)
- Cookies : `Secure`, `HttpOnly`, `SameSite=Lax`

### API JWT (mobile, desktop)

- `POST /api/auth/token/` → `{access, refresh}` (12h / 30j)
- `POST /api/auth/refresh/`
- `simplejwt.token_blacklist` activé

### Desktop : Auth shadow

- `/desktop/setup/` (publique au 1er lancement)
- POST `{username, password}` → valide contre central → si OK :
  - Sauve `credentials.json` (chmod 0o600) pour sync
  - Crée localement le user Django avec `is_superuser=True`
- L'utilisateur peut ensuite faire `/auth/login/` localement avec les mêmes creds

### Permissions UI (templatetag)

```django
{% load ui_perms %}
{% if user|can_see:"ui_btn_add" %}
  <button>إضافة</button>
{% endif %}
```

- Superuser : tout autorisé
- User vierge sans aucune perm UI : tout autorisé (mode "découverte")
- User avec ≥1 perm UI : restreint au filtre

### Audit token

- `AuthToken` rotatif (table Django) avec :
  - `idle_timeout` : 5 minutes
  - `min_touch_interval` : 60 s (réduit les writes)
- Lookup automatique sur chaque requête authentifiée

---

## 9. Synchronisation centrale ↔ locale

### Mécanique générale

1. **Outbox locale** : chaque save/delete sur le desktop empile une entrée `SyncOutbox` :
   ```python
   class SyncOutbox(models.Model):
       model_label  = models.CharField(max_length=80)  # ex: avocat_app.Affaire
       object_pk    = models.CharField(max_length=64)
       action       = models.CharField(max_length=20)  # create | update | delete
       payload_json = models.JSONField()
       created_at   = models.DateTimeField(auto_now_add=True)
       pushed_at    = models.DateTimeField(null=True)
   ```

2. **Suppression du re-trigger** : context manager `suppress_outbox` autour des pulls pour ne pas re-créer d'entrées en miroir.

3. **Pull complet** (`desktop/sync_engine.py`) :
   ```python
   @contextmanager
   def _fk_disabled():
       # SQLite uniquement — bypass FK pendant pull pour
       # éviter erreurs d'ordre (ex: Tache avant StatutTache)
       cursor.execute("PRAGMA foreign_keys = OFF")
       try: yield
       finally: cursor.execute("PRAGMA foreign_keys = ON")
   ```

4. **Push** : envoi Outbox vers `/api/sync/push/` → MySQL central.

5. **Conflict resolution** : LWW par `updated_at` (UTC).

### Files sync (binaires)

`desktop/sync_files.py` maintient un ledger SQLite :

```sql
CREATE TABLE desktop_file_state (
    piece_id              VARCHAR PRIMARY KEY,
    last_uploaded_path    TEXT,
    last_uploaded_mtime   INTEGER,
    last_downloaded_path  TEXT
);
```

- **Pull** : GET `/api/files/<piece_id>/` → save dans `media/pieces/...`
- **Push** : POST `/api/files/<piece_id>/` multipart upload

### Cycle complet `full_sync()`

```
1. pull_pre      ← référentiels (TypeAffaire, StatutAffaire, etc.)
2. files_pull    ← binaires manquants
3. push          → outbox → MySQL
4. files_push    → uploads PieceJointe modifiées
5. pull_post     ← entités métier (Affaire, Audience, ...)
```

---

## 10. Intégration mahakim.ma

### Workflow utilisateur

1. Sur `/affaires/create/` étape 1, saisir `numero / code / annee` (ex: `1234/1606/2026`)
2. Étape 2 : choisir CA → cocher "ابتدائية" → choisir PI
3. Le scraper `mahakim_scraper.py` peut être lancé manuellement pour récupérer la fiche

### Scraper (Selenium)

`avocat_app/services/mahakim_scraper.py` :
- Lance Chrome headless
- Navigue sur `mahakim.ma/#/suivi/dossier-suivi`
- Saisit numéro + code → résolution CA + checkbox + PI → submit
- Parse les résultats → modèle `MahakimSyncResult`

### Cron `sync_mahakim`

```bash
python manage.py sync_mahakim --since 2026-01-01
```

Rafraîchit toutes les affaires marquées pour sync auto.

### Référentiel

- 22 Cours d'Appel (importées du XLSX `المحاكم الابتدائية مع الاستئناف.xlsx`)
- 160 Tribunaux de 1ère Instance avec lien `TribunalParent` vers leur CA
- 691 codes d'affaire (importés de `رموز المحاكم.xlsx`)

---

## 11. Build & distribution

### Desktop macOS (.dmg)

```bash
cd /Users/.../avocat_yassine
# Build .app avec PyInstaller
pyinstaller desktop/avocat_desktop.spec
# Créer le DMG avec drag-and-drop
hdiutil create -volname "Avocat Yassine" -srcfolder dist/AvocatDesktop.app -format UDZO dist/AvocatDesktop.dmg
# Vérifier
hdiutil verify dist/AvocatDesktop.dmg
```

Spec PyInstaller (`desktop/avocat_desktop.spec`) inclut :
- Tous les templates (`templates/`)
- Tous les static (`static/`)
- Toutes les migrations (`avocat_app/migrations/`)
- Hidden imports : `django_extensions`, `django_filters`, `rest_framework_simplejwt.authentication`, `rest_framework_simplejwt.token_blacklist`, `avocat_yassine.wsgi/urls/settings`, `pyobjc` sur Darwin
- Exclusions : `tkinter`, `matplotlib`, `numpy`, `PyQt`, `axes`, `mysqlclient` (on utilise SQLite en local)

### Desktop Windows (.exe)

```bash
# Sur Windows
pyinstaller desktop/avocat_desktop.spec
# → dist/AvocatDesktop.exe
```

Le spec est cross-platform.

### Android (.apk)

```bash
cd mobile

# 1. Première fois : configurer le keystore (NE PAS COMMITER)
keytool -genkeypair -v -keystore android/app/release.jks -alias avocat \
    -keyalg RSA -keysize 4096 -validity 10000

# 2. Créer android/app/signing.properties (NE PAS COMMITER)
cat > android/app/signing.properties <<EOF
storeFile=release.jks
keyAlias=avocat
storePassword=...
keyPassword=...
EOF

# 3. Sync + build
npm install
npx cap sync android
cd android
./gradlew assembleRelease
# → app/build/outputs/apk/release/app-release.apk
```

L'APK pointe vers le serveur central (URL dans `mobile/www/index.html` ou config saved en `localStorage`).

### Installation utilisateur

| Cible | Documentation |
|-------|---------------|
| Android | `mobile/INSTALL_ANDROID.md` (sideload, autorisation source inconnue) |
| macOS  | `desktop/INSTALL_MACOS.md` (montage DMG, drag dans Applications, bypass Gatekeeper) |
| Windows | TODO |

---

## 12. Imports XLSX

### Source 1 : `media/المحاكم الابتدائية مع الاستئناف.xlsx`

22 CA + 280 lignes de PI avec correspondance.

```bash
python manage.py import_juridictions_xlsx
# 22 CA créées (codes CA00..CA21)
# 160 PI créées (codes PI00-00..PI21-N)
```

Mapping des types :
- "قسم قضاء الأسرة" → `TypeJuridiction.code_type=QAF`
- "المركز القضائي" → `TypeJuridiction.code_type=CJ`
- "المحكمة الابتدائية" → `TypeJuridiction.code_type=TPI`
- Cours d'Appel → `TypeJuridiction.code_type=CA`

### Source 2 : `media/رموز المحاكم.xlsx`

544 lignes avec hiérarchie chambre/affaire/sous_type.

```bash
python manage.py import_codes_affaires_xlsx
# 521 codes uniques importés
# 38 chambres distinctes (code_type)
# 25 sous-types distincts
```

---

## 13. API REST

### Auth (JWT)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/auth/token/` | Login → `{access, refresh}` |
| POST | `/api/auth/refresh/` | Refresh access token |

### CRUD générique (DRF ViewSets via `registry.py`)

Toutes les entités exposées en `/api/<modelname>/` :
- `GET` liste (paginé)
- `GET <pk>/` détail
- `POST /` create
- `PUT/PATCH <pk>/` update
- `DELETE <pk>/` soft delete

### Sync

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/sync/pull/?since=<iso>` | Pull entités modifiées depuis date |
| POST | `/api/sync/push/` | Push outbox (liste d'opérations) |

### Fichiers binaires

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/files/<piece_uuid>/` | Télécharger un binaire |
| POST | `/api/files/<piece_uuid>/` | Upload multipart |

### Endpoints custom (juin 2026)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/cours-appel/` | Liste des 32 CA |
| GET | `/api/juridictions-by-ca/?ca=<id>` | PI rattachées à une CA |
| GET | `/api/code-types/?sous_type=&categorie_globale=` | Chambres |
| GET | `/api/codes-affaire/?code_type=&sous_type=&q=` | Codes filtrés |
| GET | `/api/affaires/check-duplicate/?reference_interne=&exclude_id=` | Vérif doublon |
| GET | `/api/categories/<id>/juridictions/` | Juridictions compatibles avec une catégorie |

---

## 14. Tests & smoke tests

### Lancer les tests Django

```bash
python manage.py test avocat_app
```

### Smoke test post-déploiement

```bash
# 1. Login admin et stocker session
COOKIES=/tmp/avc_cookies.txt
curl -s -c $COOKIES http://127.0.0.1:8000/auth/login/ -o /tmp/login.html
CSRF=$(grep -oP 'csrfmiddlewaretoken"\s+value="\K[^"]+' /tmp/login.html | head -1)
curl -s -b $COOKIES -c $COOKIES -X POST http://127.0.0.1:8000/auth/login/ \
    -H "Referer: http://127.0.0.1:8000/auth/login/" \
    -d "csrfmiddlewaretoken=$CSRF&username=admin&password=YOUR_PASS"

# 2. Vérifier endpoints critiques
for url in \
    "/api/cours-appel/" \
    "/api/juridictions-by-ca/?ca=23" \
    "/affaires/create/" \
    "/ref/codes-affaire/" ; do
  echo -n "$url → "
  curl -s -o /dev/null -w "%{http_code}\n" -b $COOKIES "http://127.0.0.1:8000$url"
done
```

### Sync round-trip (desktop)

```bash
cd desktop
python launcher.py
# Dans la fenêtre : cliquer "Trigger sync"
# Vérifier : pending_changes diminue à 0
```

---

## 15. Conventions

### Suppression : INTERDITE en physique

```python
# ❌ NE PAS FAIRE
affaire.delete()

# ✓ FAIRE
affaire.is_deleted = True
affaire.archived_at = timezone.now()
affaire.archived_by = request.user
affaire.save()
```

### Code style

- Imports ordonnés : stdlib → tiers → local
- Type hints sur signatures publiques
- Docstrings : but du code, pas redite du nom
- Commentaires en français pour les choix techniques non-évidents

### Templates

- RTL obligatoire (`dir="rtl"` sur `<html>`)
- Bilingue : libellés en arabe, attributs HTML en anglais
- Bootstrap 5 RTL CDN
- Police principale : **Cairo** (UI) + **Amiri** (PDF)

### Commits

- Convention : `feat:` / `fix:` / `refactor:` / `docs:` / `chore:`
- Messages courts (≤72 chars) + corps détaillé si nécessaire
- Co-author Claude si IA assistée

### Migrations

- Une migration par changement logique
- Nommer explicitement : `0030_codecategorieaffaire_hierarchie.py`
- Toujours tester avec `--dry-run` puis appliquer

### Sécurité

- **Jamais** committer `.env`, `release.jks`, `signing.properties`, `google-services.json`
- Vérifier avant chaque push avec `git status --short | grep -E "\.env|jks|properties"`
- Validators arabes sur les champs texte (`arabic_text_validator`, `arabic_name_validator`)

---

## 16. Historique & roadmap

### Phases livrées (chronologique)

| Phase | Date | Livraison |
|-------|------|-----------|
| 1 — API REST | mai 2026 | DRF + JWT + ViewSets auto pour tous les modèles |
| 2 — POC offline | mai 2026 | `client_poc/` Python CLI avec SQLite local |
| 3 — Desktop wrapper | juin 2026 | PyWebView + PyInstaller + DMG drag-and-drop |
| 4 — PWA + APK | juin 2026 | Service worker + Capacitor 6 + APK signée |
| 5 — Files sync | juin 2026 | Binaires PieceJointe pull/push avec ledger |
| 6 — Fix login local | juin 2026 | Setup wizard + auth shadow user |
| 7 — Intégration mahakim.ma | juin 2026 | Cascade CA → PI + 691 codes XLSX + page CRUD |
| 8 — Anti-doublon | juin 2026 | Endpoint check + UX warning sur blur |

### Backlog

- [ ] **Build Windows .exe** (spec prêt — manque machine Windows)
- [ ] **iOS .ipa** via Capacitor (config Capacitor existe)
- [ ] **Notarisation macOS** pour distribution hors Mac App Store
- [ ] **Rotation keystore Android** pour publication Play Store
- [ ] **Tests unitaires** : couverture estimée 0% → cible 50% pour les services critiques
- [ ] **Dashboard décisionnel** : KPIs (taux victoire, durée moyenne, etc.)
- [ ] **Recherche sémantique des décisions** via embeddings.py
- [ ] **Module facturation** avec calcul TVA marocaine
- [ ] **Module gestion des audiences en vidéo** (lien Zoom/Meet)

### Dépendances critiques à surveiller

- Django 5.1.x → 5.2 (LTS) lorsque disponible
- Capacitor 6 → 7 dès passage à JDK 21 obligatoire
- Python 3.13 → 3.14 (compatibilité reportlab à vérifier)

---

## Annexe A — Variables d'environnement

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `SECRET_KEY` | ✓ | Django secret (généré au 1er run en mode desktop) |
| `DATABASE_URL` | ✓ (web) | `mysql://user:pass@host:port/db` |
| `DEBUG` | ✓ | `True` en dev, `False` en prod |
| `PORTAIL_COOKIE_SECRET` | ✓ | Cookies signés du portail client |
| `TWILIO_SID` / `TWILIO_TOKEN` / `TWILIO_WHATSAPP_FROM` | optionnel | Notifications WhatsApp |
| `DESKTOP_MODE` | auto | Mis à `True` par `settings_desktop.py` |
| `DESKTOP_REMOTE_API` | desktop | URL du serveur central (ex: `https://avocat.example.com/api`) |
| `DESKTOP_DATA_DIR` | auto | Dossier de stockage SQLite + secrets locaux |
| `DJANGO_READ_DOT_ENV_FILE` | desktop | `False` pour ignorer `.env` |

---

## Annexe B — Commandes Django utiles

```bash
# Référentiels juridiques
python manage.py import_juridictions_xlsx
python manage.py import_codes_affaires_xlsx
python manage.py import_categories_ca

# Maintenance
python manage.py shell_plus      # django-extensions : shell IPython avec auto-import
python manage.py show_urls       # lister toutes les routes
python manage.py runserver_plus  # serveur avec werkzeug debugger

# Sync
python manage.py sync_mahakim --since 2026-01-01
python manage.py collectstatic --noinput
```

---

## Annexe C — Comment poursuivre avec Claude Code

1. **Sur un nouvel ordinateur**, après `git clone` :
   ```bash
   cd avocat_yassine
   # Lire le projet
   claude
   > /init   # ou poser directement la question
   > "Lis PROJECT.md et CLAUDE.md, puis dis-moi par où commencer"
   ```

2. **Claude lira automatiquement** :
   - `CLAUDE.md` (instructions globales utilisateur, conventions stack/UX)
   - `PROJECT.md` (ce fichier)
   - La structure via `ls` et `git log`

3. **Tâches typiques** :
   - "Ajoute un nouveau champ X au modèle Affaire" → Claude créera migration + form + template
   - "Refonds la page /audiences/ pour matcher /ref/codes-affaire/" → Claude reproduira le patron AJAX
   - "Build l'APK avec une nouvelle URL de serveur" → Claude modifiera `mobile/www/index.html` + `npx cap sync`

4. **Bonnes questions à poser à Claude au démarrage** :
   - "Quel est l'état actuel des branches et des PR ?"
   - "Lance le serveur et fais un smoke test des endpoints critiques"
   - "Liste les migrations non appliquées"

---

**Dernière mise à jour** : juin 2026
**Mainteneur** : Yassine Elmoudene (kmtservicesprive@gmail.com)
**License** : interne — Province de Chtouka Aït Baha
