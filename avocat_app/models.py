from uuid import uuid4
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, EmailValidator
from django.utils.translation import gettext_lazy as _

# =============================================
# Validateurs — فرض إدخال عربي للمحتوى الظاهر للمستخدم
# =============================================
ARABIC_CHAR_CLASSES = "\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF"

arabic_text_validator = RegexValidator(
    regex=rf"^[{ARABIC_CHAR_CLASSES}0-9\s\-_'.,()\/:]+$",
    message=_("المرجو إدخال محتوى باللغة العربية (يمكن استعمال الأرقام وبعض الرموز البسيطة)."),
)

arabic_name_validator = RegexValidator(
    regex=rf"^[{ARABIC_CHAR_CLASSES}\s\-']+$",
    message=_("الاسم يجب أن يكون بالعربية."),
)

# =============================================
# Choices — القيم المخزّنة بالفرنسية، التسميات المعروضة بالعربية
# =============================================
class TypeAffaire(models.TextChoices):
    PENAL = 'Pénal', 'جنائي'
    PENAL_FLAGRANT = 'Pénal-Flagrant', 'جنائي تلبّسي'
    PENAL_CONTRAVENTION = 'Pénal-Contravention', 'مخالفة'
    PENAL_ROUTIER = 'Pénal-Routier', 'جنح السير'
    CIVIL = 'Civil', 'مدني'
    LOCATION = 'Location', 'كراء'
    FAMILLE = 'Famille', 'أسرة'
    SOCIAL = 'Social', 'اجتماعي'
    COMMERCIAL = 'Commercial', 'تجاري'
    AUTRE = 'Autre', 'أخرى'


class StatutAffaire(models.TextChoices):
    OUVERTE = 'Ouverte', 'مفتوحة'
    EN_AUDIENCE = 'En audience', 'في الجلسات'
    EN_DELIBERE = 'En délibéré', 'في المداولة'
    JUGEE = 'Jugée', 'محكوم فيها'
    EN_NOTIFICATION = 'En notification', 'قيد التبليغ'
    EN_RECOURS = 'En recours', 'قيد الطعن'
    EN_EXECUTION = 'En exécution', 'قيد التنفيذ'
    CLOTUREE = 'Clôturée', 'مختتمة'
    CLASSEE = 'Classée', 'محفوظة'


class TypeJuridiction(models.TextChoices):
    TPI = 'Tribunal de Première Instance', 'المحكمة الابتدائية'
    CA = "Cour d’Appel", 'محكمة الاستئناف'
    CC = 'Cour de Cassation', 'محكمة النقض'
    AUTRE = 'Autre', 'جهة أخرى'


class TypeAudience(models.TextChoices):
    MISE_EN_ETAT = 'Mise en état', 'جلسة تعيين/تهيئة'
    PLAIDOIRIE = 'Plaidoirie', 'مرافعة'
    DEBAT = 'Débat', 'مناقشة'
    DELIBERE = 'Délibéré', 'مداولة'
    PRONONCE = 'Prononcé', 'جلسة النطق'
    REFERES = 'Référé', 'استعجالي'
    INJONCTION = 'Injonction', 'أمر بالأداء/إنذار'
    AUTRE = 'Autre', 'أخرى'


class ResultatAudience(models.TextChoices):
    REPORT = 'Report', 'تأجيل'
    MESURE = 'Mesure ordonnée', 'اتخاذ إجراء'
    CLOTURE_PLAIDOIRIES = 'Clôture plaidoiries', 'اختتام المرافعات'
    JUGEMENT = 'Jugement prononcé', 'صدر الحكم'
    SANS_SUITE = 'Sans suite', 'بدون متابعة'


class TypeMesure(models.TextChoices):
    ENQUETE = 'Enquête', 'بحث'
    EXPERTISE = 'Expertise', 'خبرة'
    INSPECTION = 'Inspection', 'معاينة'
    INTERROGATOIRE = 'Interrogatoire', 'استجواب'
    TEMOIGNAGE = 'Témoignage', 'شهادة'
    CONFRONTATION = 'Confrontation', 'مواجهة'
    AUTRE = 'Autre', 'إجراء آخر'


