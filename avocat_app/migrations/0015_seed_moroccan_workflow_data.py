# -*- coding: utf-8 -*-
"""
Seed data migration for Moroccan legal workflow:
- TypeAvertissement (notice types with legal deadlines)
- TypeRecours delays
- DocumentRequirement per phase
"""
from django.db import migrations


def seed_type_avertissement(apps, schema_editor):
    TypeAvertissement = apps.get_model('avocat_app', 'TypeAvertissement')
    data = [
        {
            "libelle": "إنذار بالأداء",
            "libelle_fr": "Mise en demeure de paiement",
            "delai_legal_jours": 15,
            "domaine": "commercial",
            "base_legale": "المادة 155 من مدونة التجارة",
        },
        {
            "libelle": "إنذار بالإفراغ",
            "libelle_fr": "Mise en demeure d'évacuation",
            "delai_legal_jours": 30,
            "domaine": "civil",
            "base_legale": "ظهير 1955",
        },
        {
            "libelle": "إنذار بالتنفيذ",
            "libelle_fr": "Mise en demeure d'exécution",
            "delai_legal_jours": 10,
            "domaine": "civil",
            "base_legale": "المادة 440 ق.م.م",
        },
        {
            "libelle": "إنذار بتسوية الوضعية",
            "libelle_fr": "Mise en demeure de régularisation",
            "delai_legal_jours": 30,
            "domaine": "civil",
            "base_legale": "",
        },
    ]
    for item in data:
        TypeAvertissement.objects.get_or_create(libelle=item["libelle"], defaults=item)


def seed_type_recours_delays(apps, schema_editor):
    TypeRecours = apps.get_model('avocat_app', 'TypeRecours')
    delays = {
        "استئناف مدني": {"delai_legal_jours": 30, "domaine": "civil"},
        "استئناف جنائي": {"delai_legal_jours": 10, "domaine": "penal"},
        "استئناف تجاري": {"delai_legal_jours": 15, "domaine": "commercial"},
        "نقض": {"delai_legal_jours": 30, "domaine": "civil"},
        "تعرض": {"delai_legal_jours": 10, "domaine": "civil"},
    }
    for libelle, vals in delays.items():
        obj, created = TypeRecours.objects.get_or_create(
            libelle=libelle,
            defaults={"libelle_fr": libelle, **vals}
        )
        if not created:
            TypeRecours.objects.filter(pk=obj.pk).update(**vals)


def seed_document_requirements(apps, schema_editor):
    DocumentRequirement = apps.get_model('avocat_app', 'DocumentRequirement')
    requirements = [
        # المرحلة التمهيدية
        {"phase": "PRELIMINAIRE", "nom_document": "نسخة الإنذار", "nom_document_fr": "Copie de la mise en demeure", "obligatoire": True, "ordre": 1},
        {"phase": "PRELIMINAIRE", "nom_document": "إثبات التوصل", "nom_document_fr": "Preuve de réception", "obligatoire": True, "ordre": 2},
        # المحكمة الابتدائية
        {"phase": "PREMIERE_INSTANCE", "nom_document": "مقال افتتاحي", "nom_document_fr": "Requête introductive", "obligatoire": True, "ordre": 1},
        {"phase": "PREMIERE_INSTANCE", "nom_document": "وكالة", "nom_document_fr": "Procuration", "obligatoire": True, "ordre": 2},
        {"phase": "PREMIERE_INSTANCE", "nom_document": "نسخة البطاقة الوطنية", "nom_document_fr": "Copie CIN", "obligatoire": True, "ordre": 3},
        {"phase": "PREMIERE_INSTANCE", "nom_document": "مستندات الإثبات", "nom_document_fr": "Pièces justificatives", "obligatoire": False, "ordre": 4},
        # الاستئناف
        {"phase": "APPEL", "nom_document": "مقال استئنافي", "nom_document_fr": "Requête d'appel", "obligatoire": True, "ordre": 1},
        {"phase": "APPEL", "nom_document": "نسخة الحكم الابتدائي", "nom_document_fr": "Copie du jugement", "obligatoire": True, "ordre": 2},
        {"phase": "APPEL", "nom_document": "شهادة التبليغ", "nom_document_fr": "Certificat de notification", "obligatoire": True, "ordre": 3},
        # النقض
        {"phase": "CASSATION", "nom_document": "عريضة النقض", "nom_document_fr": "Mémoire de cassation", "obligatoire": True, "ordre": 1},
        {"phase": "CASSATION", "nom_document": "نسخة القرار الاستئنافي", "nom_document_fr": "Copie de l'arrêt", "obligatoire": True, "ordre": 2},
        # التنفيذ
        {"phase": "EXECUTION", "nom_document": "طلب التنفيذ", "nom_document_fr": "Demande d'exécution", "obligatoire": True, "ordre": 1},
        {"phase": "EXECUTION", "nom_document": "نسخة تنفيذية", "nom_document_fr": "Grosse exécutoire", "obligatoire": True, "ordre": 2},
    ]
    for req in requirements:
        DocumentRequirement.objects.get_or_create(
            phase=req["phase"],
            nom_document=req["nom_document"],
            defaults=req,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('avocat_app', '0014_moroccan_workflow_models'),
    ]

    operations = [
        migrations.RunPython(seed_type_avertissement, noop),
        migrations.RunPython(seed_type_recours_delays, noop),
        migrations.RunPython(seed_document_requirements, noop),
    ]
