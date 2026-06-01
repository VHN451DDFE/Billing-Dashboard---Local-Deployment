"""
MySQL 数据库模块
用户注册 → MySQL, 登录验证 → MySQL
连接池 + CRUD + 种子数据
"""
import os
import hashlib
import random
from datetime import datetime, timedelta
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
import config

# ═══════════════════════════════════════════════════════════
# 数据库自动创建
# ═══════════════════════════════════════════════════════════
def ensure_database():
    """连接到 MySQL 服务器，自动创建数据库（如果不存在）"""
    db_name = config.MYSQL_CONFIG['database']
    conn = pymysql.connect(
        host=config.MYSQL_CONFIG['host'],
        port=config.MYSQL_CONFIG['port'],
        user=config.MYSQL_CONFIG['user'],
        password=config.MYSQL_CONFIG['password'],
        charset='utf8mb4',
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"[MySQL] 数据库 '{db_name}' 已就绪")
    finally:
        conn.close()


def ensure_tables():
    """创建表结构（如果不存在）"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    username    VARCHAR(50)  NOT NULL UNIQUE,
                    password_hash VARCHAR(64) NOT NULL,
                    email       VARCHAR(100) DEFAULT '',
                    phone       VARCHAR(20)  DEFAULT '',
                    role        VARCHAR(10) DEFAULT 'user',
                    wechat_openid VARCHAR(100) DEFAULT '',
                    avatar      VARCHAR(200) DEFAULT '',
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS billing_records (
                    id            INT AUTO_INCREMENT PRIMARY KEY,
                    service_name  VARCHAR(50)  NOT NULL,
                    amount        DECIMAL(12,2) NOT NULL DEFAULT 0,
                    `type`        VARCHAR(10)  NOT NULL DEFAULT '收入',
                    category      VARCHAR(20)  DEFAULT '-',
                    description   VARCHAR(200) DEFAULT '',
                    date          DATE         NOT NULL,
                    user_id       INT          DEFAULT 1,
                    record_hash   VARCHAR(32)  DEFAULT '',
                    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_date (date),
                    INDEX idx_type (`type`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            # 兼容旧表：如果 type 列仍是 ENUM，改为 VARCHAR
            try:
                cur.execute("ALTER TABLE billing_records MODIFY COLUMN `type` VARCHAR(10) NOT NULL DEFAULT '收入'")
                conn.commit()
            except Exception:
                pass
            # 兼容旧表：如果 role 列仍是 ENUM，改为 VARCHAR
            try:
                cur.execute("ALTER TABLE users MODIFY COLUMN role VARCHAR(10) DEFAULT 'user'")
                conn.commit()
            except Exception:
                pass
            cur.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT,
                    action      VARCHAR(50)  NOT NULL,
                    detail      VARCHAR(500) DEFAULT '',
                    ip_address  VARCHAR(45)  DEFAULT '',
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
        conn.commit()
        print("[MySQL] 数据表已就绪")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# 连接池
# ═══════════════════════════════════════════════════════════
_pool = None

def get_pool():
    """获取或创建数据库连接池"""
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            maxconnections=config.MYSQL_POOL_SIZE,
            mincached=2,
            maxcached=5,
            blocking=True,
            **config.MYSQL_CONFIG,
            cursorclass=DictCursor,
        )
    return _pool

def get_db():
    """从连接池获取一个数据库连接"""
    return get_pool().connection()

# ═══════════════════════════════════════════════════════════
# 密码工具
# ═══════════════════════════════════════════════════════════
def hash_password(password: str) -> str:
    """SHA-256 哈希密码"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ═══════════════════════════════════════════════════════════
# 数据库初始化 & 种子数据
# ═══════════════════════════════════════════════════════════
def init_db():
    """初始化数据库：自动建库 → 建表 → 播种默认数据"""
    # 第一步：确保数据库存在（无数据库名连接）
    ensure_database()
    # 第二步：确保表存在
    ensure_tables()
    # 第三步：如果用户表为空则播种
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM users")
            if cur.fetchone()['cnt'] == 0:
                seed_all(conn)
    finally:
        conn.close()

