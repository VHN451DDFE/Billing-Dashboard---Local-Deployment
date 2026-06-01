"""
计费仪表盘 — Flask 主程序
认证系统 + 角色分离（管理员/用户）+ CRUD API + 数据仪表盘
"""
import flask
import json
import random
import os
import io
import csv
from datetime import datetime, timedelta
from functools import wraps
import database as db

# ── App ──
app = flask.Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'billing-dashboard-secret-key-2024'

# ── Constants ──
SERVICES = ["云服务器", "对象存储", "CDN加速", "数据库", "域名服务", "安全防护"]
COST_CATEGORIES = ["服务器", "带宽", "人工", "软件许可", "其他"]
MONTH_LABELS = ["7月","8月","9月","10月","11月","12月","1月","2月","3月","4月","5月","6月"]


# ── Auth Decorators ──
def login_required(f):
    """登录验证装饰器：未登录用户重定向到登录页"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in flask.session:
            return flask.redirect(flask.url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """管理员权限装饰器：非管理员重定向到用户页"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in flask.session:
            return flask.redirect(flask.url_for('login'))
        if flask.session.get('role') != 'admin':
            return flask.redirect(flask.url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated


# ── Helper: get request IP ──
def get_client_ip():
    """获取客户端 IP 地址"""
    if flask.request.headers.get('X-Forwarded-For'):
        return flask.request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return flask.request.remote_addr or '127.0.0.1'


# ── Dashboard Data (from SQLite) ──
def generate_mock_data(user_id=None):
    """从 SQLite 读取计费记录，计算 KPI 和图表数据。
    如果指定 user_id，只统计该用户的数据。"""
    if user_id:
        records = db.get_records_by_user_id(user_id)
    else:
        records = db.get_all_records()

    if not records:
        return {
            "kpi": {"total_revenue": 0, "total_cost": 0, "net_profit": 0, "active_services": 0},
            "revenue_trend": {"labels": MONTH_LABELS, "values": [0]*12},
            "cost_breakdown": {"labels": COST_CATEGORIES, "values": [0]*5},
            "service_revenue": {"labels": SERVICES, "values": [0]*6},
            "records": [],
        }

    total_revenue = sum(r['amount'] for r in records if r['type'] == '收入')
    total_cost = sum(r['amount'] for r in records if r['type'] == '支出')
    net_profit = total_revenue - total_cost

    service_rev = {s: 0 for s in SERVICES}
    for r in records:
        if r['type'] == '收入' and r['service_name'] in service_rev:
            service_rev[r['service_name']] += r['amount']
    service_labels = SERVICES[:]
    service_values = [round(service_rev[s], 2) for s in SERVICES]

    cat_cost = {c: 0 for c in COST_CATEGORIES}
    for r in records:
        if r['type'] == '支出' and r['category'] in cat_cost:
            cat_cost[r['category']] += r['amount']
    cost_labels = COST_CATEGORIES[:]
    cost_values = [round(cat_cost[c], 2) for c in COST_CATEGORIES]

    month_values = [0.0] * 12
    for r in records:
        if r['type'] == '收入':
            try:
                d = datetime.strptime(r['date'], "%Y-%m-%d")
                month_idx = d.month - 1
                if 0 <= month_idx < 12:
                    month_values[month_idx] += r['amount']
            except ValueError:
                pass
    month_values = [round(v, 2) for v in month_values]

    if sum(month_values) == 0:
        base_values = [82000, 85000, 88000, 90000, 95000, 102000,
                       105000, 110000, 115000, 120000, 128000, 135000]
        random.seed(42)
        month_values = [round(v + random.uniform(-5000, 8000), 2) for v in base_values]

    # 兜底支出饼图
    cost_fallback = [420000, 240000, 300000, 120000, 120000]
    svc_fallback = [300000, 180000, 220000, 150000, 70000, 80000]

    kpi = {
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_cost, 2),
        "net_profit": round(net_profit, 2),
        "active_services": len([v for v in service_values if v > 0]) or len(SERVICES),
    }

    return {
        "kpi": kpi,
        "revenue_trend": {"labels": MONTH_LABELS, "values": month_values},
        "cost_breakdown": {"labels": cost_labels, "values": cost_values if sum(cost_values) > 0 else cost_fallback},
        "service_revenue": {"labels": service_labels, "values": service_values if sum(service_values) > 0 else svc_fallback},
        "records": records,
    }


