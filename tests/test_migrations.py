"""Applies the full Alembic chain to a fresh database and checks it matches the models --
catches "changed a model, forgot `flask db migrate`" before it reaches production."""
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade

from app.extensions import db
from conftest import _make_app

pytestmark = pytest.mark.slow


def test_migrations_match_models(tmp_path):
    app = _make_app(SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'migrated.db'}")
    with app.app_context():
        upgrade()
        with db.engine.connect() as connection:
            assert MigrationContext.configure(connection).get_current_revision() is not None
            diff = compare_metadata(MigrationContext.configure(connection), db.metadata)
        db.engine.dispose()
    assert diff == []
