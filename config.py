"""
全局配置文件
MySQL + Redis + JWT 配置 — 通过环境变量注入，避免硬编码敏感信息
"""
import os

# ═══════════════════════════════════════════════════════════
# MySQL 配置 (从环境变量读取，本地开发可设置默认值)
# ═══════════════════════════════════════════════════════════
MYSQL_CONFIG = {
    'host':     os.getenv('MYSQL_HOST', 'localhost'),
    'port':     int(os.getenv('MYSQL_PORT', '3306')),
    'user':     os.getenv('MYSQL_USER', 'your_user'),
    'password': os.getenv('MYSQL_PASSWORD', 'your_password_here'),
    'database': os.getenv('MYSQL_DATABASE', 'billing_system'),
    'charset':  'utf8mb4',
    'autocommit': True,
    'connect_timeout': 10,
}

# 连接池配置
MYSQL_POOL_SIZE = int(os.getenv('MYSQL_POOL_SIZE', '5'))

# ═══════════════════════════════════════════════════════════
# Redis 配置
# ═══════════════════════════════════════════════════════════
REDIS_CONFIG = {
    'host':     os.getenv('REDIS_HOST', 'localhost'),
    'port':     int(os.getenv('REDIS_PORT', '6379')),
    'db':       int(os.getenv('REDIS_DB', '0')),
    'decode_responses': True,
    'socket_connect_timeout': 5,
}

# Redis 去重 key 前缀
REDIS_FILTER_KEY = os.getenv('REDIS_FILTER_KEY', 'jf:filter')

# ═══════════════════════════════════════════════════════════
# JWT 配置 (生产环境务必修改 JWT_SECRET_KEY)
# ═══════════════════════════════════════════════════════════
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

# ═══════════════════════════════════════════════════════════
# Flask 配置
# ═══════════════════════════════════════════════════════════
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')
DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('1', 'true', 'yes')
HOST = os.getenv('FLASK_HOST', '0.0.0.0')
PORT = int(os.getenv('FLASK_PORT', '5000'))

# ═══════════════════════════════════════════════════════════
# 业务常量
# ═══════════════════════════════════════════════════════════
SERVICES = ["云服务器", "对象存储", "CDN加速", "数据库", "域名服务", "安全防护"]
COST_CATEGORIES = ["服务器", "带宽", "人工", "软件许可", "其他"]
MONTH_LABELS = ["7月","8月","9月","10月","11月","12月","1月","2月","3月","4月","5月","6月"]
