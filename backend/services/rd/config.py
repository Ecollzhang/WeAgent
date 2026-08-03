"""WeAgent 智能研发领域服务 — 配置."""
import os
from datetime import timedelta
from dotenv import load_dotenv

_RD_DIR = os.path.abspath(os.path.dirname(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_RD_DIR, os.pardir, os.pardir))
_REPOSITORY_DIR = os.path.dirname(_BACKEND_DIR)
for _env_path in (
    os.path.join(_RD_DIR, '.env'),
    os.path.join(_BACKEND_DIR, '.env'),
    os.path.join(_REPOSITORY_DIR, '.env'),
):
    load_dotenv(_env_path, override=False)


class Config:
    SERVICE_NAME = 'weagent-rd'
    PORT = int(os.getenv('RD_PORT', '5101'))

    SECRET_KEY = os.getenv('SECRET_KEY', 'weagent-dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'weagent-jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    # MySQL — 独立数据库 weagent_rd
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'RD_DATABASE_URL',
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/weagent_rd?charset=utf8mb4',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # GitHub OAuth App
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')
    GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:5101/api/rd/github/callback')

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
