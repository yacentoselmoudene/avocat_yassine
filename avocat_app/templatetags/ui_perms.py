"""Template tags pour les permissions UI (onglets, boutons).

Usage :
    {% load ui_perms %}
    {% if user|can_see:"ui_tab_affaires" %}
        <a href="...">Affaires</a>
    {% endif %}

Les superusers et users non-authentifiés sont gérés ainsi :
- Superuser : tout autorisé
- Anonyme : rien autorisé
- Standard : autorisé si la permission UI lui est attachée (ou via un groupe).
"""
from django import template

register = template.Library()


@register.filter(name="can_see")
def can_see(user, codename: str) -> bool:
    """Vérifie une permission UI (sans préfixe app).

    Politique :
    - Anonyme : refusé
    - Superuser : accordé
    - Sinon : si l'user a la perm explicite → accordé ;
              sinon, si l'user n'a AUCUNE perm UI configurée → accordé (défaut)
    Ainsi un user fraîchement créé voit toute l'app jusqu'à ce qu'un admin
    lui définisse des permissions UI restrictives.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.has_perm(f"ui.{codename}"):
        return True
    if not hasattr(user, "_has_any_ui_perm_cache"):
        user._has_any_ui_perm_cache = (
            user.user_permissions.filter(codename__startswith="ui_").exists()
            or user.groups.filter(permissions__codename__startswith="ui_").exists()
        )
    return not user._has_any_ui_perm_cache
