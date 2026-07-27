"""WeAgent Core — 共享核心包安装脚本。

安装方式：
    cd backend
    pip install -e .

安装后，领域服务可直接导入：
    from weagent_core.services.domain_base import DomainServiceBase
"""
from setuptools import setup, find_packages

setup(
    name='weagent-core',
    version='1.0.0',
    description='WeAgent shared core package — domain service base, models, utils',
    packages=find_packages(include=['app', 'app.*']),
    install_requires=[
        'Flask>=2.3.0',
        'Flask-SQLAlchemy>=3.1.0',
        'Flask-JWT-Extended>=4.5.0',
        'Flask-CORS>=4.0.0',
        'redis>=5.0.0',
        'PyMySQL>=1.1.0',
        'python-dotenv>=1.0.0',
    ],
    python_requires='>=3.10',
)
