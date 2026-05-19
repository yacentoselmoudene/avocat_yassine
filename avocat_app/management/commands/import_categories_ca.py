"""Importe les catégories d'affaires du PDF de la Cour d'Appel de Casablanca.

Source : http://www.cacasablanca.ma/ar/document/CodeCivil.pdf

Chaque catégorie est liée à un type de juridiction "initiale" :
- CA  : compétence directe de la Cour d'Appel (1er président, chambre du conseil...)
- TPI : compétence initiale du Tribunal de Première Instance
- TC  : compétence du Tribunal de Commerce
- TA  : compétence du Tribunal Administratif
- QAF : compétence de la Section Famille (au sein du TPI)

Usage:
    python manage.py import_categories_ca
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from avocat_app.models import CodeCategorieAffaire, TypeJuridiction


# Format : (code, libellé arabe, domaine, code_type_juridiction_initiale)
CATEGORIES = [
    # ============ مؤسسة الرئيس الأول و غرفة المشورة ============
    # Compétence directe de la Cour d'Appel (1er président)
    ("1101", "الإستعجالي", "civil", "CA"),
    ("1120", "الطعن ضد مقررات تحديد الأتعاب الصادرة عن نقيب هيئة المحامين", "civil", "CA"),
    ("1121", "صعوبة التنفيذ", "execution", "CA"),
    ("1122", "أداء اليمين المهنية", "civil", "CA"),
    ("1123", "إيقاف التنفيذ", "execution", "CA"),
    ("1124", "الطعون ضد مقررات مجلس هيئة المحامين و نزاعات المحامين", "civil", "CA"),
    ("1125", "مخالفات العدول المهنية", "civil", "CA"),
    ("1126", "مخالفات المفوضين القضائين المهنية", "civil", "CA"),
    ("1127", "مخالفات الموثقين المهنية", "civil", "CA"),

    # ============ المدني ============
    ("1201", "المدني المتنوع", "civil", "TPI"),
    ("1202", "المسؤولية التقصيرية", "civil", "TPI"),
    ("1203", "التجاري", "commercial", "TC"),
    ("1204", "الإداري", "administratif", "TA"),
    ("1207", "تذييل بالصيغة التنفيذية", "execution", "TPI"),
    ("1208", "المسطرة التأديبية", "civil", "CA"),
    ("1209", "غرفة المشورة للقضايا المدنية", "civil", "CA"),
    ("1210", "مدني عبري", "civil", "TPI"),
    ("1220", "الأوامر بالأداء المستأنفة", "civil", "TPI"),
    ("1221", "القضايا الإستعجالية المستأنفة", "civil", "TPI"),

    # ============ الأكرية ============
    ("1301", "أداء واجبات الكراء", "civil", "TPI"),
    ("1302", "الإفراغ", "civil", "TPI"),
    ("1303", "الأداء والإفراغ", "civil", "TPI"),
    ("1304", "مراجعة السومة الكرائية", "civil", "TPI"),
    ("1305", "غرفة المشورة لقضايا الأكرية", "civil", "CA"),

    # ============ العقار ============
    ("1401", "العقار العادي", "immobilier", "TPI"),
    ("1402", "العقار المحفظ", "immobilier", "TPI"),
    ("1403", "العقار في طور التحفيظ", "immobilier", "TPI"),
    ("1404", "القضايا العقارية العينية المختلطة", "immobilier", "TPI"),
    ("1405", "غرفة المشورة لقضايا العقار", "immobilier", "CA"),
    ("1406", "عقار عبري", "immobilier", "TPI"),

    # ============ الاجتماعي ============
    ("1501", "نزاعات الشغل", "social", "TPI"),
    ("1502", "حوادث الشغل", "social", "TPI"),
    ("1503", "الأمراض المهنية", "social", "TPI"),
    ("1504", "غرفة المشورة لقضايا نزاعات الشغل", "social", "CA"),
    ("1505", "غرفة المشورة لقضايا حوادث الشغل", "social", "CA"),

    # ============ الأحوال الشخصية ============
    ("1601", "الإصلاح والتغيير", "famille", "QAF"),
    ("1602", "تسجيل الولادة", "famille", "QAF"),
    ("1603", "تسجيل الوفاة", "famille", "QAF"),
    ("1604", "إضافة بيانات", "famille", "QAF"),
    ("1606", "النفقة", "famille", "QAF"),
    ("1609", "الحضانة", "famille", "QAF"),
    ("1610", "الرجوع لبيت الزوجية", "famille", "QAF"),
    ("1611", "ثبوت الزوجية", "famille", "QAF"),
    ("1612", "صلة الرحم", "famille", "QAF"),
    ("1613", "النسب", "famille", "QAF"),
    ("1614", "التذييل بالصيغة التنفيذية (أسرة)", "famille", "QAF"),
    ("1615", "الميراث", "famille", "QAF"),
    ("1616", "زواج القاصر", "famille", "QAF"),
    ("1617", "الكفالة (مهملين وغير مهملين)", "famille", "QAF"),
    ("1618", "الإذن بالتعدد", "famille", "QAF"),
    ("1619", "المحاجير", "famille", "QAF"),
    ("1620", "قضايا الأحوال الشخصية الأخرى", "famille", "QAF"),
    ("1621", "غرفة المشورة لقضايا الأسرة", "famille", "CA"),
    ("1622", "مراجعة لوازم الطلاق", "famille", "QAF"),
    ("1623", "التحجير", "famille", "QAF"),
]


class Command(BaseCommand):
    help = "Importe les catégories d'affaires depuis le PDF de la CA de Casablanca."

    @transaction.atomic
    def handle(self, *args, **options):
        # Lookup table : code TypeJuridiction → instance
        type_juridictions = {tj.code_type: tj for tj in TypeJuridiction.objects.all()}
        missing = {tj for tj in {"TPI", "CA", "TC", "TA", "QAF"} if tj not in type_juridictions}
        if missing:
            self.stdout.write(self.style.ERROR(
                f"TypeJuridiction manquants : {missing}. Lance d'abord les migrations qui les peuplent."
            ))
            return

        created = updated = 0
        for code, libelle, domaine, tj_code in CATEGORIES:
            tj = type_juridictions.get(tj_code)
            obj, was_created = CodeCategorieAffaire.objects.update_or_create(
                code=code,
                defaults={
                    "libelle": libelle,
                    "domaine": domaine,
                    "type_juridiction_initiale": tj,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"  • {created} catégorie(s) créée(s), {updated} mise(s) à jour."
        ))
        # Récap par type de juridiction
        from collections import Counter
        repartition = Counter(c[3] for c in CATEGORIES)
        self.stdout.write("\n  Répartition par juridiction initiale :")
        for tj_code, n in sorted(repartition.items()):
            tj_label = type_juridictions[tj_code].libelle
            self.stdout.write(f"    - {tj_code} ({tj_label}) : {n}")
