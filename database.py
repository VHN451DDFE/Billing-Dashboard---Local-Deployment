"""
计费仪表盘 — SQLite 数据库模块
初始化数据库、建表、播种默认数据
支持管理员/普通用户角色分离
"""
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), 'billing.db')

SERVICES = ["云服务器", "对象存储", "CDN加速", "数据库", "域名服务", "安全防护"]
COST_CATEGORIES = ["服务器", "带宽", "人工", "软件许可", "其他"]
MONTH_LABELS = ["7月","8月","9月","10月","11月","12月","1月","2月","3月","4月","5月","6月"]

DESCRIPTIONS = {
    "云服务器": ["包年套餐续费", "按量计费-计算", "预留实例月结", "ECS实例升级"],
    "对象存储": ["标准存储容量费", "外网下行流量费", "归档存储取回费", "跨区域复制流量"],
    "CDN加速": ["HTTPS加速月结", "全站加速带宽", "动态加速流量包", "静态加速月结"],
    "数据库": ["RDS包年续费", "Redis集群扩容", "MongoDB副本集", "数据库备份存储"],
    "域名服务": ["com域名续费", "cn域名注册", "DNS解析套餐", "SSL证书续费"],
    "安全防护": ["DDoS高防月付", "WAF防护包年", "漏洞扫描服务", "堡垒机月结"],
}