class StatutMesure(models.TextChoices):
    ORDONNEE = 'Ordonnée', 'مأمور بها'
    EN_COURS = 'En cours', 'جارٍ'
    DEPOSEE = 'Déposée', 'أودِع التقرير'
    CONTRE_EXPERTISE = 'Contre-expertise', 'خبرة مضادّة'
    CLOTUREE = 'Clôturée', 'مختتمة'


class TypeRecours(models.TextChoices):
    APPEL = 'Appel', 'استئناف'
    OPPOSITION = 'Opposition', 'تعرض'
    CASSATION = 'Cassation', 'نقض'
    RETRACTATION = 'Rétractation', 'مراجعة'
    AUTRE = 'Autre', 'طعن آخر'


class StatutRecours(models.TextChoices):
    EN_COURS = 'En cours', 'جارٍ'
    REJETE = 'Rejeté', 'مرفوض'
    RECU = 'Reçu', 'مقبول شكلاً'
    JUGE = 'Jugé', 'محكوم'
    CLOTURE = 'Clôturé', 'مختتم'


class TypeExecution(models.TextChoices):
    MONETAIRE = 'Monétaire', 'تنفيذ مالي'
    EXPULSION = 'Expulsion/Évacuation', 'إفراغ/إخلاء'
    SAISIE = 'Saisie', 'حجز'
    AUTRE = 'Autre', 'تنفيذ آخر'


class StatutExecution(models.TextChoices):
    EN_ATTENTE = 'En attente', 'بانتظار'
    EN_COURS = 'En cours', 'جارٍ'
    SUSPENDU = 'Suspendu', 'موقوف'
    ACHEVE = 'Achevé', 'منتهٍ'
    INFRUCTUEUX = 'Infructueux', 'متعذّر'


class TypeDepense(models.TextChoices):
    FRAIS_JUSTICE = 'Frais de justice', 'رسوم قضائية'
    HUISSIER = 'Huissier', 'مفوض قضائي'
    EXPERTISE = 'Expertise', 'خبرة'
    DEPLACEMENT = 'Déplacement', 'تنقل'
    FRAIS_DOSSIER = 'Frais de dossier', 'مصاريف ملف'
    AUTRE = 'Autre', 'أخرى'


class TypeRecette(models.TextChoices):
    PROVISION = 'Provision', 'تسبيق'
    HONORAIRES = 'Honoraires', 'أتعاب'
    REMBOURSEMENT = 'Remboursement frais', 'استرجاع مصاريف'
    CONDAMNATION = 'Condamnation', 'مبالغ محكوم بها'
    AUTRE = 'Autre', 'أخرى'


class RoleUtilisateur(models.TextChoices):
    ADMIN = 'Admin', 'مدير'
    AVOCAT = 'Avocat', 'محامٍ'
    ASSISTANT = 'Assistant', 'مساعد'
    STAGIAIRE = 'Stagiaire', 'متدرّب'
    LECTEUR = 'Lecteur', 'قارىء'


class StatutTache(models.TextChoices):
    A_FAIRE = 'A faire', 'للتنفيذ'
    EN_COURS = 'En cours', 'جارٍ'
    EN_ATTENTE = 'En attente', 'بانتظار'
    TERMINE = 'Terminé', 'منجز'


class TypeAlerte(models.TextChoices):
    AUDIENCE = 'Audience', 'جلسة'
    ECHEANCE_RECOURS = 'Echéance recours', 'أجل الطعن'
    EXECUTION = 'Exécution', 'تنفيذ'
    DEPENSE = 'Dépense', 'مصاريف'
    AUTRE = 'Autre', 'أخرى'


# =============================================
# النماذج — أسماء الحقول الفرنسية؛ التسميات الظاهرة بالعربية
# =============================================
class Juridiction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nom = models.CharField(max_length=180, verbose_name='اسم الجهة', validators=[arabic_text_validator])
    ville = models.CharField(max_length=120, verbose_name='المدينة', validators=[arabic_text_validator])
    type = models.CharField(max_length=40, choices=TypeJuridiction.choices, verbose_name='النوع')

    class Meta:
        db_table = 'juridiction'
        verbose_name = 'جهة قضائية'
        verbose_name_plural = 'جهات قضائية'
        indexes = [models.Index(fields=['ville'])]

    def __str__(self):
        return f"{self.nom} - {self.ville}"


