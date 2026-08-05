import os

from app.models.user_model_config import UserModelConfig
from urllib.parse import urlparse
from app import db as app_db
import os


def _clean_config_value(value):
    text = str(value or '').strip()
    text = text.strip(" \t\r\n'\"")
    return text


def _mask_key(api_key):
    if not api_key:
        return ''
    if len(api_key) <= 8:
        return '****'
    return f'{api_key[:4]}****{api_key[-4:]}'


def _openai_compatible_base_url(base_url):
    """Derive the OpenAI-compatible endpoint used by Codex/OpenCode.

    Some Claude Code providers are configured with an Anthropic-compatible
    suffix (`/anthropic`). Codex uses the OpenAI Responses API shape, so it
    must target the sibling `/v1` endpoint when the provider exposes one.
    """
    text = _clean_config_value(base_url).rstrip('/')
    if not text:
        return ''
    if text.endswith('/anthropic'):
        return text[:-len('/anthropic')] + '/v1'
    return text


def _codex_should_use_relay(base_url):
    host = urlparse(_clean_config_value(base_url).rstrip('/')).netloc.lower()
    return any(marker in host for marker in ('deepseek', 'xiaomimimo'))


def _server_managed_container_env_vars():
    api_key = _clean_config_value(
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("CODEX_API_KEY")
    )
    if not api_key:
        return None
    base_url = _clean_config_value(
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or os.getenv("CODEX_BASE_URL")
    ).rstrip("/")
    model_name = _clean_config_value(
        os.getenv("TEXT2IFC_DEEPSEEK_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("CODEX_MODEL")
    )
    codex_base_url = _openai_compatible_base_url(base_url)
    env = {
        "ANTHROPIC_API_KEY": api_key,
        "CODEX_API_KEY": api_key,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    }
    if base_url:
        env["ANTHROPIC_BASE_URL"] = base_url
    if codex_base_url:
        env["CODEX_BASE_URL"] = codex_base_url
    if _codex_should_use_relay(codex_base_url or base_url):
        env["CODEX_USE_RELAY"] = "1"
    if model_name:
        env["ANTHROPIC_MODEL"] = model_name
        env["CODEX_MODEL"] = model_name
    return env


class SettingsService:
    """User settings persistence."""

    def _effective_model(self, config):
        selected_model = _clean_config_value(getattr(config, 'model', ''))
        custom_model = _clean_config_value(getattr(config, 'custom_model', ''))
        if selected_model == 'custom':
            return custom_model
        return selected_model

    def get_model_config(self, user_id, mask_api_key=True):
        config = UserModelConfig.query.filter_by(user_id=user_id).first()
        if not config:
            return None, None

        data = config.to_dict()
        data['api_key'] = _mask_key(config.api_key) if mask_api_key else (config.api_key or '')
        data['has_api_key'] = bool(config.api_key)
        data['effective_model'] = self._effective_model(config)
        return data, None

    def save_model_config(self, user_id, data):
        config = UserModelConfig.query.filter_by(user_id=user_id).first()
        if not config:
            config = UserModelConfig(user_id=user_id)

        api_key = data.get('api_key')
        if api_key and api_key != '****' and '****' not in api_key:
            config.api_key = _clean_config_value(api_key)

        for field in ('base_url', 'model', 'custom_model', 'temperature', 'max_tokens'):
            if field in data and data[field] is not None:
                value = data[field]
                if field in ('base_url', 'model', 'custom_model'):
                    value = _clean_config_value(value)
                    if field == 'base_url':
                        value = value.rstrip('/')
                setattr(config, field, value)

        if _clean_config_value(config.model) == 'custom' and not _clean_config_value(config.custom_model):
            return None, 'Custom model name is required'

        config.save()
        # 同步到 RD 服务的本地表
        _sync_to_rd_db(user_id, data, config)
        result, error = self.get_model_config(user_id, mask_api_key=True)
        if error:
            return result, error

        try:
            env_vars, env_error = self.get_container_env_vars(user_id)
            if not env_error and env_vars:
                from app.sandbox import get_manager
                sync_result = get_manager().update_model_config_for_user_sessions(user_id, env_vars)
                result['container_sync'] = sync_result
        except Exception as e:
            result['container_sync'] = {
                'status': 'error',
                'error': str(e),
            }
        return result, None

    def get_container_env_vars(self, user_id, allow_server_fallback=False):
        config = UserModelConfig.query.filter_by(user_id=user_id).first()
        if not config or not config.api_key:
            if allow_server_fallback:
                server_env = _server_managed_container_env_vars()
                if server_env:
                    return server_env, None
            return None, '请先在设置中配置模型 API Key'

        env = {
            'ANTHROPIC_API_KEY': _clean_config_value(config.api_key),
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
        }
        if config.base_url:
            env['ANTHROPIC_BASE_URL'] = _clean_config_value(config.base_url).rstrip('/')
        model_name = self._effective_model(config)
        if model_name:
            env['ANTHROPIC_MODEL'] = model_name
        codex_base_url = _openai_compatible_base_url(config.base_url)
        env['CODEX_API_KEY'] = _clean_config_value(config.api_key)
        if codex_base_url:
            env['CODEX_BASE_URL'] = codex_base_url
        if _codex_should_use_relay(codex_base_url or config.base_url):
            env['CODEX_USE_RELAY'] = '1'
        if model_name:
            env['CODEX_MODEL'] = model_name
        return env, None


def _sync_to_rd_db(user_id, data, config):
    """Sync model config to RD service's local table (weagent_rd.rd_model_configs)."""
    try:
        import pymysql
        from flask import current_app
        cfg = current_app.config
        conn = pymysql.connect(
            host=cfg.get('MYSQL_HOST', 'localhost'),
            port=cfg.get('MYSQL_PORT', 3306),
            user=cfg.get('MYSQL_USER', 'root'),
            password=cfg.get('MYSQL_PASSWORD', ''),
            database='weagent_rd',
            charset='utf8mb4',
        )
        cursor = conn.cursor()
        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rd_model_configs (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL UNIQUE,
                api_key TEXT NULL,
                base_url VARCHAR(500) NULL,
                model VARCHAR(100) NOT NULL DEFAULT 'gpt-4o',
                custom_model VARCHAR(100) NOT NULL DEFAULT '',
                temperature FLOAT NOT NULL DEFAULT 0.7,
                max_tokens INT NOT NULL DEFAULT 4096,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        import uuid as _uuid
        cursor.execute("""
            INSERT INTO rd_model_configs
                (id, user_id, api_key, base_url, model, custom_model, temperature, max_tokens)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                api_key = VALUES(api_key),
                base_url = VALUES(base_url),
                model = VALUES(model),
                custom_model = VALUES(custom_model),
                temperature = VALUES(temperature),
                max_tokens = VALUES(max_tokens)
        """, (
            str(_uuid.uuid4()),
            user_id,
            config.api_key or '',
            config.base_url or '',
            config.model or 'gpt-4o',
            config.custom_model or '',
            config.temperature or 0.7,
            config.max_tokens or 4096,
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass  # RD database not available — non-critical


settings_service = SettingsService()
