"""Vues pour les paramètres du cabinet + impression PDF des listes /ref/."""
from __future__ import annotations

import os
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import CabinetParams
from .ref_registry import REF_REGISTRY


def _pdf_link_callback(uri: str, rel: str | None = None) -> str:
    """Résout les URLs (static/media) vers des chemins absolus pour xhtml2pdf."""
    if uri.startswith(settings.STATIC_URL):
        path = finders.find(uri.replace(settings.STATIC_URL, "", 1))
        if path:
            return path
        return os.path.join(str(settings.BASE_DIR), "static", uri.replace(settings.STATIC_URL, "", 1))
    if uri.startswith(settings.MEDIA_URL):
        return os.path.join(str(settings.MEDIA_ROOT), uri.replace(settings.MEDIA_URL, "", 1))
    if uri.startswith("/"):
        candidate = os.path.join(str(settings.BASE_DIR), uri.lstrip("/"))
        if os.path.exists(candidate):
            return candidate
    return uri


@login_required
@require_http_methods(["GET", "POST"])
def cabinet_params_view(request):
    """Page de paramètres du cabinet (singleton).

    Affiche un formulaire qui édite l'unique instance CabinetParams.
    """
    obj = CabinetParams.get_solo()

    if request.method == "POST":
        text_fields = [
            "nom_cabinet_ar", "nom_cabinet_fr", "nom_avocat_ar", "nom_avocat_fr",
            "barreau", "numero_carte_pro", "adresse", "ville",
            "telephone", "fax", "email", "site_web", "ice", "rib",
            "devise_ar", "pied_page_ar",
        ]
        for f in text_fields:
            if f in request.POST:
                setattr(obj, f, request.POST.get(f, "").strip())

        if "logo_cabinet" in request.FILES:
            obj.logo_cabinet = request.FILES["logo_cabinet"]
        if "logo_ministere" in request.FILES:
            obj.logo_ministere = request.FILES["logo_ministere"]
        if request.POST.get("clear_logo_cabinet") == "1":
            obj.logo_cabinet = None
        if request.POST.get("clear_logo_ministere") == "1":
            obj.logo_ministere = None

        obj.save()
        messages.success(request, "تم حفظ إعدادات المكتب.")
        return redirect("cabinet:cabinet_params")

    return render(request, "cabinet/cabinet_params.html", {"obj": obj})


def _ar(text) -> str:
    """Prépare un texte arabe pour reportlab : reshape + bidi.

    reportlab ne gère pas nativement les ligatures arabes ni le BIDI ; il faut
    reshape (jonction des lettres) puis appliquer python-bidi (ordre logique → ordre visuel).
    Idempotent sur les chaînes vides / non-arabes.
    """
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    try:
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        return get_display(reshape(s))
    except ImportError:
        return s


