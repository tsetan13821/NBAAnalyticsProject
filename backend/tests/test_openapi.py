"""The committed openapi.json is the API contract; the frontend generates its TypeScript types from it.

If you change the API on purpose, regenerate the file and commit it:
    python -m scripts.export_openapi
"""
import json

from scripts.export_openapi import OPENAPI_PATH, openapi_json


def test_openapi_snapshot_is_up_to_date(client):
    assert OPENAPI_PATH.exists(), "Run: python -m scripts.export_openapi"
    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert committed == json.loads(openapi_json(client.app)), (
        "The API schema changed. If that was intended, run: python -m scripts.export_openapi"
    )


def test_every_route_is_versioned(client):
    paths = client.app.openapi()["paths"]
    assert paths and all(path.startswith("/api/v1/") for path in paths)


def test_every_route_documents_its_response(client):
    for path, operations in client.app.openapi()["paths"].items():
        for method, operation in operations.items():
            assert "200" in operation["responses"], (method, path)
            assert operation.get("summary"), (method, path)
