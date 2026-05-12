"""Client IA Claude (Anthropic) pour l'analyse de décisions juridiques.

Conçu pour ne JAMAIS faire planter l'app si:
- la clé `ANTHROPIC_API_KEY` est absente → mode dry-run avec résumé factice;
- la lib `anthropic` (SDK) est absente → utilise l'API HTTP directe via `requests`;
- la requête échoue → renvoie un dict avec error_message rempli.

Le prompt force un JSON structuré pour une extraction fiable.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_INPUT_CHARS = 80000  # ~ tokens; on tronque proprement si le texte est trop long


@dataclass
class AnalysisResult:
    ok: bool
    is_dry_run: bool = False
    model_used: str = ""
    resume_ar: str = ""
    resume_fr: str = ""
    decision_essentielle: str = ""
    parties_extraites: list = field(default_factory=list)
    motifs: list = field(default_factory=list)
    delai_appel_jours: Optional[int] = None
    dates_importantes: list = field(default_factory=list)
    raw_response: str = ""
    error_message: str = ""


# --- PDF extraction ---------------------------------------------------------

def extract_text_from_pdf(file_path_or_obj) -> str:
    """Extrait le texte brut d'un PDF. Retourne '' en cas d'erreur."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return ""
    try:
        reader = PdfReader(file_path_or_obj)
        pages_text = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
                pages_text.append(t)
            except Exception:
                continue
        return "\n\n".join(pages_text).strip()
    except Exception as e:
        logger.exception("PDF extraction failed: %s", e)
        return ""


# --- Prompt -----------------------------------------------------------------

ANALYSIS_PROMPT = """أنت مساعد قانوني خبير في القانون المغربي. حلّل نص الحكم/القرار التالي وأعد JSON صالحًا فقط (بدون أي نص قبل أو بعد) بهذا المخطط:

{
  "resume_ar": "ملخص في 4-6 جمل بالعربية",
  "resume_fr": "Résumé en 4-6 phrases en français",
  "decision_essentielle": "المنطوق الأساسي للحكم باللغة العربية",
  "parties_extraites": [
    {"nom": "...", "role": "مدعٍ|مدعى عليه|مستأنف|مستأنف عليه|متّهم|..."}
  ],
  "motifs": [
    {"titre": "...", "contenu": "..."}
  ],
  "delai_appel_jours": <integer | null>,
  "dates_importantes": [
    {"label": "تاريخ النطق|تاريخ التبليغ|...", "date_iso": "YYYY-MM-DD"}
  ]
}

قواعد:
- إذا لم تجد المعلومة، استعمل null أو قائمة فارغة.
- التاريخ بصيغة ISO يجب أن يكون YYYY-MM-DD فقط.
- لا تخمن المعلومات؛ استخرج فقط مما هو موجود في النص.
- التزم الصرامة في صياغة JSON: استخدم \" للسلاسل، لا فاصلة بعد آخر عنصر.

النص:
---
{TEXT}
---"""


# --- Public API -------------------------------------------------------------

def _truncate(text: str) -> str:
    if not text:
        return ""
    if len(text) <= MAX_INPUT_CHARS:
        return text
    return text[: MAX_INPUT_CHARS] + "\n\n[...النص مقتطع لتجاوز الحد الأقصى...]"


def _dry_run_result(text: str) -> AnalysisResult:
    sample = (text or "").strip()
    preview = sample[:200] + ("…" if len(sample) > 200 else "")
    return AnalysisResult(
        ok=True,
        is_dry_run=True,
        model_used="dry-run",
        resume_ar="[محاكاة] لم يتم تكوين مفتاح Anthropic بعد. هذا ملخص توضيحي مبني على بداية النص: "
                  + (preview or "لا يوجد نص."),
        resume_fr="[Dry-run] Configurez ANTHROPIC_API_KEY pour l'analyse réelle. Aperçu du texte source: "
                  + (preview or "Pas de texte."),
        decision_essentielle="[محاكاة] هنا سيظهر منطوق الحكم الذي استخرجه الذكاء الاصطناعي.",
        parties_extraites=[],
        motifs=[],
        delai_appel_jours=None,
        dates_importantes=[],
        raw_response="dry_run",
    )


