"""Recalcule les embeddings de toutes les DecisionAnalysis pour la recherche sémantique."""
from django.core.management.base import BaseCommand

from avocat_app.services.embeddings import reindex_all_decisions


class Command(BaseCommand):
    help = "Indexe (ou ré-indexe) les embeddings des analyses de décisions."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Indexation en cours…"))
        result = reindex_all_decisions()
        self.stdout.write(self.style.SUCCESS(
            f"Indexés: {result['indexed']} | Sautés (vides): {result['skipped']}"
        ))
