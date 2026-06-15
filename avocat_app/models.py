import secrets
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, EmailValidator, FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models_base import TimeStampedSoftDeleteModel


# =============================================
# File upload validators
# =============================================
ALLOWED_FILE_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'wav', 'ogg']
MAX_UPLOAD_SIZE_MB = 10

file_extension_validator = FileExtensionValidator(
    allowed_extensions=ALLOWED_FILE_EXTENSIONS,
    message=_("نوع الملف غير مسموح. الأنواع المسموحة: %(allowed_extensions)s"),
)


def validate_file_size(value):
    limit = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if value.size > limit:
        raise ValidationError(
            _(f"حجم الملف يتجاوز الحد الأقصى المسموح ({MAX_UPLOAD_SIZE_MB} ميغابايت)."),
        )
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
# Enums réutilisables — تعدادات مشتركة
# =============================================
class DomaineJuridique(models.TextChoices):
    CIVIL = "civil", "مدني"
    PENAL = "penal", "جنائي"
    COMMERCIAL = "commercial", "تجاري"
    ADMINISTRATIF = "administratif", "إداري"
    SOCIAL = "social", "اجتماعي"

class PhaseAffaire(models.TextChoices):
    PRELIMINAIRE = "PRELIMINAIRE", "المرحلة التمهيدية"
    PREMIERE_INSTANCE = "PREMIERE_INSTANCE", "المحكمة الابتدائية"
    APPEL = "APPEL", "محكمة الاستئناف"
    CASSATION = "CASSATION", "محكمة النقض"
    EXECUTION = "EXECUTION", "التنفيذ"
    CLOTURE = "CLOTURE", "مقفلة"

class AuditAction(models.TextChoices):
    CREATE = "CREATE", "إنشاء"
    UPDATE = "UPDATE", "تعديل"
    DELETE = "DELETE", "حذف"
    LOGIN  = "LOGIN",  "دخول"
    LOGOUT = "LOGOUT", "خروج"
    ATTACH = "ATTACH", "إرفاق ملف"
    EMAIL  = "EMAIL",  "إرسال بريد"
    SMS    = "SMS",    "إرسال SMS"
    EXPORT = "EXPORT", "تصدير"
    IMPORT = "IMPORT", "استيراد"
    OTHER  = "OTHER",  "أخرى"

