"""
Minimal conftest for engine rule tests.

Engine rules are pure Python dataclass functions with no database or
HTTP dependencies. This conftest sets only the environment variables
required to import app modules without triggering the full app startup,
and overrides the parent conftest's autouse reset_db fixture so that
no database is created or destroyed for each test in this package.
"""
import os

import pytest

# Satisfy config validation without a real database or secret key
os.environ.setdefault("DATABASE_URL", "sqlite:///./engine_test.sqlite3")
os.environ.setdefault("SECRET_KEY", "engine-test-secret-not-for-production")
os.environ.setdefault("ENCRYPTION_KEY", "svJt37a4pzcIQ91auVTrJU5Wo9VrfTZ548d2SkkT2tc=")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("META_APP_ID", "mock")


@pytest.fixture(autouse=True)
def reset_db():
    """
    Override the parent conftest reset_db so no SQLAlchemy operations
    run for engine unit tests.  These tests use only in-memory dataclasses.
    """
    yield
