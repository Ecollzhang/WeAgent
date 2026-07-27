from app.models import db


class GrayscaleConfig(db.Model):
    """Grayscale/Feature Flag configuration model — 灰度配置."""
    __tablename__ = 'grayscale_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    config_key = db.Column(db.String(100), nullable=False)
    config_name = db.Column(db.String(200), nullable=False)
    config_type = db.Column(
        db.Enum('ui', 'feature', 'agent', 'tool', name='grayscale_config_type'),
        nullable=False
    )
    domain = db.Column(db.String(50), nullable=False, comment='common / rd / edu / office')
    enabled = db.Column(db.Boolean, default=True)
    visible = db.Column(db.Boolean, default=True)
    domains = db.Column(db.JSON, default=None, comment='common config: list of domains this config applies to')
    description = db.Column(db.Text, default='')
    extra_meta = db.Column('metadata', db.JSON, default=None)

    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_name': self.config_name,
            'config_type': self.config_type,
            'domain': self.domain,
            'enabled': self.enabled,
            'visible': self.visible,
            'domains': self.domains or [],
            'description': self.description,
            'metadata': self.extra_meta,
        }
