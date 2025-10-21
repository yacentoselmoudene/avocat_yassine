# FILE: templates/_templatetags/form_extras.py                    #}
# فلتر لإضافة صنف CSS إلى حقل نموذج                                 #}
# ============================================================= #}
from django import template
register = template.Library()
@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})
# ============================================================= #}
