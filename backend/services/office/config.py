"""WeAgent 智慧办公领域服务 — 配置."""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SERVICE_NAME = 'weagent-office'
    PORT = int(os.getenv('OFFICE_PORT', '5103'))

    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-me')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    # MySQL — 独立数据库 weagent_office
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'OFFICE_DATABASE_URL',
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/weagent_office?charset=utf8mb4',
    )
    # The Office domain owns its own business database, but workspace ownership
    # lives in the main WeAgent database and must be checked for every request.
    MAIN_DATABASE_URL = os.getenv(
        'MAIN_DATABASE_URL',
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{os.getenv("MYSQL_DB", "weagent")}?charset=utf8mb4',
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
