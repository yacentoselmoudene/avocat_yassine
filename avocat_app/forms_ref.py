# avocat_app/forms_ref.py
from django import forms

class ArabicModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-control")
            f.widget.attrs.setdefault("dir", "rtl")
            if isinstance(f.widget, forms.Textarea):
                f.widget.attrs.setdefault("rows", 3)

def make_ref_form(model, fields, labels=None, widgets=None):
        labels = labels or {}
        widgets = widgets or {}

        Meta = type("Meta", (), {
            "model": model,
            "fields": fields,
            "labels": labels,
            "widgets": widgets,
        })
        attrs = {"Meta": Meta}
        RefForm = type("RefForm", (ArabicModelForm,), attrs)
        return RefForm
