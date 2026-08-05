"""Idempotent compatibility upgrades for existing Education databases."""

from flask import current_app
from sqlalchemy import inspect, text

from .extensions import db


def migrate_existing_education_schema():
    """Add columns that ``create_all`` cannot add to an existing table."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    changes = []
    if "edu_assets" in tables and db.engine.dialect.name == "mysql":
        blob_column = next(
            (
                column
                for column in inspector.get_columns("edu_assets")
                if column["name"] == "blob_bytes"
            ),
            None,
        )
        if blob_column and "LONGBLOB" not in str(blob_column["type"]).upper():
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE edu_assets "
                        "MODIFY blob_bytes LONGBLOB NOT NULL"
                    )
                )
            changes.append("edu_assets.blob_bytes_longblob")
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

    for table_name in ("edu_assessment_items", "edu_assessment_papers"):
        if table_name not in tables:
            continue
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns(table_name)
        }
        if "published_version_id" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN published_version_id VARCHAR(36) DEFAULT NULL"
                    )
                )
                connection.execute(
                    text(
                        f"UPDATE {table_name} SET published_version_id = current_version_id "
                        "WHERE status = 'published' AND published_version_id IS NULL"
                    )
                )
            changes.append(f"{table_name}.published_version_id")
        indexes = {
            index["name"] for index in inspect(db.engine).get_indexes(table_name)
        }
        index_name = f"ix_{table_name}_published_version_id"
        if index_name not in indexes:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        f"CREATE INDEX {index_name} "
                        f"ON {table_name} (published_version_id)"
                    )
                )
            changes.append(index_name)

    for table_name in ("edu_assessment_items", "edu_assessment_stimuli"):
        if table_name not in tables:
            continue
        columns = {
            column["name"] for column in inspect(db.engine).get_columns(table_name)
        }
        if "lesson_id" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN lesson_id VARCHAR(36) DEFAULT NULL"
                    )
                )
            changes.append(f"{table_name}.lesson_id")
        indexes = {
            index["name"] for index in inspect(db.engine).get_indexes(table_name)
        }
        index_name = f"ix_{table_name}_lesson_id"
        if index_name not in indexes:
            with db.engine.begin() as connection:
                connection.execute(
                    text(f"CREATE INDEX {index_name} ON {table_name} (lesson_id)")
                )
            changes.append(index_name)

    if "edu_assessment_item_versions" in tables:
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("edu_assessment_item_versions")
        }
        with db.engine.begin() as connection:
            if "stimulus_version_id" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE edu_assessment_item_versions "
                        "ADD COLUMN stimulus_version_id VARCHAR(36) DEFAULT NULL"
                    )
                )
                changes.append("edu_assessment_item_versions.stimulus_version_id")
            if "stimulus_order" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE edu_assessment_item_versions "
                        "ADD COLUMN stimulus_order INTEGER DEFAULT NULL"
                    )
                )
                changes.append("edu_assessment_item_versions.stimulus_order")
        indexes = {
            index["name"]
            for index in inspect(db.engine).get_indexes("edu_assessment_item_versions")
        }
        if "ix_edu_assessment_item_versions_stimulus_version_id" not in indexes:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE INDEX ix_edu_assessment_item_versions_stimulus_version_id "
                        "ON edu_assessment_item_versions (stimulus_version_id)"
                    )
                )
            changes.append("ix_edu_assessment_item_versions_stimulus_version_id")

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

    if "edu_agent_runs" in tables:
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("edu_agent_runs")
        }
        if "tool_grant_id" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE edu_agent_runs "
                        "ADD COLUMN tool_grant_id VARCHAR(36) DEFAULT NULL"
                    )
                )
            changes.append("edu_agent_runs.tool_grant_id")
        indexes = {
            index["name"]
            for index in inspect(db.engine).get_indexes("edu_agent_runs")
        }
        if "ix_edu_agent_runs_tool_grant_id" not in indexes:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE INDEX ix_edu_agent_runs_tool_grant_id "
                        "ON edu_agent_runs (tool_grant_id)"
                    )
                )
            changes.append("edu_agent_runs.tool_grant_id_index")

    if "edu_tool_grants" in tables:
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("edu_tool_grants")
        }
        with db.engine.begin() as connection:
            if "agent_ids" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE edu_tool_grants "
                        "ADD COLUMN agent_ids JSON DEFAULT NULL"
                    )
                )
                changes.append("edu_tool_grants.agent_ids")
            if "lesson_id" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE edu_tool_grants "
                        "ADD COLUMN lesson_id VARCHAR(36) DEFAULT NULL"
                    )
                )
                changes.append("edu_tool_grants.lesson_id")
            if "confirmed_actions" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE edu_tool_grants "
                        "ADD COLUMN confirmed_actions JSON NULL"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE edu_tool_grants "
                        "SET confirmed_actions = JSON_ARRAY() "
                        "WHERE confirmed_actions IS NULL"
                    )
                )
                changes.append("edu_tool_grants.confirmed_actions")

    if "edu_assignments" in tables:
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("edu_assignments")
        }
        if "max_score" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE edu_assignments "
                        "ADD COLUMN max_score FLOAT NOT NULL DEFAULT 100"
                    )
                )
            changes.append("edu_assignments.max_score")
        if "source_asset_ids" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE edu_assignments "
                        "ADD COLUMN source_asset_ids JSON NULL"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE edu_assignments "
                        "SET source_asset_ids = JSON_ARRAY() "
                        "WHERE source_asset_ids IS NULL"
                    )
                )
                connection.execute(
                    text(
                        "ALTER TABLE edu_assignments "
                        "MODIFY COLUMN source_asset_ids JSON NOT NULL"
                    )
                )
            changes.append("edu_assignments.source_asset_ids")
        for column_name in ("current_version_id", "published_version_id"):
            if column_name not in columns:
                with db.engine.begin() as connection:
                    connection.execute(
                        text(
                            f"ALTER TABLE edu_assignments "
                            f"ADD COLUMN {column_name} VARCHAR(36) DEFAULT NULL"
                        )
                    )
                changes.append(f"edu_assignments.{column_name}")

        indexes = {
            index["name"]
            for index in inspect(db.engine).get_indexes("edu_assignments")
        }
        for column_name in ("current_version_id", "published_version_id"):
            index_name = f"ix_edu_assignments_{column_name}"
            if index_name not in indexes:
                with db.engine.begin() as connection:
                    connection.execute(
                        text(
                            f"CREATE INDEX {index_name} "
                            f"ON edu_assignments ({column_name})"
                        )
                    )
                changes.append(index_name)

        # ``create_all`` creates the immutable version table before this
        # compatibility pass. Backfill one canonical snapshot for legacy rows.
        from .content_models import Assignment, AssignmentContentVersion

        backfilled = 0
        for assignment in Assignment.query.filter(
            Assignment.current_version_id.is_(None)
        ).all():
            version = AssignmentContentVersion(
                assignment_id=assignment.id,
                version_number=1,
                title=assignment.title,
                kind=assignment.kind,
                instruction_json=assignment.instruction_json,
                evaluation_json=assignment.evaluation_json or {},
                source_asset_ids=assignment.source_asset_ids or [],
                max_score=assignment.max_score,
                max_attempts=assignment.max_attempts,
                allow_revision_after_feedback=assignment.allow_revision_after_feedback,
                created_by=assignment.published_by or "schema_migration",
                published_at=(
                    assignment.published_at
                    if assignment.status == "published"
                    else None
                ),
            )
            db.session.add(version)
            db.session.flush()
            assignment.current_version_id = version.id
            if assignment.status == "published":
                assignment.published_version_id = version.id
            backfilled += 1
        if backfilled:
            db.session.commit()
            changes.append("edu_assignments.content_versions_backfilled")

        # Migrate only assets proven to be assignment sources. File extension
        # heuristics are intentionally excluded.
        from .asset_models import EducationAsset
        from .content_models import AssignmentImportJob

        assignment_source_ids = {
            row.source_asset_id
            for row in AssignmentImportJob.query.with_entities(
                AssignmentImportJob.source_asset_id
            ).all()
            if row.source_asset_id
        }
        for assignment in Assignment.query.all():
            assignment_source_ids.update(assignment.source_asset_ids or [])
        migrated_assets = 0
        if assignment_source_ids:
            assets = EducationAsset.query.filter(
                EducationAsset.id.in_(assignment_source_ids),
                EducationAsset.purpose == "course_material",
            ).all()
            for asset in assets:
                asset.purpose = "assignment_source"
                migrated_assets += 1
        if migrated_assets:
            db.session.commit()
            changes.append("edu_assets.assignment_source_migrated")
    if "edu_course_mind_maps" in tables:
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("edu_course_mind_maps")
        }
        if "scope_type" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE edu_course_mind_maps "
                        "ADD COLUMN scope_type VARCHAR(20) NOT NULL DEFAULT 'course'"
                    )
                )
            changes.append("edu_course_mind_maps.scope_type")
        if "lesson_ids" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE edu_course_mind_maps "
                        "ADD COLUMN lesson_ids JSON NULL"
                    )
                )
                if db.engine.dialect.name == "mysql":
                    connection.execute(
                        text(
                            "UPDATE edu_course_mind_maps SET lesson_ids = JSON_ARRAY() "
                            "WHERE lesson_ids IS NULL"
                        )
                    )
                    connection.execute(
                        text(
                            "ALTER TABLE edu_course_mind_maps "
                            "MODIFY COLUMN lesson_ids JSON NOT NULL"
                        )
                    )
                else:
                    connection.execute(
                        text(
                            "UPDATE edu_course_mind_maps SET lesson_ids = '[]' "
                            "WHERE lesson_ids IS NULL"
                        )
                    )
            changes.append("edu_course_mind_maps.lesson_ids")
        indexes = {
            index["name"]
            for index in inspect(db.engine).get_indexes("edu_course_mind_maps")
        }
        if "ix_edu_course_mind_maps_scope_type" not in indexes:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE INDEX ix_edu_course_mind_maps_scope_type "
                        "ON edu_course_mind_maps (scope_type)"
                    )
                )
            changes.append("ix_edu_course_mind_maps_scope_type")
    if "edu_feedback" in tables:
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("edu_feedback")
        }
        feedback_columns = {
            "version_number": "INTEGER NOT NULL DEFAULT 1",
            "rubric_scores": "JSON NULL",
            "annotations": "JSON NULL",
            "revision_requested": "BOOLEAN NOT NULL DEFAULT FALSE",
        }
        added_json_columns = False
        for name, definition in feedback_columns.items():
            if name not in columns:
                with db.engine.begin() as connection:
                    connection.execute(
                        text(
                            f"ALTER TABLE edu_feedback "
                            f"ADD COLUMN {name} {definition}"
                        )
                    )
                changes.append(f"edu_feedback.{name}")
                added_json_columns = added_json_columns or name in {
                    "rubric_scores",
                    "annotations",
                }
        if added_json_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE edu_feedback SET rubric_scores = JSON_OBJECT() "
                        "WHERE rubric_scores IS NULL"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE edu_feedback SET annotations = JSON_ARRAY() "
                        "WHERE annotations IS NULL"
                    )
                )
                connection.execute(
                    text(
                        "ALTER TABLE edu_feedback "
                        "MODIFY COLUMN rubric_scores JSON NOT NULL"
                    )
                )
                connection.execute(
                    text(
                        "ALTER TABLE edu_feedback "
                        "MODIFY COLUMN annotations JSON NOT NULL"
                    )
                )
    if {
        "edu_agent_runs",
        "edu_conversation_bindings",
        "edu_course_memberships",
    }.issubset(tables):
        from .agent_policy import (
            EducationAgentPolicyError,
            resolve_agent_service_views,
        )
        from .models import CourseMembership
        from .workflow_models import (
            EducationAgentRun,
            EducationConversationBinding,
        )

        existing_ids = {
            value
            for (value,) in EducationConversationBinding.query.with_entities(
                EducationConversationBinding.conversation_id
            ).all()
        }
        backfilled = 0
        runs = EducationAgentRun.query.filter(
            EducationAgentRun.conversation_id.isnot(None)
        ).order_by(EducationAgentRun.created_at.asc()).all()
        for run in runs:
            conversation_id = str(run.conversation_id or "").strip()
            if not conversation_id or conversation_id in existing_ids:
                continue
            membership = CourseMembership.query.filter_by(
                course_id=run.course_id,
                user_id=run.requested_by,
                status="active",
            ).first()
            if not membership:
                continue
            agent_ids = list(
                dict.fromkeys(
                    str(node.get("agent_id") or "").strip()
                    for node in (run.nodes or [])
                    if isinstance(node, dict)
                    and node.get("type") == "agent_task"
                    and str(node.get("agent_id") or "").strip()
                )
            )
            if not agent_ids:
                continue
            try:
                views = resolve_agent_service_views(
                    agent_ids,
                    role=membership.role,
                    material_policy="authorized_knowledge",
                    rag_enabled=bool(
                        current_app.config.get(
                            "EDUCATION_RAG_ENABLED",
                            True,
                        )
                    ),
                )
            except EducationAgentPolicyError:
                continue
            route = run.to_dict().get("business_route")
            db.session.add(
                EducationConversationBinding(
                    conversation_id=conversation_id,
                    actor_user_id=run.requested_by,
                    course_id=run.course_id,
                    lesson_id=run.lesson_id,
                    membership_role_snapshot=membership.role,
                    binding_mode="product",
                    material_policy="authorized_knowledge",
                    agent_service_views=views,
                    source_route=route if isinstance(route, dict) else None,
                    status="active",
                )
            )
            existing_ids.add(conversation_id)
            backfilled += 1
        if backfilled:
            db.session.commit()
            changes.append(
                f"edu_conversation_bindings.backfilled:{backfilled}"
            )
    return changes
