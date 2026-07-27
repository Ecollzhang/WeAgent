"""WeAgent 智慧教育领域服务 — 配置."""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SERVICE_NAME = 'weagent-edu'
    PORT = int(os.getenv('EDU_PORT', '5102'))

    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-me')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    # MySQL — 独立数据库 weagent_edu
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'EDU_DATABASE_URL',
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/weagent_edu?charset=utf8mb4',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

    EDUCATION_FEATURE_ENABLED = os.getenv(
        'EDUCATION_FEATURE_ENABLED', 'true'
    ).lower() in ('1', 'true', 'yes', 'on')