class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_entries")
    action = models.CharField(max_length=16, choices=AuditAction.choices)
    app_label = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    object_pk = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(blank=True, null=True)   # {field: [old, new]}
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=8, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    token_id = models.CharField(max_length=36, null=True, blank=True)

    class Meta:
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=["app_label", "model", "object_pk"]),
            models.Index(fields=["actor", "action", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.action} {self.app_label}.{self.model}#{self.object_pk}"


class TypeAffaire(TimeStampedSoftDeleteModel):
    code = models.CharField(max_length=4, unique=True, verbose_name='الرمز')
    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typeaffaire_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class StatutExecution(TimeStampedSoftDeleteModel):
    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_statutexecution_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class TypeExecution(TimeStampedSoftDeleteModel):
    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typeexecution_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class StatutRecours(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_statutrecours_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class TypeRecours(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')
    delai_legal_jours = models.PositiveIntegerField(default=30, verbose_name='الأجل القانوني (أيام)')
    domaine = models.CharField(max_length=20, choices=DomaineJuridique.choices, default=DomaineJuridique.CIVIL, verbose_name='المجال')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typerecours_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class StatutMesure(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_statutmesure_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class TypeMesure(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typemesure_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class TypeAudience(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typeaudience_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class DegreJuridiction(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_degrejuridiction_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class ResultatAudience(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_resultataudience_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class TypeJuridiction(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    code_type = models.CharField(max_length=180, verbose_name='الرمز', validators=[arabic_text_validator])
    niveau = models.CharField(max_length=180, verbose_name='المستوى', validators=[arabic_text_validator])
    description = models.CharField(max_length=580, verbose_name='الوصف', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typejuridiction_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class StatutAffaire(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_statutaffaire_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class TypeDepense(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typedepense_libelle_alive",
            )
        ]

class TypeRecette(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typerecette_libelle_alive",
            )
        ]

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

class RoleUtilisateur(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_roleutilisateur_libelle_alive",
            )
        ]

class StatutTache(TimeStampedSoftDeleteModel):

    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    def __str__(self):
        s = self.libelle
        return f"{s} (محذوف)" if self.is_deleted else s

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_statuttache_libelle_alive",
            )
        ]



class TypeAlerte(TimeStampedSoftDeleteModel):
    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, verbose_name='nom en français')

    def __str__(self):
        return f"{self.libelle} (محذوف)" if self.is_deleted else self.libelle

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typealerte_libelle_alive",
            )
        ]


class TypeAvertissement(TimeStampedSoftDeleteModel):
    libelle = models.CharField(max_length=180, verbose_name='الاسم', validators=[arabic_text_validator])
    libelle_fr = models.CharField(max_length=180, blank=True, default='', verbose_name='nom en français')
    delai_legal_jours = models.PositiveIntegerField(default=15, verbose_name='الأجل القانوني (أيام)')
    domaine = models.CharField(max_length=20, choices=DomaineJuridique.choices, default=DomaineJuridique.CIVIL, verbose_name='المجال')
    base_legale = models.CharField(max_length=255, blank=True, default='', verbose_name='السند القانوني')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["libelle"],
                condition=models.Q(is_deleted=False),
                name="uniq_typeavertissement_libelle_alive",
            )
        ]

    def __str__(self):
        return f"{self.libelle} (محذوف)" if self.is_deleted else self.libelle


# =============================================
# النماذج — أسماء الحقول الفرنسية؛ التسميات الظاهرة بالعربية
# =============================================
class Juridiction(TimeStampedSoftDeleteModel):

    code = models.CharField(max_length=180, verbose_name='الرمز')
    nomtribunal_fr = models.CharField(max_length=180,null=True,blank=True, verbose_name='الاسم بالفرنسية')
    nomtribunal_ar = models.CharField(max_length=180,null=True,blank=True, verbose_name='الاسم بالعربية', validators=[arabic_text_validator])
    adressetribunal_fr = models.CharField(max_length=180,null=True,blank=True, verbose_name='العنوان بالفرنسية')
    adressetribunal_ar = models.CharField(max_length=180,null=True,blank=True, verbose_name='العنوان بالعربية', validators=[arabic_text_validator])
    villetribunal_fr = models.CharField(max_length=180,null=True,blank=True, verbose_name='المدينة بالفرنسية')
    villetribunal_ar = models.CharField(max_length=180,null=True,blank=True, verbose_name='المدينة بالعربية', validators=[arabic_text_validator])
    telephonetribunal = models.CharField(max_length=180,null=True,blank=True, verbose_name='رقم الهاتف')
    type = models.ForeignKey(TypeJuridiction, on_delete=models.PROTECT, verbose_name='نوع المحكمة')
    TribunalParent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="juridictions_filles", verbose_name="تنتمي إلى")
    id_mahakim = models.CharField(
        max_length=20, null=True, blank=True,
        verbose_name='معرف محاكم.ما',
        help_text='المعرف الرقمي للمحكمة في بوابة mahakim.ma'
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        verbose_name='خط العرض', help_text='Latitude (ex: 33.589886)'
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        verbose_name='خط الطول', help_text='Longitude (ex: -7.603869)'
    )

    class Meta:
        db_table = 'juridiction'
        verbose_name = 'محكمة'
        verbose_name_plural = 'محاكم'
        indexes = [models.Index(fields=['villetribunal_ar'])]

    @property
    def has_coords(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def google_maps_directions_url(self) -> str:
        if self.has_coords:
            return f"https://www.google.com/maps/dir/?api=1&destination={self.latitude},{self.longitude}"
        name = self.nomtribunal_ar or self.nomtribunal_fr or self.code
        ville = self.villetribunal_ar or self.villetribunal_fr or ""
        from urllib.parse import quote
        return f"https://www.google.com/maps/dir/?api=1&destination={quote(f'{name} {ville}')}"

    @property
    def waze_url(self) -> str:
        if self.has_coords:
            return f"https://waze.com/ul?ll={self.latitude},{self.longitude}&navigate=yes"
        return ""

    def __str__(self):
        return f"{self.nomtribunal_ar} - {self.villetribunal_ar}"

    def get_absolute_url(self):
        return reverse("cabinet:juridiction_detail", kwargs={"pk": self.pk})

class Barreau(TimeStampedSoftDeleteModel):
    nom = models.CharField(max_length=150, verbose_name="الهيئة")
    juridiction_appel = models.ForeignKey(Juridiction, null=True, blank=True, on_delete=models.SET_NULL,
                                         verbose_name="محكمة الاستئناف (اختياري)")
    class Meta:
        db_table = 'barreau'
        verbose_name = 'هيئة المحامين'
        verbose_name_plural = 'هيئات المحامين'
    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse("cabinet:barreau_detail", kwargs={"pk": self.pk})

class Avocat(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nom = models.CharField(max_length=120, verbose_name='اسم المحامي', validators=[arabic_name_validator])
    telephone = models.CharField(max_length=30, null=True, blank=True, verbose_name='هاتف')
    email = models.EmailField(max_length=120, null=True, blank=True, verbose_name='بريد إلكتروني')
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='تعريفة بالساعة', validators=[MinValueValidator(0)])
    barreau = models.ForeignKey(Barreau, on_delete=models.PROTECT, verbose_name="الهيئة")

    class Meta:
        db_table = 'avocat'
        verbose_name = 'محامٍ'
        verbose_name_plural = 'محامون'

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse("cabinet:avocat_detail", kwargs={"pk": self.pk})


class CodeCategorieAffaire(TimeStampedSoftDeleteModel):
    DOMAINE_CHOICES = [
        ('civil', 'مدني'), ('penal', 'جنائي'), ('famille', 'أسرة'),
        ('commercial', 'تجاري'), ('administratif', 'إداري'),
        ('social', 'اجتماعي'), ('immobilier', 'عقاري'),
        ('execution', 'تنفيذ'), ('notification', 'تبليغ'),
        ('proximite', 'قضاء القرب'), ('plainte', 'شكاية'),
    ]
    NIVEAU_CHOICES = [
        ('premiere_instance', 'ابتدائي'), ('appel', 'استئناف'),
        ('cassation', 'نقض'), ('execution', 'تنفيذ'),
        ('notification', 'تبليغ'),
    ]
    # رموز الملفات — colonne du XLSX. 4 grandes familles (sheet cat3).
    CATEGORIE_GLOBALE_CHOICES = [
        ('civil',      'رموز الملفات بالمحاكم المدنية'),
        ('penal',      'رموز الملفات الجنحية'),
        ('admin',      'رموز الملفات بالمحاكم الإدارية'),
        ('commercial', 'رموز الملفات بالمحاكم التجارية'),
    ]
    code = models.CharField(max_length=10, unique=True, verbose_name='الرمز')
    libelle = models.CharField(max_length=200, verbose_name='التسمية')
    domaine = models.CharField(max_length=30, choices=DOMAINE_CHOICES, verbose_name='المجال')
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES, default='premiere_instance', verbose_name='الدرجة')
    type_juridiction_initiale = models.ForeignKey(
        TypeJuridiction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="categories_initiales",
        verbose_name="نوع المحكمة الأولى",
        help_text="نوع المحكمة المختصة ابتدائيًا لهذه الفئة (مثلاً TPI، TC، TA، CA مباشرة...)",
    )
    # === Hiérarchie introduite depuis رموز المحاكم.xlsx ===
    # code_type : code 4 chiffres de la chambre (ex 1100, 1200, 1300...).
    # Plusieurs CodeCategorieAffaire partagent le même code_type.
    code_type = models.CharField(
        max_length=10, null=True, blank=True, db_index=True,
        verbose_name='رمز الغرفة',
        help_text='Code du groupe / chambre (ex: 1100, 1200, 1300)',
    )
    type_libelle = models.CharField(
        max_length=200, null=True, blank=True,
        verbose_name='تسمية الغرفة',
        help_text='Libellé de la chambre (ex: مؤسسة الرئيس وغرفة المشورة, المدني)',
    )
    sous_type = models.CharField(
        max_length=80, blank=True, default='',
        verbose_name='النوع الفرعي',
        help_text='ابتدائي / استئنافي / محلي / إنابة / ... (texte libre depuis le XLSX)',
    )
    categorie_globale = models.CharField(
        max_length=20, blank=True, default='',
        choices=CATEGORIE_GLOBALE_CHOICES,
        verbose_name='الفئة العامة',
        help_text='Grande famille (civil/pénal/admin/commercial)',
    )

    class Meta:
        db_table = 'code_categorie_affaire'
        verbose_name = 'رمز صنف القضية'
        verbose_name_plural = 'رموز أصناف القضايا'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code_type']),
            models.Index(fields=['sous_type']),
            models.Index(fields=['categorie_globale']),
        ]

    def __str__(self):
        return f"{self.code} — {self.libelle}"

    @property
    def is_premiere_instance(self) -> bool:
        """True si l'affaire est de 1ère instance (cascade mahakim.ma)."""
        return self.sous_type == "ابتدائي" or self.niveau == "premiere_instance"

    @property
    def is_appel(self) -> bool:
        return self.sous_type == "استئنافي" or self.niveau == "appel"


