# avocat_app/management/commands/sync_mahakim.py
"""
Management command pour synchroniser les affaires avec mahakim.ma.

Usage:
    python manage.py sync_mahakim                  # Toutes les affaires avec référence structurée
    python manage.py sync_mahakim --limit=5        # Limiter à 5 affaires
    python manage.py sync_mahakim --affaire=UUID   # Une seule affaire
    python manage.py sync_mahakim --no-headless    # Mode visible (debug)
"""
import logging

from django.core.management.base import BaseCommand, CommandError

from avocat_app.models import Affaire, MahakimSyncResult
from avocat_app.services.mahakim_scraper import MahakimScraper

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "مزامنة القضايا مع بوابة محاكم.ما (mahakim.ma)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=0,
            help="عدد القضايا الأقصى للمزامنة (0 = بدون حد)",
        )
        parser.add_argument(
            "--affaire", type=str, default=None,
            help="UUID قضية محددة للمزامنة",
        )
        parser.add_argument(
            "--no-headless", action="store_true", default=False,
            help="تشغيل المتصفح بشكل مرئي (للتشخيص)",
        )
        parser.add_argument(
            "--timeout", type=int, default=30,
            help="مهلة الانتظار بالثواني",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        affaire_pk = options["affaire"]
        headless = not options["no_headless"]
        timeout = options["timeout"]

        # Construire le queryset
        if affaire_pk:
            try:
                affaires = Affaire.objects.filter(pk=affaire_pk)
                if not affaires.exists():
                    raise CommandError(f"القضية {affaire_pk} غير موجودة")
            except Exception as e:
                raise CommandError(str(e))
        else:
            # Seulement les affaires avec référence structurée
            affaires = Affaire.objects.filter(
                numero_dossier__isnull=False,
                code_categorie__isnull=False,
                annee_dossier__isnull=False,
            ).exclude(
                numero_dossier=""
            ).exclude(
                annee_dossier=""
            ).select_related("code_categorie", "juridiction")

        if limit > 0:
            affaires = affaires[:limit]

        total = affaires.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("لا توجد قضايا للمزامنة (تأكد من وجود رقم الملف وصنف القضية والسنة)"))
            return

        self.stdout.write(f"بدء مزامنة {total} قضية(قضايا) مع محاكم.ما ...")

        success_count = 0
        error_count = 0

        with MahakimScraper(headless=headless, timeout=timeout) as scraper:
            for i, affaire in enumerate(affaires, 1):
                self.stdout.write(f"\n[{i}/{total}] {affaire.reference_interne} — "
                                  f"{affaire.numero_dossier}/{affaire.code_categorie.code}/{affaire.annee_dossier}")

                # Déterminer le type de juridiction
                type_juridiction = None
                if hasattr(affaire.juridiction, 'type') and affaire.juridiction.type:
                    type_juridiction = str(affaire.juridiction.type)

                result = scraper.scrape_affaire(
                    numero=affaire.numero_dossier,
                    code_categorie=affaire.code_categorie.code,
                    annee=affaire.annee_dossier,
                    type_juridiction=type_juridiction,
                )

                # Sauvegarder le résultat
                sync_obj = MahakimSyncResult.objects.create(
                    affaire=affaire,
                    statut_mahakim=result.get("statut_mahakim"),
                    prochaine_audience=result.get("prochaine_audience"),
                    juge=result.get("juge"),
                    observations=result.get("observations"),
                    raw_html=result.get("raw_html", "")[:50000],  # Limiter la taille
                    success=result.get("success", False),
                    error_message=result.get("error_message"),
                )

                if result["success"]:
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ نجاح — الحالة: {result.get('statut_mahakim', '—')}"
                    ))
                    if result.get("prochaine_audience"):
                        self.stdout.write(f"    الجلسة القادمة: {result['prochaine_audience']}")
                    if result.get("juge"):
                        self.stdout.write(f"    القاضي: {result['juge']}")
                else:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(
                        f"  ✗ فشل — {result.get('error_message', 'خطأ غير معروف')}"
                    ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"اكتملت المزامنة: {success_count} نجاح / {error_count} فشل / {total} إجمالي"))
