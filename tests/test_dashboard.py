"""Smoke test: every dashboard page runs without raising, including after clicking its buttons."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "streamlit_app"
PAGES = [APP_DIR / "app.py"] + sorted((APP_DIR / "pages").glob("*.py"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem.encode("ascii", "ignore").decode())
def test_page_runs_without_errors(page):
    at = AppTest.from_file(str(page), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]

    for button in at.button:
        button.click()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
