"""Idempotent compatibility upgrades for existing Education databases."""

from sqlalchemy import inspect, text

from .extensions import db


def migrate_existing_education_schema():
    """Add columns that ``create_all`` cannot add to an existing table."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "edu_materials" not in tables:
        return []

    changes = []
    columns = {column["name"] for column in inspector.get_columns("edu_materials")}
    with db.engine.begin() as connection:
        if "asset_id" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE edu_materials "
                    "ADD COLUMN asset_id VARCHAR(36) DEFAULT NULL"
                )
            )
            changes.append("edu_materials.asset_id")

    inspector = inspect(db.engine)
    indexes = {
        index["name"] for index in inspector.get_indexes("edu_materials")
    }
    if "ix_edu_materials_asset_id" not in indexes:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE INDEX ix_edu_materials_asset_id "
                    "ON edu_materials (asset_id)"
                )
            )
        changes.append("edu_materials.asset_id_index")
    return changes

