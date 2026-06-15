"""Central registry of tables exposed via the sync API.

role:
  - "core"   : bidirectional sync (pull AND push from clients)
  - "config" : pull-only on clients (reference data managed server-side)
  - "server" : never synced (audit, integrations, server-internal)
"""
from avocat_app import models as M

CORE_TABLES = [
    ("affaire",         M.Affaire),
    ("partie",          M.Partie),
    ("affaire_partie",  M.AffairePartie),
    ("affaire_avocat",  M.AffaireAvocat),
    ("audience",        M.Audience),
    ("decision",        M.Decision),
    ("mesure",          M.Mesure),
    ("expertise",       M.Expertise),
    ("execution",       M.Execution),
    ("voie_recours",    M.VoieDeRecours),
    ("avertissement",   M.Avertissement),
    ("notification",    M.Notification),
    ("tache",           M.Tache),
    ("alerte",          M.Alerte),
    ("depense",         M.Depense),
    ("recette",         M.Recette),
    ("piece_jointe",    M.PieceJointe),
]

CONFIG_TABLES = [
    ("type_affaire",            M.TypeAffaire),
    ("statut_affaire",          M.StatutAffaire),
    ("type_audience",           M.TypeAudience),
    ("resultat_audience",       M.ResultatAudience),
    ("type_recours",            M.TypeRecours),
    ("statut_recours",          M.StatutRecours),
    ("type_execution",          M.TypeExecution),
    ("statut_execution",        M.StatutExecution),
    ("type_mesure",             M.TypeMesure),
    ("statut_mesure",           M.StatutMesure),
    ("type_avertissement",      M.TypeAvertissement),
    ("type_alerte",             M.TypeAlerte),
    ("type_depense",            M.TypeDepense),
    ("type_recette",            M.TypeRecette),
    ("statut_tache",            M.StatutTache),
    ("type_juridiction",        M.TypeJuridiction),
    ("degre_juridiction",       M.DegreJuridiction),
    ("juridiction",             M.Juridiction),
    ("code_categorie_affaire",  M.CodeCategorieAffaire),
    ("barreau",                 M.Barreau),
    ("avocat",                  M.Avocat),
    ("expert",                  M.Expert),
    ("role_utilisateur",        M.RoleUtilisateur),
    ("document_requirement",    M.DocumentRequirement),
    ("cabinet_params",          M.CabinetParams),
]

SYNC_TABLES = CORE_TABLES + CONFIG_TABLES

_MODEL_BY_NAME = {name: model for name, model in SYNC_TABLES}
_ROLE_BY_NAME = {**{n: "core" for n, _ in CORE_TABLES},
                 **{n: "config" for n, _ in CONFIG_TABLES}}


def get_model(name: str):
    return _MODEL_BY_NAME.get(name)


def get_role(name: str) -> str | None:
    return _ROLE_BY_NAME.get(name)


def is_pushable(name: str) -> bool:
    """Only core tables accept POST /sync/push from clients."""
    return _ROLE_BY_NAME.get(name) == "core"


def list_table_names(role: str | None = None) -> list[str]:
    if role is None:
        return list(_MODEL_BY_NAME.keys())
    return [n for n, r in _ROLE_BY_NAME.items() if r == role]
