"""Same as wrap_list_perms but for *_detail.html templates."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from wrap_list_perms import ensure_load_ui_perms, wrap_buttons_by_icon

TEMPLATES = list(Path("templates/avocat").glob("*_detail.html"))


def process_file(path):
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
    n = 0
    for f in TEMPLATES:
        if process_file(f):
            n += 1
            print(f"modified: {f}")
    print(f"\n{n} modified / {len(TEMPLATES)}")
