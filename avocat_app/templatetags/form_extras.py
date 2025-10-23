# -*- coding: utf-8 -*-
from django import template

register = template.Library()

def _append(val, suffix):
    return (val + " " + suffix).strip() if val else suffix

@register.filter(name="add_class")
def add_class(field, css):
    """{{ field|add_class:'form-control is-invalid' }}"""
    attrs = field.field.widget.attrs
    attrs["class"] = _append(attrs.get("class", ""), css)
    return field.as_widget(attrs=attrs)

@register.filter(name="set_attr")
def set_attr(field, arg):
    """{{ field|set_attr:'placeholder:اكتب هنا' }}"""
    try:
        k, v = arg.split(":", 1)
    except ValueError:
        return field
    attrs = field.field.widget.attrs
    attrs[k] = v
    return field.as_widget(attrs=attrs)

@register.filter(name="add_attr")
def add_attr(field, arg):
    """{{ field|add_attr:'data-hx:1' }}"""
    try:
        k, v = arg.split(":", 1)
    except ValueError:
        return field
    attrs = field.field.widget.attrs
    # لا تستبدل إن كان موجودًا
    if k in attrs:
        return field
    attrs[k] = v
    return field.as_widget(attrs=attrs)
