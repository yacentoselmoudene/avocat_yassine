"""JWT auth — login + token cache on disk."""
import json
import time

import requests

from . import config


def login(username: str, password: str) -> dict:
    r = requests.post(
        f"{config.API_BASE}/auth/token/",
        json={"username": username, "password": password},
        timeout=config.HTTP_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    data["_obtained_at"] = int(time.time())
    config.TOKEN_PATH.write_text(json.dumps(data))
    return data


def load_token() -> dict | None:
    if not config.TOKEN_PATH.exists():
        return None
    return json.loads(config.TOKEN_PATH.read_text())


def access_token() -> str:
    tok = load_token()
    if not tok:
        raise RuntimeError("not logged in — run `cli.py login <user> <pass>`")
    return tok["access"]


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {access_token()}"}
