"""POC config — overridable via env vars."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("POC_DB", BASE_DIR / "local.sqlite3"))
TOKEN_PATH = Path(os.getenv("POC_TOKEN", BASE_DIR / ".token.json"))

API_BASE = os.getenv("POC_API", "http://127.0.0.1:8003/api")

# POC scope — 3 cœur tables only.
TABLES = ["affaire", "audience", "tache"]

PULL_PAGE_SIZE = 200
PUSH_BATCH_SIZE = 100
HTTP_TIMEOUT = 30