def _register_amiri():
    """Enregistre la police Amiri pour reportlab (1 seule fois par process)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "Amiri" in pdfmetrics.getRegisteredFontNames():
        return
    base = os.path.join(str(settings.BASE_DIR), "static", "fonts")
    regular = os.path.join(base, "Amiri-Regular.ttf")
    bold = os.path.join(base, "Amiri-Bold.ttf")
    if os.path.exists(regular):
        pdfmetrics.registerFont(TTFont("Amiri", regular))
    if os.path.exists(bold):
        pdfmetrics.registerFont(TTFont("Amiri-Bold", bold))
    # Famille (utilisé par certains styles)
    try:
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily("Amiri", normal="Amiri", bold="Amiri-Bold")
    except Exception:  # noqa: BLE001
        pass


@login_required
def ref_print_pdf(request, refname: str):
    """Génère un PDF élégant d'un référentiel avec reportlab + Amiri.

    Mise en page :
      - En-tête : logo cabinet + nom AR/FR + barreau + adresse
      - Titre centré
      - Tableau bordé, alterné, colonnes auto-dimensionnées
      - Pied de page : téléphone/email + numéro de page + horodatage
      - Police Amiri pour parfait rendu arabe (ligatures + BIDI)
    """
    cfg = REF_REGISTRY.get(refname)
    if not cfg:
        return HttpResponse("Référentiel inconnu", status=404)

    model = cfg.get("model")
    fields = cfg.get("fields", ["libelle"])
    labels = cfg.get("labels", {})
    list_title = cfg.get("list_title") or refname

    qs = model.objects.all()
    if hasattr(model, "is_deleted"):
        qs = qs.filter(is_deleted=False)
    order_by = cfg.get("order_by") or "libelle"
    items = list(qs.order_by(order_by))

    params = CabinetParams.get_solo()

    # === reportlab setup ===
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
        PageBreak, KeepTogether,
    )
    from reportlab.pdfgen import canvas as rl_canvas

    _register_amiri()

    # Palette mahakim.ma : marine + or sable
    COLOR_PRIMARY = colors.HexColor("#1c2b4a")
    COLOR_ACCENT = colors.HexColor("#c9a464")
    COLOR_LIGHT = colors.HexColor("#f6f1e6")
    COLOR_TEXT = colors.HexColor("#1c2b4a")
    COLOR_MUTED = colors.HexColor("#6b7280")

    # === Styles ===
    style_title = ParagraphStyle(
        "title", fontName="Amiri-Bold", fontSize=18, alignment=1,
        textColor=COLOR_PRIMARY, spaceAfter=4, leading=22,
    )
    style_subtitle = ParagraphStyle(
        "subtitle", fontName="Amiri", fontSize=10, alignment=1,
        textColor=COLOR_MUTED, spaceAfter=12, leading=14,
    )
    style_cell = ParagraphStyle(
        "cell", fontName="Amiri", fontSize=10, alignment=2,  # right-align (RTL)
        textColor=COLOR_TEXT, leading=14,
    )
    style_cell_head = ParagraphStyle(
        "cell_head", fontName="Amiri-Bold", fontSize=10, alignment=1,
        textColor=colors.white, leading=14,
    )
    style_cell_num = ParagraphStyle(
        "cell_num", fontName="Amiri", fontSize=10, alignment=1,
        textColor=COLOR_MUTED, leading=14,
    )

    # === Header/Footer factories ===
    cabinet_name = (params.nom_cabinet_ar or params.nom_cabinet_fr or "").strip()
    avocat_name = (params.nom_avocat_ar or params.nom_avocat_fr or "").strip()
    barreau = params.barreau or ""
    adresse = (params.adresse or "").replace("\n", " - ")
    ville = params.ville or ""
    phone = params.telephone or ""
    email = params.email or ""
    logo_path = None
    if params.logo_cabinet and hasattr(params.logo_cabinet, "path"):
        try:
            if os.path.exists(params.logo_cabinet.path):
                logo_path = params.logo_cabinet.path
        except (ValueError, OSError):
            logo_path = None

    def on_page(c: "rl_canvas.Canvas", doc):
        """Dessine entête et pied de page sur chaque page."""
        c.saveState()
        page_w, page_h = A4

        # ===== HEADER =====
        header_h = 3.0 * cm
        # Bande supérieure marine
        c.setFillColor(COLOR_PRIMARY)
        c.rect(0, page_h - 0.7 * cm, page_w, 0.7 * cm, stroke=0, fill=1)
        # Bande or-sable juste en dessous
        c.setFillColor(COLOR_ACCENT)
        c.rect(0, page_h - 0.85 * cm, page_w, 0.15 * cm, stroke=0, fill=1)

        # Logo gauche
        x_text = 1.6 * cm
        if logo_path:
            try:
                c.drawImage(logo_path, 1.6 * cm, page_h - header_h + 0.2 * cm,
                            width=2.0 * cm, height=2.0 * cm, preserveAspectRatio=True, mask='auto')
                x_text = 4.0 * cm
            except Exception:  # noqa: BLE001
                pass

        # Bloc nom cabinet (à droite, car RTL)
        c.setFillColor(COLOR_PRIMARY)
        c.setFont("Amiri-Bold", 13)
        c.drawRightString(page_w - 1.6 * cm, page_h - 1.5 * cm, _ar(cabinet_name) or "")
        c.setFont("Amiri", 9)
        c.setFillColor(COLOR_MUTED)
        sub_line = " · ".join(filter(None, [avocat_name, barreau]))
        if sub_line:
            c.drawRightString(page_w - 1.6 * cm, page_h - 2.0 * cm, _ar(sub_line))
        loc_line = " · ".join(filter(None, [adresse, ville]))
        if loc_line:
            c.drawRightString(page_w - 1.6 * cm, page_h - 2.5 * cm, _ar(loc_line))

        # ===== FOOTER =====
        footer_h = 2.0 * cm
        # Ligne or
        c.setStrokeColor(COLOR_ACCENT)
        c.setLineWidth(0.6)
        c.line(1.6 * cm, footer_h - 0.2 * cm, page_w - 1.6 * cm, footer_h - 0.2 * cm)

        # Téléphone / email à gauche
        c.setFillColor(COLOR_MUTED)
        c.setFont("Amiri", 8.5)
        contact = " · ".join(filter(None, [phone, email]))
        if contact:
            c.drawString(1.6 * cm, 1.2 * cm, _ar(contact))

        # Numéro de page au centre
        c.drawCentredString(page_w / 2, 1.2 * cm,
                            _ar(f"صفحة {doc.page}"))

        # Date à droite
        now = timezone.localtime(timezone.now())
        c.drawRightString(page_w - 1.6 * cm, 1.2 * cm,
                          _ar(f"تاريخ الطباعة: {now.strftime('%Y-%m-%d %H:%M')}"))

        # Petite mention "اعتماد قانوني" tout en bas
        c.setFont("Amiri", 7)
        c.drawCentredString(page_w / 2, 0.7 * cm,
                            _ar("وثيقة مولّدة آليا — منصة إدارة المكتب القانوني"))
        c.restoreState()

    # === Construction du tableau ===
    # Colonnes : N° + (un par champ du registry, avec libellé du modèle)
    def _label_for(fname: str) -> str:
        if fname in labels:
            return labels[fname]
        try:
            return model._meta.get_field(fname).verbose_name
        except Exception:  # noqa: BLE001
            return fname

    # On ne montre que les champs présents dans le modèle
    visible_fields = [f for f in fields if hasattr(model, f) or f == "libelle"]
    # libelle est toujours là si pas dans fields
    if "libelle" not in visible_fields and hasattr(model, "libelle"):
        visible_fields = ["libelle"] + visible_fields

    # En-tête de tableau (en RTL → on inverse l'ordre visuel pour le rendu droite→gauche)
    head_cells = [Paragraph(_ar(_label_for(f)), style_cell_head) for f in visible_fields]
    head_cells.append(Paragraph(_ar("N°"), style_cell_head))
    head_row = list(reversed(head_cells))

    table_data = [head_row]
    for idx, obj in enumerate(items, 1):
        row = []
        for f in visible_fields:
            value = getattr(obj, f, "")
            if value is None:
                value = ""
            row.append(Paragraph(_ar(str(value)), style_cell))
        row.append(Paragraph(str(idx), style_cell_num))
        table_data.append(list(reversed(row)))

    # Largeurs colonnes : N° fixe, autres réparties
    page_w = A4[0] - 3.2 * cm  # marges
    n_cols = len(visible_fields) + 1
    num_col_w = 1.2 * cm
    other_w = (page_w - num_col_w) / (n_cols - 1) if n_cols > 1 else page_w
    col_widths = [num_col_w] + [other_w] * (n_cols - 1)  # RTL → N° à gauche

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, COLOR_ACCENT),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        # Lignes alternées
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT]),
        # Bordures
        ("LINEABOVE", (0, 1), (-1, -1), 0.25, colors.HexColor("#d4cdb8")),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]))

    # === Doc ===
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=3.4 * cm,
        bottomMargin=2.4 * cm,
        title=list_title,
        author=cabinet_name or "Cabinet d'avocat",
    )

    story = [
        Paragraph(_ar(list_title), style_title),
        Paragraph(_ar(f"{len(items)} عنصر(ا)"), style_subtitle),
        Spacer(1, 4),
        table,
    ]

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{refname}.pdf"'
    return response
