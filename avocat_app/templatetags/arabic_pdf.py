"""Filtre Django pour shaper + bidi le texte arabe avant rendu PDF.

xhtml2pdf ne fait pas de shaping arabe ni de bidi natif. Ce filtre transforme
les caractères arabes en leurs formes contextuelles (initiale/médiane/finale/
isolée) via arabic_reshaper, puis inverse l'ordre visuel via python-bidi.

Usage dans le template PDF :
    {% load arabic_pdf %}
    {{ ma_chaine|ar }}
"""
from __future__ import annotations

import re

import arabic_reshaper
from bidi.algorithm import get_display
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_ARABIC_RANGE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")


def _has_arabic(s: str) -> bool:
    return bool(_ARABIC_RANGE.search(s))


@register.filter(name="ar")
def ar(value):
    """Shape + bidi un texte arabe pour rendu correct dans xhtml2pdf.

    - Préserve les valeurs non-arabes (chiffres, ponctuation, latin) sans toucher.
    - Si la chaîne contient de l'arabe, applique reshape + get_display.
    - Sûr à passer à n'importe quelle valeur (None, int, str).
    """
    if value is None:
        return ""
    s = str(value)
    if not s.strip():
        return s
    if not _has_arabic(s):
        return s
    try:
        reshaped = arabic_reshaper.reshape(s)
        display = get_display(reshaped)
        return mark_safe(display)
    except Exception:
        return s


@register.filter(name="ar_label")
def ar_label(value):
    """Variante de |ar pour les libellés courts (titres de colonnes, etc).
    Identique pour l'instant — on garde un filtre dédié pour évolution future.
    """
    return ar(value)
