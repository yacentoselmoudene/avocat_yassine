# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from django.db.models import Q

class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        # soft delete en masse
        return super().update(is_deleted=True, updated_at=timezone.now())

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)

class ActiveManager(models.Manager):
    """Manager par défaut: ne renvoie que les objets non supprimés."""
    def get_queryset(self):
      return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

class AllManager(models.Manager):
    """Manager alternatif: renvoie tout, supprimés inclus."""
    def get_queryset(self):
      return SoftDeleteQuerySet(self.model, using=self._db)