class Avocat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nom = models.CharField(max_length=120, verbose_name='اسم المحامي', validators=[arabic_name_validator])
    barreau = models.CharField(max_length=120, null=True, blank=True, verbose_name='هيئة الانتماء', validators=[arabic_text_validator])
    telephone = models.CharField(max_length=30, null=True, blank=True, verbose_name='هاتف')
    email = models.EmailField(max_length=120, null=True, blank=True, verbose_name='بريد إلكتروني')
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='تعريفة بالساعة', validators=[MinValueValidator(0)])

    class Meta:
        db_table = 'avocat'
        verbose_name = 'محامٍ'
        verbose_name_plural = 'محامون'

    def __str__(self):
        return self.nom


class Affaire(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    reference_interne = models.CharField(max_length=50, verbose_name='مرجع داخلي', unique=True)
    reference_tribunal = models.CharField(max_length=100, null=True, blank=True, verbose_name='مرجع المحكمة')
    type_affaire = models.CharField(max_length=30, choices=TypeAffaire.choices, verbose_name='نوع القضية')
    statut_affaire = models.CharField(max_length=20, choices=StatutAffaire.choices, default=StatutAffaire.OUVERTE, verbose_name='حالة القضية')
    juridiction = models.ForeignKey(Juridiction, on_delete=models.PROTECT, verbose_name='المحكمة')
    date_ouverture = models.DateField(verbose_name='تاريخ الفتح')
    objet = models.TextField(null=True, blank=True, verbose_name='موضوع الدعوى', validators=[arabic_text_validator])
    valeur_litige = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name='قيمة النزاع', validators=[MinValueValidator(0)])
    priorite = models.CharField(max_length=10, choices=[('Haute','مرتفعة'),('Normale','عادية'),('Basse','منخفضة')], default='Normale', verbose_name='الأولوية')
    avocat_responsable = models.ForeignKey('Avocat', on_delete=models.PROTECT, related_name='affaires_responsable', verbose_name='المحامي المسؤول')
    notes = models.TextField(null=True, blank=True, verbose_name='ملاحظات', validators=[arabic_text_validator])

    avocats = models.ManyToManyField(Avocat, through='AffaireAvocat', related_name='affaires', verbose_name='محامون')

    class Meta:
        db_table = 'affaire'
        verbose_name = 'قضية'
        verbose_name_plural = 'قضايا'
        indexes = [
            models.Index(fields=['reference_interne']),
            models.Index(fields=['reference_tribunal']),
            models.Index(fields=['type_affaire', 'statut_affaire']),
        ]

    def __str__(self):
        return f"{self.reference_interne} ({self.get_type_affaire_display()})"


class Partie(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    type_partie = models.CharField(max_length=20, choices=[
        ('Demandeur','مدعٍ'),('Défendeur','مدعى عليه'),('Plagnant','شاكي'),('Prévenu','متّهم'),
        ('Intimé','مستأنف عليه'),('Appelant','مستأنِف'),('Témoin','شاهد'),('Expert','خبير'),('Autre','غير ذلك')
    ], verbose_name='صفة الطرف')
    nom_complet = models.CharField(max_length=180, verbose_name='الاسم الكامل', validators=[arabic_name_validator])
    cin_ou_rc = models.CharField(max_length=50, null=True, blank=True, verbose_name='رقم التعريف/السجل التجاري')
    adresse = models.TextField(null=True, blank=True, verbose_name='العنوان', validators=[arabic_text_validator])
    telephone = models.CharField(max_length=30, null=True, blank=True, verbose_name='هاتف')
    email = models.EmailField(max_length=120, null=True, blank=True, verbose_name='بريد إلكتروني')
    representant_legal = models.CharField(max_length=180, null=True, blank=True, verbose_name='الممثل القانوني', validators=[arabic_name_validator])
    avocat = models.ForeignKey(Avocat, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='محامي الطرف')

    class Meta:
        db_table = 'partie'
        verbose_name = 'طرف'
        verbose_name_plural = 'أطراف'
        indexes = [models.Index(fields=['nom_complet'])]

    def __str__(self):
        return f"{self.nom_complet} — {self.get_type_partie_display()}"


class AffairePartie(models.Model):
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE)
    partie = models.ForeignKey(Partie, on_delete=models.CASCADE)
    role_dans_affaire = models.CharField(max_length=20, choices=[
        ('Demandeur','مدعٍ'),('Défendeur','مدعى عليه'),('Plagnant','شاكي'),('Prévenu','متّهم'),('Intimé','مستأنف عليه'),('Appelant','مستأنِف'),('Autre','غير ذلك')
    ], verbose_name='الدور في القضية')
    actif = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        db_table = 'affaire_partie'
        verbose_name = 'ربط طرف بقضية'
        verbose_name_plural = 'أطراف القضايا'
        unique_together = ('affaire','partie','role_dans_affaire')


