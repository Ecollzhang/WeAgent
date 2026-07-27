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