def hash_password(password: str) -> str:
    """SHA-256 哈希密码"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库：建表 + 种子数据（仅在首次时执行）"""
    conn = get_db()
    cursor = conn.cursor()

    # ── 建表 ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            password_hash TEXT   NOT NULL,
            email       TEXT    DEFAULT '',
            phone       TEXT    DEFAULT '',
            role        TEXT    DEFAULT 'user',
            wechat_openid TEXT   DEFAULT '',
            avatar      TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now','localtime'))
        )
    ''')

    # 兼容旧表：尝试添加 role 列（如果不存在）
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass  # 列已存在

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing_records (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name  TEXT    NOT NULL,
            amount        REAL    NOT NULL DEFAULT 0,
            type          TEXT    NOT NULL DEFAULT '收入',
            category      TEXT    DEFAULT '-',
            description   TEXT    DEFAULT '',
            date          TEXT    NOT NULL,
            user_id       INTEGER DEFAULT 1,
            created_at    TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # ── 审计日志表 ──
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            action      TEXT    NOT NULL,
            detail      TEXT    DEFAULT '',
            ip_address  TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # ── 检查是否已播种 ──
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        # 种子管理员账户
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (?, ?, ?, ?, ?)",
            ("admin", hash_password("123456"), "admin@billing.com", "13800000000", "admin")
        )
        # 种子一个普通用户用于演示
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (?, ?, ?, ?, ?)",
            ("demo", hash_password("demo123"), "demo@billing.com", "13900000001", "user")
        )
        # 种子 yy 用户
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (?, ?, ?, ?, ?)",
            ("yy", hash_password("yy1"), "yy@billing.com", "13900000002", "user")
        )
    else:
        # 已有用户时，确保 admin 角色为 admin
        cursor.execute("UPDATE users SET role='admin' WHERE username='admin' AND role='user'")
        # 如果 yy 用户不存在则创建
        existing = cursor.execute("SELECT id FROM users WHERE username='yy'").fetchone()
        if not existing:
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, phone, role) VALUES (?, ?, ?, ?, ?)",
                ("yy", hash_password("yy1"), "yy@billing.com", "13900000002", "user")
            )

    cursor.execute("SELECT COUNT(*) FROM billing_records")
    record_count = cursor.fetchone()[0]

    if record_count == 0:
        seed_billing_records(cursor)

    # 种子一些审计日志
    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    log_count = cursor.fetchone()[0]
    if log_count == 0:
        seed_audit_logs(cursor)

    conn.commit()
    conn.close()


def seed_billing_records(cursor):
    """播种 25 条默认计费记录"""
    random.seed(42)
    records = []
    base_date = datetime(2025, 7, 1)

    for i in range(25):
        offset_days = random.randint(0, 365)
        record_date = base_date + timedelta(days=offset_days)
        service_name = random.choice(SERVICES)
        is_expense = random.random() < 0.35
        rec_type = "支出" if is_expense else "收入"
        category = random.choice(COST_CATEGORIES) if is_expense else "-"
        amount = round(random.uniform(200, 50000), 2) if is_expense else round(random.uniform(500, 100000), 2)
        description = f"{service_name} - {random.choice(DESCRIPTIONS[service_name])}"
        # 分散到不同用户
        user_id = random.choice([1, 2, 3])  # admin(1), demo(2), yy(3)

        records.append((
            service_name,
            amount,
            rec_type,
            category,
            description,
            record_date.strftime("%Y-%m-%d"),
            user_id
        ))

    # 按日期降序排序后插入
    records.sort(key=lambda r: r[5], reverse=True)
    cursor.executemany(
        "INSERT INTO billing_records (service_name, amount, type, category, description, date, user_id) VALUES (?,?,?,?,?,?,?)",
        records
    )


def seed_audit_logs(cursor):
    """播种默认审计日志"""
    logs = [
        (1, "系统启动", "计费仪表盘系统初始化完成", "127.0.0.1"),
        (1, "用户登录", "管理员 admin 登录系统", "192.168.1.100"),
        (1, "数据导出", "导出当月计费报表", "192.168.1.100"),
        (1, "用户管理", "创建用户 demo", "192.168.1.100"),
        (2, "用户登录", "用户 demo 登录系统", "192.168.1.101"),
        (2, "记录新增", "添加云服务器计费记录", "192.168.1.101"),
        (1, "系统配置", "修改仪表盘显示参数", "192.168.1.100"),
    ]
    for log in logs:
        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, detail, ip_address) VALUES (?,?,?,?)",
            log
        )


# ═══════════════════════════════════════════════════════════
# 计费记录 CRUD
# ═══════════════════════════════════════════════════════════

def get_all_records():
    """获取所有计费记录（最近的在前面）"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM billing_records ORDER BY date DESC, id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_records_by_user_id(user_id):
    """获取某个用户的计费记录"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM billing_records WHERE user_id=? ORDER BY date DESC, id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_record(service_name, amount, rec_type, category, description, date, user_id=1):
    """添加一条计费记录"""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO billing_records (service_name, amount, type, category, description, date, user_id) VALUES (?,?,?,?,?,?,?)",
        (service_name, amount, rec_type, category, description, date, user_id)
    )
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id


def update_record(record_id, service_name, amount, rec_type, category, description, date):
    """更新一条计费记录"""
    conn = get_db()
    conn.execute(
        "UPDATE billing_records SET service_name=?, amount=?, type=?, category=?, description=?, date=? WHERE id=?",
        (service_name, amount, rec_type, category, description, date, record_id)
    )
    conn.commit()
    conn.close()


def delete_record(record_id):
    """删除一条计费记录"""
    conn = get_db()
    conn.execute("DELETE FROM billing_records WHERE id=?", (record_id,))
    conn.commit()
    conn.close()


def get_record_by_id(record_id):
    """按 ID 获取单条记录"""
    conn = get_db()
    row = conn.execute("SELECT * FROM billing_records WHERE id=?", (record_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ═══════════════════════════════════════════════════════════
# 用户管理
# ═══════════════════════════════════════════════════════════

def get_user_by_username(username):
    """按用户名查找用户"""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    """按 ID 查找用户"""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    """获取所有用户列表（管理员用）"""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, email, phone, role, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username, password, email='', phone='', role='user'):
    """创建新用户"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, email, phone, role) VALUES (?,?,?,?,?)",
            (username, hash_password(password), email, phone, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def verify_user(username, password):
    """验证用户凭据，成功返回用户 dict，失败返回 None"""
    user = get_user_by_username(username)
    if user and user['password_hash'] == hash_password(password):
        return user
    return None


def update_user_role(user_id, new_role):
    """更新用户角色"""
    conn = get_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id):
    """删除用户及其所有计费记录"""
    conn = get_db()
    conn.execute("DELETE FROM billing_records WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM audit_logs WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def update_user_profile(user_id, email='', phone=''):
    """更新用户个人资料"""
    conn = get_db()
    conn.execute(
        "UPDATE users SET email=?, phone=? WHERE id=?",
        (email, phone, user_id)
    )
    conn.commit()
    conn.close()


def change_password(user_id, old_password, new_password):
    """修改密码：先验证旧密码，再更新"""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "用户不存在"
    user = dict(row)
    if user['password_hash'] != hash_password(old_password):
        conn.close()
        return False, "原密码错误"
    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(new_password), user_id)
    )
    conn.commit()
    conn.close()
    return True, "密码修改成功"


def get_user_stats():
    """获取用户统计信息（管理员用）"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
    user_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0]
    conn.close()
    return {
        "total_users": total,
        "admin_count": admin_count,
        "user_count": user_count,
    }


# ═══════════════════════════════════════════════════════════
# 审计日志
# ═══════════════════════════════════════════════════════════

def add_audit_log(user_id, action, detail='', ip_address=''):
    """添加一条审计日志"""
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs (user_id, action, detail, ip_address) VALUES (?,?,?,?)",
        (user_id, action, detail, ip_address)
    )
    conn.commit()
    conn.close()


def get_audit_logs(limit=50):
    """获取最近的审计日志"""
    conn = get_db()
    rows = conn.execute(
        """SELECT a.id, a.action, a.detail, a.ip_address, a.created_at,
                  u.username
           FROM audit_logs a
           LEFT JOIN users u ON a.user_id = u.id
           ORDER BY a.created_at DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_or_create_social_user(provider, openid, nickname, avatar=''):
    """为社交登录查找或创建用户"""
    conn = get_db()
    col = f"{provider}_openid" if provider in ('wechat', 'qq', 'weibo') else 'wechat_openid'

    # 查找已有社交账户
    row = conn.execute(f"SELECT * FROM users WHERE {col}=?", (openid,)).fetchone()
    if row:
        conn.close()
        return dict(row)

    # 创建新用户
    username = f"{provider}_{openid[:8]}"
    try:
        cursor = conn.execute(
            f"INSERT INTO users (username, password_hash, {col}, avatar, role) VALUES (?,?,?,?,?)",
            (username, hash_password(openid), openid, avatar, 'user')
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"id": user_id, "username": username, "avatar": avatar, "role": "user"}
    except sqlite3.IntegrityError:
        conn.close()
        return get_or_create_social_user(provider, openid, nickname, avatar)


# ═══════════════════════════════════════════════════════════
# 数据导出
# ═══════════════════════════════════════════════════════════

def export_records_csv():
    """导出所有计费记录为 CSV 格式字符串"""
    records = get_all_records()
    if not records:
        return "id,service_name,amount,type,category,description,date\n"
    header = "id,service_name,amount,type,category,description,date,user_id\n"
    rows = []
    for r in records:
        rows.append(f'{r["id"]},"{r["service_name"]}",{r["amount"]},"{r["type"]}","{r["category"]}","{r["description"]}","{r["date"]}",{r["user_id"]}')
    return header + "\n".join(rows)


# ── 启动时自动初始化 ──
init_db()
