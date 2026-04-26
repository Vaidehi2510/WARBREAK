from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_OUT = ROOT / "frontend" / "out"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.main import app as backend_app  # noqa: E402

app = FastAPI(title="WARBREAK", version="2.0.0")
app.mount("/api", backend_app)

if (FRONTEND_OUT / "_next").is_dir():
    app.mount(
        "/_next",
        StaticFiles(directory=FRONTEND_OUT / "_next"),
        name="next_static",
    )


def _frontend_file(path: str) -> Path | None:
    if not FRONTEND_OUT.is_dir():
        return None

    clean_path = path.strip("/")
    candidates = [FRONTEND_OUT / "index.html"]
    if clean_path:
        candidates = [
            FRONTEND_OUT / clean_path,
            FRONTEND_OUT / f"{clean_path}.html",
            FRONTEND_OUT / clean_path / "index.html",
        ]

    for candidate in candidates:
        try:
            candidate.relative_to(FRONTEND_OUT)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return FRONTEND_OUT / "index.html"


@app.get("/", include_in_schema=False)
@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str = ""):
    file_path = _frontend_file(path)
    if file_path is None:
        raise HTTPException(
            status_code=503,
            detail="Frontend build output is missing. Run `npm run build` in frontend/.",
        )
    return FileResponse(file_path)
