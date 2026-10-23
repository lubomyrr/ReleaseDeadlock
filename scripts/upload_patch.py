import json
from pathlib import Path

import httpx

PATCH_PATH = Path(__file__).resolve().parents[1] / "data/raw/patch_2026_10_05.md"
API_URL = "http://127.0.0.1:8000/documents"


def upload_patch():
    content = PATCH_PATH.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"File is empty: {PATCH_PATH}")

    payload = {"filename": PATCH_PATH.name, "content": content}
    response = httpx.post(API_URL, json=payload, timeout=120.0)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    print(json.dumps(upload_patch(), ensure_ascii=False, indent=2))
