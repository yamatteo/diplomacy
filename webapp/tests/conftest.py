""" Shared test setup for the web app. """
import pytest


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    """ Real PBKDF2 cost (~0.2 s per hash) would make the suite several times slower. Hashes record their
        iteration count, so verification works the same. """
    monkeypatch.setattr('webapp.users.PBKDF2_ITERATIONS', 1000)
