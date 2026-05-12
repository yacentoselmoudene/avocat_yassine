# Generated data migration — add commercial & administrative courts (2024 judicial map)
from django.db import migrations


def add_courts(apps, schema_editor):
    TypeJuridiction = apps.get_model('avocat_app', 'TypeJuridiction')
    Juridiction = apps.get_model('avocat_app', 'Juridiction')

    # --- 1. New TypeJuridiction entries ---
    type_ca_com, _ = TypeJuridiction.objects.get_or_create(
        code_type='CA_COM',
        defaults={
            'libelle': 'محكمة استئناف تجارية',
            'niveau': 'استئناف',
            'description': 'محكمة الاستئناف التجارية — الدرجة الثانية في القضاء التجاري',
            'libelle_fr': "Cour d'appel de commerce",
        }
    )
    type_ca_admin, _ = TypeJuridiction.objects.get_or_create(
        code_type='CA_ADMIN',
        defaults={
            'libelle': 'محكمة استئناف إدارية',
            'niveau': 'استئناف',
            'description': 'محكمة الاستئناف الإدارية — الدرجة الثانية في القضاء الإداري',
            'libelle_fr': "Cour d'appel administrative",
        }
    )

    # Existing types (for new first-instance courts)
    type_com = TypeJuridiction.objects.filter(code_type='TRIB_COM').first()
    type_admin = TypeJuridiction.objects.filter(code_type='TRIB_ADMIN').first()

    # --- Helper to create court if not exists ---
    def _get_or_create_court(nom_ar, nom_fr, ville_ar, ville_fr, court_type, code=''):
        existing = Juridiction.objects.filter(nomtribunal_ar=nom_ar).first()
        if existing:
            return existing
        return Juridiction.objects.create(
            code=code,
            nomtribunal_ar=nom_ar,
            nomtribunal_fr=nom_fr,
            villetribunal_ar=ville_ar,
            villetribunal_fr=ville_fr,
            type=court_type,
        )

    # --- 2. Commercial appeal courts (5) ---
    ca_com_courts = [
        ('محكمة الاستئناف التجارية بالدار البيضاء', "Cour d'appel de commerce de Casablanca", 'الدار البيضاء', 'Casablanca'),
        ('محكمة الاستئناف التجارية بفاس', "Cour d'appel de commerce de Fès", 'فاس', 'Fès'),
        ('محكمة الاستئناف التجارية بمراكش', "Cour d'appel de commerce de Marrakech", 'مراكش', 'Marrakech'),
        ('محكمة الاستئناف التجارية بطنجة', "Cour d'appel de commerce de Tanger", 'طنجة', 'Tanger'),
        ('محكمة الاستئناف التجارية بأكادير', "Cour d'appel de commerce d'Agadir", 'أكادير', 'Agadir'),
    ]

    ca_com_objs = {}
    for nom_ar, nom_fr, ville_ar, ville_fr in ca_com_courts:
        obj = _get_or_create_court(nom_ar, nom_fr, ville_ar, ville_fr, type_ca_com, 'CA_COM')
        ca_com_objs[ville_ar] = obj

    # --- 3. Administrative appeal courts (5) ---
    ca_admin_courts = [
        ('محكمة الاستئناف الإدارية بالرباط', "Cour d'appel administrative de Rabat", 'الرباط', 'Rabat'),
        ('محكمة الاستئناف الإدارية بمراكش', "Cour d'appel administrative de Marrakech", 'مراكش', 'Marrakech'),
        ('محكمة الاستئناف الإدارية بفاس', "Cour d'appel administrative de Fès", 'فاس', 'Fès'),
        ('محكمة الاستئناف الإدارية بأكادير', "Cour d'appel administrative d'Agadir", 'أكادير', 'Agadir'),
        ('محكمة الاستئناف الإدارية بطنجة', "Cour d'appel administrative de Tanger", 'طنجة', 'Tanger'),
    ]

    ca_admin_objs = {}
    for nom_ar, nom_fr, ville_ar, ville_fr in ca_admin_courts:
        obj = _get_or_create_court(nom_ar, nom_fr, ville_ar, ville_fr, type_ca_admin, 'CA_ADMIN')
        ca_admin_objs[ville_ar] = obj

    # --- 4. New first-instance commercial courts (3) ---
    if type_com:
        new_com = [
            ('المحكمة التجارية ببني ملال', 'Tribunal de commerce de Beni Mellal', 'بني ملال', 'Beni Mellal'),
            ('المحكمة التجارية بالعيون', 'Tribunal de commerce de Laâyoune', 'العيون', 'Laâyoune'),
            ('المحكمة التجارية بالداخلة', 'Tribunal de commerce de Dakhla', 'الداخلة', 'Dakhla'),
        ]
        for nom_ar, nom_fr, ville_ar, ville_fr in new_com:
            _get_or_create_court(nom_ar, nom_fr, ville_ar, ville_fr, type_com, 'TRIB_COM')

    # --- 5. New first-instance administrative courts (4) ---
    if type_admin:
        new_admin = [
            ('المحكمة الإدارية بطنجة', 'Tribunal administratif de Tanger', 'طنجة', 'Tanger'),
            ('المحكمة الإدارية ببني ملال', 'Tribunal administratif de Beni Mellal', 'بني ملال', 'Beni Mellal'),
            ('المحكمة الإدارية بالعيون', 'Tribunal administratif de Laâyoune', 'العيون', 'Laâyoune'),
            ('المحكمة الإدارية بالداخلة', 'Tribunal administratif de Dakhla', 'الداخلة', 'Dakhla'),
        ]
        for nom_ar, nom_fr, ville_ar, ville_fr in new_admin:
            _get_or_create_court(nom_ar, nom_fr, ville_ar, ville_fr, type_admin, 'TRIB_ADMIN')

    # --- 6. Set TribunalParent relationships ---
    # Commercial first instance → commercial appeal court
    com_parent_map = {
        'الدار البيضاء': 'الدار البيضاء',
        'الرباط': 'الدار البيضاء',
        'فاس': 'فاس',
        'مراكش': 'مراكش',
        'أكادير': 'أكادير',
        'وجدة': 'فاس',
        'طنجة': 'طنجة',
        'بني ملال': 'مراكش',
        'العيون': 'أكادير',
        'الداخلة': 'أكادير',
    }
    if type_com:
        for j in Juridiction.objects.filter(type=type_com):
            city = j.villetribunal_ar
            if city and city in com_parent_map:
                parent_city = com_parent_map[city]
                parent = ca_com_objs.get(parent_city)
                if parent and j.TribunalParent_id != parent.pk:
                    j.TribunalParent = parent
                    j.save(update_fields=['TribunalParent'])

    # Administrative first instance → administrative appeal court
    admin_parent_map = {
        'الرباط': 'الرباط',
        'الدار البيضاء': 'الرباط',
        'فاس': 'فاس',
        'مراكش': 'مراكش',
        'أكادير': 'أكادير',
        'وجدة': 'فاس',
        'مكناس': 'فاس',
        'طنجة': 'طنجة',
        'بني ملال': 'مراكش',
        'العيون': 'أكادير',
        'الداخلة': 'أكادير',
    }
    if type_admin:
        for j in Juridiction.objects.filter(type=type_admin):
            city = j.villetribunal_ar
            if city and city in admin_parent_map:
                parent_city = admin_parent_map[city]
                parent = ca_admin_objs.get(parent_city)
                if parent and j.TribunalParent_id != parent.pk:
                    j.TribunalParent = parent
                    j.save(update_fields=['TribunalParent'])