# ═══════════════════════════════════════════════════════════
# Routes: 首页（按角色分发）
# ═══════════════════════════════════════════════════════════

@app.route('/')
@login_required
def index():
    """根据角色跳转到对应仪表盘"""
    role = flask.session.get('role', 'user')
    if role == 'admin':
        return flask.redirect(flask.url_for('admin_dashboard'))
    return flask.redirect(flask.url_for('user_dashboard'))


# ═══════════════════════════════════════════════════════════
# Routes: 管理员仪表盘
# ═══════════════════════════════════════════════════════════

@app.route('/admin')
@admin_required
def admin_dashboard():
    """管理员专用仪表盘：全部数据 + 用户管理"""
    dashboard = generate_mock_data(user_id=None)  # 全部用户数据
    user = db.get_user_by_username(flask.session.get('username', '')) or {}
    all_users = db.get_all_users()
    user_stats = db.get_user_stats()
    audit_logs = db.get_audit_logs(limit=30)
    return flask.render_template('admin_dashboard.html',
                                 dashboard=dashboard,
                                 user=user,
                                 all_users=all_users,
                                 user_stats=user_stats,
                                 audit_logs=audit_logs)


# ═══════════════════════════════════════════════════════════
# Routes: 普通用户仪表盘
# ═══════════════════════════════════════════════════════════

@app.route('/user')
@login_required
def user_dashboard():
    """普通用户仪表盘：仅显示自己的数据"""
    user_id = flask.session.get('user_id')
    dashboard = generate_mock_data(user_id=user_id)
    user = db.get_user_by_username(flask.session.get('username', '')) or {}
    return flask.render_template('user_dashboard.html',
                                 dashboard=dashboard,
                                 user=user)


# ═══════════════════════════════════════════════════════════
# Routes: 个人资料管理
# ═══════════════════════════════════════════════════════════

@app.route('/profile')
@login_required
def profile():
    """个人资料页面"""
    user = db.get_user_by_id(flask.session.get('user_id')) or {}
    return flask.render_template('profile.html', user=user)


@app.route('/api/profile/update', methods=['POST'])
@login_required
def api_update_profile():
    """更新个人资料（邮箱、手机号）"""
    data = flask.request.get_json() or flask.request.form
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    user_id = flask.session.get('user_id')

    db.update_user_profile(user_id, email, phone)
    db.add_audit_log(user_id, "个人资料更新", f"更新邮箱/手机号", get_client_ip())
    return flask.jsonify({"success": True, "message": "个人资料更新成功"})


@app.route('/api/profile/password', methods=['POST'])
@login_required
def api_change_password():
    """修改密码"""
    data = flask.request.get_json() or flask.request.form
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    confirm = data.get('confirm', '')

    if not new_password or len(new_password) < 6:
        return flask.jsonify({"success": False, "message": "新密码至少 6 位"}), 400
    if new_password != confirm:
        return flask.jsonify({"success": False, "message": "两次新密码不一致"}), 400

    user_id = flask.session.get('user_id')
    success, msg = db.change_password(user_id, old_password, new_password)
    if success:
        db.add_audit_log(user_id, "密码修改", "用户修改密码", get_client_ip())
    return flask.jsonify({"success": success, "message": msg})


