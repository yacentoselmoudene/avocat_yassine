# -*- coding: utf-8 -*-
"""Peuple les tables référentielles avec les données du droit marocain.

Sources:
- Code de procédure civile marocain (Dahir 28/09/1974)
- Code de procédure pénale (Loi 22.01)
- Code de la famille (Moudawana — Loi 70.03)
- Code de commerce (Loi 15-95)
- Code du travail (Loi 65-99)
- Loi 41-90 sur les tribunaux administratifs
- Loi 53-95 sur les tribunaux de commerce
- Loi 38.15 portant organisation judiciaire (2022)

Idempotent: utilise get_or_create pour ne pas écraser les données existantes.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from avocat_app.models import (
    TypeJuridiction, DegreJuridiction, TypeAffaire, StatutAffaire,
    TypeAudience, ResultatAudience, TypeRecours, StatutRecours,
    TypeExecution, StatutExecution, TypeMesure, StatutMesure,
    TypeDepense, TypeRecette, RoleUtilisateur, StatutTache,
    TypeAlerte, TypeAvertissement,
)


# =====================================================================
# DONNÉES DE RÉFÉRENCE — DROIT MAROCAIN
# =====================================================================

# Note: les libellés arabes utilisent uniquement les caractères autorisés par
# arabic_text_validator: lettres arabes, chiffres 0-9, espaces, et - _ ' . , ( ) / :

# ---------- 1. Types de juridictions ----------
TYPES_JURIDICTION = [
    ("المحكمة الابتدائية", "Tribunal de première instance", "TPI", "ابتدائي",
     "محكمة من الدرجة الأولى تختص بالنظر في القضايا المدنية والتجارية والاجتماعية والجنحية والمخالفات."),
    ("محكمة الاستئناف", "Cour d'appel", "CA", "استئنافي",
     "محكمة الدرجة الثانية تختص بالنظر في الاستئنافات المقدمة ضد أحكام المحاكم الابتدائية."),
    ("محكمة النقض", "Cour de cassation", "MNQ", "نقض",
     "أعلى هيئة قضائية بالمملكة المغربية. تنظر في الطعون بالنقض ضد القرارات النهائية."),
    ("المحكمة التجارية", "Tribunal de commerce", "TC", "ابتدائي",
     "محكمة متخصصة تختص بالنظر في النزاعات التجارية بين التجار، والإفلاس وصعوبات المقاولة."),
    ("محكمة الاستئناف التجارية", "Cour d'appel de commerce", "CAC", "استئنافي",
     "تنظر في الاستئنافات المقدمة ضد أحكام المحاكم التجارية. أحدثت بموجب قانون 53.95."),
    ("المحكمة الإدارية", "Tribunal administratif", "TA", "ابتدائي",
     "محكمة متخصصة في القضاء الإداري. تختص بدعاوى الإلغاء والقضاء الشامل والصفقات العمومية."),
    ("محكمة الاستئناف الإدارية", "Cour d'appel administrative", "CAA", "استئنافي",
     "تنظر في الاستئنافات المقدمة ضد أحكام المحاكم الإدارية. أحدثت بموجب قانون 80.03."),
    ("قسم قضاء الأسرة", "Section de la justice de la famille", "QAF", "ابتدائي",
     "قسم متخصص داخل المحكمة الابتدائية، يختص بقضايا الأحوال الشخصية وفق مدونة الأسرة 70.03."),
    ("قسم قضاء القرب", "Section de la justice de proximité", "QQP", "ابتدائي",
     "قسم يختص بالنزاعات البسيطة التي لا تتجاوز قيمتها 5000 درهم. أحدث بقانون 42.10."),
    ("المحكمة العسكرية", "Tribunal militaire", "TMIL", "عسكري",
     "محكمة متخصصة تنظر في الجرائم العسكرية وفق القانون 108.13 (2014)."),
    ("المجلس الأعلى للحسابات", "Cour des comptes", "MAH", "مالي",
     "هيئة عليا للرقابة المالية على المال العام، طبقا للفصل 147 من الدستور والقانون 62.99."),
    ("المحكمة الدستورية", "Cour constitutionnelle", "MDST", "دستوري",
     "تختص بمراقبة دستورية القوانين، طبقا للفصل 129 من دستور 2011 والقانون التنظيمي 066.13."),
]

# ---------- 2. Degrés de juridiction ----------
DEGRES_JURIDICTION = [
    ("ابتدائي", "Première instance"),
    ("استئنافي", "Appel"),
    ("نقض", "Cassation"),
    ("تنفيذي", "Exécution"),
    ("تبليغي", "Notification"),
]

# ---------- 3. Types d'affaires (code 4 chars max + Arabe + Français) ----------
TYPES_AFFAIRE = [
    # Civil — Droit des obligations et contrats (DOC)
    ("CIV1", "دعوى مدنية عامة", "Action civile générale"),
    ("CIV2", "مطالبة بدين", "Recouvrement de créance"),
    ("CIV3", "مسؤولية مدنية", "Responsabilité civile"),
    ("CIV4", "بطلان عقد", "Nullité de contrat"),
    ("CIV5", "فسخ عقد", "Résolution de contrat"),
    ("CIV6", "تعويض عن الضرر", "Indemnisation"),

    # Immobilier / Foncier
    ("IMM1", "دعوى عقارية", "Action immobilière"),
    ("IMM2", "تحفيظ عقاري", "Immatriculation foncière"),
    ("IMM3", "قسمة عقارية", "Partage immobilier"),
    ("IMM4", "تحديد إداري", "Délimitation administrative"),
    ("IMM5", "ارتفاقات", "Servitudes"),

    # Bail / Location
    ("LOC1", "نزاع كراء", "Différend de bail"),
    ("LOC2", "إفراغ المحلات", "Expulsion"),
    ("LOC3", "مراجعة السومة الكرائية", "Révision du loyer"),

    # Famille (Code de la famille 70.03)
    ("FAM1", "طلاق اتفاقي", "Divorce par consentement mutuel"),
    ("FAM2", "تطليق للشقاق", "Divorce judiciaire pour discorde"),
    ("FAM3", "تطليق للضرر", "Divorce pour préjudice"),
    ("FAM4", "خلع", "Divorce par Khôl"),
    ("FAM5", "نفقة", "Pension alimentaire"),
    ("FAM6", "حضانة الأطفال", "Garde d'enfants"),
    ("FAM7", "إثبات النسب", "Action en filiation"),
    ("FAM8", "إرث وتركة", "Succession"),
    ("FAM9", "كفالة", "Kafala"),

    # Pénal
    ("PEN1", "جناية", "Crime"),
    ("PEN2", "جنحة تأديبية", "Délit correctionnel"),
    ("PEN3", "جنحة ضبطية", "Délit de police"),
    ("PEN4", "مخالفة", "Contravention"),
    ("PEN5", "جنحة سير", "Délit routier"),
    ("PEN6", "نصب واحتيال", "Escroquerie"),
    ("PEN7", "ضرب وجرح", "Coups et blessures"),
    ("PEN8", "سرقة", "Vol"),
    ("PEN9", "إصدار شيك بدون رصيد", "Chèque sans provision"),

    # Commercial (Code de commerce 15.95)
    ("COM1", "نزاع تجاري عام", "Différend commercial"),
    ("COM2", "صعوبات المقاولة", "Procédures collectives"),
    ("COM3", "تسوية قضائية", "Redressement judiciaire"),
    ("COM4", "تصفية قضائية", "Liquidation judiciaire"),
    ("COM5", "أوراق تجارية", "Effets de commerce"),
    ("COM6", "منافسة غير مشروعة", "Concurrence déloyale"),
    ("COM7", "ملكية صناعية", "Propriété industrielle"),
    ("COM8", "نقل", "Transport"),

    # Social / Travail (Code du travail 65.99)
    ("SOC1", "نزاع شغل فردي", "Conflit individuel du travail"),
    ("SOC2", "فصل تعسفي", "Licenciement abusif"),
    ("SOC3", "حادثة شغل", "Accident de travail"),
    ("SOC4", "مرض مهني", "Maladie professionnelle"),
    ("SOC5", "ضمان اجتماعي", "Sécurité sociale (CNSS)"),

    # Administratif (Loi 41.90)
    ("ADM1", "دعوى إلغاء", "Recours pour excès de pouvoir"),
    ("ADM2", "قضاء شامل", "Plein contentieux"),
    ("ADM3", "صفقات عمومية", "Marchés publics"),
    ("ADM4", "الوظيفة العمومية", "Fonction publique"),
    ("ADM5", "نزاعات ضريبية", "Contentieux fiscal"),
    ("ADM6", "نزع الملكية", "Expropriation"),

    # Procédures particulières
    ("REF1", "استعجالية", "Référé"),
    ("EXE1", "تنفيذ حكم", "Exécution de jugement"),
    ("NOT1", "تبليغ", "Notification"),
]

# ---------- 4. Statuts d'affaire ----------
STATUTS_AFFAIRE = [
    ("مفتوحة", "Ouverte"),
    ("قيد التحقيق", "En instruction"),
    ("مؤجلة", "Reportée"),
    ("محجوزة للمداولة", "En délibéré"),
    ("محسومة", "Jugée"),
    ("نهائية", "Définitive"),
    ("مستأنفة", "En appel"),
    ("في النقض", "En cassation"),
    ("قيد التنفيذ", "En exécution"),
    ("منفذة", "Exécutée"),
    ("موقوفة", "Suspendue"),
    ("محفوظة", "Classée"),
    ("شطبت", "Radiée"),
    ("صلح", "Conciliation"),
    ("تنازل", "Désistement"),
    ("براءة", "Acquittement"),
    ("إدانة", "Condamnation"),
]

# ---------- 5. Types d'audience ----------
TYPES_AUDIENCE = [
    ("جلسة أولى", "Première audience"),
    ("جلسة بحث", "Audience d'instruction"),
    ("جلسة مرافعة", "Audience de plaidoirie"),
    ("جلسة الحجز للمداولة", "Mise en délibéré"),
    ("جلسة نطق الحكم", "Prononcé du jugement"),
    ("جلسة علنية", "Audience publique"),
    ("جلسة سرية", "Audience à huis clos"),
    ("جلسة بمكتب القاضي", "Audience en cabinet"),
    ("جلسة استعجالية", "Audience de référé"),
    ("جلسة صلح", "Audience de conciliation"),
    ("جلسة خبرة", "Audience d'expertise"),
    ("جلسة شهادة", "Audience de témoignage"),
    ("جلسة مواجهة", "Audience de confrontation"),
    ("جلسة مثول", "Comparution"),
    ("جلسة تنفيذية", "Audience d'exécution"),
    ("جلسة تحقيق", "Audience d'instruction pénale"),
    ("جلسة جنحية", "Audience correctionnelle"),
    ("جلسة جنائية", "Audience criminelle"),
]

# ---------- 6. Résultats d'audience ----------
RESULTATS_AUDIENCE = [
    ("تم تأجيل الجلسة", "Audience reportée"),
    ("حجزت للمداولة", "Mise en délibéré"),
    ("صدر الحكم", "Jugement rendu"),
    ("صدر القرار", "Arrêt rendu"),
    ("صلح بين الأطراف", "Conciliation entre parties"),
    ("أمر بإجراء بحث", "Enquête ordonnée"),
    ("أمر بإجراء خبرة", "Expertise ordonnée"),
    ("ضمت لقضية أخرى", "Jonction d'instance"),
    ("موقوفة", "Suspendue"),
    ("تنازل", "Désistement"),
    ("إلغاء", "Annulation"),
    ("شطب على القضية", "Radiation"),
    ("قرار تمهيدي", "Décision avant-dire-droit"),
    ("قرار استعجالي", "Ordonnance de référé"),
    ("عدم الاختصاص", "Incompétence"),
    ("عدم القبول", "Irrecevabilité"),
    ("سقوط الدعوى", "Péremption d'instance"),
]

# ---------- 7. Types de recours ----------
# Format: (libelle_ar, libelle_fr, delai_jours, domaine)
TYPES_RECOURS = [
    ("استئناف مدني", "Appel civil", 30, "civil"),
    ("استئناف تجاري", "Appel commercial", 15, "commercial"),
    ("استئناف إداري", "Appel administratif", 30, "administratif"),
    ("استئناف اجتماعي", "Appel social", 30, "social"),
    ("استئناف أسرة", "Appel en matière familiale", 30, "civil"),
    ("استئناف جنحي", "Appel correctionnel", 10, "penal"),
    ("استئناف جنائي", "Appel criminel", 10, "penal"),
    ("نقض مدني", "Cassation civile", 30, "civil"),
    ("نقض تجاري", "Cassation commerciale", 30, "commercial"),
    ("نقض إداري", "Cassation administrative", 30, "administratif"),
    ("نقض جنائي", "Cassation pénale", 30, "penal"),
    ("تعرض", "Opposition", 10, "civil"),
    ("تعرض الغير الخارج عن الخصومة", "Tierce opposition", 30, "civil"),
    ("إعادة النظر", "Recours en révision", 30, "civil"),
    ("طلب تصحيح خطأ مادي", "Rectification d'erreur matérielle", 30, "civil"),
    ("طلب تفسير", "Demande d'interprétation", 30, "civil"),
]

# ---------- 8. Statuts de recours ----------
STATUTS_RECOURS = [
    ("مودع", "Déposé"),
    ("قيد البحث", "En cours d'examen"),
    ("مقبول شكلا", "Recevable en la forme"),
    ("غير مقبول شكلا", "Irrecevable"),
    ("محجوز للمداولة", "En délibéré"),
    ("مقبول موضوعا", "Accueilli"),
    ("مرفوض موضوعا", "Rejeté"),
    ("تأييد الحكم", "Confirmation"),
    ("إلغاء جزئي", "Réformation partielle"),
    ("إلغاء كلي", "Annulation totale"),
    ("نقض وإحالة", "Cassation avec renvoi"),
    ("نقض بدون إحالة", "Cassation sans renvoi"),
    ("تنازل عن الطعن", "Désistement du pourvoi"),
]

# ---------- 9. Types d'exécution ----------
TYPES_EXECUTION = [
    ("تنفيذ جبري", "Exécution forcée"),
    ("حجز تحفظي", "Saisie conservatoire"),
    ("حجز تنفيذي", "Saisie exécutoire"),
    ("حجز عقاري", "Saisie immobilière"),
    ("حجز منقول", "Saisie mobilière"),
    ("حجز على الأجر", "Saisie sur salaire"),
    ("حجز على الحساب البنكي", "Saisie sur compte bancaire"),
    ("حجز ما للمدين لدى الغير", "Saisie-arrêt"),
    ("إفراغ", "Expulsion"),
    ("هدم", "Démolition"),
    ("تسليم الشيء", "Délivrance de la chose"),
    ("أداء مبلغ مالي", "Paiement de somme"),
    ("مزاد علني", "Adjudication"),
    ("غرامة تهديدية", "Astreinte"),
]

# ---------- 10. Statuts d'exécution ----------
STATUTS_EXECUTION = [
    ("مطلوب التنفيذ", "Demandée"),
    ("قيد التنفيذ", "En cours"),
    ("موقوف التنفيذ", "Suspendue"),
    ("تم التنفيذ", "Exécutée"),
    ("تنفيذ جزئي", "Partiellement exécutée"),
    ("متعذر التنفيذ", "Impossible"),
    ("مرفوض", "Refusée"),
    ("ملغى", "Annulée"),
]

# ---------- 11. Types de mesures ----------
TYPES_MESURE = [
    ("خبرة", "Expertise"),
    ("خبرة طبية", "Expertise médicale"),
    ("خبرة تقنية", "Expertise technique"),
    ("خبرة عقارية", "Expertise immobilière"),
    ("خبرة محاسبية", "Expertise comptable"),
    ("بحث", "Enquête"),
    ("معاينة", "Constat"),
    ("حجز تحفظي", "Saisie conservatoire"),
    ("إنابة قضائية", "Délégation judiciaire"),
    ("مواجهة", "Confrontation"),
    ("شهادة", "Témoignage"),
    ("الإدلاء بالوثائق", "Production de documents"),
    ("وضع تحت الحراسة", "Mise sous séquestre"),
    ("إجراءات استعجالية", "Mesures d'urgence"),
    ("منع من السفر", "Interdiction de sortie du territoire"),
]

# ---------- 12. Statuts de mesure ----------
STATUTS_MESURE = [
    ("مأمور به", "Ordonné"),
    ("قيد التنفيذ", "En cours"),
    ("منفذ", "Exécuté"),
    ("ملغى", "Annulé"),
    ("معلق", "En attente"),
]

# ---------- 13. Types de dépenses ----------
TYPES_DEPENSE = [
    ("مصاريف كتابة الضبط", "Frais de greffe"),
    ("أتعاب المحامي", "Honoraires d'avocat"),
    ("أتعاب المفوض القضائي", "Honoraires d'huissier"),
    ("أتعاب الخبرة", "Honoraires d'expert"),
    ("أتعاب الترجمة", "Honoraires de traducteur assermenté"),
    ("مصاريف التنقل", "Frais de transport"),
    ("مصاريف الطوابع", "Frais de timbres"),
    ("مصاريف النسخ", "Frais de copie"),
    ("مصاريف التسجيل", "Frais d'enregistrement"),
    ("مصاريف النشر", "Frais de publicité légale"),
    ("مصاريف التبليغ", "Frais de signification"),
    ("الرسوم القضائية", "Frais judiciaires"),
    ("مصاريف الإيداع", "Frais de dépôt"),
    ("مصاريف الإيواء", "Frais d'hébergement"),
    ("مصاريف متفرقة", "Frais divers"),
]

# ---------- 14. Types de recettes ----------
TYPES_RECETTE = [
    ("أتعاب محاماة", "Honoraires d'avocat"),
    ("دفعة على الحساب", "Acompte"),
    ("سلفة", "Provision"),
    ("تصفية نهائية", "Solde final"),
    ("استرجاع مصاريف", "Remboursement de frais"),
    ("تعويض", "Indemnité"),
    ("تعويضات", "Dommages-intérêts"),
    ("مصاريف مسترجعة", "Frais récupérés"),
    ("استشارة قانونية", "Consultation juridique"),
    ("صياغة عقد", "Rédaction de contrat"),
]

# ---------- 15. Rôles utilisateurs ----------
ROLES_UTILISATEUR = [
    ("محامي شريك", "Avocat associé"),
    ("محامي مساعد", "Avocat collaborateur"),
    ("محامي متمرن", "Avocat stagiaire"),
    ("سكرتير", "Secrétaire"),
    ("مساعد قانوني", "Assistant juridique"),
    ("محاسب", "Comptable"),
    ("متمرن", "Stagiaire"),
    ("مسؤول إداري", "Administrateur"),
    ("قارئ", "Lecture seule"),
    ("مدير المكتب", "Manager du cabinet"),
]

# ---------- 16. Statuts de tâche ----------
STATUTS_TACHE = [
    ("جديدة", "Nouvelle"),
    ("قيد التنفيذ", "En cours"),
    ("في الانتظار", "En attente"),
    ("منجزة", "Terminée"),
    ("ملغاة", "Annulée"),
    ("معلقة", "Bloquée"),
    ("متأخرة", "En retard"),
]

# ---------- 17. Types d'alertes ----------
TYPES_ALERTE = [
    ("جلسة قريبة", "Audience proche"),
    ("أجل استئناف", "Délai d'appel"),
    ("أجل نقض", "Délai de cassation"),
    ("أجل تعرض", "Délai d'opposition"),
    ("أجل تنفيذ", "Délai d'exécution"),
    ("أجل إنذار", "Échéance d'avertissement"),
    ("موعد مهمة", "Échéance de tâche"),
    ("صدور حكم", "Décision rendue"),
    ("تبليغ متوصل به", "Notification reçue"),
    ("وثيقة ناقصة", "Document manquant"),
    ("فاتورة غير مؤداة", "Facture impayée"),
    ("تجديد تسجيل", "Renouvellement d'inscription"),
    ("انتهاء صلاحية وكالة", "Expiration de procuration"),
    ("ذكرى سنوية", "Date anniversaire"),
]

# ---------- 18. Types d'avertissements ----------
# Format: (libelle_ar, libelle_fr, delai_jours, domaine, base_legale)
TYPES_AVERTISSEMENT = [
    ("إنذار بالأداء", "Mise en demeure de paiement", 15, "commercial",
     "المادة 155 من مدونة التجارة"),
    ("إنذار بالإفراغ", "Mise en demeure d'évacuation", 30, "civil",
     "ظهير 24 ماي 1955 المتعلق بكراء المحلات"),
    ("إنذار بالتنفيذ", "Mise en demeure d'exécution", 10, "civil",
     "المادة 440 من قانون المسطرة المدنية"),
    ("إنذار بتسوية الوضعية", "Mise en demeure de régularisation", 30, "civil",
     "الفصول 254 وما يليه من قانون الالتزامات والعقود"),
    ("إنذار بالتسليم", "Mise en demeure de livraison", 15, "commercial",
     "الفصل 254 من قانون الالتزامات والعقود"),
    ("إنذار بأداء واجب الكراء", "Mise en demeure de paiement de loyer", 15, "civil",
     "المادة 38 من القانون 67.12 المتعلق بالكراء"),
    ("إنذار بإصلاح العين المكتراة", "Mise en demeure de réparation des lieux loués", 30, "civil",
     "المادة 6 من القانون 67.12"),
    ("إنذار بالعمل", "Mise en demeure de faire", 15, "civil",
     "الفصل 255 من قانون الالتزامات والعقود"),
    ("مذكرة أداء", "Sommation de payer", 15, "commercial",
     "المادة 188 من مدونة التجارة"),
    ("إنذار بفسخ العقد", "Mise en demeure de résolution du contrat", 30, "civil",
     "الفصل 259 من قانون الالتزامات والعقود"),
    ("إشعار بالطرد من الشغل", "Notification de licenciement", 8, "social",
     "المادة 62 من مدونة الشغل"),
    ("إنذار للوقاية من الفصل", "Avertissement avant licenciement", 8, "social",
     "المادة 37 من مدونة الشغل"),
]


# =====================================================================
# COMMAND
# =====================================================================

class Command(BaseCommand):
    help = "Peuple les tables référentielles avec les données du droit marocain (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Affiche les opérations sans modifier la base.")
        parser.add_argument("--only", type=str, default=None,
                            help="Limite à un type (typeaffaire, typejuridiction, ...).")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        only = options.get("only")

        seeders = [
            ("typejuridiction", self._seed_type_juridiction),
            ("degrejuridiction", self._seed_degre_juridiction),
            ("typeaffaire", self._seed_type_affaire),
            ("statutaffaire", self._seed_statut_affaire),
            ("typeaudience", self._seed_type_audience),
            ("resultataudience", self._seed_resultat_audience),
            ("typerecours", self._seed_type_recours),
            ("statutrecours", self._seed_statut_recours),
            ("typeexecution", self._seed_type_execution),
            ("statutexecution", self._seed_statut_execution),
            ("typemesure", self._seed_type_mesure),
            ("statutmesure", self._seed_statut_mesure),
            ("typedepense", self._seed_type_depense),
            ("typerecette", self._seed_type_recette),
            ("roleutilisateur", self._seed_role_utilisateur),
            ("statuttache", self._seed_statut_tache),
            ("typealerte", self._seed_type_alerte),
            ("typeavertissement", self._seed_type_avertissement),
        ]

        total_created = 0
        total_skipped = 0
        with transaction.atomic():
            for name, fn in seeders:
                if only and only != name:
                    continue
                created, skipped = fn(dry)
                total_created += created
                total_skipped += skipped
                self.stdout.write(self.style.SUCCESS(
                    f"  {name:20s} → créés: {created:3d} | déjà présents: {skipped:3d}"
                ))
            if dry:
                self.stdout.write(self.style.WARNING("DRY-RUN — rollback"))
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Total: créés {total_created} | sautés {total_skipped}"
        ))

    # ----- seed methods -----

    def _seed_type_juridiction(self, dry):
        created = skipped = 0
        for libelle, libelle_fr, code, niveau, description in TYPES_JURIDICTION:
            obj, was_created = TypeJuridiction.objects.get_or_create(
                libelle=libelle,
                defaults={"libelle_fr": libelle_fr, "code_type": code,
                          "niveau": niveau, "description": description},
            )
            created += int(was_created)
            skipped += int(not was_created)
        return created, skipped

    def _seed_degre_juridiction(self, dry):
        return self._seed_pair(DegreJuridiction, DEGRES_JURIDICTION)

    def _seed_type_affaire(self, dry):
        created = skipped = 0
        for code, libelle, libelle_fr in TYPES_AFFAIRE:
            obj, was_created = TypeAffaire.objects.get_or_create(
                code=code,
                defaults={"libelle": libelle, "libelle_fr": libelle_fr},
            )
            created += int(was_created)
            skipped += int(not was_created)
        return created, skipped

    def _seed_statut_affaire(self, dry):
        return self._seed_pair(StatutAffaire, STATUTS_AFFAIRE)

    def _seed_type_audience(self, dry):
        return self._seed_pair(TypeAudience, TYPES_AUDIENCE)

    def _seed_resultat_audience(self, dry):
        return self._seed_pair(ResultatAudience, RESULTATS_AUDIENCE)

    def _seed_type_recours(self, dry):
        created = skipped = 0
        for libelle, libelle_fr, delai, domaine in TYPES_RECOURS:
            obj, was_created = TypeRecours.objects.get_or_create(
                libelle=libelle,
                defaults={"libelle_fr": libelle_fr,
                          "delai_legal_jours": delai, "domaine": domaine},
            )
            created += int(was_created)
            skipped += int(not was_created)
        return created, skipped

    def _seed_statut_recours(self, dry):
        return self._seed_pair(StatutRecours, STATUTS_RECOURS)

    def _seed_type_execution(self, dry):
        return self._seed_pair(TypeExecution, TYPES_EXECUTION)

    def _seed_statut_execution(self, dry):
        return self._seed_pair(StatutExecution, STATUTS_EXECUTION)

    def _seed_type_mesure(self, dry):
        return self._seed_pair(TypeMesure, TYPES_MESURE)

    def _seed_statut_mesure(self, dry):
        return self._seed_pair(StatutMesure, STATUTS_MESURE)

    def _seed_type_depense(self, dry):
        return self._seed_pair(TypeDepense, TYPES_DEPENSE)

    def _seed_type_recette(self, dry):
        return self._seed_pair(TypeRecette, TYPES_RECETTE)

    def _seed_role_utilisateur(self, dry):
        return self._seed_pair(RoleUtilisateur, ROLES_UTILISATEUR)

    def _seed_statut_tache(self, dry):
        return self._seed_pair(StatutTache, STATUTS_TACHE)

    def _seed_type_alerte(self, dry):
        return self._seed_pair(TypeAlerte, TYPES_ALERTE)

    def _seed_type_avertissement(self, dry):
        created = skipped = 0
        for libelle, libelle_fr, delai, domaine, base_legale in TYPES_AVERTISSEMENT:
            obj, was_created = TypeAvertissement.objects.get_or_create(
                libelle=libelle,
                defaults={"libelle_fr": libelle_fr,
                          "delai_legal_jours": delai, "domaine": domaine,
                          "base_legale": base_legale},
            )
            created += int(was_created)
            skipped += int(not was_created)
        return created, skipped

    def _seed_pair(self, model, data):
        """Helper pour les tables (libelle, libelle_fr)."""
        created = skipped = 0
        for libelle, libelle_fr in data:
            obj, was_created = model.objects.get_or_create(
                libelle=libelle,
                defaults={"libelle_fr": libelle_fr},
            )
            created += int(was_created)
            skipped += int(not was_created)
        return created, skipped
