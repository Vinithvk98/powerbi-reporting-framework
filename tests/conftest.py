import pytest


@pytest.fixture
def warehouse_dsn(tmp_path, monkeypatch):
    """Isolate each test's warehouse in a temp SQLite file."""
    dsn = f"sqlite:///{tmp_path / 'reporting.db'}"
    monkeypatch.setenv("BI_WAREHOUSE_DSN", dsn)
    return dsn
