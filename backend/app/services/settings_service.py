from app.models.user_model_config import UserModelConfig


def _mask_key(api_key):
    if not api_key:
        return ''
    if len(api_key) <= 8:
        return '****'
    return f'{api_key[:4]}****{api_key[-4:]}'


class SettingsService:
    """User settings persistence."""

    def get_model_config(self, user_id, mask_api_key=True):
        config = UserModelConfig.query.filter_by(user_id=user_id).first()
        if not config:
            return None, None

        data = config.to_dict()
        data['api_key'] = _mask_key(config.api_key) if mask_api_key else (config.api_key or '')
        data['has_api_key'] = bool(config.api_key)
        return data, None

    def save_model_config(self, user_id, data):
        config = UserModelConfig.query.filter_by(user_id=user_id).first()
        if not config:
            config = UserModelConfig(user_id=user_id)

        api_key = data.get('api_key')
        if api_key and api_key != '****' and '****' not in api_key:
            config.api_key = api_key

        for field in ('base_url', 'model', 'temperature', 'max_tokens'):
            if field in data and data[field] is not None:
                setattr(config, field, data[field])

        config.save()
        return self.get_model_config(user_id, mask_api_key=True)

    def get_container_env_vars(self, user_id):
        config = UserModelConfig.query.filter_by(user_id=user_id).first()
        if not config or not config.api_key:
            return None, '请先在设置中配置模型 API Key'

        env = {
            'ANTHROPIC_API_KEY': config.api_key,
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
        }
        if config.base_url:
            env['ANTHROPIC_BASE_URL'] = config.base_url
        if config.model:
            env['ANTHROPIC_MODEL'] = config.model
        return env, None


settings_service = SettingsService()
