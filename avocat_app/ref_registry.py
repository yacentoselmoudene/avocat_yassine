# avocat_app/ref_registry.py
from .models import (TypeDepense, TypeRecette, RoleUtilisateur, StatutTache, TypeAlerte, StatutExecution, StatutRecours,
                     StatutAffaire, TypeAudience, TypeRecours, TypeExecution, ResultatAudience, DegreJuridiction,
                     TypeJuridiction, TypeAffaire)

REF_REGISTRY = {
    # refname : config
    "typedepenses": {
        "model": TypeDepense,
        "title": "أنواع المصاريف",
        "extra_fields": [],                     # seulement libelle
        "perm_prefix": "typedepense",
    },
    "typerecettes": {
        "model": TypeRecette,
        "title": "أنواع المداخيل",
        "extra_fields": [],
        "perm_prefix": "typerecette",
    },
    "roles": {
        "model": RoleUtilisateur,
        "title": "أدوار المستخدمين",
        "extra_fields": [],
        "perm_prefix": "roleutilisateur",
    },
    "statuttache": {
        "model": StatutTache,
        "title": "حالات المهام",
        "extra_fields": [],
        "perm_prefix": "statuttache",
    },
    "typealerte": {
        "model": TypeAlerte,
        "title": "أنواع التنبيهات",
        "extra_fields": [],        # ← exemple: champ additionnel
        "perm_prefix": "typealerte",
        "labels": {"delai_jours": "أجل (أيام)"},
    },
    "degrejuridiction": {
        "model": DegreJuridiction,
        "title": "درجات المحاكم",
        "extra_fields": [],      # ← exemple: deux champs en plus
        "perm_prefix": "degrejuridiction",
        "labels": {"code": "رمز", "ordre": "ترتيب"},
    },
    "typejuridiction": {
        "model": TypeJuridiction,
        "title": "أنواع المحاكم",
        "extra_fields": [],
        "perm_prefix": "typejuridiction",
        "labels": {"code": "رمز"},
    },
    "typeaffaire": {
        "model": TypeAffaire,
        "title": "أنواع القضايا",
        "extra_fields": ["code"],
        "perm_prefix": "typeaffaire",
        "labels": {"code": "رمز"},
    },
    "statutexecution": {
        "model": StatutExecution,
        "title": "حالات التنفيذ",
        "extra_fields": [],
        "perm_prefix": "statutexecution",
    },
    "statutrecours": {
        "model": StatutRecours,
        "title": "حالات الطعون",
        "extra_fields": [],
        "perm_prefix": "statutrecours",
    },
    "statutaffaire": {
        "model": StatutAffaire,
        "title": "حالات القضايا",
        "extra_fields": [],
        "perm_prefix": "statutaffaire",
    },
    "typeaudience": {
        "model": TypeAudience,
        "title": "أنواع الجلسات",
        "extra_fields": [],
        "perm_prefix": "typeaudience",
    },
    "typerecours": {
        "model": TypeRecours,
        "title": "أنواع الطعون",
        "extra_fields": [],
        "perm_prefix": "typerecours",
    },
    "typeexecution": {
        "model": TypeExecution,
        "title": "أنواع التنفيذ",
        "extra_fields": [],
        "perm_prefix": "typeexecution",
    },
    "resultataudience": {
        "model": ResultatAudience,
        "title": "نتائج الجلسات",
        "extra_fields": [],
        "perm_prefix": "resultataudience",
    },


}
# Vous pouvez ajouter d'autres références ici en suivant le même format.