# ═══════════════════════════════════════════════════════════
# Routes: Authentication
# ═══════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if flask.request.method == 'POST':
        username = flask.request.form.get('username', '').strip()
        password = flask.request.form.get('password', '')
        if username and password:
            user = db.verify_user(username, password)
            if user:
                flask.session['user_id'] = user['id']
                flask.session['username'] = user['username']
                flask.session['role'] = user.get('role', 'user')
                db.add_audit_log(user['id'], "用户登录",
                                 f"用户 {username} 登录系统（角色: {user.get('role', 'user')}）",
                                 get_client_ip())
                next_url = flask.request.args.get('next', '/')
                return flask.redirect(next_url)
        error = '用户名或密码错误'
    return flask.render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if flask.request.method == 'POST':
        username = flask.request.form.get('username', '').strip()
        email = flask.request.form.get('email', '').strip()
        phone = flask.request.form.get('phone', '').strip()
        password = flask.request.form.get('password', '')
        confirm = flask.request.form.get('confirm', '')

        if not username or len(username) < 2:
            error = '用户名至少 2 个字符'
        elif not password or len(password) < 6:
            error = '密码至少 6 位'
        elif password != confirm:
            error = '两次密码不一致'
        elif db.get_user_by_username(username):
            error = '用户名已存在'
        else:
            user_id = db.create_user(username, password, email, phone, role='user')
            if user_id:
                flask.session['user_id'] = user_id
                flask.session['username'] = username
                flask.session['role'] = 'user'
                db.add_audit_log(user_id, "用户注册", f"新用户 {username} 注册", get_client_ip())
                return flask.redirect(flask.url_for('index'))
            error = '注册失败，请重试'
    return flask.render_template('register.html', error=error)


@app.route('/logout')
def logout():
    if 'user_id' in flask.session:
        db.add_audit_log(flask.session['user_id'], "用户登出",
                         f"用户 {flask.session.get('username', '')} 登出",
                         get_client_ip())
    flask.session.clear()
    return flask.redirect(flask.url_for('login'))


# ═══════════════════════════════════════════════════════════
# Routes: Social Login (simulated OAuth)
# ═══════════════════════════════════════════════════════════

SOCIAL_PROVIDERS = {
    'wechat': {'name': '微信', 'color': '#07C160', 'icon': '💬'},
    'qq':     {'name': 'QQ',   'color': '#12B7F5', 'icon': '🐧'},
    'weibo':  {'name': '微博', 'color': '#E6162D', 'icon': '📢'},
}


@app.route('/social-login/<provider>', methods=['GET', 'POST'])
def social_login(provider):
    """模拟 OAuth 授权流程"""
    if provider not in SOCIAL_PROVIDERS:
        return '不支持的登录方式', 400

    info = SOCIAL_PROVIDERS[provider]
    if flask.request.method == 'GET':
        return flask.render_template('social_login.html', provider=provider, info=info)

    mock_openid = f"{provider}_user_{random.randint(10000, 99999)}"
    mock_nickname = f"{info['name']}用户{mock_openid[-4:]}"
    mock_avatar = ''

    user = db.get_or_create_social_user(provider, mock_openid, mock_nickname, mock_avatar)
    flask.session['user_id'] = user['id']
    flask.session['username'] = user['username']
    flask.session['role'] = user.get('role', 'user')
    db.add_audit_log(user['id'], "社交登录",
                     f"{info['name']}授权登录 (openid: {mock_openid[:12]}...)",
                     get_client_ip())
    return flask.redirect(flask.url_for('index'))


# ═══════════════════════════════════════════════════════════
# Routes: 用户管理 API（仅管理员）
# ═══════════════════════════════════════════════════════════

@app.route('/api/users')
@admin_required
def api_users():
    """获取所有用户列表"""
    users = db.get_all_users()
    return flask.jsonify({"success": True, "users": users})


