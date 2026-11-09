"""Write the API's OpenAPI schema to backend/openapi.json.

Run from the backend/ folder:
    python -m scripts.export_openapi
"""
import json
from pathlib import Path

from fastapi import FastAPI

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def openapi_json(app: FastAPI) -> str:
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    # Building the schema needs no database, so create the app without running its startup.
    from app.main import create_app

    OPENAPI_PATH.write_text(openapi_json(create_app()), encoding="utf-8", newline="\n")
    print(f"Wrote {OPENAPI_PATH}")


if __name__ == "__main__":
    main()
