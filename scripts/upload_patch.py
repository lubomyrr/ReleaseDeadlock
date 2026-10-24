from pathlib import Path

import httpx

API_URL = "http://127.0.0.1:8000/documents"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def upload_all_patches() -> None:
    files = sorted(RAW_DIR.glob("patch_*.md"), key=lambda p: p.name)
    if not files:
        raise SystemExit(f"No patch files found in {RAW_DIR}")
    failed = False
    with httpx.Client(timeout=120.0) as client:
        for file in files:
            try:
                content = file.read_text(encoding="utf-8")
                if not content.strip():
                    raise ValueError(f"File is empty: {file}")
                response = client.post(API_URL, json={"filename": file.name, "content": content})
                response.raise_for_status()
                data = response.json()
                print(
                    f"{file.name} | {response.status_code} | "
                    f"chunks_created={data['chunks_created']}",
                    flush=True,
                )
            except httpx.ConnectError as exc:
                raise SystemExit(
                    f"Cannot connect to {API_URL}. Start the API in another terminal:\n"
                    "python -m uvicorn app.main:app --reload"
                ) from exc
            except httpx.HTTPStatusError as exc:
                print(f"{file.name} | {exc.response.status_code} | error={exc.response.text[:300]}", flush=True)
                failed = True
            except (httpx.HTTPError, OSError, ValueError) as exc:
                print(f"{file.name} | ERROR | {exc}", flush=True)
                failed = True
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    upload_all_patches()