class AffaireAvocat(models.Model):
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE)
    avocat = models.ForeignKey(Avocat, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('Responsable','مسؤول'),('Collaborateur','مساعد'),('Correspondant','مراسل'),('Adversaire','خصم')
    ], verbose_name='دور المحامي')

    class Meta:
        db_table = 'affaire_avocat'
        verbose_name = 'ربط محامٍ بقضية'
        verbose_name_plural = 'محامو القضايا'
        unique_together = ('affaire','avocat','role')


class Audience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    type_audience = models.CharField(max_length=20, choices=TypeAudience.choices, verbose_name='نوع الجلسة')
    date_audience = models.DateTimeField(verbose_name='تاريخ الجلسة')
    resultat = models.CharField(max_length=30, choices=ResultatAudience.choices, null=True, blank=True, verbose_name='النتيجة')
    proces_verbal = models.TextField(null=True, blank=True, verbose_name='محضر الجلسة', validators=[arabic_text_validator])

    class Meta:
        db_table = 'audience'
        verbose_name = 'جلسة'
        verbose_name_plural = 'جلسات'
        ordering = ['-date_audience']
        indexes = [models.Index(fields=['date_audience'])]

    def __str__(self):
        return f"{self.affaire.reference_interne} @ {self.date_audience:%Y-%m-%d}"


class Mesure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    audience = models.ForeignKey(Audience, on_delete=models.CASCADE, verbose_name='الجلسة')
    type_mesure = models.CharField(max_length=20, choices=TypeMesure.choices, verbose_name='نوع الإجراء')
    statut = models.CharField(max_length=20, choices=StatutMesure.choices, default=StatutMesure.ORDONNEE, verbose_name='حالة الإجراء')
    notes = models.TextField(null=True, blank=True, verbose_name='ملاحظات', validators=[arabic_text_validator])

    class Meta:
        db_table = 'mesure'
        verbose_name = 'إجراء'
        verbose_name_plural = 'إجراءات'


class Expertise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    expert_nom = models.CharField(max_length=180, verbose_name='اسم الخبير', validators=[arabic_name_validator])
    date_ordonnee = models.DateField(verbose_name='تاريخ الأمر')
    date_depot = models.DateField(null=True, blank=True, verbose_name='تاريخ الإيداع')
    contre_expertise = models.BooleanField(default=False, verbose_name='خبرة مضادّة')
    rapport = models.FileField(upload_to='expertises/', null=True, blank=True, verbose_name='تقرير (ملف)')

    class Meta:
        db_table = 'expertise'
        verbose_name = 'خبرة'
        verbose_name_plural = 'خبرات'


