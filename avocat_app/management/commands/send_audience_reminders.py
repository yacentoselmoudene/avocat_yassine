"""Envoie les rappels d'audience J-1 par WhatsApp (Twilio).

À planifier dans cron (ex: tous les jours à 17:00):
    0 17 * * * /path/to/python manage.py send_audience_reminders

Options:
    --days N    Nombre de jours avant l'audience (défaut: 1)
    --dry-run   N'envoie rien, affiche seulement les destinataires.
    --audience UUID  Cible une seule audience par son ID.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from avocat_app.models import Audience, WhatsAppMessage
from avocat_app.services.twilio_client import send_audience_reminder


class Command(BaseCommand):
    help = "Envoie les rappels d'audience J-1 par WhatsApp via Twilio."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=1, help="Jours avant l'audience (défaut: 1)")
        parser.add_argument("--dry-run", action="store_true", help="Affiche seulement, n'envoie pas")
        parser.add_argument("--audience", type=str, default=None, help="UUID d'une audience spécifique")

    def handle(self, *args, **options):
        days_ahead = options["days"]
        dry_run = options["dry_run"]
        audience_id = options.get("audience")

        if audience_id:
            audiences = Audience.objects.filter(pk=audience_id).select_related("affaire", "affaire__juridiction")
        else:
            target_date = timezone.localdate() + timedelta(days=days_ahead)
            audiences = (
                Audience.objects.select_related("affaire", "affaire__juridiction", "type_audience")
                .filter(date_audience__date=target_date)
            )

        total = audiences.count()
        self.stdout.write(self.style.NOTICE(f"Audiences à traiter: {total}"))

        sent = 0
        failed = 0
        skipped_already = 0

        for aud in audiences:
            # Éviter les doublons: si on a déjà envoyé un rappel J-1 pour cette audience aujourd'hui
            if not audience_id:
                already = WhatsAppMessage.objects.filter(
                    audience=aud,
                    status__in=["sent", "delivered", "read", "dry_run"],
                    created_at__date=timezone.localdate(),
                ).exists()
                if already:
                    skipped_already += 1
                    continue

            if dry_run:
                self.stdout.write(f"  [dry-run] {aud.affaire.reference_interne} @ {aud.date_audience}")
                continue

            msg = send_audience_reminder(aud)
            if msg and msg.status in ("sent", "dry_run"):
                sent += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ {aud.affaire.reference_interne} → {msg.to_number} [{msg.status}]"
                ))
            else:
                failed += 1
                err = (msg.error_message if msg else "unknown") or "unknown"
                self.stdout.write(self.style.WARNING(
                    f"  ✗ {aud.affaire.reference_interne}: {err}"
                ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Terminé. Envoyés: {sent} | Échecs: {failed} | Déjà envoyés: {skipped_already}"
        ))
