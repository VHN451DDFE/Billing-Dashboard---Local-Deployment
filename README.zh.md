<div align="center">

# 📊 Billing Dashboard — 计费仪表盘

<a href="README.md" translate="no"><b>English</b></a> &nbsp;|&nbsp; <b translate="no">简体中文</b>

</div>

---

> 基于 **Flask REST API + MySQL + Redis + JWT** 的前后端分离计费管理系统，支持管理员/普通用户双角色、数据可视化、Redis 去重、批量导入导出。

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────┐
│                   Frontend (SPA)                  │
│   login.html  register.html  admin.html          │
│   user.html   profile.html                       │
│   ↓ fetch() + JWT Token in Authorization Header  │
├──────────────────────────────────────────────────┤
│              Flask REST API (app.py)              │
│   JWT Auth  │  Role Guard  │  JSON Response      │
├──────────────────┬───────────────────────────────┤
│   MySQL 8.0      │      Redis 7.0                │
│   billing_system │      jf:filter (Set)          │
│   · users        │      · MD5 去重               │
│   · billing_records    · SADD 原子操作            │
│   · audit_logs   │                               │
└──────────────────┴───────────────────────────────┘
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.12 / Flask 3.x |
| **数据库** | MySQL 8.0 + PyMySQL + DBUtils 连接池 |
| **缓存/去重** | Redis 7.0 + hashlib MD5 + SADD |
| **认证** | JWT (PyJWT) + Bearer Token |
| **导出** | openpyxl (Excel) / CSV |
| **前端** | 原生 HTML5/CSS3/JS + Chart.js 4.x |

---

## ✨ 功能特性

### 🔐 双角色权限
| 功能 | 管理员 | 普通用户 |
|------|:-----:|:-----:|
| 数据概览 (KPI + 图表) | 全平台 | 仅自己 |
| 计费记录 CRUD | ✅ | 仅自己 |
| 批量添加记录 | ✅ | ✅ |
| 搜索 & 筛选 | ✅ | ✅ |
| 导出 Excel / CSV | 全平台 | 仅自己 |
| 用户管理 (增/删/改角色) | ✅ | ❌ |
| 审计日志查看 | ✅ | ❌ |
| Redis 去重统计 | ✅ | ❌ |
| 个人资料 & 密码修改 | ✅ | ✅ |

### 🛡️ Redis 去重 (`jf:filter`)
- 每条记录添加前使用 `hashlib.md5()` 生成指纹
- 通过 `SADD jf:filter <hash>` 原子检查
- 返回 `1` → 新记录，写入 MySQL
- 返回 `0` → 重复记录，拦截并返回 409

### 📥 导出报表
- **Excel (.xlsx)** — 带紫色表头样式、自动列宽、边框
- **CSV (.csv)** — UTF-8 BOM 编码，Excel 直接打开不乱码
- 弹出格式选择对话框

### 📋 批量添加
- 文本框粘贴多行记录，逗号分隔 6 个字段
- 自动验证 + 逐条 Redis 去重
- 返回成功/跳过/错误详细统计

---

## 📁 项目结构

```
jsq/
├── app.py              # Flask REST API 主程序 (28 个路由)
├── config.py           # MySQL / Redis / JWT 配置 (环境变量)
├── mysql_db.py         # MySQL 数据库模块 (连接池 + CRUD + 种子数据)
├── redis_filter.py     # Redis 去重模块 (hashlib MD5 + SADD)
├── init_db.sql         # MySQL 建表参考 SQL
├── database.py         # [旧版] SQLite 数据库模块 (保留参考)
├── sever.py            # [旧版] Flask Jinja 模板版 (保留参考)
├── requirements.txt    # Python 依赖
├── .gitignore
├── README.md           # 英文文档
├── README.zh.md         # 中文文档
├── templates/          # [旧版] Jinja2 模板
├── static/             # [旧版] CSS 文件
└── frontend/           # 新版前后端分离前端
    ├── login.html      # 登录页
    ├── register.html   # 注册页
    ├── admin.html      # 管理员控制台 (SPA: 4 Tab)
    ├── user.html       # 用户仪表盘
    └── profile.html    # 个人设置
```

---

## 🚀 快速启动

### 前置条件
- Python 3.10+
- MySQL 8.0+
- Redis 7.0+

### 1. 设置环境变量

**Linux/Mac:**
```bash
export MYSQL_HOST=localhost
export MYSQL_USER=your_user
export MYSQL_PASSWORD=your_mysql_password
export MYSQL_DATABASE=billing_system
export REDIS_HOST=localhost
export JWT_SECRET_KEY=your-secret-key-min-32-chars
```

