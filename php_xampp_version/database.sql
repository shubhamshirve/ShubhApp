-- Multi-Tenant SaaS Recurring Billing Platform
-- MySQL Database Schema for XAMPP/cPanel
-- Run this file to create all tables

CREATE DATABASE IF NOT EXISTS saas_billing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE saas_billing;

-- Users Table (Super Admin, Operators, Staff)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'operator', 'staff') NOT NULL DEFAULT 'operator',
    operator_id VARCHAR(36),
    permissions JSON,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_operator_id (operator_id),
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB;

-- Operators Table
CREATE TABLE IF NOT EXISTS operators (
    id VARCHAR(36) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    owner_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    gst_number VARCHAR(20),
    charge_gst BOOLEAN DEFAULT FALSE,
    bank_account_name VARCHAR(255),
    bank_account_number VARCHAR(50),
    bank_ifsc VARCHAR(20),
    bank_name VARCHAR(100),
    saas_plan_id VARCHAR(36),
    saas_plan_name VARCHAR(100),
    status ENUM('trial', 'active', 'suspended', 'expired') DEFAULT 'trial',
    trial_ends_at TIMESTAMP NULL,
    subscription_ends_at TIMESTAMP NULL,
    is_read_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_status (status),
    INDEX idx_saas_plan_id (saas_plan_id)
) ENGINE=InnoDB;

-- SaaS Plans Table (Admin Managed)
CREATE TABLE IF NOT EXISTS saas_plans (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    monthly_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    max_subscribers INT NOT NULL DEFAULT 100,
    max_staff INT NOT NULL DEFAULT 3,
    trial_enabled BOOLEAN DEFAULT FALSE,
    trial_days INT DEFAULT 0,
    notification_module BOOLEAN DEFAULT FALSE,
    auto_reminder BOOLEAN DEFAULT FALSE,
    audit_logs BOOLEAN DEFAULT FALSE,
    payment_gateway_setup BOOLEAN DEFAULT FALSE,
    gst_applicable BOOLEAN DEFAULT TRUE,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Operator Plans Table (Operator Defined Service Plans)
CREATE TABLE IF NOT EXISTS operator_plans (
    id VARCHAR(36) PRIMARY KEY,
    operator_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    validity ENUM('monthly', 'quarterly', 'half_yearly', 'yearly') DEFAULT 'monthly',
    tax_percentage DECIMAL(5,2) DEFAULT 0,
    tax_type ENUM('none', 'inclusive', 'exclusive') DEFAULT 'none',
    description TEXT,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_operator_id (operator_id),
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Subscribers Table
CREATE TABLE IF NOT EXISTS subscribers (
    id VARCHAR(36) PRIMARY KEY,
    operator_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    whatsapp_number VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    address TEXT,
    plan_id VARCHAR(36) NOT NULL,
    plan_name VARCHAR(100),
    billing_date TINYINT NOT NULL CHECK (billing_date BETWEEN 1 AND 28),
    discount DECIMAL(10,2) DEFAULT 0,
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_operator_id (operator_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_billing_date (billing_date),
    INDEX idx_status (status),
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(36) PRIMARY KEY,
    operator_id VARCHAR(36) NOT NULL,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    subscriber_id VARCHAR(36) NOT NULL,
    subscriber_name VARCHAR(255),
    plan_id VARCHAR(36) NOT NULL,
    plan_name VARCHAR(100),
    base_amount DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    final_amount DECIMAL(10,2) NOT NULL,
    service_start_date DATE NOT NULL,
    service_end_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status ENUM('pending', 'paid', 'overdue', 'cancelled') DEFAULT 'pending',
    payment_id VARCHAR(100),
    gateway_fee DECIMAL(10,2) DEFAULT 0,
    gateway_gst DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    INDEX idx_operator_id (operator_id),
    INDEX idx_subscriber_id (subscriber_id),
    INDEX idx_status (status),
    INDEX idx_due_date (due_date),
    INDEX idx_invoice_number (invoice_number),
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Payment Gateway Configuration
CREATE TABLE IF NOT EXISTS payment_gateways (
    id VARCHAR(36) PRIMARY KEY,
    operator_id VARCHAR(36) NOT NULL UNIQUE,
    gateway_type ENUM('razorpay', 'cashfree', 'phonepe') NOT NULL,
    api_key VARCHAR(255) NOT NULL,
    api_secret VARCHAR(255) NOT NULL,
    webhook_secret VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    user_name VARCHAR(255),
    role VARCHAR(20),
    action VARCHAR(50) NOT NULL,
    module VARCHAR(50) NOT NULL,
    old_value JSON,
    new_value JSON,
    ip_address VARCHAR(45),
    operator_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operator_id (operator_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- Notification Queue Table
CREATE TABLE IF NOT EXISTS notification_queue (
    id VARCHAR(36) PRIMARY KEY,
    operator_id VARCHAR(36) NOT NULL,
    subscriber_id VARCHAR(36),
    invoice_id VARCHAR(36),
    notification_type ENUM('invoice', 'reminder', 'bulk') NOT NULL,
    whatsapp_number VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    sent_at TIMESTAMP NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operator_id (operator_id),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- SaaS Payments Table (Platform Revenue)
CREATE TABLE IF NOT EXISTS saas_payments (
    id VARCHAR(36) PRIMARY KEY,
    operator_id VARCHAR(36) NOT NULL,
    saas_plan_id VARCHAR(36) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    gst_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),
    billing_period_start DATE,
    billing_period_end DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operator_id (operator_id)
) ENGINE=InnoDB;

-- Insert Default Admin User
INSERT INTO users (id, email, name, phone, password, role, status) VALUES
(UUID(), 'admin@saas.com', 'Super Admin', '9999999999', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin', 'active');
-- Default password is 'admin123'

-- Insert Default SaaS Plans
INSERT INTO saas_plans (id, name, monthly_price, max_subscribers, max_staff, trial_enabled, trial_days, notification_module, auto_reminder, audit_logs, payment_gateway_setup, gst_applicable, status) VALUES
(UUID(), 'Starter (Trial)', 0, 10, 1, TRUE, 3, FALSE, FALSE, FALSE, FALSE, FALSE, 'active'),
(UUID(), 'Basic', 999, 100, 3, FALSE, 0, TRUE, TRUE, FALSE, TRUE, TRUE, 'active'),
(UUID(), 'Professional', 2499, 500, 10, FALSE, 0, TRUE, TRUE, TRUE, TRUE, TRUE, 'active'),
(UUID(), 'Enterprise', 4999, 2000, 25, FALSE, 0, TRUE, TRUE, TRUE, TRUE, TRUE, 'active');