@app.route('/api/users/add', methods=['POST'])
@admin_required
def api_add_user():
    """管理员添加新用户"""
    data = flask.request.get_json() or flask.request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    role = data.get('role', 'user').strip()

    if not username or len(username) < 2:
        return flask.jsonify({"success": False, "message": "用户名至少 2 个字符"}), 400
    if not password or len(password) < 6:
        return flask.jsonify({"success": False, "message": "密码至少 6 位"}), 400
    if db.get_user_by_username(username):
        return flask.jsonify({"success": False, "message": "用户名已存在"}), 400

    user_id = db.create_user(username, password, email, phone, role)
    if user_id:
        db.add_audit_log(flask.session['user_id'], "用户管理",
                         f"管理员创建用户 {username}（角色: {role}）",
                         get_client_ip())
        return flask.jsonify({"success": True, "id": user_id, "message": f"用户 {username} 创建成功"})
    return flask.jsonify({"success": False, "message": "创建失败"}), 500


@app.route('/api/users/role/<int:user_id>', methods=['POST'])
@admin_required
def api_update_user_role(user_id):
    """管理员修改用户角色"""
    data = flask.request.get_json() or flask.request.form
    new_role = data.get('role', 'user').strip()
    if new_role not in ('admin', 'user'):
        return flask.jsonify({"success": False, "message": "无效的角色"}), 400

    target = db.get_user_by_id(user_id)
    if not target:
        return flask.jsonify({"success": False, "message": "用户不存在"}), 404
    if target['username'] == 'admin' and new_role != 'admin':
        return flask.jsonify({"success": False, "message": "不能移除主管理员的权限"}), 403

    db.update_user_role(user_id, new_role)
    db.add_audit_log(flask.session['user_id'], "用户管理",
                     f"修改用户 {target['username']} 角色为 {new_role}",
                     get_client_ip())
    return flask.jsonify({"success": True, "message": "角色更新成功"})


