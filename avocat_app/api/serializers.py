"""Auto-generate ModelSerializer for every table in the sync registry.

FileField/ImageField are exposed as URLs only (the binary itself is
fetched/uploaded via a dedicated /api/files/<uuid>/ endpoint in a later phase).
ManyToManyField is excluded — the through table is registered separately.
"""
from rest_framework import serializers
from django.db import models as dj_models

from .registry import SYNC_TABLES


def _exclude_fields(model) -> list[str]:
    """Skip M2M (their through table is registered) and reverse relations."""
    excluded = []
    for f in model._meta.get_fields():
        if isinstance(f, dj_models.ManyToManyField):
            excluded.append(f.name)
    return excluded


def _file_field_overrides(model) -> dict:
    """For every FileField/ImageField on the model, emit a serializer field
    that returns the storage-relative name (e.g. 'pieces/x.bin') rather than
    the absolute URL ('/media/pieces/x.bin'). Clients need the relative path
    so they can join it against their own MEDIA_ROOT."""
    overrides = {}
    for f in model._meta.get_fields():
        if isinstance(f, (dj_models.FileField, dj_models.ImageField)):
            overrides[f.name] = serializers.FileField(
                use_url=False, required=False, allow_null=True, allow_empty_file=True
            )
    return overrides


def _build_serializer(name: str, model):
    excluded = _exclude_fields(model)

    class Meta:
        pass

    Meta.model = model
    if excluded:
        Meta.exclude = excluded
    else:
        Meta.fields = "__all__"

    attrs = {"Meta": Meta, **_file_field_overrides(model)}
    cls_name = f"{model.__name__}SyncSerializer"
    return type(cls_name, (serializers.ModelSerializer,), attrs)


SERIALIZERS: dict[str, type[serializers.ModelSerializer]] = {
    name: _build_serializer(name, model) for name, model in SYNC_TABLES
}


def get_serializer(name: str):
    return SERIALIZERS.get(name)
