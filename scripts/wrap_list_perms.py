"""Wraps action buttons in list templates with ui_perms permission checks.

Run from project root:
    python3 scripts/wrap_list_perms.py

Handles both single-line and multi-line <a>/<button> tags.
Idempotent : skips already-wrapped buttons.
"""
import re
from pathlib import Path

LIST_TEMPLATES = list(Path("templates/avocat").glob("*_list.html"))


def ensure_load_ui_perms(content: str) -> str:
    if "ui_perms" in content:
        return content
    m = re.search(r"\{%\s*load\s+([^\%]+?)\s*%\}", content)
    if m:
        loaded = m.group(1).strip()
        if "ui_perms" not in loaded:
            new_load = f"{{% load {loaded} ui_perms %}}"
            content = content[:m.start()] + new_load + content[m.end():]
    else:
        m2 = re.search(r"(\{%\s*extends[^%]+%\})", content)
        if m2:
            content = content[:m2.end()] + "\n{% load ui_perms %}" + content[m2.end():]
    return content


def find_tag_close(lines: list, start_idx: int, tag_name: str) -> int:
    """Find the index of the line containing </tag_name> starting from start_idx."""
    close = f"</{tag_name}>"
    for i in range(start_idx, min(start_idx + 10, len(lines))):
        if close in lines[i]:
            return i
    return -1


def wrap_buttons_by_icon(content: str, icon: str, perm: str) -> str:
    """Find <a>/<button> blocks containing the icon, wrap them with {% if can_see %}."""
    lines = content.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "{% if user|can_see" in line:
            out.append(line)
            i += 1
            continue

        m = re.match(r"^(\s*)(<(a|button)\b[^>]*)$|^(\s*)(<(a|button)\b[^>]*>)\s*$|^(\s*)(<(a|button)\b[^>]*>.*</\3>)\s*$", line)
        # try to detect: line opening an a/button (possibly multi-line) or a complete a/button
        opening_match = re.match(r"^(\s*)(<(a|button)\b)", line)
        if not opening_match:
            out.append(line)
            i += 1
            continue

        indent = opening_match.group(1)
        tag_name = opening_match.group(3)

        # Find closing tag (could be same line or later)
        close_str = f"</{tag_name}>"
        if close_str in line:
            close_line = i
        else:
            close_line = find_tag_close(lines, i + 1, tag_name)
            if close_line == -1:
                out.append(line)
                i += 1
                continue

        block = "\n".join(lines[i:close_line + 1])
        if icon not in block:
            out.append(line)
            i += 1
            continue

        # Check previous out line for already-wrapped
        if out and "{% if user|can_see" in out[-1]:
            for j in range(i, close_line + 1):
                out.append(lines[j])
            i = close_line + 1
            continue

        # Wrap
        out.append(f'{indent}{{% if user|can_see:"{perm}" %}}')
        for j in range(i, close_line + 1):
            out.append(lines[j])
        out.append(f'{indent}{{% endif %}}')
        i = close_line + 1

    return "\n".join(out)


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = ensure_load_ui_perms(text)
    text = wrap_buttons_by_icon(text, "bi-plus-circle", "ui_btn_add")
    text = wrap_buttons_by_icon(text, "bi-pencil", "ui_btn_edit")
    text = wrap_buttons_by_icon(text, "bi-pencil-square", "ui_btn_edit")
    text = wrap_buttons_by_icon(text, "bi-trash", "ui_btn_delete")
    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    n_changed = 0
    for f in LIST_TEMPLATES:
        if process_file(f):
            n_changed += 1
            print(f"  modified: {f}")
    print(f"\n{n_changed} file(s) modified out of {len(LIST_TEMPLATES)}")