class Decision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    numero_decision = models.CharField(max_length=80, verbose_name='رقم الحكم/القرار')
    date_prononce = models.DateField(verbose_name='تاريخ النطق')
    formation = models.CharField(max_length=120, null=True, blank=True, verbose_name='الهيئة/القاضي', validators=[arabic_text_validator])
    resumé = models.TextField(null=True, blank=True, verbose_name='ملخص', validators=[arabic_text_validator])
    susceptible_recours = models.BooleanField(default=True, verbose_name='قابل للطعن')

    class Meta:
        db_table = 'decision'
        verbose_name = 'حكم/قرار'
        verbose_name_plural = 'أحكام/قرارات'
        indexes = [models.Index(fields=['numero_decision'])]

    def __str__(self):
        return f"{self.numero_decision} — {self.date_prononce}"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE, verbose_name='الحكم/القرار')
    demande_numero = models.CharField(max_length=80, verbose_name='رقم طلب التبليغ')
    date_depot_demande = models.DateField(verbose_name='تاريخ إيداع الطلب')
    dossier_notification_numero = models.CharField(max_length=80, null=True, blank=True, verbose_name='رقم ملف التبليغ')
    huissier_nom = models.CharField(max_length=180, null=True, blank=True, verbose_name='اسم المفوض القضائي', validators=[arabic_name_validator])
    date_remise_huissier = models.DateField(null=True, blank=True, verbose_name='تاريخ التسليم للمفوض')
    date_signification = models.DateField(null=True, blank=True, verbose_name='تاريخ التبليغ')
    preuve = models.FileField(upload_to='notifications/', null=True, blank=True, verbose_name='محضر/إثبات (ملف)')

    class Meta:
        db_table = 'notification'
        verbose_name = 'تبليغ'
        verbose_name_plural = 'تبليغات'
        indexes = [models.Index(fields=['date_signification'])]


class VoieDeRecours(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE, verbose_name='الحكم/القرار')
    type_recours = models.CharField(max_length=20, choices=TypeRecours.choices, verbose_name='نوع الطعن')
    date_depot = models.DateField(verbose_name='تاريخ الإيداع')
    numero_recours = models.CharField(max_length=80, null=True, blank=True, verbose_name='رقم ملف الطعن')
    juridiction = models.ForeignKey(Juridiction, on_delete=models.PROTECT, verbose_name='الجهة الناظرة')
    statut = models.CharField(max_length=15, choices=StatutRecours.choices, default=StatutRecours.EN_COURS, verbose_name='الحالة')

    class Meta:
        db_table = 'voie_de_recours'
        verbose_name = 'طريق طعن'
        verbose_name_plural = 'طرق الطعن'


class Execution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE, verbose_name='الحكم/القرار')
    type_execution = models.CharField(max_length=30, choices=TypeExecution.choices, verbose_name='نوع التنفيذ')
    date_demande = models.DateField(verbose_name='تاريخ الطلب')
    statut = models.CharField(max_length=15, choices=StatutExecution.choices, default=StatutExecution.EN_ATTENTE, verbose_name='حالة التنفيذ')
    depot_caisse_barreau = models.BooleanField(default=False, verbose_name='إيداع بصندوق الهيئة')
    date_demande_liquidation = models.DateField(null=True, blank=True, verbose_name='تاريخ طلب التصفية')
    proces_verbal_refus = models.CharField(max_length=120, null=True, blank=True, verbose_name='مرجع محضر الامتناع')
    date_pv_refus = models.DateField(null=True, blank=True, verbose_name='تاريخ محضر الامتناع')
    contrainte_par_corps_num = models.CharField(max_length=120, null=True, blank=True, verbose_name='رقم ملف الإكراه البدني')
    date_contrainte = models.DateField(null=True, blank=True, verbose_name='تاريخ الإحالة على الإكراه')

    class Meta:
        db_table = 'execution'
        verbose_name = 'تنفيذ'
        verbose_name_plural = 'تنفيذات'


class Depense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    type_depense = models.CharField(max_length=20, choices=TypeDepense.choices, verbose_name='نوع المصروف')
    montant = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='المبلغ')
    date_depense = models.DateField(verbose_name='تاريخ الصرف')
    beneficiaire = models.CharField(max_length=180, null=True, blank=True, verbose_name='المستفيد', validators=[arabic_name_validator])
    piece = models.FileField(upload_to='depenses/', null=True, blank=True, verbose_name='مرفق (ملف)')

    class Meta:
        db_table = 'depense'
        verbose_name = 'مصروف'
        verbose_name_plural = 'مصاريف'
        indexes = [models.Index(fields=['date_depense'])]


class Recette(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    type_recette = models.CharField(max_length=25, choices=TypeRecette.choices, verbose_name='نوع الدخل')
    montant = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='المبلغ')
    date_recette = models.DateField(verbose_name='تاريخ التحصيل')
    source = models.CharField(max_length=180, null=True, blank=True, verbose_name='المصدر', validators=[arabic_text_validator])
    piece = models.FileField(upload_to='recettes/', null=True, blank=True, verbose_name='مرفق (ملف)')

    class Meta:
        db_table = 'recette'
        verbose_name = 'دخل/تحصيل'
        verbose_name_plural = 'مداخيل'
        indexes = [models.Index(fields=['date_recette'])]