def _parse_json_loose(text: str) -> Optional[dict]:
    """Tente de parser le JSON, avec tolérance pour les blocs markdown ou texte autour."""
    if not text:
        return None
    # Enlever les balises markdown ```json ... ```
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    # Trouver la 1ère { et la dernière } pour isoler le bloc JSON
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def analyze_decision_text(text: str, *, model: Optional[str] = None) -> AnalysisResult:
    """Appelle Claude pour analyser le texte d'une décision juridique."""
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    dry_run = bool(getattr(settings, "ANTHROPIC_DRY_RUN", False))
    chosen_model = model or getattr(settings, "ANTHROPIC_MODEL", DEFAULT_MODEL)

    if not text or not text.strip():
        return AnalysisResult(ok=False, error_message="النص فارغ — لا يمكن التحليل.")

    if dry_run or not api_key:
        return _dry_run_result(text)

    truncated = _truncate(text)
    prompt = ANALYSIS_PROMPT.replace("{TEXT}", truncated)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    payload = {
        "model": chosen_model,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        r = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
    except requests.HTTPError as e:
        logger.exception("Anthropic HTTP error")
        body = ""
        try:
            body = e.response.text[:500] if e.response is not None else ""
        except Exception:
            pass
        return AnalysisResult(ok=False, model_used=chosen_model,
                              error_message=f"HTTP {e.response.status_code if e.response else '?'}: {body}",
                              raw_response=body)
    except Exception as e:
        logger.exception("Anthropic call failed")
        return AnalysisResult(ok=False, model_used=chosen_model, error_message=str(e))

    # Extraire le texte de la réponse Claude
    try:
        content_blocks = data.get("content", [])
        raw_text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
    except Exception:
        raw_text = json.dumps(data)[:5000]

    parsed = _parse_json_loose(raw_text)
    if not parsed:
        return AnalysisResult(
            ok=False, model_used=chosen_model,
            error_message="تعذّر استخراج JSON من الاستجابة.",
            raw_response=raw_text[:5000],
        )

    def _str(v): return v if isinstance(v, str) else ""
    def _list(v): return v if isinstance(v, list) else []
    delai = parsed.get("delai_appel_jours")
    try:
        delai = int(delai) if delai is not None else None
    except (TypeError, ValueError):
        delai = None

    return AnalysisResult(
        ok=True,
        model_used=chosen_model,
        resume_ar=_str(parsed.get("resume_ar")),
        resume_fr=_str(parsed.get("resume_fr")),
        decision_essentielle=_str(parsed.get("decision_essentielle")),
        parties_extraites=_list(parsed.get("parties_extraites")),
        motifs=_list(parsed.get("motifs")),
        delai_appel_jours=delai,
        dates_importantes=_list(parsed.get("dates_importantes")),
        raw_response=raw_text[:8000],
    )


def analyze_decision(decision, *, source_text: Optional[str] = None,
                     piece_jointe=None) -> "DecisionAnalysis":
    """Orchestrateur de plus haut niveau:
    - Reçoit une Decision
    - Choisit la source: source_text > piece_jointe (PDF) > rien
    - Lance l'analyse et persiste DecisionAnalysis
    """
    from django.utils import timezone
    from ..models import DecisionAnalysis

    text = (source_text or "").strip()
    if not text and piece_jointe and getattr(piece_jointe, "fichier", None):
        try:
            text = extract_text_from_pdf(piece_jointe.fichier.path)
        except Exception:
            text = ""

    if not text and getattr(decision, "resumé", None):
        text = decision.resumé or ""

    result = analyze_decision_text(text)

    analysis, _ = DecisionAnalysis.objects.update_or_create(
        decision=decision,
        defaults={
            "source_text": text[:50000] if text else "",
            "resume_ar": result.resume_ar or "",
            "resume_fr": result.resume_fr or "",
            "decision_essentielle": result.decision_essentielle or "",
            "parties_extraites": result.parties_extraites or [],
            "motifs": result.motifs or [],
            "delai_appel_jours": result.delai_appel_jours,
            "dates_importantes": result.dates_importantes or [],
            "raw_response": result.raw_response or "",
            "model_used": result.model_used or "",
            "is_dry_run": result.is_dry_run,
            "error_message": result.error_message or "",
            "generated_at": timezone.now() if result.ok else None,
        },
    )

    # Mettre à jour l'embedding pour la recherche sémantique
    if result.ok:
        try:
            from .embeddings import embed_text
            text_parts = [
                result.resume_ar, result.resume_fr, result.decision_essentielle, text,
            ]
            for m in (result.motifs or []):
                if isinstance(m, dict):
                    text_parts.append(m.get("titre", ""))
                    text_parts.append(m.get("contenu", ""))
            joined = "\n".join(p for p in text_parts if p).strip()
            if joined:
                vec, model = embed_text(joined)
                analysis.embedding = vec
                analysis.embedding_model = model
                analysis.save(update_fields=["embedding", "embedding_model"])
        except Exception:
            logger.exception("Embedding update failed")

    return analysis
