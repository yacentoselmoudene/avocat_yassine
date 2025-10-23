# -*- coding: utf-8 -*-
import django.utils.timezone
from django.db import models
from django.utils import timezone
from .models_softdelete import ActiveManager, AllManager

class TimeStampedSoftDeleteModel(models.Model):
    created_at = models.DateTimeField(default=django.utils.timezone.now, verbose_name="أُنشئ في")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تم التحديث في")
    is_deleted = models.BooleanField(default=False, db_index=True, verbose_name="محذوف؟")

    # managers
    objects = ActiveManager()     # par défaut: visibles (is_deleted=False)
    all_objects = AllManager()    # alternatif: tout

    class Meta:
        abstract = True

    # soft delete instance
    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.updated_at = timezone.now()
        self.save(update_fields=["is_deleted", "updated_at"])

    # suppression définitive
    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    # restaurer
    def restore(self):
        self.is_deleted = False
        self.updated_at = timezone.now()
        self.save(update_fields=["is_deleted", "updated_at"])
