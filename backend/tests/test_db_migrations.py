import sqlite3

import pytest

from backend.app import db
from backend.app.config import settings


def test_init_db_rolls_back_the_whole_migration_on_failure(monkeypatch, tmp_path):
    database_path = tmp_path / "migration-rollback.db"
    monkeypatch.setattr(settings, "database_path", database_path)
    monkeypatch.setattr(
        db,
        "_seed_default_users",
        lambda _conn: (_ for _ in ()).throw(RuntimeError("injected migration failure")),
    )

    with pytest.raises(RuntimeError, match="injected migration failure"):
        db.init_db()

    with sqlite3.connect(database_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

    assert tables == []