def remove_courts(apps, schema_editor):
    """Reverse: remove only the courts created by this migration."""
    TypeJuridiction = apps.get_model('avocat_app', 'TypeJuridiction')
    Juridiction = apps.get_model('avocat_app', 'Juridiction')

    # Remove commercial appeal courts
    Juridiction.objects.filter(
        nomtribunal_ar__startswith='محكمة الاستئناف التجارية'
    ).delete()
    # Remove administrative appeal courts
    Juridiction.objects.filter(
        nomtribunal_ar__startswith='محكمة الاستئناف الإدارية'
    ).delete()
    # Remove new first instance courts
    for name in ['المحكمة التجارية ببني ملال', 'المحكمة التجارية بالعيون',
                 'المحكمة التجارية بالداخلة', 'المحكمة الإدارية بطنجة',
                 'المحكمة الإدارية ببني ملال', 'المحكمة الإدارية بالعيون',
                 'المحكمة الإدارية بالداخلة']:
        Juridiction.objects.filter(nomtribunal_ar=name).delete()
    # Remove new types
    TypeJuridiction.objects.filter(code_type__in=['CA_COM', 'CA_ADMIN']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('avocat_app', '0020_contumace_record'),
    ]
    operations = [
        migrations.RunPython(add_courts, remove_courts),
    ]
