from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('avocat_app', '0025_portailaccess_decisionanalysis_embedding_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CabinetParams',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('nom_cabinet_ar', models.CharField(blank=True, default='', max_length=200, verbose_name='اسم المكتب (عربية)')),
                ('nom_cabinet_fr', models.CharField(blank=True, default='', max_length=200, verbose_name='اسم المكتب (فرنسية)')),
                ('nom_avocat_ar', models.CharField(blank=True, default='', max_length=200, verbose_name='اسم المحامي (عربية)')),
                ('nom_avocat_fr', models.CharField(blank=True, default='', max_length=200, verbose_name='اسم المحامي (فرنسية)')),
                ('barreau', models.CharField(blank=True, default='', max_length=120, verbose_name='الهيئة')),
                ('numero_carte_pro', models.CharField(blank=True, default='', max_length=60, verbose_name='رقم البطاقة المهنية')),
                ('adresse', models.TextField(blank=True, default='', verbose_name='العنوان')),
                ('ville', models.CharField(blank=True, default='', max_length=120, verbose_name='المدينة')),
                ('telephone', models.CharField(blank=True, default='', max_length=30, verbose_name='الهاتف')),
                ('fax', models.CharField(blank=True, default='', max_length=30, verbose_name='الفاكس')),
                ('email', models.EmailField(blank=True, default='', max_length=254, verbose_name='البريد الإلكتروني')),
                ('site_web', models.URLField(blank=True, default='', verbose_name='الموقع الإلكتروني')),
                ('ice', models.CharField(blank=True, default='', max_length=30, verbose_name='ICE')),
                ('rib', models.CharField(blank=True, default='', max_length=40, verbose_name='RIB')),
                ('logo_cabinet', models.ImageField(blank=True, null=True, upload_to='cabinet/', verbose_name='شعار المكتب')),
                ('logo_ministere', models.ImageField(blank=True, null=True, upload_to='cabinet/', verbose_name='شعار وزارة العدل (اختياري)')),
                ('devise_ar', models.CharField(blank=True, default='المملكة المغربية — وزارة العدل', max_length=200, verbose_name='الشعار (الرأس)')),
                ('pied_page_ar', models.TextField(blank=True, default='', verbose_name='نص أسفل الصفحة')),
            ],
            options={
                'verbose_name': 'إعدادات المكتب',
                'verbose_name_plural': 'إعدادات المكتب',
                'db_table': 'cabinet_params',
            },
        ),
    ]
