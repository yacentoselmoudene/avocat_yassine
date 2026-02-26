# Generated migration for MahakimSyncResult model
import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('avocat_app', '0016_code_categorie_affaire'),
    ]

    operations = [
        migrations.CreateModel(
            name='MahakimSyncResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='أُنشئ في')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تم التحديث في')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, verbose_name='محذوف؟')),
                ('date_sync', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ المزامنة')),
                ('statut_mahakim', models.CharField(blank=True, max_length=200, null=True, verbose_name='حالة القضية بمحاكم')),
                ('prochaine_audience', models.DateField(blank=True, null=True, verbose_name='الجلسة القادمة')),
                ('juge', models.CharField(blank=True, max_length=200, null=True, verbose_name='القاضي')),
                ('observations', models.TextField(blank=True, null=True, verbose_name='ملاحظات')),
                ('raw_html', models.TextField(blank=True, null=True, verbose_name='HTML خام')),
                ('success', models.BooleanField(default=False, verbose_name='نجاح المزامنة')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='رسالة الخطأ')),
                ('affaire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mahakim_syncs', to='avocat_app.affaire', verbose_name='القضية')),
            ],
            options={
                'verbose_name': 'نتيجة مزامنة محاكم',
                'verbose_name_plural': 'نتائج مزامنة محاكم',
                'db_table': 'mahakim_sync_result',
                'ordering': ['-date_sync'],
            },
        ),
    ]
