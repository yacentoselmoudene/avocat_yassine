# cabinet/services/audit_utils.py
from django.forms.models import model_to_dict
from django.db.models import Model
from django.conf import settings

REDACT = "•••"

def _redact_field(name: str) -> bool:
    return name.lower() in [f.lower() for f in getattr(settings, "AUDIT_REDACT_FIELDS", [])]

def serialize_model(instance: Model) -> dict:
    data = {}
    for k, v in model_to_dict(instance).items():
        data[k] = REDACT if _redact_field(k) else (str(v) if v is not None else None)
    return data

def diff_instances(old: Model | None, new: Model | None) -> dict:
    """
    يعيد قاموس {field: [old, new]} للفروقات. None يعني القيمة غير موجودة.
    """
    old_data = serialize_model(old) if old else {}
    new_data = serialize_model(new) if new else {}
    changes = {}
    keys = set(old_data.keys()) | set(new_data.keys())
    for k in keys:
        ov, nv = old_data.get(k), new_data.get(k)
        if ov != nv:
            changes[k] = [ov, nv]
    return changes
