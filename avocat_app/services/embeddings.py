"""Embeddings sémantiques pour la recherche jurisprudentielle.

Stratégie :
- Si `VOYAGE_API_KEY` est configurée → embeddings réels via Voyage AI
  (modèle voyage-3, recommandé par Anthropic pour l'usage avec Claude).
- Sinon → fallback déterministe basé sur hashing de tokens (bag-of-words
  haché normalisé L2). Pas d'API, fonctionne en dev, utile pour la
  recherche par mots-clés sémantiquement proches.

Le résultat est toujours `list[float]` stockable en JSONField.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Iterable, List, Optional, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_DIM = 512
VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_DEFAULT_MODEL = "voyage-3"


# ---------- Fallback hash-based ----------

_ARABIC_DIACRITICS = re.compile(r"[ً-ٰٟ]")
_TOKEN_RE = re.compile(r"[\w؀-ۿ]+", re.UNICODE)


def _normalize(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    # Retirer les harakat arabes
    t = _ARABIC_DIACRITICS.sub("", t)
    # Normaliser certaines variantes
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
    return t


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(_normalize(text))


def _hash_to_bucket(token: str, dim: int) -> int:
    h = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
    return h % dim


def _hash_embedding(text: str, dim: int = DEFAULT_DIM) -> List[float]:
    """Bag-of-words haché, normalisé L2."""
    vec = [0.0] * dim
    for tok in _tokenize(text):
        if len(tok) < 2:
            continue
        vec[_hash_to_bucket(tok, dim)] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


# ---------- Voyage AI ----------

def _voyage_embedding(text: str, *, model: str = VOYAGE_DEFAULT_MODEL) -> Optional[List[float]]:
    api_key = getattr(settings, "VOYAGE_API_KEY", "") or ""
    if not api_key:
        return None
    try:
        r = requests.post(
            VOYAGE_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json={"input": text[:8000], "model": model},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        emb = data.get("data", [{}])[0].get("embedding")
        if isinstance(emb, list):
            return [float(x) for x in emb]
    except Exception:
        logger.exception("Voyage AI embedding failed")
    return None


# ---------- Public API ----------

def embed_text(text: str, *, prefer_real: bool = True) -> Tuple[List[float], str]:
    """Retourne (vecteur, nom_du_modèle).

    En cas d'échec de l'API réelle, fallback sur le hash deterministe.
    """
    if prefer_real:
        v = _voyage_embedding(text or "")
        if v is not None:
            return v, VOYAGE_DEFAULT_MODEL
    return _hash_embedding(text or ""), f"hash-bow-{DEFAULT_DIM}"


def cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    """Similarité cosinus entre deux vecteurs (longueur identique)."""
    a = list(a)
    b = list(b)
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n))) or 1.0
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n))) or 1.0
    return dot / (na * nb)


def search_decisions(query: str, *, top_k: int = 10):
    """Recherche les DecisionAnalysis les plus similaires à la requête.
    Retourne [(analysis, score), ...] trié décroissant.
    """
    from ..models import DecisionAnalysis

    if not query or not query.strip():
        return []

    q_vec, _model = embed_text(query)
    analyses = (
        DecisionAnalysis.objects
        .select_related("decision", "decision__affaire")
        .exclude(embedding__isnull=True)
    )
    scored = []
    for a in analyses:
        if not a.embedding:
            continue
        # Compatibilité dimension: comparer uniquement si dim match
        if len(a.embedding) != len(q_vec):
            continue
        score = cosine_similarity(q_vec, a.embedding)
        if score > 0:
            scored.append((a, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def reindex_all_decisions() -> dict:
    """Recalcule l'embedding de toutes les DecisionAnalysis ayant du contenu."""
    from ..models import DecisionAnalysis
    indexed = 0
    skipped = 0
    for a in DecisionAnalysis.objects.all().iterator():
        text_parts = [
            a.resume_ar or "",
            a.resume_fr or "",
            a.decision_essentielle or "",
            a.source_text or "",
        ]
        if a.motifs:
            for m in a.motifs:
                if isinstance(m, dict):
                    text_parts.append(m.get("titre", "") or "")
                    text_parts.append(m.get("contenu", "") or "")
        text = "\n".join(p for p in text_parts if p).strip()
        if not text:
            skipped += 1
            continue
        vec, model = embed_text(text)
        a.embedding = vec
        a.embedding_model = model
        a.save(update_fields=["embedding", "embedding_model"])
        indexed += 1
    return {"indexed": indexed, "skipped": skipped}
