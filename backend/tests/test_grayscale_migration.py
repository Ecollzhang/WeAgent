from app import create_app, db
from app.models.grayscale_config import GrayscaleConfig


def test_grayscale_migration_runs_on_sqlite_and_preserves_disabled_flags():
    app = create_app("testing")

    with app.app_context():
        config = GrayscaleConfig.query.filter_by(
            config_key="ui.sidebar.courses",
            domain="edu",
        ).first()
        assert config is not None

        config.enabled = False
        config.visible = False
        db.session.commit()

        from app import _migrate_grayscale_configs

        _migrate_grayscale_configs()
        db.session.expire_all()

        migrated = GrayscaleConfig.query.get(config.id)
        assert migrated.enabled is False
        assert migrated.visible is False


def test_chat_tab_migration_preserves_operator_disabled_choice():
    app = create_app("testing")

    with app.app_context():
        config = GrayscaleConfig.query.filter_by(
            config_key="ui.chat.tabs.agent_config",
            domain="common",
        ).first()
        assert config is not None

        config.enabled = False
        config.visible = False
        db.session.commit()

        from app import _migrate_grayscale_configs

        _migrate_grayscale_configs()
        db.session.expire_all()

        migrated = GrayscaleConfig.query.filter_by(
            config_key="ui.chat.tabs.agent_config",
            domain="common",
        ).one()
        assert migrated.enabled is False
        assert migrated.visible is False


def test_education_chat_flags_and_domain_card_boundaries_are_migrated():
    app = create_app("testing")

    with app.app_context():
        required = {
            ("feature.education.chat.enabled", "edu"),
            ("feature.education.chat.manual_create", "edu"),
            ("feature.education.chat.tools", "edu"),
            ("feature.education.rag.enabled", "edu"),
            ("ui.chat.card.education", "common"),
        }
        present = {
            (row.config_key, row.domain)
            for row in GrayscaleConfig.query.filter(
                GrayscaleConfig.config_key.in_([key for key, _ in required])
            ).all()
        }
        assert required <= present

        education_card = GrayscaleConfig.query.filter_by(
            config_key="ui.chat.card.education",
            domain="common",
        ).one()
        assert education_card.domains == ["edu"]

        rd_card_keys = {
            "ui.chat.card.requirement",
            "ui.chat.card.bug",
            "ui.chat.card.iteration",
            "ui.chat.card.project",
        }
        for config in GrayscaleConfig.query.filter(
            GrayscaleConfig.config_key.in_(rd_card_keys)
        ).all():
            assert config.domain == "common"
            assert config.domains == ["rd"]


def test_grayscale_migration_repairs_card_domains_without_reenabling_flags():
    app = create_app("testing")

    with app.app_context():
        manual = GrayscaleConfig.query.filter_by(
            config_key="feature.education.chat.manual_create",
            domain="edu",
        ).one()
        manual.enabled = False
        manual.visible = False
        requirement = GrayscaleConfig.query.filter_by(
            config_key="ui.chat.card.requirement",
            domain="common",
        ).one()
        requirement.domains = ["rd", "edu", "office"]
        db.session.commit()

        from app import _migrate_grayscale_configs

        _migrate_grayscale_configs()
        db.session.expire_all()

        assert manual.enabled is False
        assert manual.visible is False
        assert requirement.domains == ["rd"]
