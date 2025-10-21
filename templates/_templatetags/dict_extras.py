# FILE: templates/_templatetags/dict_extras.py                    #}
# فلتر للحصول على قيمة من قاموس باستخدام مفتاح                      #}
# ============================================================= #}
from django import template
register = template.Library()
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
# ============================================================= #}