def seed_all(conn):
    """播种种子用户 + 计费记录 + 审计日志"""
    services = config.SERVICES
    categories = config.COST_CATEGORIES
    descriptions = {
        "云服务器": ["包年套餐续费", "按量计费-计算", "预留实例月结", "ECS实例升级"],
        "对象存储": ["标准存储容量费", "外网下行流量费", "归档存储取回费", "跨区域复制流量"],
        "CDN加速": ["HTTPS加速月结", "全站加速带宽", "动态加速流量包", "静态加速月结"],
        "数据库": ["RDS包年续费", "Redis集群扩容", "MongoDB副本集", "数据库备份存储"],
        "域名服务": ["com域名续费", "cn域名注册", "DNS解析套餐", "SSL证书续费"],
        "安全防护": ["DDoS高防月付", "WAF防护包年", "漏洞扫描服务", "堡垒机月结"],
    }

    with conn.cursor() as cur:
        # 种子用户 — 密码通过环境变量配置，默认值仅用于本地开发
        admin_pw = os.getenv('ADMIN_SEED_PASSWORD', 'admin123')
        demo_pw  = os.getenv('DEMO_SEED_PASSWORD',  'demo123')
        yy_pw    = os.getenv('YY_SEED_PASSWORD',    'yy123')
        cur.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (%s,%s,%s,%s,%s)",
            ("admin", hash_password(admin_pw), "admin@billing.com", "13800000000", "admin")
        )
        cur.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (%s,%s,%s,%s,%s)",
            ("demo", hash_password(demo_pw), "demo@billing.com", "13900000001", "user")
        )
        cur.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (%s,%s,%s,%s,%s)",
            ("yy", hash_password(yy_pw), "yy@billing.com", "13900000002", "user")
        )

        # 种子计费记录
        random.seed(42)
        records = []
        base_date = datetime(2025, 7, 1)
        for i in range(25):
            offset_days = random.randint(0, 365)
            record_date = base_date + timedelta(days=offset_days)
            service_name = random.choice(services)
            is_expense = random.random() < 0.35
            rec_type = "支出" if is_expense else "收入"
            category = random.choice(categories) if is_expense else "-"
            amount = round(random.uniform(200, 50000), 2) if is_expense else round(random.uniform(500, 100000), 2)
            desc = f"{service_name} - {random.choice(descriptions[service_name])}"
            user_id = random.choice([1, 2, 3])
            records.append((service_name, amount, rec_type, category, desc, record_date.strftime("%Y-%m-%d"), user_id))
        records.sort(key=lambda r: r[5], reverse=True)
        cur.executemany(
            "INSERT INTO billing_records (service_name, amount, type, category, description, date, user_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            records
        )

        # 种子审计日志
        logs = [
            (1, "系统启动", "计费仪表盘系统初始化完成", "127.0.0.1"),
            (1, "用户登录", "管理员 admin 登录系统", "192.168.1.100"),
            (1, "数据导出", "导出当月计费报表", "192.168.1.100"),
            (1, "用户管理", "创建用户 demo", "192.168.1.100"),
            (2, "用户登录", "用户 demo 登录系统", "192.168.1.101"),
            (2, "记录新增", "添加云服务器计费记录", "192.168.1.101"),
            (1, "系统配置", "修改仪表盘显示参数", "192.168.1.100"),
        ]
        cur.executemany(
            "INSERT INTO audit_logs (user_id, action, detail, ip_address) VALUES (%s,%s,%s,%s)", logs
        )
    conn.commit()

# ═══════════════════════════════════════════════════════════
# 计费记录 CRUD
# ═══════════════════════════════════════════════════════════
def get_all_records():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM billing_records ORDER BY date DESC, id DESC")
            return cur.fetchall()
    finally:
        conn.close()

