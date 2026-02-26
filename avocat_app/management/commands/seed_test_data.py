# -*- coding: utf-8 -*-
"""
Management command: python manage.py seed_test_data
Populates the database with realistic Moroccan law firm test data.
"""
import random
from datetime import date, timedelta, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from avocat_app.models import (
    TypeAffaire, StatutAffaire, TypeAudience, ResultatAudience,
    TypeRecours, StatutRecours, TypeExecution, StatutExecution,
    TypeMesure, StatutMesure, TypeDepense, TypeRecette,
    TypeAlerte, TypeAvertissement, TypeJuridiction, RoleUtilisateur, StatutTache,
    Juridiction, Barreau, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Expert, Utilisateur, Tache, Alerte,
    Avertissement, PhaseAffaire,
)


class Command(BaseCommand):
    help = "Seed the database with realistic Moroccan law firm test data"

    def handle(self, *args, **options):
        self.stdout.write("بدء ملء قاعدة البيانات بالبيانات التجريبية...")

        self._seed_type_affaire()
        barreaux = self._seed_barreaux()
        avocats = self._seed_avocats(barreaux)
        experts = self._seed_experts()
        utilisateurs = self._seed_utilisateurs()
        parties = self._seed_parties(avocats)
        affaires = self._seed_affaires(avocats)
        self._seed_affaire_parties(affaires, parties)
        self._seed_affaire_avocats(affaires, avocats)
        self._seed_avertissements(affaires)
        self._seed_audiences(affaires)
        self._seed_decisions(affaires)
        self._seed_notifications(affaires)
        self._seed_recours(affaires)
        self._seed_executions(affaires)
        self._seed_depenses(affaires)
        self._seed_recettes(affaires)
        self._seed_taches(affaires, utilisateurs)
        self._seed_alertes()

        self.stdout.write(self.style.SUCCESS("تم ملء قاعدة البيانات بنجاح!"))

    # ── TypeAffaire ──
    def _seed_type_affaire(self):
        types = [
            ("CIV", "دعوى مدنية", "Affaire civile"),
            ("PEN", "دعوى جنائية", "Affaire pénale"),
            ("COM", "دعوى تجارية", "Affaire commerciale"),
            ("ADM", "دعوى إدارية", "Affaire administrative"),
            ("SOC", "دعوى اجتماعية", "Affaire sociale"),
            ("FAM", "دعوى أسرة", "Affaire familiale"),
            ("IMM", "دعوى عقارية", "Affaire immobilière"),
        ]
        for code, ar, fr in types:
            TypeAffaire.objects.get_or_create(code=code, defaults={"libelle": ar, "libelle_fr": fr})
        self.stdout.write(f"  TypeAffaire: {TypeAffaire.objects.count()}")

    # ── Barreaux ──
    def _seed_barreaux(self):
        noms = ["هيئة المحامين بالدار البيضاء", "هيئة المحامين بالرباط",
                "هيئة المحامين بمراكش", "هيئة المحامين بفاس"]
        barreaux = []
        for nom in noms:
            b, _ = Barreau.objects.get_or_create(nom=nom)
            barreaux.append(b)
        self.stdout.write(f"  Barreau: {Barreau.objects.count()}")
        return barreaux

    # ── Avocats ──
    def _seed_avocats(self, barreaux):
        avocats_data = [
            ("أحمد بنعلي", "0661-111111", "ahmed@cabinet.ma", Decimal("500")),
            ("فاطمة الزهراء العلوي", "0662-222222", "fatima@cabinet.ma", Decimal("600")),
            ("محمد كريم الإدريسي", "0663-333333", "karim@cabinet.ma", Decimal("450")),
            ("سلمى بن حدو", "0664-444444", "salma@cabinet.ma", Decimal("550")),
            ("يوسف المنصوري", "0665-555555", "youssef@cabinet.ma", Decimal("700")),
        ]
        avocats = []
        for nom, tel, email, taux in avocats_data:
            a, _ = Avocat.objects.get_or_create(
                nom=nom,
                defaults={
                    "telephone": tel, "email": email,
                    "taux_horaire": taux,
                    "barreau": random.choice(barreaux),
                }
            )
            avocats.append(a)
        self.stdout.write(f"  Avocat: {Avocat.objects.count()}")
        return avocats

    # ── Experts ──
    def _seed_experts(self):
        experts_data = [
            ("عبد الله التازي", "0666-111111", "tazi@experts.ma", "خبير محاسب", "الدار البيضاء"),
            ("نادية بوزيد", "0666-222222", "bouzid@experts.ma", "خبير عقاري", "الرباط"),
            ("حسن الفيلالي", "0666-333333", "filali@experts.ma", "خبير طبي", "مراكش"),
            ("ليلى أمزيان", "0666-444444", "amzian@experts.ma", "خبير بيئي", "فاس"),
        ]
        experts = []
        for nom, tel, email, spec, adr in experts_data:
            e, _ = Expert.objects.get_or_create(
                nom_complet=nom,
                defaults={"telephone": tel, "email": email, "specialite": spec, "adresse": adr}
            )
            experts.append(e)
        self.stdout.write(f"  Expert: {Expert.objects.count()}")
        return experts

    # ── Utilisateurs ──
    def _seed_utilisateurs(self):
        roles = list(RoleUtilisateur.objects.all())
        if not roles:
            return []
        users_data = [
            ("أمينة بنجلون", "0670-111111", "amina@cabinet.ma"),
            ("هشام القادري", "0670-222222", "hicham@cabinet.ma"),
            ("مريم السعدي", "0670-333333", "maryam@cabinet.ma"),
        ]
        utilisateurs = []
        for nom, tel, email in users_data:
            u, _ = Utilisateur.objects.get_or_create(
                nom_complet=nom,
                defaults={"telephone": tel, "email": email, "role": random.choice(roles)}
            )
            utilisateurs.append(u)
        self.stdout.write(f"  Utilisateur: {Utilisateur.objects.count()}")
        return utilisateurs

    # ── Parties ──
    def _seed_parties(self, avocats):
        parties_data = [
            ("Demandeur", "عبد الرحمن الحسني", "AB123456", "شارع الحسن الثاني، الدار البيضاء", "0671-111111"),
            ("Défendeur", "شركة النجاح للتجارة", "RC45678", "المنطقة الصناعية، عين السبع", "0522-334455"),
            ("Demandeur", "خديجة بنت أحمد", "CD789012", "حي الرياض، الرباط", "0672-222222"),
            ("Défendeur", "المؤسسة العامة للسكن", "RC98765", "شارع محمد الخامس، مراكش", "0524-556677"),
            ("Demandeur", "محمد بن يوسف", "EF345678", "زنقة المقاومة، فاس", "0673-333333"),
            ("Plagnant", "فاطمة الزهراء بنت علي", "GH901234", "حي السلام، طنجة", "0674-444444"),
            ("Prévenu", "عمر بن سعيد", "IJ567890", "شارع الجيش الملكي، مكناس", "0675-555555"),
            ("Demandeur", "شركة الأطلس للبناء", "RC11223", "المنطقة الحرة، القنيطرة", "0537-112233"),
            ("Défendeur", "البنك المغربي للتجارة", "RC33445", "شارع الأمير مولاي عبد الله", "0522-998877"),
            ("Demandeur", "حسن المرابط", "KL234567", "حي المحمدي، الدار البيضاء", "0676-666666"),
            ("Témoin", "أمينة بنت محمد", "MN890123", "شارع بئر أنزران، أكادير", "0677-777777"),
            ("Demandeur", "سعيد بوزيان", "OP456789", "حي الحسني، سلا", "0678-888888"),
        ]
        parties = []
        for role, nom, cin, adr, tel in parties_data:
            p, _ = Partie.objects.get_or_create(
                nom_complet=nom,
                defaults={
                    "type_partie": role,
                    "cin_ou_rc": cin, "adresse": adr, "telephone": tel,
                    "avocat": random.choice(avocats) if random.random() > 0.4 else None,
                }
            )
            parties.append(p)
        self.stdout.write(f"  Partie: {Partie.objects.count()}")
        return parties

    # ── Affaires ──
    def _seed_affaires(self, avocats):
        types = list(TypeAffaire.objects.all())
        statuts = list(StatutAffaire.objects.all())
        juridictions = list(Juridiction.objects.all())

        if not types or not statuts or not juridictions:
            self.stdout.write(self.style.WARNING("  Manque TypeAffaire/StatutAffaire/Juridiction — skip Affaire"))
            return []

        today = date.today()
        affaires_data = [
            # (ref, ref_tribunal, type_idx, phase, days_ago, objet, valeur, priorite)
            ("AFF-2025-001", "1234/2025", 0, PhaseAffaire.PREMIERE_INSTANCE, 180,
             "دعوى أداء مبلغ مالي ناتج عن عقد قرض", Decimal("150000"), "Haute"),
            ("AFF-2025-002", "2345/2025", 2, PhaseAffaire.PRELIMINAIRE, 30,
             "نزاع تجاري حول عدم تنفيذ عقد توريد", Decimal("500000"), "Haute"),
            ("AFF-2025-003", "3456/2025", 0, PhaseAffaire.APPEL, 365,
             "دعوى إفراغ من محل تجاري لعدم أداء الكراء", Decimal("80000"), "Normale"),
            ("AFF-2025-004", "4567/2025", 6, PhaseAffaire.PREMIERE_INSTANCE, 120,
             "نزاع عقاري حول ملكية أرض فلاحية", Decimal("2000000"), "Haute"),
            ("AFF-2025-005", "5678/2025", 4, PhaseAffaire.PREMIERE_INSTANCE, 90,
             "دعوى الطرد التعسفي والمطالبة بالتعويض", Decimal("45000"), "Normale"),
            ("AFF-2025-006", None, 5, PhaseAffaire.PRELIMINAIRE, 15,
             "دعوى نفقة وحضانة", Decimal("3000"), "Haute"),
            ("AFF-2025-007", "6789/2025", 0, PhaseAffaire.EXECUTION, 400,
             "تنفيذ حكم بأداء مبلغ ناتج عن حادثة سير", Decimal("250000"), "Normale"),
            ("AFF-2025-008", "7890/2025", 3, PhaseAffaire.PREMIERE_INSTANCE, 60,
             "طعن في قرار إداري بشأن رخصة بناء", Decimal("0"), "Normale"),
            ("AFF-2025-009", "8901/2025", 2, PhaseAffaire.CASSATION, 500,
             "نزاع حول فسخ عقد شراكة تجارية", Decimal("1200000"), "Haute"),
            ("AFF-2025-010", "9012/2025", 0, PhaseAffaire.PRELIMINAIRE, 7,
             "دعوى تعويض عن الأضرار الناتجة عن أعمال البناء", Decimal("300000"), "Basse"),
            ("AFF-2026-001", "1111/2026", 1, PhaseAffaire.PREMIERE_INSTANCE, 45,
             "شكاية بالنصب والاحتيال", Decimal("0"), "Haute"),
            ("AFF-2026-002", "2222/2026", 0, PhaseAffaire.PREMIERE_INSTANCE, 70,
             "دعوى استرداد حيازة عقار", Decimal("950000"), "Normale"),
            ("AFF-2026-003", None, 2, PhaseAffaire.PRELIMINAIRE, 5,
             "نزاع بين شريكين حول تقسيم الأرباح", Decimal("800000"), "Haute"),
            ("AFF-2026-004", "3333/2026", 0, PhaseAffaire.CLOTURE, 730,
             "دعوى تعويض عن ضرر جسدي منتهية", Decimal("120000"), "Basse"),
            ("AFF-2026-005", "4444/2026", 6, PhaseAffaire.APPEL, 200,
             "استئناف حكم قسمة عقار بين الورثة", Decimal("3500000"), "Haute"),
        ]

        affaires = []
        for ref, ref_trib, type_idx, phase, days_ago, objet, valeur, prio in affaires_data:
            a, created = Affaire.objects.get_or_create(
                reference_interne=ref,
                defaults={
                    "reference_tribunal": ref_trib,
                    "type_affaire": types[type_idx % len(types)],
                    "statut_affaire": random.choice(statuts),
                    "juridiction": random.choice(juridictions),
                    "date_ouverture": today - timedelta(days=days_ago),
                    "objet": objet,
                    "valeur_litige": valeur if valeur else None,
                    "priorite": prio,
                    "avocat_responsable": random.choice(avocats),
                    "phase": phase,
                }
            )
            affaires.append(a)
        self.stdout.write(f"  Affaire: {Affaire.objects.count()}")
        return affaires

    # ── AffairePartie ──
    def _seed_affaire_parties(self, affaires, parties):
        if not affaires or not parties:
            return
        roles = ["Demandeur", "Défendeur"]
        count = 0
        for aff in affaires:
            # 2 parties per case
            selected = random.sample(parties, min(2, len(parties)))
            for i, p in enumerate(selected):
                role = roles[i % 2]
                _, created = AffairePartie.objects.get_or_create(
                    affaire=aff, partie=p, role_dans_affaire=role
                )
                if created:
                    count += 1
        self.stdout.write(f"  AffairePartie: {count} created")

    # ── AffaireAvocat ──
    def _seed_affaire_avocats(self, affaires, avocats):
        if not affaires or not avocats:
            return
        count = 0
        for aff in affaires:
            # Link the responsible avocat + maybe a collaborator
            _, created = AffaireAvocat.objects.get_or_create(
                affaire=aff, avocat=aff.avocat_responsable, role="Responsable"
            )
            if created:
                count += 1
            if random.random() > 0.5:
                collab = random.choice([a for a in avocats if a != aff.avocat_responsable])
                _, created = AffaireAvocat.objects.get_or_create(
                    affaire=aff, avocat=collab, role="Collaborateur"
                )
                if created:
                    count += 1
        self.stdout.write(f"  AffaireAvocat: {count} created")

    # ── Avertissements ──
    def _seed_avertissements(self, affaires):
        if not affaires:
            return
        types_av = list(TypeAvertissement.objects.all())
        if not types_av:
            return
        count = 0
        # Add avertissements to affaires in PRELIMINAIRE phase
        prelim = [a for a in affaires if a.phase == PhaseAffaire.PRELIMINAIRE]
        # Also add some to other affaires (historical)
        targets = prelim + random.sample(affaires, min(4, len(affaires)))
        today = date.today()

        avertissement_data = [
            ("عبد الرحمن الحسني", "شارع الحسن الثاني، الدار البيضاء", "huissier", "en_attente",
             "المطالبة بأداء مبلغ الدين المترتب بذمتكم", 3),
            ("شركة النجاح للتجارة", "المنطقة الصناعية، عين السبع", "poste", "sans_reponse",
             "إنذار بتنفيذ بنود عقد التوريد المبرم", 20),
            ("خديجة بنت أحمد", "حي الرياض، الرباط", "huissier", "reponse",
             "إنذار بإفراغ المحل التجاري لعدم أداء الكراء", 45),
            ("محمد بن يوسف", "زنقة المقاومة، فاس", "main", "en_attente",
             "إنذار بتسوية الوضعية القانونية للعقار", 1),
            ("البنك المغربي للتجارة", "شارع الأمير مولاي عبد الله", "poste", "partielle",
             "إنذار بأداء القسط المتأخر من القرض", 35),
            ("حسن المرابط", "حي المحمدي، الدار البيضاء", "huissier", "en_attente",
             "إنذار بالأداء قبل اللجوء إلى القضاء", 5),
            ("شركة الأطلس للبناء", "المنطقة الحرة، القنيطرة", "email", "sans_reponse",
             "إنذار بإتمام أشغال البناء المتفق عليها", 60),
        ]

        for i, aff in enumerate(targets):
            if i >= len(avertissement_data):
                break
            dest_nom, dest_adr, moyen, resultat, objet, days_ago = avertissement_data[i]
            _, created = Avertissement.objects.get_or_create(
                affaire=aff,
                destinataire_nom=dest_nom,
                defaults={
                    "type_avertissement": random.choice(types_av),
                    "date_envoi": today - timedelta(days=days_ago),
                    "destinataire_adresse": dest_adr,
                    "moyen_envoi": moyen,
                    "numero_suivi": f"SV-{random.randint(10000, 99999)}",
                    "resultat": resultat,
                    "date_reponse": (today - timedelta(days=max(0, days_ago - 10))) if resultat in ("reponse", "partielle") else None,
                    "objet_avertissement": objet,
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Avertissement: {count} created")

    # ── Audiences ──
    def _seed_audiences(self, affaires):
        if not affaires:
            return
        types_aud = list(TypeAudience.objects.all())
        resultats = list(ResultatAudience.objects.all())
        if not types_aud or not resultats:
            return

        count = 0
        today = date.today()
        # Cases not in PRELIMINAIRE get audiences
        with_audiences = [a for a in affaires if a.phase != PhaseAffaire.PRELIMINAIRE]

        for aff in with_audiences:
            # 2-5 audiences per case
            n_audiences = random.randint(2, 5)
            base_date = aff.date_ouverture + timedelta(days=30)
            for j in range(n_audiences):
                aud_date = base_date + timedelta(days=j * random.randint(14, 45))
                aud, created = Audience.objects.get_or_create(
                    affaire=aff,
                    date_audience=timezone.make_aware(datetime.combine(aud_date, datetime.min.time().replace(hour=9))),
                    type_audience=random.choice(types_aud),
                    defaults={"resultat": random.choice(resultats)}
                )
                if created:
                    count += 1

        # Add some future audiences
        for aff in random.sample(with_audiences, min(5, len(with_audiences))):
            future_date = today + timedelta(days=random.randint(3, 30))
            aud, created = Audience.objects.get_or_create(
                affaire=aff,
                date_audience=timezone.make_aware(datetime.combine(future_date, datetime.min.time().replace(hour=10))),
                type_audience=random.choice(types_aud),
                defaults={"resultat": resultats[0]}  # first result (probably تأجيل)
            )
            if created:
                count += 1

        self.stdout.write(f"  Audience: {count} created")

    # ── Decisions ──
    def _seed_decisions(self, affaires):
        if not affaires:
            return
        count = 0
        # Cases past PREMIERE_INSTANCE get decisions
        with_decisions = [a for a in affaires
                          if a.phase in (PhaseAffaire.APPEL, PhaseAffaire.CASSATION,
                                         PhaseAffaire.EXECUTION, PhaseAffaire.CLOTURE)]
        # Also some PREMIERE_INSTANCE cases
        pi_cases = [a for a in affaires if a.phase == PhaseAffaire.PREMIERE_INSTANCE]
        with_decisions += random.sample(pi_cases, min(3, len(pi_cases)))

        for aff in with_decisions:
            dec_date = aff.date_ouverture + timedelta(days=random.randint(90, 250))
            dec, created = Decision.objects.get_or_create(
                affaire=aff,
                numero_decision=f"حكم/{random.randint(1000, 9999)}/{dec_date.year}",
                defaults={
                    "date_prononce": timezone.make_aware(datetime.combine(dec_date, datetime.min.time().replace(hour=14))),
                    "formation": random.choice(["الغرفة المدنية الأولى", "الغرفة التجارية", "غرفة الأحوال الشخصية", "الغرفة الجنائية"]),
                    "resumé": random.choice([
                        "الحكم بأداء المدعى عليه المبلغ المطلوب مع الفوائد القانونية",
                        "رفض الطلب لعدم التأسيس",
                        "الحكم بإفراغ المدعى عليه من المحل مع التعويض",
                        "الحكم بالتعويض عن الضرر مع النفاذ المعجل",
                        "عدم قبول الدعوى شكلاً",
                    ]),
                    "susceptible_recours": random.choice([True, True, True, False]),
                }
            )
            if created:
                count += 1

            # APPEL/CASSATION cases get a second decision
            if aff.phase in (PhaseAffaire.APPEL, PhaseAffaire.CASSATION) and created:
                dec2_date = dec_date + timedelta(days=random.randint(60, 180))
                Decision.objects.get_or_create(
                    affaire=aff,
                    numero_decision=f"قرار/{random.randint(1000, 9999)}/{dec2_date.year}",
                    defaults={
                        "date_prononce": timezone.make_aware(datetime.combine(dec2_date, datetime.min.time().replace(hour=14))),
                        "formation": "محكمة الاستئناف — الغرفة المدنية",
                        "resumé": random.choice([
                            "تأييد الحكم الابتدائي",
                            "إلغاء الحكم الابتدائي والحكم من جديد",
                            "تعديل الحكم الابتدائي جزئياً",
                        ]),
                        "susceptible_recours": aff.phase == PhaseAffaire.APPEL,
                    }
                )
                count += 1

        self.stdout.write(f"  Decision: {count} created")

    # ── Notifications ──
    def _seed_notifications(self, affaires):
        if not affaires:
            return
        decisions = Decision.objects.filter(affaire__in=affaires)
        count = 0
        today = date.today()

        for dec in decisions:
            notif_date = dec.date_prononce.date() + timedelta(days=random.randint(5, 20))
            n, created = Notification.objects.get_or_create(
                decision=dec,
                demande_numero=f"TBL/{random.randint(1000, 9999)}/{notif_date.year}",
                defaults={
                    "date_depot_demande": notif_date,
                    "dossier_notification_numero": f"DN-{random.randint(10000, 99999)}",
                    "huissier_nom": random.choice(["أحمد المفوض", "يونس المفوض", "سعيد المفوض", "عبد الكريم المفوض"]),
                    "date_remise_huissier": notif_date + timedelta(days=3),
                    "date_signification": notif_date + timedelta(days=random.randint(7, 25)) if random.random() > 0.2 else None,
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Notification: {count} created")

    # ── Voies de Recours ──
    def _seed_recours(self, affaires):
        if not affaires:
            return
        types_rec = list(TypeRecours.objects.all())
        statuts_rec = list(StatutRecours.objects.all())
        juridictions = list(Juridiction.objects.all())
        if not types_rec or not statuts_rec or not juridictions:
            return

        count = 0
        appel_cases = [a for a in affaires if a.phase in (PhaseAffaire.APPEL, PhaseAffaire.CASSATION)]

        for aff in appel_cases:
            decs = Decision.objects.filter(affaire=aff, susceptible_recours=True)
            for dec in decs:
                dep_date = dec.date_prononce.date() + timedelta(days=random.randint(5, 25))
                r, created = VoieDeRecours.objects.get_or_create(
                    decision=dec,
                    type_recours=random.choice(types_rec[:3]),
                    defaults={
                        "statut": random.choice(statuts_rec),
                        "date_depot": dep_date,
                        "numero_recours": f"REC/{random.randint(1000, 9999)}/{dep_date.year}",
                        "juridiction": random.choice(juridictions),
                    }
                )
                if created:
                    count += 1
        self.stdout.write(f"  VoieDeRecours: {count} created")

    # ── Executions ──
    def _seed_executions(self, affaires):
        if not affaires:
            return
        types_ex = list(TypeExecution.objects.all())
        statuts_ex = list(StatutExecution.objects.all())
        if not types_ex or not statuts_ex:
            return

        count = 0
        exec_cases = [a for a in affaires if a.phase == PhaseAffaire.EXECUTION]

        for aff in exec_cases:
            decs = Decision.objects.filter(affaire=aff)
            for dec in decs[:1]:
                ex_date = dec.date_prononce.date() + timedelta(days=random.randint(30, 90))
                ex, created = Execution.objects.get_or_create(
                    decision=dec,
                    type_execution=random.choice(types_ex),
                    defaults={
                        "statut": random.choice(statuts_ex),
                        "date_demande": ex_date,
                        "depot_caisse_barreau": random.choice([True, False]),
                    }
                )
                if created:
                    count += 1
        self.stdout.write(f"  Execution: {count} created")

    # ── Dépenses ──
    def _seed_depenses(self, affaires):
        if not affaires:
            return
        types_dep = list(TypeDepense.objects.all())
        if not types_dep:
            return

        count = 0
        for aff in affaires:
            n_dep = random.randint(1, 4)
            for _ in range(n_dep):
                dep_date = aff.date_ouverture + timedelta(days=random.randint(0, 120))
                dep, created = Depense.objects.get_or_create(
                    affaire=aff,
                    type_depense=random.choice(types_dep),
                    date_depense=dep_date,
                    defaults={
                        "montant": Decimal(str(random.randint(100, 5000))),
                        "beneficiaire": random.choice(["صندوق المحكمة", "المفوض القضائي", "الخبير", "مصاريف تنقل", "مصاريف ملف"]),
                    }
                )
                if created:
                    count += 1
        self.stdout.write(f"  Depense: {count} created")

    # ── Recettes ──
    def _seed_recettes(self, affaires):
        if not affaires:
            return
        types_rec = list(TypeRecette.objects.all())
        if not types_rec:
            return

        count = 0
        for aff in random.sample(affaires, min(10, len(affaires))):
            n_rec = random.randint(1, 3)
            for _ in range(n_rec):
                rec_date = aff.date_ouverture + timedelta(days=random.randint(0, 60))
                rec, created = Recette.objects.get_or_create(
                    affaire=aff,
                    type_recette=random.choice(types_rec),
                    date_recette=rec_date,
                    defaults={
                        "montant": Decimal(str(random.randint(500, 20000))),
                        "source": random.choice(["الموكل", "تسبيق أتعاب", "أتعاب مرحلة", "مبلغ محكوم به"]),
                    }
                )
                if created:
                    count += 1
        self.stdout.write(f"  Recette: {count} created")

    # ── Tâches ──
    def _seed_taches(self, affaires, utilisateurs):
        if not affaires or not utilisateurs:
            return
        statuts = list(StatutTache.objects.all())
        if not statuts:
            return

        taches_data = [
            "إعداد المقال الافتتاحي",
            "تجهيز ملف التبليغ",
            "متابعة الخبرة القضائية",
            "إعداد مذكرة جوابية",
            "مراجعة الحكم الابتدائي",
            "تحضير مقال استئنافي",
            "متابعة ملف التنفيذ",
            "التواصل مع الموكل",
            "تسجيل طلب التبليغ",
            "إعداد عريضة النقض",
            "متابعة المفوض القضائي",
            "تجديد الوكالة",
        ]

        count = 0
        today = date.today()
        for i, titre in enumerate(taches_data):
            aff = random.choice(affaires)
            echeance = today + timedelta(days=random.randint(-5, 30))
            t, created = Tache.objects.get_or_create(
                titre=titre,
                affaire=aff,
                defaults={
                    "description": f"مهمة خاصة بالقضية {aff.reference_interne}",
                    "echeance": timezone.make_aware(datetime.combine(echeance, datetime.min.time().replace(hour=17))),
                    "assigne_a": random.choice(utilisateurs),
                    "statut": random.choice(statuts),
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Tache: {count} created")

    # ── Alertes ──
    def _seed_alertes(self):
        types_al = list(TypeAlerte.objects.all())
        if not types_al:
            return

        alertes_data = [
            "تذكير بجلسة قادمة يوم الاثنين",
            "أجل الطعن ينتهي خلال خمسة أيام",
            "موعد تنفيذ الحكم اقترب",
            "مصاريف ملف تحتاج موافقة",
            "تذكير بتجديد الوكالة",
        ]
        count = 0
        today = date.today()
        for msg in alertes_data:
            from uuid import uuid4
            a, created = Alerte.objects.get_or_create(
                message=msg,
                defaults={
                    "type_alerte": random.choice(types_al),
                    "reference_id": uuid4(),
                    "date_alerte": timezone.make_aware(datetime.combine(today - timedelta(days=random.randint(0, 10)), datetime.min.time().replace(hour=8))),
                    "moyen": random.choice(["InApp", "Email"]),
                    "destinataire": "المحامي المسؤول",
                }
            )
            if created:
                count += 1
        self.stdout.write(f"  Alerte: {count} created")
