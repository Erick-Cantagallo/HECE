# HECE/tests/conftest.py
import pytest


@pytest.fixture(autouse=True)
def hermetic_environment(monkeypatch):
    """
    Tests must not depend on the developer's .env (hece.main loads it on import):
    start every test from the documented defaults.
    """
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("MAX_RETRIES", raising=False)