**Windows PowerShell:**
```powershell
$env:MYSQL_HOST = "localhost"
$env:MYSQL_USER = "your_user"
$env:MYSQL_PASSWORD = "your_mysql_password"
$env:MYSQL_DATABASE = "billing_system"
$env:REDIS_HOST = "localhost"
$env:JWT_SECRET_KEY = "your-secret-key-min-32-chars"
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 启动服务
```bash
# 确保 MySQL 和 Redis 已启动
# Linux/Mac: sudo systemctl start mysql redis
```

### 4. 运行
```bash
python app.py
# 访问 http://localhost:5000
```

> 首次启动自动创建数据库 `billing_system` 及所有表，并播种默认用户和演示数据。

---

## 📡 API 文档

### 认证 (Auth)
| Method | Route | Auth | 说明 |
|--------|-------|:----:|------|
| POST | `/api/auth/register` | — | 用户注册 → MySQL |
| POST | `/api/auth/login` | — | 登录验证 → 返回 JWT |
| GET | `/api/auth/me` | 🔒 | 获取当前用户信息 |

### 仪表盘 (Dashboard)
| Method | Route | Auth | 说明 |
|--------|-------|:----:|------|
| GET | `/api/dashboard` | 🔒 | KPI + 图表数据 (按角色) |

### 计费记录 (Records)
| Method | Route | Auth | 说明 |
|--------|-------|:----:|------|
| GET | `/api/records` | 🔒 | 记录列表 |
| POST | `/api/records/add` | 🔒 | 新增 (Redis 去重) |
| POST | `/api/records/batch-add` | 🔒 | 批量添加 |
| PUT | `/api/records/update/<id>` | 🔒 | 更新记录 |
| DELETE | `/api/records/delete/<id>` | 🔒 | 删除记录 |
| GET | `/api/records/search` | 🔒 | 搜索筛选 |

### 导出 (Export)
| Method | Route | Auth | 说明 |
|--------|-------|:----:|------|
| GET | `/api/export?format=excel` | 🔒 | 导出 Excel |
| GET | `/api/export?format=csv` | 🔒 | 导出 CSV |

### 用户管理 (Admin)
| Method | Route | Auth | 说明 |
|--------|-------|:----:|------|
| GET | `/api/users` | 🛡️ | 用户列表 |
| POST | `/api/users/add` | 🛡️ | 添加用户 |
| PUT | `/api/users/role/<id>` | 🛡️ | 修改角色 |
| DELETE | `/api/users/delete/<id>` | 🛡️ | 删除用户 |

### 其他
| Method | Route | Auth | 说明 |
|--------|-------|:----:|------|
| PUT | `/api/profile` | 🔒 | 更新个人资料 |
| PUT | `/api/profile/password` | 🔒 | 修改密码 |
| GET | `/api/audit-logs` | 🛡️ | 审计日志 |
| GET | `/api/redis/stats` | 🛡️ | Redis 去重统计 |

> 🔒 = 需要 JWT Token &nbsp;|&nbsp; 🛡️ = 需要管理员权限

---

## 👥 预置账户

> 密码可通过环境变量 `ADMIN_SEED_PASSWORD` / `DEMO_SEED_PASSWORD` / `YY_SEED_PASSWORD` 覆盖。

| 用户名 | 默认密码 | 角色 | 页面 |
|--------|----------|------|------|
| `admin` | `admin123` | 管理员 | admin.html |
| `demo` | `demo123` | 普通用户 | user.html |
| `yy` | `yy123` | 普通用户 | user.html |

---

## 🔑 JWT 认证流程

```
1. POST /api/auth/login {username, password}
2. → MySQL 验证用户是否存在
3. → 存在 & 密码正确 → 返回 {token: "eyJ...", user: {...}}
4. → 不存在 → 返回 401 {"need_register": true, "message": "该用户不存在，请先注册"}
5. 前端将 token 存入 localStorage
6. 后续请求统一携带: Authorization: Bearer <token>
7. Token 有效期 24 小时
```

---

## 🔄 Redis 去重机制

```python
# redis_filter.py
def check_and_add(record_data: dict) -> (is_duplicate, md5_hash):
    # 1. hashlib MD5 序列化后的记录数据
    md5_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    # 2. Redis SADD 检查 (原子操作)
    added = redis_client.sadd("jf:filter", md5_hash)
    # 3. added=1 → 新记录 | added=0 → 重复
    return (added == 0), md5_hash
```

- **Key**: `jf:filter`
- **类型**: Redis Set
- **指纹算法**: MD5 (sort_keys 保证一致性)

---

## ⚠️ 安全提示

1. **生产环境**: 设置 `FLASK_DEBUG=false`，`JWT_SECRET_KEY` 使用 ≥32 字节随机字符串
2. **种子密码**: 部署后通过环境变量覆盖，或启动后手动修改
3. **MySQL 密码**: 务必使用强密码，不要提交真实凭据到 Git
4. **Redis**: 默认无密码，生产环境应配置 `requirepass` 或仅监听 `127.0.0.1`
5. **密码哈希**: 演示项目使用 SHA-256，生产环境建议升级为 bcrypt/scrypt

---

## 📝 License

MIT License — 仅供学习参考
