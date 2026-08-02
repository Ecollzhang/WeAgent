"""本地模型配置表 — 同步自 weagent.user_model_configs，供 RD 服务独立使用."""
from database import db
from models.project import gen_uuid


class RdModelConfig(db.Model):
    """Per-user LLM model configuration, synced from main weagent database."""
    __tablename__ = 'rd_model_configs'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), nullable=False, unique=True, index=True, comment='用户ID')
    api_key = db.Column(db.Text, nullable=True, comment='API Key（加密存储）')
    base_url = db.Column(db.String(500), nullable=True, comment='API Base URL')
    model = db.Column(db.String(100), nullable=False, default='gpt-4o', comment='模型名称')
    custom_model = db.Column(db.String(100), nullable=False, default='', comment='自定义模型名')
    temperature = db.Column(db.Float, nullable=False, default=0.7, comment='温度参数')
    max_tokens = db.Column(db.Integer, nullable=False, default=4096, comment='最大Token数')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self, mask_api_key=True):
        data = {
            'user_id': self.user_id,
            'base_url': self.base_url or '',
            'model': self.model,
            'custom_model': self.custom_model or '',
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }
        if mask_api_key:
            key = self.api_key or ''
            if key and len(key) > 8:
                data['api_key'] = f'{key[:4]}****{key[-4:]}'
            elif key:
                data['api_key'] = '****'
            else:
                data['api_key'] = ''
            data['has_api_key'] = bool(self.api_key)
        else:
            data['api_key'] = self.api_key or ''
            data['has_api_key'] = bool(self.api_key)
        return data