class PieceJointe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, related_name='pieces', verbose_name='القضية')
    titre = models.CharField(max_length=180, verbose_name='عنوان المرفق', validators=[arabic_text_validator])
    type_piece = models.CharField(max_length=10, choices=[('PDF','PDF'),('Image','صورة'),('Doc','مستند'),('Audio','صوت'),('Autre','أخرى')], verbose_name='نوع الملف')
    fichier = models.FileField(upload_to='pieces/', verbose_name='ملف')
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        db_table = 'piece_jointe'
        verbose_name = 'مرفق'
        verbose_name_plural = 'مرفقات'


class Utilisateur(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nom_complet = models.CharField(max_length=120, verbose_name='الاسم الكامل', validators=[arabic_name_validator])
    role = models.CharField(max_length=10, choices=RoleUtilisateur.choices, verbose_name='الدور')
    telephone = models.CharField(max_length=30, null=True, blank=True, verbose_name='هاتف')
    email = models.EmailField(max_length=120, verbose_name='بريد إلكتروني', validators=[EmailValidator()])
    actif = models.BooleanField(default=True, verbose_name='نشط')
    preferences_langue = models.CharField(max_length=2, choices=[('ar','العربية'),('fr','الفرنسية')], default='ar', verbose_name='لغة التفضيل')

    class Meta:
        db_table = 'utilisateur'
        verbose_name = 'مستخدم'
        verbose_name_plural = 'مستخدمون'

    def __str__(self):
        return f"{self.nom_complet} ({self.get_role_display()})"


class Tache(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='القضية')
    titre = models.CharField(max_length=180, verbose_name='عنوان المهمة', validators=[arabic_text_validator])
    description = models.TextField(null=True, blank=True, verbose_name='وصف', validators=[arabic_text_validator])
    echeance = models.DateTimeField(null=True, blank=True, verbose_name='موعد الاستحقاق')
    assigne_a = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='مكلّف')
    statut = models.CharField(max_length=12, choices=StatutTache.choices, default=StatutTache.A_FAIRE, verbose_name='الحالة')

    class Meta:
        db_table = 'tache'
        verbose_name = 'مهمة'
        verbose_name_plural = 'مهام'
        indexes = [models.Index(fields=['echeance'])]


class Alerte(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    type_alerte = models.CharField(max_length=20, choices=TypeAlerte.choices, verbose_name='نوع التنبيه')
    reference_id = models.UUIDField(verbose_name='المعرّف المرتبط')
    date_alerte = models.DateTimeField(verbose_name='تاريخ التنبيه')
    moyen = models.CharField(max_length=10, choices=[('Email','Email'),('SMS','SMS'),('InApp','داخل النظام')], verbose_name='قناة الإشعار')
    destinataire = models.CharField(max_length=180, verbose_name='المرسل إليه')
    message = models.TextField(verbose_name='نص التنبيه', validators=[arabic_text_validator])

    class Meta:
        db_table = 'alerte'
        verbose_name = 'تنبيه'
        verbose_name_plural = 'تنبيهات'
        indexes = [models.Index(fields=['date_alerte'])]

    def __str__(self):
        return f"{self.get_type_alerte_display()} — {self.date_alerte:%Y-%m-%d %H:%M}"


class JournalActivite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, verbose_name='المستخدم')
    action = models.CharField(max_length=120, verbose_name='الإجراء')
    objet = models.CharField(max_length=120, verbose_name='الكيان')
    objet_id = models.UUIDField(verbose_name='معرّف الكيان')
    date_action = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإجراء')
    details = models.TextField(null=True, blank=True, verbose_name='تفاصيل', validators=[arabic_text_validator])

    class Meta:
        db_table = 'journal_activite'
        verbose_name = 'سجلّ نشاط'
        verbose_name_plural = 'سجلّ الأنشطة'
        indexes = [models.Index(fields=['date_action'])]

    def __str__(self):
        return f"{self.action} — {self.objet} @ {self.date_action:%Y-%m-%d %H:%M}"