@app.route('/api/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def api_delete_user(user_id):
    """管理员删除用户"""
    target = db.get_user_by_id(user_id)
    if not target:
        return flask.jsonify({"success": False, "message": "用户不存在"}), 404
    if target['username'] == 'admin':
        return flask.jsonify({"success": False, "message": "不能删除主管理员账户"}), 403
    if user_id == flask.session.get('user_id'):
        return flask.jsonify({"success": False, "message": "不能删除自己的账户"}), 403

    username = target['username']
    db.delete_user(user_id)
    db.add_audit_log(flask.session['user_id'], "用户管理",
                     f"管理员删除用户 {username}",
                     get_client_ip())
    return flask.jsonify({"success": True, "message": f"用户 {username} 已删除"})


# ═══════════════════════════════════════════════════════════
# Routes: 数据导出（仅管理员）
# ═══════════════════════════════════════════════════════════

@app.route('/api/export/csv')
@admin_required
def api_export_csv():
    """导出计费记录为 CSV 文件"""
    csv_data = db.export_records_csv()
    db.add_audit_log(flask.session['user_id'], "数据导出",
                     "导出计费记录 CSV",
                     get_client_ip())

    # 使用 io.StringIO 构建响应
    si = io.StringIO()
    si.write(csv_data)
    output = flask.make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=billing_records.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    si.close()
    return output


# ═══════════════════════════════════════════════════════════
# Routes: 审计日志 API
# ═══════════════════════════════════════════════════════════

@app.route('/api/audit-logs')
@admin_required
def api_audit_logs():
    """获取审计日志"""
    limit = flask.request.args.get('limit', 50, type=int)
    logs = db.get_audit_logs(limit=limit)
    return flask.jsonify({"success": True, "logs": logs})


# ═══════════════════════════════════════════════════════════
# Routes: Dashboard API
# ═══════════════════════════════════════════════════════════

@app.route('/api/dashboard')
@login_required
def api_dashboard():
    role = flask.session.get('role', 'user')
    user_id = None if role == 'admin' else flask.session.get('user_id')
    return flask.jsonify(generate_mock_data(user_id=user_id))


# ═══════════════════════════════════════════════════════════
# Routes: CRUD API (protected)
# ═══════════════════════════════════════════════════════════

@app.route('/api/records/add', methods=['POST'])
@login_required
def api_add_record():
    data = flask.request.get_json() or flask.request.form
    service_name = data.get('service_name', '').strip()
    amount = float(data.get('amount', 0))
    rec_type = data.get('type', '收入').strip()
    category = data.get('category', '-').strip()
    description = data.get('description', '').strip()
    date = data.get('date', datetime.now().strftime("%Y-%m-%d")).strip()
    user_id = flask.session.get('user_id', 1)

    if not service_name or amount <= 0:
        return flask.jsonify({"success": False, "message": "服务名称和金额不能为空"}), 400

    record_id = db.add_record(service_name, amount, rec_type, category, description, date, user_id)
    db.add_audit_log(user_id, "记录新增",
                     f"添加 {rec_type} 记录: {service_name} ¥{amount:,.2f}",
                     get_client_ip())
    return flask.jsonify({"success": True, "id": record_id, "message": "记录添加成功"})


@app.route('/api/records/update/<int:record_id>', methods=['POST'])
@login_required
def api_update_record(record_id):
    record = db.get_record_by_id(record_id)
    if not record:
        return flask.jsonify({"success": False, "message": "记录不存在"}), 404

    # 普通用户只能修改自己的记录
    if flask.session.get('role') != 'admin' and record['user_id'] != flask.session.get('user_id'):
        return flask.jsonify({"success": False, "message": "无权修改此记录"}), 403

    data = flask.request.get_json() or flask.request.form
    service_name = data.get('service_name', record['service_name']).strip()
    amount = float(data.get('amount', record['amount']))
    rec_type = data.get('type', record['type']).strip()
    category = data.get('category', record['category']).strip()
    description = data.get('description', record.get('description', '')).strip()
    date = data.get('date', record['date']).strip()

    db.update_record(record_id, service_name, amount, rec_type, category, description, date)
    return flask.jsonify({"success": True, "message": "记录更新成功"})


@app.route('/api/records/delete/<int:record_id>', methods=['POST'])
@login_required
def api_delete_record(record_id):
    record = db.get_record_by_id(record_id)
    if not record:
        return flask.jsonify({"success": False, "message": "记录不存在"}), 404

    # 普通用户只能删除自己的记录
    if flask.session.get('role') != 'admin' and record['user_id'] != flask.session.get('user_id'):
        return flask.jsonify({"success": False, "message": "无权删除此记录"}), 403

    db.delete_record(record_id)
    return flask.jsonify({"success": True, "message": "记录已删除"})


# ═══════════════════════════════════════════════════════════
# Routes: 搜索 & 筛选 API
# ═══════════════════════════════════════════════════════════

@app.route('/api/records/search')
@login_required
def api_search_records():
    """搜索计费记录：支持关键词、类型、日期范围筛选"""
    keyword = flask.request.args.get('keyword', '').strip()
    rec_type = flask.request.args.get('type', '').strip()
    date_from = flask.request.args.get('date_from', '').strip()
    date_to = flask.request.args.get('date_to', '').strip()

    role = flask.session.get('role', 'user')
    user_id = None if role == 'admin' else flask.session.get('user_id')
    records = db.get_all_records() if user_id is None else db.get_records_by_user_id(user_id)

    # 筛选
    filtered = []
    for r in records:
        if keyword and keyword.lower() not in r['service_name'].lower() and keyword.lower() not in r.get('description', '').lower():
            continue
        if rec_type and r['type'] != rec_type:
            continue
        if date_from and r['date'] < date_from:
            continue
        if date_to and r['date'] > date_to:
            continue
        filtered.append(r)

    return flask.jsonify({"success": True, "records": filtered, "count": len(filtered)})


if __name__ == '__main__':
    app.run(debug=True)