class Affaire(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    reference_interne = models.CharField(max_length=50, verbose_name='مرجع داخلي', unique=True)
    reference_tribunal = models.CharField(max_length=100, null=True, blank=True, verbose_name='مرجع المحكمة')

    # Structured reference for mahakim.ma
    numero_dossier = models.CharField(max_length=20, null=True, blank=True, verbose_name='رقم الملف')
    code_categorie = models.ForeignKey(CodeCategorieAffaire, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='صنف القضية')
    annee_dossier = models.CharField(max_length=4, null=True, blank=True, verbose_name='السنة')

    type_affaire = models.ForeignKey(TypeAffaire, on_delete=models.PROTECT, verbose_name="نوع القضية")
    statut_affaire = models.ForeignKey(StatutAffaire, on_delete=models.PROTECT, verbose_name="حالة القضية")

    juridiction = models.ForeignKey(Juridiction, on_delete=models.PROTECT, verbose_name='المحكمة')
    date_ouverture = models.DateField(verbose_name='تاريخ الفتح')
    objet = models.TextField(null=True, blank=True, verbose_name='موضوع الدعوى', validators=[arabic_text_validator])
    valeur_litige = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name='قيمة النزاع', validators=[MinValueValidator(0)])
    priorite = models.CharField(max_length=10, choices=[('Haute','مرتفعة'),('Normale','عادية'),('Basse','منخفضة')], default='Normale', verbose_name='الأولوية')
    avocat_responsable = models.ForeignKey('Avocat', on_delete=models.PROTECT, related_name='affaires_responsable', verbose_name='المحامي المسؤول')
    notes = models.TextField(null=True, blank=True, verbose_name='ملاحظات', validators=[arabic_text_validator])
    phase = models.CharField(max_length=20, choices=PhaseAffaire.choices, default=PhaseAffaire.PRELIMINAIRE, verbose_name='المرحلة')

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
        return f"{self.reference_interne} ({self.type_affaire})"

    def get_absolute_url(self):
        return reverse("cabinet:affaire_detail", kwargs={"pk": self.pk})

    def has_decision(self) -> bool:
        return self.decision_set.exists()

    @property
    def reference_tribunal_compose(self):
        parts = [self.numero_dossier, str(self.code_categorie.code) if self.code_categorie else None, self.annee_dossier]
        parts = [p for p in parts if p]
        return "/".join(parts) if parts else self.reference_tribunal or ""

