"""Grayscale / Feature Flag service — 灰度配置服务."""
from app.models.grayscale_config import GrayscaleConfig
from app import db


class GrayscaleService:
    """灰度配置查询与更新."""

    def get_by_domain(self, domain):
        """获取指定领域的全部灰度配置."""
        configs = GrayscaleConfig.query.filter_by(domain=domain).order_by(
            GrayscaleConfig.config_type, GrayscaleConfig.config_key
        ).all()
        return [c.to_dict() for c in configs], None

    def get_domains(self):
        """返回所有有灰度配置的领域列表（去重）."""
        from sqlalchemy import distinct
        domains = (
            GrayscaleConfig.query
            .with_entities(distinct(GrayscaleConfig.domain))
            .order_by(GrayscaleConfig.domain)
            .all()
        )
        domain_map = {
            'common': {'key': 'common', 'name': '公共'},
            'rd': {'key': 'rd', 'name': '智能研发'},
            'edu': {'key': 'edu', 'name': '智慧教育'},
            'office': {'key': 'office', 'name': '智慧办公'},
        }
        result = []
        for (d,) in domains:
            if d in domain_map:
                result.append(domain_map[d])
            else:
                result.append({'key': d, 'name': d})
        return result, None

    def update(self, config_id, data):
        """更新单条灰度配置."""
        config = GrayscaleConfig.query.get(config_id)
        if not config:
            return None, 'Config not found'

        if 'enabled' in data:
            config.enabled = bool(data['enabled'])
        if 'visible' in data:
            config.visible = bool(data['visible'])

        db.session.commit()
        return config.to_dict(), None

    def create(self, data):
        """新建灰度配置.
        data: {"config_key": "...", "config_name": "...", "config_type": "ui",
               "domain": "common", "domains": ["rd","edu","office"], "description": "..."}
        """
        key = (data.get('config_key') or '').strip()
        domain = (data.get('domain') or '').strip()
        name = (data.get('config_name') or '').strip()
        ctype = data.get('config_type', 'ui')

        if not key or not domain or not name:
            return None, 'config_key, domain, config_name are required'
        if ctype not in ('ui', 'feature', 'agent', 'tool'):
            return None, 'config_type must be one of: ui, feature, agent, tool'
        if domain not in ('common', 'rd', 'edu', 'office'):
            return None, 'domain must be one of: common, rd, edu, office'

        exists = GrayscaleConfig.query.filter_by(config_key=key, domain=domain).first()
        if exists:
            return None, f'Config "{key}" already exists in domain "{domain}"'

        config = GrayscaleConfig(
            config_key=key,
            config_name=name,
            config_type=ctype,
            domain=domain,
            enabled=True,
            visible=True,
            domains=data.get('domains') if domain == 'common' else None,
            description=data.get('description', ''),
        )
        db.session.add(config)
        db.session.commit()
        return config.to_dict(), None

    def delete(self, config_id):
        """删除灰度配置."""
        config = GrayscaleConfig.query.get(config_id)
        if not config:
            return None, 'Config not found'
        db.session.delete(config)
        db.session.commit()
        return {'id': config_id}, None

    def batch_update(self, updates):
        """批量更新灰度配置.
        updates: [{"id": 1, "enabled": true, "visible": false, "domains": [...]}, ...]
        """
        for item in updates:
            config = GrayscaleConfig.query.get(item.get('id'))
            if not config:
                continue
            if 'enabled' in item:
                config.enabled = bool(item['enabled'])
            if 'visible' in item:
                config.visible = bool(item['visible'])
            if 'domains' in item:
                config.domains = item['domains']
        db.session.commit()
        # Return all updated configs
        ids = [item.get('id') for item in updates]
        configs = GrayscaleConfig.query.filter(GrayscaleConfig.id.in_(ids)).all()
        return {'updated': len(configs), 'items': [c.to_dict() for c in configs]}, None


grayscale_service = GrayscaleService()
