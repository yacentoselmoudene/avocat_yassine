"""Adds UIPermRequiredMixin + ui_perm attr to Create/Update/Delete views.

Run from project root:
    python3 scripts/wrap_views_perms.py

Idempotent.
"""
import re
from pathlib import Path

FILES = [
    Path("avocat_app/views.py"),
]

PERM_MAP = {
    "Create": "ui_btn_add",
    "Update": "ui_btn_edit",
    "Delete": "ui_btn_delete",
}


def ensure_import(content: str) -> str:
    """Ensure UIPermRequiredMixin is imported."""
    if "UIPermRequiredMixin" in content:
        return content
    # Find existing import from views_mixins
    m = re.search(r"from\s+\.views_mixins\s+import\s+\(([^)]+)\)", content)
    if m:
        existing = m.group(1)
        if "UIPermRequiredMixin" not in existing:
            new_import = existing.rstrip().rstrip(",") + ",\n    UIPermRequiredMixin,"
            content = content[:m.start(1)] + new_import + content[m.end(1):]
        return content
    m2 = re.search(r"from\s+\.views_mixins\s+import\s+([^\n(]+)", content)
    if m2:
        existing = m2.group(1).strip()
        if "UIPermRequiredMixin" not in existing:
            content = content[:m2.start(1)] + existing + ", UIPermRequiredMixin" + content[m2.end(1):]
    return content


def wrap_class(content: str) -> str:
    """For each class XxxCreate/Update/Delete that inherits SecureBase,
    add UIPermRequiredMixin in front and ui_perm attribute."""
    lines = content.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(class\s+\w+)(Create|Update|Delete)(\s*\(\s*)(SecureBase)(.*?)\)\s*:\s*$", line)
        if m:
            prefix = m.group(1)
            suffix = m.group(2)
            paren = m.group(3)
            base = m.group(4)
            rest = m.group(5)
            if "UIPermRequiredMixin" not in line:
                new_line = f"{prefix}{suffix}{paren}UIPermRequiredMixin, {base}{rest}):"
                out.append(new_line)
                # Check if next line already has ui_perm
                next_has_ui_perm = False
                for k in range(i + 1, min(i + 8, len(lines))):
                    if lines[k].strip().startswith("ui_perm"):
                        next_has_ui_perm = True
                        break
                    if re.match(r"^class\s", lines[k]):
                        break
                if not next_has_ui_perm:
                    # Add ui_perm = "..." attribute after the class declaration
                    # Determine indent (4 spaces by convention)
                    out.append(f'    ui_perm = "{PERM_MAP[suffix]}"')
                i += 1
                continue
        out.append(line)
        i += 1
    return "\n".join(out)


for f in FILES:
    text = f.read_text(encoding="utf-8")
    orig = text
    text = ensure_import(text)
    text = wrap_class(text)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        print(f"modified: {f}")
    else:
        print(f"unchanged: {f}")
