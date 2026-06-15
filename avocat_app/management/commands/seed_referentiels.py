"""Dump et load des tables de référentiel (paramètres) en JSON.

Permet de :
  1. Exporter les paramètres d'un serveur (dev/staging) vers un fichier JSON
  2. Importer ce JSON sur un nouveau serveur (déploiement / restauration)

L'import est **idempotent** : update_or_create par clé naturelle (libelle / code).
Utilise les tables listées dans REF_REGISTRY + quelques entités supplémentaires.

USAGE :

    # Export (par défaut → seeds/referentiels.json)
    python manage.py seed_referentiels --dump
    python manage.py seed_referentiels --dump --output backup.json

    # Import
    python manage.py seed_referentiels --load
    python manage.py seed_referentiels --load --input backup.json

    # Limiter à certaines tables
    python manage.py seed_referentiels --dump --only typeaffaire,statutaffaire
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


# === Tables à seeder ===
# Format : { "slug": (Model, [champs_à_exporter], "clé_naturelle") }
# La clé naturelle sert à update_or_create lors du load.
SEED_TABLES: dict[str, tuple[str, list[str], str]] = {
    # Référentiels simples libellé
    "typedepense":       ("avocat_app.TypeDepense",        ["libelle", "libelle_fr"],                              "libelle"),
    "typerecette":       ("avocat_app.TypeRecette",        ["libelle", "libelle_fr"],                              "libelle"),
    "roleutilisateur":   ("avocat_app.RoleUtilisateur",    ["libelle", "libelle_fr"],                              "libelle"),
    "statuttache":       ("avocat_app.StatutTache",        ["libelle", "libelle_fr"],                              "libelle"),
    "typealerte":        ("avocat_app.TypeAlerte",         ["libelle", "libelle_fr"],                              "libelle"),
    "statutexecution":   ("avocat_app.StatutExecution",    ["libelle", "libelle_fr"],                              "libelle"),
    "statutrecours":     ("avocat_app.StatutRecours",      ["libelle", "libelle_fr"],                              "libelle"),
    "statutmesure":      ("avocat_app.StatutMesure",       ["libelle", "libelle_fr"],                              "libelle"),
    "statutaffaire":     ("avocat_app.StatutAffaire",      ["libelle", "libelle_fr"],                              "libelle"),
    "typeaudience":      ("avocat_app.TypeAudience",       ["libelle", "libelle_fr"],                              "libelle"),
    "resultataudience":  ("avocat_app.ResultatAudience",   ["libelle", "libelle_fr"],                              "libelle"),
    "typemesure":        ("avocat_app.TypeMesure",         ["libelle", "libelle_fr"],                              "libelle"),
    "degrejuridiction":  ("avocat_app.DegreJuridiction",   ["libelle", "libelle_fr"],                              "libelle"),

    # Avec champs supplémentaires
    "typejuridiction":   ("avocat_app.TypeJuridiction",    ["libelle", "libelle_fr", "code_type", "niveau", "description"], "libelle"),
    "typeaffaire":       ("avocat_app.TypeAffaire",        ["libelle", "libelle_fr", "code"],                      "libelle"),
    "typerecours":       ("avocat_app.TypeRecours",        ["libelle", "libelle_fr", "delai_legal_jours", "domaine"], "libelle"),
    "typeexecution":     ("avocat_app.TypeExecution",      ["libelle", "libelle_fr"],                              "libelle"),
    "typeavertissement": ("avocat_app.TypeAvertissement",  ["libelle", "libelle_fr", "delai_legal_jours", "domaine", "base_legale"], "libelle"),

    # Référentiels métier
    "barreau":           ("avocat_app.Barreau",            ["nom"],                                                "nom"),
    "codecategorieaffaire": ("avocat_app.CodeCategorieAffaire",
                            ["code", "libelle", "domaine", "niveau", "code_type", "type_libelle", "sous_type", "categorie_globale"],
                            "code"),
    "juridiction":       ("avocat_app.Juridiction",
                            ["code", "nomtribunal_fr", "nomtribunal_ar", "adressetribunal_fr", "adressetribunal_ar",
                             "villetribunal_fr", "villetribunal_ar", "telephonetribunal",
                             "type", "TribunalParent", "id_mahakim", "latitude", "longitude"],
                            "code"),
}


def _field_value_for_export(obj, field_name: str) -> Any:
    """Sérialise une valeur du modèle vers JSON-friendly."""
    value = getattr(obj, field_name, None)
    if value is None:
        return None
    # FK → on dump la clé naturelle de l'objet pointé si disponible
    field = obj._meta.get_field(field_name)
    if field.is_relation and field.many_to_one:
        related = value
        # Convention : clé naturelle = code, libelle ou nom
        for candidate in ("code", "libelle", "nom"):
            if hasattr(related, candidate):
                v = getattr(related, candidate)
                if v:
                    return {"_ref": candidate, "value": str(v),
                            "model": f"{related._meta.app_label}.{related._meta.model_name}"}
        return {"_ref": "pk", "value": str(related.pk),
                "model": f"{related._meta.app_label}.{related._meta.model_name}"}
    # Decimal / date → str
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if not isinstance(value, (str, int, float, bool)):
        return str(value)
    return value


def _resolve_fk(model, payload: dict) -> Any:
    """Résout {_ref: 'code', value: 'X', model: 'app.M'} → instance ou None."""
    if not isinstance(payload, dict) or "_ref" not in payload:
        return payload
    ref_field = payload["_ref"]
    ref_value = payload["value"]
    target_model_label = payload.get("model")
    target_model = apps.get_model(target_model_label) if target_model_label else model
    try:
        return target_model.objects.get(**{ref_field: ref_value})
    except target_model.DoesNotExist:
        return None
    except target_model.MultipleObjectsReturned:
        return target_model.objects.filter(**{ref_field: ref_value}).first()


def _dump_table(slug: str, model_label: str, fields: list[str]) -> list[dict]:
    Model = apps.get_model(model_label)
    qs = Model.objects.all()
    if hasattr(Model, "is_deleted"):
        qs = qs.filter(is_deleted=False)
    rows = []
    for obj in qs:
        row = {}
        for f in fields:
            try:
                row[f] = _field_value_for_export(obj, f)
            except Exception:  # noqa: BLE001
                row[f] = None
        rows.append(row)
    return rows


def _load_table(slug: str, model_label: str, fields: list[str], natural_key: str,
                rows: list[dict], stdout) -> tuple[int, int, int]:
    """Insère ou met à jour les lignes. Retourne (created, updated, skipped)."""
    Model = apps.get_model(model_label)
    created = updated = skipped = 0
    for row in rows:
        key_value = row.get(natural_key)
        if not key_value:
            skipped += 1
            continue
        # Préparer les defaults : résoudre les FK
        defaults = {}
        for f, v in row.items():
            if f == natural_key:
                continue
            if isinstance(v, dict) and "_ref" in v:
                fk = _resolve_fk(Model, v)
                if fk is None:
                    # FK absente → on skip ce champ (sera NULL)
                    continue
                defaults[f] = fk
            else:
                defaults[f] = v
        try:
            _, was_created = Model.objects.update_or_create(
                **{natural_key: key_value},
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception as exc:  # noqa: BLE001
            stdout.write(f"    ⚠ skip {slug} {natural_key}={key_value} : {exc}")
            skipped += 1
    return created, updated, skipped


class Command(BaseCommand):
    help = "Dump/load des tables de référentiel (paramètres) en JSON, idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--dump", action="store_true", help="Exporter vers JSON")
        parser.add_argument("--load", action="store_true", help="Importer depuis JSON")
        parser.add_argument("--output", default=None, help="Fichier de sortie (par défaut seeds/referentiels.json)")
        parser.add_argument("--input",  default=None, help="Fichier d'entrée (par défaut seeds/referentiels.json)")
        parser.add_argument("--only", default=None,
                            help="Liste de slugs séparés par virgule (ex: typeaffaire,statutaffaire)")
        parser.add_argument("--exclude", default=None,
                            help="Liste de slugs à exclure")
        parser.add_argument("--dry-run", action="store_true",
                            help="Affiche sans écrire (pour load)")

    def handle(self, *args, **options):
        if not options["dump"] and not options["load"]:
            raise CommandError("Précise --dump ou --load.")

        only = set((options.get("only") or "").split(",")) - {""}
        exclude = set((options.get("exclude") or "").split(",")) - {""}
        tables = {
            slug: spec for slug, spec in SEED_TABLES.items()
            if (not only or slug in only) and slug not in exclude
        }
        if not tables:
            raise CommandError("Aucune table à traiter (vérifie --only/--exclude).")

        default_path = Path(settings.BASE_DIR) / "seeds" / "referentiels.json"

        if options["dump"]:
            path = Path(options["output"] or default_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "_meta": {
                    "generated_at": timezone.now().isoformat(),
                    "tables": list(tables.keys()),
                },
                "tables": {},
            }
            total = 0
            for slug, (model_label, fields, _key) in tables.items():
                rows = _dump_table(slug, model_label, fields)
                data["tables"][slug] = rows
                self.stdout.write(f"  ✓ {slug:25s} → {len(rows):4d} lignes")
                total += len(rows)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Export terminé : {total} lignes dans {path}"
            ))
            return

        # === LOAD ===
        path = Path(options["input"] or default_path)
        if not path.exists():
            raise CommandError(f"Fichier introuvable : {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if "tables" not in data:
            raise CommandError(f"Format JSON invalide (manque 'tables') : {path}")

        dry = options["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("[DRY-RUN] aucune écriture en base"))

        total_c = total_u = total_s = 0
        # Important : charger d'abord les tables sans FK (référentiels simples),
        # puis Juridiction (qui a une FK type) en dernier.
        load_order = [s for s in tables if s != "juridiction"] + (["juridiction"] if "juridiction" in tables else [])

        with transaction.atomic():
            for slug in load_order:
                model_label, fields, key = tables[slug]
                rows = data["tables"].get(slug, [])
                if not rows:
                    self.stdout.write(f"  · {slug:25s} : (vide)")
                    continue
                if dry:
                    self.stdout.write(f"  [DRY] {slug:25s} : {len(rows)} lignes")
                    continue
                c, u, s = _load_table(slug, model_label, fields, key, rows, self.stdout)
                total_c += c
                total_u += u
                total_s += s
                self.stdout.write(
                    f"  ✓ {slug:25s} : {c:4d} créés · {u:4d} màj · {s:4d} ignorés"
                )
            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Import terminé : {total_c} créés, {total_u} mis à jour, {total_s} ignorés."
        ))
