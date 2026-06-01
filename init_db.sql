-- ============================================
-- 计费系统 MySQL 初始化脚本 (仅建表)
-- 使用方式: mysql -u root -p < init_db.sql
-- 种子数据由 Python 程序自动生成
-- ============================================

CREATE DATABASE IF NOT EXISTS billing_system
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE billing_system;

CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(64) NOT NULL,
    email       VARCHAR(100) DEFAULT '',
    phone       VARCHAR(20)  DEFAULT '',
    role        ENUM('admin', 'user') DEFAULT 'user',
    wechat_openid VARCHAR(100) DEFAULT '',
    avatar      VARCHAR(200) DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS billing_records (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    service_name  VARCHAR(50)  NOT NULL,
    amount        DECIMAL(12,2) NOT NULL DEFAULT 0,
    type          ENUM('收入', '支出') NOT NULL DEFAULT '收入',
    category      VARCHAR(20)  DEFAULT '-',
    description   VARCHAR(200) DEFAULT '',
    date          DATE         NOT NULL,
    user_id       INT          DEFAULT 1,
    record_hash   VARCHAR(32)  DEFAULT '',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_date (date),
    INDEX idx_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    action      VARCHAR(50)  NOT NULL,
    detail      VARCHAR(500) DEFAULT '',
    ip_address  VARCHAR(45)  DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
