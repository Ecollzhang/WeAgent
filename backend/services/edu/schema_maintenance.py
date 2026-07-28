"""Idempotent compatibility upgrades for existing Education databases."""

from sqlalchemy import inspect, text

from .extensions import db


def migrate_existing_education_schema():
    """Add columns that ``create_all`` cannot add to an existing table."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    changes = []
    if "edu_materials" in tables:
        columns = {
            column["name"] for column in inspector.get_columns("edu_materials")
        }
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

    if "edu_assessment_papers" in tables:
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("edu_assessment_papers")
        }
        with db.engine.begin() as connection:
            if "generated_for_user_id" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE edu_assessment_papers "
                        "ADD COLUMN generated_for_user_id VARCHAR(100) DEFAULT NULL"
                    )
                )
                changes.append("edu_assessment_papers.generated_for_user_id")
            if "visibility_scope" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE edu_assessment_papers "
                        "ADD COLUMN visibility_scope VARCHAR(30) "
                        "NOT NULL DEFAULT 'course_published'"
                    )
                )
                changes.append("edu_assessment_papers.visibility_scope")

        indexes = {
            index["name"]
            for index in inspect(db.engine).get_indexes("edu_assessment_papers")
        }
        index_statements = {
            "ix_edu_assessment_papers_generated_for_user_id": (
                "CREATE INDEX ix_edu_assessment_papers_generated_for_user_id "
                "ON edu_assessment_papers (generated_for_user_id)"
            ),
            "ix_edu_assessment_papers_visibility_scope": (
                "CREATE INDEX ix_edu_assessment_papers_visibility_scope "
                "ON edu_assessment_papers (visibility_scope)"
            ),
        }
        for index_name, statement in index_statements.items():
            if index_name not in indexes:
                with db.engine.begin() as connection:
                    connection.execute(text(statement))
                changes.append(index_name)
    return changes
