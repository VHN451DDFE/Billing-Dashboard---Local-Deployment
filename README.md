<div align="center">

# 📊 Billing Dashboard

<b translate="no">English</b> &nbsp;|&nbsp; <a href="README.zh.md" translate="no"><b>简体中文</b></a>

</div>

---

> A full-stack **Flask REST API + MySQL + Redis + JWT** billing management system with admin/user role separation, data visualization, Redis deduplication, and batch import/export.

---

## 🏗️ Architecture

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
│   · users        │      · MD5 dedup              │
│   · billing_records    · SADD atomic             │
│   · audit_logs   │                               │
└──────────────────┴───────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12 / Flask 3.x |
| **Database** | MySQL 8.0 + PyMySQL + DBUtils Pool |
| **Cache/Dedup** | Redis 7.0 + hashlib MD5 + SADD |
| **Auth** | JWT (PyJWT) + Bearer Token |
| **Export** | openpyxl (Excel) / CSV |
| **Frontend** | Vanilla HTML5/CSS3/JS + Chart.js 4.x |

---

## ✨ Features

### 🔐 Dual-Role RBAC
| Feature | Admin | User |
|---------|:----:|:---:|
| Dashboard (KPI + Charts) | All users | Self only |
| Billing CRUD | ✅ | Self only |
| Batch Add Records | ✅ | ✅ |
| Search & Filter | ✅ | ✅ |
| Export Excel / CSV | All users | Self only |
| User Management (CRUD) | ✅ | ❌ |
| Audit Logs | ✅ | ❌ |
| Redis Dedup Stats | ✅ | ❌ |
| Profile & Password | ✅ | ✅ |

### 🛡️ Redis Dedup (`jf:filter`)
- Generates `hashlib.md5()` fingerprint before insert
- Atomic check via `SADD jf:filter <hash>`
- `1` → new record → write MySQL
- `0` → duplicate → reject with HTTP 409

### 📥 Export
- **Excel (.xlsx)** — styled header, auto column width, borders
- **CSV (.csv)** — UTF-8 BOM, Excel-compatible
- Format chooser dialog before download

### 📋 Batch Add
- Paste multi-line records in textarea, comma-separated
- Auto validation + per-record Redis dedup
- Returns success/skip/error summary

---

## 📁 Project Structure

```
jsq/
├── app.py              # Flask REST API (28 routes)
├── config.py           # MySQL / Redis / JWT config (env vars)
├── mysql_db.py         # MySQL module (pool + CRUD + seed)
├── redis_filter.py     # Redis dedup module (MD5 + SADD)
├── init_db.sql         # MySQL schema reference
├── database.py         # [Legacy] SQLite version (reference)
├── sever.py            # [Legacy] Jinja template version (reference)
├── requirements.txt    # Python dependencies
├── .gitignore
├── README.md
├── cn.md
├── templates/          # [Legacy] Jinja2 templates
├── static/             # [Legacy] CSS files
└── frontend/           # New SPA frontend
    ├── login.html
    ├── register.html
    ├── admin.html      # Admin console (4 tabs)
    ├── user.html       # User dashboard
    └── profile.html    # Profile settings
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- MySQL 8.0+
- Redis 7.0+

### 1. Set Environment Variables

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

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Services
```bash
# Ensure MySQL & Redis are running
# Linux/Mac: sudo systemctl start mysql redis
```

### 4. Run
```bash
python app.py
# Open http://localhost:5000
```

> First run auto-creates database `billing_system`, all tables, and seeds demo data.

---

## 📡 API Reference

### Authentication
| Method | Route | Auth | Description |
|--------|-------|:----:|-------------|
| POST | `/api/auth/register` | — | Register → MySQL |
| POST | `/api/auth/login` | — | Login → JWT |
| GET | `/api/auth/me` | 🔒 | Current user info |

### Dashboard
| Method | Route | Auth | Description |
|--------|-------|:----:|-------------|
| GET | `/api/dashboard` | 🔒 | KPI + chart data |

### Billing Records
| Method | Route | Auth | Description |
|--------|-------|:----:|-------------|
| GET | `/api/records` | 🔒 | List records |
| POST | `/api/records/add` | 🔒 | Add (Redis dedup) |
| POST | `/api/records/batch-add` | 🔒 | Batch add |
| PUT | `/api/records/update/<id>` | 🔒 | Update |
| DELETE | `/api/records/delete/<id>` | 🔒 | Delete |
| GET | `/api/records/search` | 🔒 | Search & filter |

### Export
| Method | Route | Auth | Description |
|--------|-------|:----:|-------------|
| GET | `/api/export?format=excel` | 🔒 | Export Excel |
| GET | `/api/export?format=csv` | 🔒 | Export CSV |

### User Management (Admin)
| Method | Route | Auth | Description |
|--------|-------|:----:|-------------|
| GET | `/api/users` | 🛡️ | List users |
| POST | `/api/users/add` | 🛡️ | Add user |
| PUT | `/api/users/role/<id>` | 🛡️ | Change role |
| DELETE | `/api/users/delete/<id>` | 🛡️ | Delete user |

### Other
| Method | Route | Auth | Description |
|--------|-------|:----:|-------------|
| PUT | `/api/profile` | 🔒 | Update profile |
| PUT | `/api/profile/password` | 🔒 | Change password |
| GET | `/api/audit-logs` | 🛡️ | Audit logs |
| GET | `/api/redis/stats` | 🛡️ | Redis dedup stats |

> 🔒 = `Authorization: Bearer <token>` &nbsp;|&nbsp; 🛡️ = Admin only

---

## 👥 Default Accounts

> Override passwords via `ADMIN_SEED_PASSWORD` / `DEMO_SEED_PASSWORD` / `YY_SEED_PASSWORD` env vars.

| Username | Default Password | Role | Page |
|----------|-----------------|------|------|
| `admin` | `admin123` | Admin | admin.html |
| `demo` | `demo123` | User | user.html |
| `yy` | `yy123` | User | user.html |

---

## 🔄 Redis Dedup Mechanism

```python
# redis_filter.py
def check_and_add(record_data: dict) -> (is_duplicate, md5_hash):
    md5_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    added = redis_client.sadd("jf:filter", md5_hash)
    # added=1 → new  |  added=0 → duplicate
    return (added == 0), md5_hash
```

- **Key**: `jf:filter`
- **Type**: Redis Set
- **Hash**: MD5 with sorted keys for consistency

---

## ⚠️ Security Notes

1. **Production**: Set `FLASK_DEBUG=false`, use a strong `JWT_SECRET_KEY` (≥32 bytes)
2. **Seed passwords**: Override via env vars or change manually after first run
3. **MySQL**: Use strong passwords, never commit real credentials
4. **Redis**: Default no-password; production should set `requirepass` or bind `127.0.0.1`
5. **Password hashing**: Demo uses SHA-256; production should use bcrypt/scrypt

---

## 📝 License

MIT — For educational purposes