class Avertissement(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    type_avertissement = models.ForeignKey(TypeAvertissement, on_delete=models.PROTECT, verbose_name='نوع الإنذار')
    date_envoi = models.DateField(verbose_name='تاريخ الإرسال')
    date_echeance = models.DateField(null=True, blank=True, verbose_name='تاريخ انتهاء الأجل')
    destinataire_nom = models.CharField(max_length=180, verbose_name='اسم المرسل إليه', validators=[arabic_name_validator])
    destinataire_adresse = models.TextField(null=True, blank=True, verbose_name='عنوان المرسل إليه', validators=[arabic_text_validator])
    moyen_envoi = models.CharField(max_length=20, choices=[
        ('huissier', 'مفوض قضائي'), ('poste', 'البريد المضمون'),
        ('main', 'تسليم باليد'), ('email', 'بريد إلكتروني'),
    ], default='huissier', verbose_name='وسيلة الإرسال')
    numero_suivi = models.CharField(max_length=80, null=True, blank=True, verbose_name='رقم التتبع')
    resultat = models.CharField(max_length=20, choices=[
        ('en_attente', 'في الانتظار'), ('reponse', 'تم الرد'),
        ('sans_reponse', 'بدون رد'), ('partielle', 'استجابة جزئية'),
    ], default='en_attente', verbose_name='النتيجة')
    date_reponse = models.DateField(null=True, blank=True, verbose_name='تاريخ الرد')
    objet_avertissement = models.TextField(verbose_name='موضوع الإنذار', validators=[arabic_text_validator])
    document = models.FileField(upload_to='avertissements/', null=True, blank=True, verbose_name='نسخة الإنذار', validators=[file_extension_validator, validate_file_size])
    preuve_envoi = models.FileField(upload_to='avertissements/preuves/', null=True, blank=True, verbose_name='إثبات الإرسال', validators=[file_extension_validator, validate_file_size])
    notes_reponse = models.TextField(null=True, blank=True, verbose_name='ملاحظات على الرد', validators=[arabic_text_validator])

    class Meta:
        db_table = 'avertissement'
        verbose_name = 'إنذار'
        verbose_name_plural = 'إنذارات'
        ordering = ['-date_envoi']
        indexes = [models.Index(fields=['date_envoi']), models.Index(fields=['date_echeance'])]

    def save(self, *args, **kwargs):
        if not self.date_echeance and self.date_envoi and self.type_avertissement_id:
            self.date_echeance = self.date_envoi + timedelta(days=self.type_avertissement.delai_legal_jours)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if not self.date_echeance:
            return False
        return timezone.localdate() > self.date_echeance

    @property
    def jours_restants(self):
        if not self.date_echeance:
            return None
        return (self.date_echeance - timezone.localdate()).days

    def __str__(self):
        return f"إنذار — {self.affaire.reference_interne} — {self.type_avertissement}"

    def get_absolute_url(self):
        return reverse("cabinet:avertissement_detail", kwargs={"pk": self.pk})


class Partie(TimeStampedSoftDeleteModel):
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

    def get_absolute_url(self):
        return reverse("cabinet:partie_detail", kwargs={"pk": self.pk})


class AffairePartie(TimeStampedSoftDeleteModel):
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

    def __str__(self):
        return f"{self.partie.nom_complet} في {self.affaire.reference_interne} كـ {self.get_role_dans_affaire_display()}"

    def get_absolute_url(self):
        return reverse("cabinet:affaire_partie_detail", kwargs={"pk": self.pk})

class AffaireAvocat(TimeStampedSoftDeleteModel):
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

    def __str__(self):
        return f"{self.avocat.nom} في {self.affaire.reference_interne} كـ {self.get_role_display()}"

    def get_absolute_url(self):
        return reverse("cabinet:affaire_avocat_detail", kwargs={"pk": self.pk})


class Audience(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    type_audience = models.ForeignKey(TypeAudience, on_delete=models.PROTECT, verbose_name="نوع الجلسة")
    date_audience = models.DateTimeField(verbose_name='تاريخ الجلسة')
    resultat = models.ForeignKey(ResultatAudience, on_delete=models.PROTECT, null=True, blank=True, verbose_name="النتيجة")
    proces_verbal = models.TextField(null=True, blank=True, verbose_name='محضر الجلسة', validators=[arabic_text_validator])

    class Meta:
        db_table = 'audience'
        verbose_name = 'جلسة'
        verbose_name_plural = 'جلسات'
        ordering = ['-date_audience']
        indexes = [models.Index(fields=['date_audience'])]

    def __str__(self):
        return f"{self.affaire.reference_interne} @ {self.date_audience:%Y-%m-%d}"
    def get_absolute_url(self):
        return reverse("cabinet:audience_detail", kwargs={"pk": self.pk})


class Mesure(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    audience = models.ForeignKey(Audience, on_delete=models.CASCADE, verbose_name='الجلسة')
    type_mesure = models.ForeignKey(TypeMesure, on_delete=models.PROTECT, verbose_name="نوع الإجراء")
    statut = models.ForeignKey(StatutMesure, on_delete=models.PROTECT, verbose_name="حالة الإجراء")
    notes = models.TextField(null=True, blank=True, verbose_name='ملاحظات', validators=[arabic_text_validator])
    date_ordonnee = models.DateTimeField(verbose_name='تاريخ الأمر')

    class Meta:
        db_table = 'mesure'
        verbose_name = 'إجراء'
        verbose_name_plural = 'إجراءات'

    def get_absolute_url(self):
        return reverse("cabinet:mesure_detail", kwargs={"pk": self.pk})


class Expertise(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    expert_nom = models.CharField(max_length=180, verbose_name='اسم الخبير', validators=[arabic_name_validator])
    date_ordonnee = models.DateField(verbose_name='تاريخ الأمر')
    date_depot = models.DateField(null=True, blank=True, verbose_name='تاريخ الإيداع')
    contre_expertise = models.BooleanField(default=False, verbose_name='خبرة مضادّة')
    rapport = models.FileField(upload_to='expertises/', null=True, blank=True, verbose_name='تقرير (ملف)', validators=[file_extension_validator, validate_file_size])

    class Meta:
        db_table = 'expertise'
        verbose_name = 'خبرة'
        verbose_name_plural = 'خبرات'

    def get_absolute_url(self):
        return reverse("cabinet:expertise_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"خبرة في {self.affaire.reference_interne} — {self.expert_nom}"


class Decision(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    numero_decision = models.CharField(max_length=80, verbose_name='رقم الحكم/القرار')
    date_prononce = models.DateTimeField(verbose_name='تاريخ النطق')
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

    def get_absolute_url(self):
        return reverse("cabinet:decision_detail", kwargs={"pk": self.pk})


class Notification(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE, verbose_name='الحكم/القرار')
    demande_numero = models.CharField(max_length=80, verbose_name='رقم طلب التبليغ')
    date_depot_demande = models.DateField(verbose_name='تاريخ إيداع الطلب')
    dossier_notification_numero = models.CharField(max_length=80, null=True, blank=True, verbose_name='رقم ملف التبليغ')
    huissier_nom = models.CharField(max_length=180, null=True, blank=True, verbose_name='اسم المفوض القضائي', validators=[arabic_name_validator])
    date_remise_huissier = models.DateField(null=True, blank=True, verbose_name='تاريخ التسليم للمفوض')
    date_signification = models.DateField(null=True, blank=True, verbose_name='تاريخ التبليغ')
    preuve = models.FileField(upload_to='notifications/', null=True, blank=True, verbose_name='محضر/إثبات (ملف)', validators=[file_extension_validator, validate_file_size])

    class Meta:
        db_table = 'notification'
        verbose_name = 'تبليغ'
        verbose_name_plural = 'تبليغات'
        indexes = [models.Index(fields=['date_signification'])]

    def get_absolute_url(self):
        return reverse("cabinet:notification_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"تبليغ لـ {self.decision.numero_decision}"


class VoieDeRecours(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE, verbose_name='الحكم/القرار')
    type_recours = models.ForeignKey(TypeRecours, on_delete=models.PROTECT, verbose_name="نوع الطعن")
    statut = models.ForeignKey(StatutRecours, on_delete=models.PROTECT, verbose_name="الحالة")
    date_depot = models.DateField(verbose_name='تاريخ الإيداع')
    numero_recours = models.CharField(max_length=80, null=True, blank=True, verbose_name='رقم ملف الطعن')
    juridiction = models.ForeignKey(Juridiction, on_delete=models.PROTECT, verbose_name='المحكمة')
    date_echeance_recours = models.DateField(null=True, blank=True, verbose_name='تاريخ انتهاء أجل الطعن')

    class Meta:
        db_table = 'voie_de_recours'
        verbose_name = 'طريق طعن'
        verbose_name_plural = 'طرق الطعن'

    def save(self, *args, **kwargs):
        if not self.date_echeance_recours and self.date_depot and self.type_recours_id:
            self.date_echeance_recours = self.date_depot + timedelta(days=self.type_recours.delai_legal_jours)
        super().save(*args, **kwargs)

    @property
    def is_deadline_expired(self):
        if not self.date_echeance_recours:
            return False
        return timezone.localdate() > self.date_echeance_recours

    @property
    def jours_restants_recours(self):
        if not self.date_echeance_recours:
            return None
        return (self.date_echeance_recours - timezone.localdate()).days

    @property
    def urgence_level(self):
        j = self.jours_restants_recours
        if j is None:
            return "green"
        if j <= 0:
            return "red"
        if j <= 5:
            return "red"
        if j <= 10:
            return "yellow"
        return "green"

    def get_absolute_url(self):
        return reverse("cabinet:voie_de_recours_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"طعن لـ {self.decision.numero_decision} — {self.type_recours}"


class Execution(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE, verbose_name='الحكم/القرار')
    type_execution = models.ForeignKey(TypeExecution, on_delete=models.PROTECT, verbose_name="نوع التنفيذ")
    statut = models.ForeignKey(StatutExecution, on_delete=models.PROTECT, verbose_name="حالة التنفيذ")
    date_demande = models.DateField(verbose_name='تاريخ الطلب')
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

    def get_absolute_url(self):
        return reverse("cabinet:execution_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"تنفيذ لـ {self.decision.numero_decision}"


class Depense(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    type_depense = models.ForeignKey(TypeDepense, on_delete=models.PROTECT, verbose_name="نوع المصروف")
    montant = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='المبلغ')
    date_depense = models.DateField(verbose_name='تاريخ الصرف')
    beneficiaire = models.CharField(max_length=180, null=True, blank=True, verbose_name='المستفيد', validators=[arabic_name_validator])
    piece = models.FileField(upload_to='depenses/', null=True, blank=True, verbose_name='مرفق (ملف)', validators=[file_extension_validator, validate_file_size])

    class Meta:
        db_table = 'depense'
        verbose_name = 'مصروف'
        verbose_name_plural = 'مصاريف'
        indexes = [models.Index(fields=['date_depense'])]

    def get_absolute_url(self):
        return reverse("cabinet:depense_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"مصروف في {self.affaire.reference_interne} — {self.montant} د.م."

class Recette(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, verbose_name='القضية')
    type_recette = models.ForeignKey(TypeRecette, on_delete=models.PROTECT, verbose_name="نوع الدخل")
    montant = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='المبلغ')
    date_recette = models.DateField(verbose_name='تاريخ التحصيل')
    source = models.CharField(max_length=180, null=True, blank=True, verbose_name='المصدر', validators=[arabic_text_validator])
    piece = models.FileField(upload_to='recettes/', null=True, blank=True, verbose_name='مرفق (ملف)', validators=[file_extension_validator, validate_file_size])

    class Meta:
        db_table = 'recette'
        verbose_name = 'دخل/تحصيل'
        verbose_name_plural = 'مداخيل'
        indexes = [models.Index(fields=['date_recette'])]

    def get_absolute_url(self):
        return reverse("cabinet:recette_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"دخل في {self.affaire.reference_interne} — {self.montant} د.م."

class PieceJointe(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, related_name='pieces', verbose_name='القضية')
    titre = models.CharField(max_length=180, verbose_name='عنوان المرفق', validators=[arabic_text_validator])
    type_piece = models.CharField(max_length=10, choices=[('PDF','PDF'),('Image','صورة'),('Doc','مستند'),('Audio','صوت'),('Autre','أخرى')], verbose_name='نوع الملف')
    fichier = models.FileField(upload_to='pieces/', verbose_name='ملف', validators=[file_extension_validator, validate_file_size])
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        db_table = 'piece_jointe'
        verbose_name = 'مرفق'
        verbose_name_plural = 'مرفقات'

    def get_absolute_url(self):
        return reverse("cabinet:piece_jointe_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"{self.titre} — {self.affaire.reference_interne}"

class Expert(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nom_complet = models.CharField(max_length=120, verbose_name='الاسم الكامل', validators=[arabic_name_validator])
    telephone = models.CharField(max_length=30, null=True, blank=True, verbose_name='هاتف')
    email = models.EmailField(max_length=120, verbose_name='بريد إلكتروني', validators=[EmailValidator()])
    adresse = models.CharField(max_length=120, verbose_name='العنوان', validators=[arabic_name_validator])
    specialite = models.CharField(max_length=120, verbose_name='التخصص', validators=[arabic_name_validator])

    class Meta:
        db_table = 'expert'
        verbose_name = 'خبير'
        verbose_name_plural = 'خبراء'

    def __str__(self):
        return f"{self.nom_complet} ({self.specialite})"

    def get_absolute_url(self):
        return reverse("cabinet:expert_detail", kwargs={"pk": self.pk})

class Utilisateur(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nom_complet = models.CharField(max_length=120, verbose_name='الاسم الكامل', validators=[arabic_name_validator])
    role = models.ForeignKey(RoleUtilisateur, on_delete=models.PROTECT, verbose_name="الدور")
    telephone = models.CharField(max_length=30, null=True, blank=True, verbose_name='هاتف')
    email = models.EmailField(max_length=120, verbose_name='بريد إلكتروني', validators=[EmailValidator()])
    actif = models.BooleanField(default=True, verbose_name='نشط')
    preferences_langue = models.CharField(max_length=2, choices=[('ar','العربية'),('fr','الفرنسية')], default='ar', verbose_name='لغة التفضيل')

    class Meta:
        db_table = 'utilisateur'
        verbose_name = 'مستخدم'
        verbose_name_plural = 'مستخدمون'

    def __str__(self):
        return f"{self.nom_complet} ({self.role})"

    def get_absolute_url(self):
        return reverse("cabinet:utilisateur_detail", kwargs={"pk": self.pk})

class Tache(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='القضية')
    titre = models.CharField(max_length=180, verbose_name='عنوان المهمة', validators=[arabic_text_validator])
    description = models.TextField(null=True, blank=True, verbose_name='وصف', validators=[arabic_text_validator])
    echeance = models.DateTimeField(null=True, blank=True, verbose_name='موعد الاستحقاق')
    assigne_a = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='مكلّف')
    statut = models.ForeignKey(StatutTache, on_delete=models.PROTECT, verbose_name="الحالة")

    class Meta:
        db_table = 'tache'
        verbose_name = 'مهمة'
        verbose_name_plural = 'مهام'
        indexes = [models.Index(fields=['echeance'])]

    def __str__(self):
        return f"{self.titre} — {self.statut}"

    def get_absolute_url(self):
        return reverse("cabinet:tache_detail", kwargs={"pk": self.pk})

class Alerte(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    type_alerte = models.ForeignKey(TypeAlerte, on_delete=models.PROTECT, verbose_name="نوع التنبيه")
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
        return f"{self.type_alerte} — {self.date_alerte:%Y-%m-%d %H:%M}"

    def get_absolute_url(self):
        return reverse("cabinet:alerte_detail", kwargs={"pk": self.pk})

class JournalActivite(TimeStampedSoftDeleteModel):
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

    def get_absolute_url(self):
        return reverse("cabinet:journal_activite_detail", kwargs={"pk": self.pk})

# إذا كان لديك موديل Utilisateur هو الـUser الفعلي:
# settings.AUTH_USER_MODEL يجب أن يشير إليه (مثلاً "avocat_app.Utilisateur")

class DocumentRequirement(TimeStampedSoftDeleteModel):
    phase = models.CharField(max_length=20, choices=PhaseAffaire.choices, verbose_name='المرحلة')
    type_affaire = models.ForeignKey(TypeAffaire, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='نوع القضية')
    nom_document = models.CharField(max_length=180, verbose_name='اسم الوثيقة', validators=[arabic_text_validator])
    nom_document_fr = models.CharField(max_length=180, blank=True, default='', verbose_name='nom du document')
    obligatoire = models.BooleanField(default=True, verbose_name='إلزامي')
    description = models.TextField(null=True, blank=True, verbose_name='وصف', validators=[arabic_text_validator])
    ordre = models.PositiveIntegerField(default=0, verbose_name='الترتيب')

    class Meta:
        db_table = 'document_requirement'
        verbose_name = 'متطلب وثائقي'
        verbose_name_plural = 'متطلبات وثائقية'
        ordering = ['phase', 'ordre']

    def __str__(self):
        return f"{self.nom_document} ({self.get_phase_display()})"


class AuthToken(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    # FK إلى المستخدم — اسم الحقل لديك "utilisateur"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='المستخدم', related_name="tokens")
    token = models.CharField(max_length=255, unique=True, verbose_name='رمز المصادقة')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    date_expiration = models.DateTimeField(verbose_name='تاريخ الانتهاء')
    # لإدارة عدم النشاط:
    last_seen = models.DateTimeField(default=timezone.now, verbose_name='آخر نشاط')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    user_agent = models.CharField(max_length=256, null=True, blank=True)
    ip_addr = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "is_active"]),
        ]
        verbose_name = "رمز مصادقة"
        verbose_name_plural = "رموز المصادقة"

    def __str__(self):
        return f"{self.user} — {self.token[:8]}…"

    @classmethod
    def issue(cls, user, request=None):
        """
        إنشاء توكن جديد للمستخدم مع انتهاء بعد مهلة الخمول (5 دقائق افتراضيًا).
        """
        idle_seconds = int(getattr(settings, "TOKEN_IDLE_TIMEOUT_SECONDS", 300))
        now = timezone.now()
        tok = secrets.token_urlsafe(48)
        ua = None
        ip = None
        if request is not None:
            ua = (request.META.get("HTTP_USER_AGENT") or "")[:256] or None
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            if xff:
                ip = xff.split(",")[0].strip()
            else:
                ip = request.META.get("REMOTE_ADDR")
            if ip and ":" in ip and "." not in ip:
                ip = ip.split("%")[0]
        return cls.objects.create(
            user=user,
            token=tok,
            date_expiration=now + timedelta(seconds=idle_seconds),
            last_seen=now,
            is_active=True,
            user_agent=ua,
            ip_addr=ip,
        )

    def touch(self):
        """
        تحديث آخر نشاط وإعادة ضبط تاريخ الانتهاء بناءً على عدم النشاط.
        """
        idle_seconds = int(getattr(settings, "TOKEN_IDLE_TIMEOUT_SECONDS", 300))
        now = timezone.now()
        self.last_seen = now
        self.date_expiration = now + timedelta(seconds=idle_seconds)
        self.save(update_fields=["last_seen", "date_expiration"])

    def revoke(self):
        if self.is_active:
            self.is_active = False
            self.save(update_fields=["is_active"])


class MahakimSyncResult(TimeStampedSoftDeleteModel):
    SYNC_TYPE_CHOICES = [
        ('dossier', 'ملف/محضر/شكاية'),
        ('sessions', 'جدول الجلسات'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    affaire = models.ForeignKey(Affaire, on_delete=models.CASCADE, related_name='mahakim_syncs', verbose_name='القضية',
                                null=True, blank=True)
    date_sync = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ المزامنة')
    sync_type = models.CharField(max_length=20, default='dossier', choices=SYNC_TYPE_CHOICES, verbose_name='نوع المزامنة')
    statut_mahakim = models.CharField(max_length=200, null=True, blank=True, verbose_name='حالة القضية بمحاكم')
    prochaine_audience = models.DateField(null=True, blank=True, verbose_name='الجلسة القادمة')
    juge = models.CharField(max_length=200, null=True, blank=True, verbose_name='القاضي')
    observations = models.TextField(null=True, blank=True, verbose_name='ملاحظات')
    raw_html = models.TextField(null=True, blank=True, verbose_name='HTML خام')
    success = models.BooleanField(default=False, verbose_name='نجاح المزامنة')
    error_message = models.TextField(null=True, blank=True, verbose_name='رسالة الخطأ')
    procedures_json = models.JSONField(null=True, blank=True, verbose_name='الإجراءات المستخرجة')
    parties_json = models.JSONField(null=True, blank=True, verbose_name='الأطراف المستخرجة')

    class Meta:
        db_table = 'mahakim_sync_result'
        verbose_name = 'نتيجة مزامنة محاكم'
        verbose_name_plural = 'نتائج مزامنة محاكم'
        ordering = ['-date_sync']

    def __str__(self):
        status = "✓" if self.success else "✗"
        ref = self.affaire.reference_interne if self.affaire else self.get_sync_type_display()
        return f"{status} مزامنة {ref} — {self.date_sync:%Y-%m-%d %H:%M}"


class ContumaceRecord(TimeStampedSoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    cour_appel = models.CharField(max_length=200, verbose_name='محكمة الاستئناف')
    numero_dossier = models.CharField(max_length=100, verbose_name='رقم الملف')
    nom_accuse = models.CharField(max_length=200, verbose_name='اسم المتهم')
    nom_pere = models.CharField(max_length=200, null=True, blank=True, verbose_name='اسم الأب')
    nom_mere = models.CharField(max_length=200, null=True, blank=True, verbose_name='اسم الأم')
    numero_carte = models.CharField(max_length=50, null=True, blank=True, verbose_name='رقم البطاقة')
    details_text = models.TextField(null=True, blank=True, verbose_name='التفاصيل')
    date_sync = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ المزامنة')

    class Meta:
        db_table = 'contumace_record'
        verbose_name = 'سجل المسطرة الغيابية'
        verbose_name_plural = 'سجلات المسطرة الغيابية'
        ordering = ['-date_sync']
        unique_together = [('numero_dossier', 'cour_appel')]

    def __str__(self):
        return f"{self.nom_accuse} — {self.numero_dossier} ({self.cour_appel})"


class TaxCalculatorCache(models.Model):
    """
    Cache les options du calculateur de taxes judiciaires
    (caisseenligne.justice.gov.ma/CalculTaxes/CalculTaxes).

    Stocke l'arbre complet des options cascadées en JSON:
    {
        "مدني": {
            "options_type_maqal": [
                {
                    "value": "...", "label": "...",
                    "categories": [
                        {"value": "...", "label": "...", "types_qadiya": ["..."]}
                    ]
                }
            ]
        },
        ...
    }
    """
    id = models.AutoField(primary_key=True)
    options_tree = models.JSONField(default=dict, verbose_name='شجرة الخيارات')
    date_sync = models.DateTimeField(auto_now=True, verbose_name='تاريخ المزامنة')

    class Meta:
        db_table = 'tax_calculator_cache'
        verbose_name = 'ذاكرة حاسبة الرسوم'

    def __str__(self):
        return f"Tax Cache — {self.date_sync:%Y-%m-%d %H:%M}"


# =============================================================
# WhatsApp / Twilio messaging
# =============================================================

class WhatsAppTemplate(TimeStampedSoftDeleteModel):
    """Modèle de message WhatsApp réutilisable avec variables {{...}}.
    Variables disponibles selon le contexte (audience J-1):
    - {{client}} : nom du client
    - {{ref}} : référence interne de l'affaire
    - {{tribunal}} : nom du tribunal
    - {{date}} : date de l'audience (JJ/MM/AAAA)
    - {{heure}} : heure de l'audience (HH:MM)
    - {{avocat}} : nom de l'avocat responsable
    """
    KIND_CHOICES = [
        ('audience_j1', 'تذكير بجلسة (يوم قبل)'),
        ('audience_j0', 'تذكير بجلسة (اليوم)'),
        ('decision_rendue', 'إشعار بصدور حكم'),
        ('piece_manquante', 'طلب وثيقة'),
        ('rdv', 'تأكيد موعد'),
        ('autre', 'أخرى'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nom = models.CharField(max_length=120, verbose_name='اسم القالب')
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default='audience_j1', verbose_name='النوع')
    body = models.TextField(verbose_name='نص الرسالة',
                            help_text='يمكن استعمال المتغيرات: {{client}} {{ref}} {{tribunal}} {{date}} {{heure}} {{avocat}}')
    is_active = models.BooleanField(default=True, verbose_name='مفعّل')
    twilio_content_sid = models.CharField(max_length=64, null=True, blank=True,
                                          verbose_name='Twilio Content SID',
                                          help_text='إذا كانت Twilio تتطلب قالب معتمد (Business)')

    class Meta:
        db_table = 'whatsapp_template'
        verbose_name = 'قالب واتساب'
        verbose_name_plural = 'قوالب واتساب'
        ordering = ['kind', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_kind_display()})"

    def render(self, context: dict) -> str:
        text = self.body or ""
        for k, v in (context or {}).items():
            text = text.replace("{{" + k + "}}", str(v if v is not None else ""))
        return text


class WhatsAppMessage(TimeStampedSoftDeleteModel):
    """Journal des messages WhatsApp envoyés via Twilio."""
    STATUS_CHOICES = [
        ('pending', 'في الانتظار'),
        ('sent', 'تم الإرسال'),
        ('delivered', 'تم التسليم'),
        ('read', 'تمت القراءة'),
        ('failed', 'فشل الإرسال'),
        ('dry_run', 'محاكاة (بدون إرسال)'),
        ('received', 'وارد'),
    ]
    DIRECTION_CHOICES = [
        ('outbound', 'صادر'),
        ('inbound', 'وارد'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default='outbound',
                                 verbose_name='الاتجاه')
    affaire = models.ForeignKey(Affaire, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='whatsapp_messages', verbose_name='القضية')
    audience = models.ForeignKey(Audience, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='whatsapp_messages', verbose_name='الجلسة')
    template = models.ForeignKey(WhatsAppTemplate, null=True, blank=True, on_delete=models.SET_NULL,
                                 verbose_name='القالب')
    to_number = models.CharField(max_length=30, verbose_name='رقم المستلم',
                                 help_text='بصيغة E.164 (+212...)')
    to_name = models.CharField(max_length=180, null=True, blank=True, verbose_name='اسم المستلم')
    body = models.TextField(verbose_name='نص الرسالة المُرسلة')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='الحالة')
    twilio_sid = models.CharField(max_length=64, null=True, blank=True, verbose_name='معرف Twilio')
    error_message = models.TextField(null=True, blank=True, verbose_name='رسالة الخطأ')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإرسال')

    class Meta:
        db_table = 'whatsapp_message'
        verbose_name = 'رسالة واتساب'
        verbose_name_plural = 'رسائل واتساب'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['to_number']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['direction']),
        ]

    def __str__(self):
        arrow = "←" if self.direction == "inbound" else "→"
        return f"WA {arrow} {self.to_number} ({self.get_status_display()})"


# =============================================================
# AI — Résumé automatique de décision (Claude)
# =============================================================

class DecisionAnalysis(TimeStampedSoftDeleteModel):
    """Résumé et extraction structurée d'une décision par l'IA (Claude)."""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    decision = models.OneToOneField(Decision, on_delete=models.CASCADE,
                                    related_name='analysis', verbose_name='الحكم')
    source_text = models.TextField(null=True, blank=True, verbose_name='النص المصدر',
                                   help_text='Texte source soumis à l\'IA (extrait du PDF ou saisi).')
    resume_ar = models.TextField(null=True, blank=True, verbose_name='ملخص بالعربية')
    resume_fr = models.TextField(null=True, blank=True, verbose_name='Résumé en français')
    decision_essentielle = models.TextField(null=True, blank=True, verbose_name='القرار الجوهري')
    parties_extraites = models.JSONField(null=True, blank=True, verbose_name='الأطراف المستخرجة',
                                         help_text='[{nom, role}]')
    motifs = models.JSONField(null=True, blank=True, verbose_name='الحيثيات',
                              help_text='[{titre, contenu}]')
    delai_appel_jours = models.IntegerField(null=True, blank=True, verbose_name='أجل الاستئناف (أيام)')
    dates_importantes = models.JSONField(null=True, blank=True, verbose_name='تواريخ مهمة',
                                         help_text='[{label, date_iso}]')
    raw_response = models.TextField(null=True, blank=True, verbose_name='الاستجابة الخام')
    model_used = models.CharField(max_length=64, null=True, blank=True, verbose_name='النموذج')
    is_dry_run = models.BooleanField(default=False, verbose_name='محاكاة (بدون استدعاء API)')
    error_message = models.TextField(null=True, blank=True, verbose_name='رسالة الخطأ')
    generated_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت التحليل')
    embedding = models.JSONField(null=True, blank=True, verbose_name='التضمين',
                                 help_text='Vecteur de similarité sémantique (list[float]).')
    embedding_model = models.CharField(max_length=64, null=True, blank=True,
                                       verbose_name='نموذج التضمين')

    class Meta:
        db_table = 'decision_analysis'
        verbose_name = 'تحليل الحكم'
        verbose_name_plural = 'تحاليل الأحكام'
        ordering = ['-generated_at']

    def __str__(self):
        return f"تحليل — {self.decision.numero_decision}"


# =============================================================
# Portail client — Accès sécurisé par magic link
# =============================================================

class PortailAccess(TimeStampedSoftDeleteModel):
    """Token magique pour l'accès au portail client par une Partie.

    Le token est généré, envoyé par email ou WhatsApp, et permet une
    session lecture seule de courte durée (par défaut 24h).
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    partie = models.ForeignKey(Partie, on_delete=models.CASCADE,
                               related_name='portail_accesses', verbose_name='الطرف')
    token = models.CharField(max_length=80, unique=True, verbose_name='رمز الوصول')
    expires_at = models.DateTimeField(verbose_name='ينتهي في')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='تم الاستعمال في')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='عنوان IP')
    user_agent = models.CharField(max_length=256, null=True, blank=True, verbose_name='User Agent')
    revoked = models.BooleanField(default=False, verbose_name='ملغى')

    class Meta:
        db_table = 'portail_access'
        verbose_name = 'وصول إلى البوابة'
        verbose_name_plural = 'وصولات إلى البوابة'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['partie', 'revoked']),
        ]

    def __str__(self):
        return f"Portail — {self.partie.nom_complet} (expire {self.expires_at:%Y-%m-%d %H:%M})"

    @property
    def is_valid(self) -> bool:
        from django.utils import timezone
        return (
            not self.revoked
            and self.expires_at > timezone.now()
        )

    def revoke(self):
        if not self.revoked:
            self.revoked = True
            self.save(update_fields=["revoked"])


# =============================================================
# Paramètres du cabinet — utilisés pour les en-têtes/footers PDF
# =============================================================

class CabinetParams(TimeStampedSoftDeleteModel):
    """Paramètres du cabinet d'avocat (singleton).

    Utilisé pour générer les en-têtes / pieds de page des PDFs imprimés,
    et personnaliser l'application multi-tenant.
    Toujours récupéré via CabinetParams.get_solo().
    """
    nom_cabinet_ar = models.CharField(max_length=200, blank=True, default='',
                                       verbose_name='اسم المكتب (عربية)')
    nom_cabinet_fr = models.CharField(max_length=200, blank=True, default='',
                                       verbose_name='اسم المكتب (فرنسية)')
    nom_avocat_ar = models.CharField(max_length=200, blank=True, default='',
                                      verbose_name='اسم المحامي (عربية)')
    nom_avocat_fr = models.CharField(max_length=200, blank=True, default='',
                                      verbose_name='اسم المحامي (فرنسية)')
    barreau = models.CharField(max_length=120, blank=True, default='',
                                verbose_name='الهيئة')
    numero_carte_pro = models.CharField(max_length=60, blank=True, default='',
                                          verbose_name='رقم البطاقة المهنية')
    adresse = models.TextField(blank=True, default='', verbose_name='العنوان')
    ville = models.CharField(max_length=120, blank=True, default='', verbose_name='المدينة')
    telephone = models.CharField(max_length=30, blank=True, default='', verbose_name='الهاتف')
    fax = models.CharField(max_length=30, blank=True, default='', verbose_name='الفاكس')
    email = models.EmailField(blank=True, default='', verbose_name='البريد الإلكتروني')
    site_web = models.URLField(blank=True, default='', verbose_name='الموقع الإلكتروني')
    ice = models.CharField(max_length=30, blank=True, default='',
                            verbose_name='ICE')
    rib = models.CharField(max_length=40, blank=True, default='',
                            verbose_name='RIB')
    logo_cabinet = models.ImageField(upload_to='cabinet/', blank=True, null=True,
                                       verbose_name='شعار المكتب')
    logo_ministere = models.ImageField(upload_to='cabinet/', blank=True, null=True,
                                         verbose_name='شعار وزارة العدل (اختياري)')
    devise_ar = models.CharField(max_length=200, blank=True,
                                  default='المملكة المغربية — وزارة العدل',
                                  verbose_name='الشعار (الرأس)')
    pied_page_ar = models.TextField(blank=True, default='',
                                     verbose_name='نص أسفل الصفحة')

    class Meta:
        db_table = 'cabinet_params'
        verbose_name = 'إعدادات المكتب'
        verbose_name_plural = 'إعدادات المكتب'

    def __str__(self):
        return self.nom_cabinet_ar or self.nom_avocat_ar or 'إعدادات المكتب'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# =============================================
# SyncOutbox — staging table for desktop (.exe/.apk) local writes.
# Filled by post_save/post_delete signals when DESKTOP_MODE is True;
# drained by the desktop sync engine which pushes to the central API.
# =============================================
class SyncOutbox(models.Model):
    UPSERT = "upsert"
    DELETE = "delete"
    OP_CHOICES = [(UPSERT, "upsert"), (DELETE, "delete")]

    table_name = models.CharField(max_length=64, db_index=True)
    entity_id = models.CharField(max_length=64)
    op = models.CharField(max_length=8, choices=OP_CHOICES)
    changed_fields = models.TextField(null=True, blank=True)
    client_updated_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    pushed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "sync_outbox"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["pushed_at", "created_at"]),
            models.Index(fields=["table_name", "entity_id"]),
        ]

    def __str__(self):
        return f"[{self.op}] {self.table_name}:{self.entity_id}"