def get_records_by_user_id(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM billing_records WHERE user_id=%s ORDER BY date DESC, id DESC", (user_id,))
            return cur.fetchall()
    finally:
        conn.close()

def add_record(service_name, amount, rec_type, category, description, date, user_id=1, record_hash=''):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO billing_records (service_name, amount, type, category, description, date, user_id, record_hash)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (service_name, amount, rec_type, category, description, date, user_id, record_hash)
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

def update_record(record_id, service_name, amount, rec_type, category, description, date):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE billing_records SET service_name=%s, amount=%s, type=%s, category=%s, description=%s, date=%s
                   WHERE id=%s""",
                (service_name, amount, rec_type, category, description, date, record_id)
            )
            conn.commit()
    finally:
        conn.close()

def delete_record(record_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM billing_records WHERE id=%s", (record_id,))
            conn.commit()
    finally:
        conn.close()

def get_record_by_id(record_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM billing_records WHERE id=%s", (record_id,))
            return cur.fetchone()
    finally:
        conn.close()

# ═══════════════════════════════════════════════════════════
# 用户管理 (注册 → MySQL, 登录 → MySQL 验证)
# ═══════════════════════════════════════════════════════════
def get_user_by_username(username):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            return cur.fetchone()
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            return cur.fetchone()
    finally:
        conn.close()

def get_all_users():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, email, phone, role, created_at FROM users ORDER BY id")
            return cur.fetchall()
    finally:
        conn.close()

def create_user(username, password, email='', phone='', role='user'):
    """注册新用户 → 写入 MySQL"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, email, phone, role) VALUES (%s,%s,%s,%s,%s)",
                (username, hash_password(password), email, phone, role)
            )
            conn.commit()
            return cur.lastrowid
    except pymysql.IntegrityError:
        return None
    finally:
        conn.close()

def verify_user(username, password):
    """登录验证 → 查询 MySQL，有则返回用户，无则返回 None"""
    user = get_user_by_username(username)
    if user and user['password_hash'] == hash_password(password):
        return user
    return None

def update_user_role(user_id, new_role):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role=%s WHERE id=%s", (new_role, user_id))
            conn.commit()
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
            conn.commit()
    finally:
        conn.close()

def update_user_profile(user_id, email='', phone=''):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET email=%s, phone=%s WHERE id=%s", (email, phone, user_id))
            conn.commit()
    finally:
        conn.close()

def change_password(user_id, old_password, new_password):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            user = cur.fetchone()
            if not user:
                return False, "用户不存在"
            if user['password_hash'] != hash_password(old_password):
                return False, "原密码错误"
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hash_password(new_password), user_id))
            conn.commit()
            return True, "密码修改成功"
    finally:
        conn.close()

def get_user_stats():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM users")
            total = cur.fetchone()['cnt']
            cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role='admin'")
            admin_count = cur.fetchone()['cnt']
            cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE role='user'")
            user_count = cur.fetchone()['cnt']
        return {"total_users": total, "admin_count": admin_count, "user_count": user_count}
    finally:
        conn.close()

# ═══════════════════════════════════════════════════════════
# 审计日志
# ═══════════════════════════════════════════════════════════
def add_audit_log(user_id, action, detail='', ip_address=''):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_logs (user_id, action, detail, ip_address) VALUES (%s,%s,%s,%s)",
                (user_id, action, detail, ip_address)
            )
            conn.commit()
    finally:
        conn.close()

def get_audit_logs(limit=50):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT a.id, a.action, a.detail, a.ip_address, a.created_at, u.username
                   FROM audit_logs a LEFT JOIN users u ON a.user_id = u.id
                   ORDER BY a.created_at DESC LIMIT %s""", (limit,))
            return cur.fetchall()
    finally:
        conn.close()

# ═══════════════════════════════════════════════════════════
# 数据导出
# ═══════════════════════════════════════════════════════════
def export_records_csv():
    records = get_all_records()
    lines = ["id,service_name,amount,type,category,description,date,user_id"]
    for r in records:
        lines.append(f'{r["id"]},"{r["service_name"]}",{r["amount"]},"{r["type"]}","{r["category"]}","{r["description"]}","{r["date"]}",{r["user_id"]}')
    return "\n".join(lines)

# ── 启动时自动初始化 ──
init_db()
