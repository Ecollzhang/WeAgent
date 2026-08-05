-- ========================================
-- WeAgent Office Service — 数据库初始化脚本
-- 数据库: weagent_office
-- 方式: mysql -u root -p < init.sql
-- ========================================

CREATE DATABASE IF NOT EXISTS `weagent_office`
  DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `weagent_office`;

-- ========================================
-- 1. 会议
-- ========================================
CREATE TABLE IF NOT EXISTS `office_meetings` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `organizer_id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `agenda` TEXT,
    `participants` JSON,
    `location` VARCHAR(200),
    `start_time` DATETIME,
    `end_time` DATETIME,
    `transcript` TEXT,
    `minutes` TEXT,
    `materials` JSON,
    `resolutions` JSON,
    `meeting_link` VARCHAR(1000) DEFAULT '',
    `status` ENUM('scheduled','ongoing','completed','cancelled') NOT NULL DEFAULT 'scheduled',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_start_time` (`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 2. 行动项
-- ========================================
CREATE TABLE IF NOT EXISTS `office_action_items` (
    `id` VARCHAR(36) NOT NULL,
    `meeting_id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `creator_id` VARCHAR(36) NOT NULL,
    `assignee_id` VARCHAR(36),
    `assignee_name` VARCHAR(100),
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT,
    `due_date` DATETIME,
    `priority` ENUM('low','medium','high') DEFAULT 'medium',
    `status` ENUM('pending','in_progress','done','cancelled') NOT NULL DEFAULT 'pending',
    `schedule_id` VARCHAR(36),
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_due_date` (`due_date`),
    FOREIGN KEY (`meeting_id`) REFERENCES `office_meetings`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 3. 日程
-- ========================================
CREATE TABLE IF NOT EXISTS `office_schedules` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT,
    `event_type` ENUM('meeting','task','reminder','other') NOT NULL DEFAULT 'task',
    `start_time` DATETIME NOT NULL,
    `end_time` DATETIME NOT NULL,
    `priority` ENUM('low','medium','high') DEFAULT 'medium',
    `status` ENUM('pending','in_progress','done','cancelled') NOT NULL DEFAULT 'pending',
    `meeting_id` VARCHAR(36),
    `document_id` VARCHAR(36),
    `action_item_id` VARCHAR(36),
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_start_time` (`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 4. 公文
-- ========================================
CREATE TABLE IF NOT EXISTS `office_documents` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `meeting_id` VARCHAR(36),
    `title` VARCHAR(200) NOT NULL,
    `document_type` ENUM('notice','report','request','letter','minutes','other') NOT NULL,
    `content` TEXT,
    `recipients` JSON,
    `approvers` JSON,
    `template_id` VARCHAR(36),
    `status` ENUM('draft','reviewing','approved','published','archived') NOT NULL DEFAULT 'draft',
    `reviewer_id` VARCHAR(36),
    `review_comment` TEXT,
    `published_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 5. 公文签收
-- ========================================
CREATE TABLE IF NOT EXISTS `office_document_receipts` (
    `id` VARCHAR(36) NOT NULL,
    `document_id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `recipient_id` VARCHAR(36) NOT NULL,
    `recipient_name` VARCHAR(100),
    `read_at` DATETIME,
    `confirmed_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_document` (`document_id`),
    INDEX `idx_recipient` (`recipient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 6. 公文模板
-- ========================================
CREATE TABLE IF NOT EXISTS `office_doc_templates` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36),
    `creator_id` VARCHAR(36),
    `name` VARCHAR(200) NOT NULL,
    `document_type` ENUM('notice','report','request','letter','minutes','other') NOT NULL,
    `content` TEXT NOT NULL,
    `format_spec` TEXT,
    `is_system` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 7. 审批
-- ========================================
CREATE TABLE IF NOT EXISTS `office_approvals` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `document_id` VARCHAR(36),
    `title` VARCHAR(200) NOT NULL,
    `approval_type` VARCHAR(50),
    `initiator_id` VARCHAR(36) NOT NULL,
    `current_step` INT NOT NULL DEFAULT 1,
    `steps` JSON,
    `history` JSON,
    `status` ENUM('pending','approved','rejected','cancelled') NOT NULL DEFAULT 'pending',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 8. 部门
-- ========================================
CREATE TABLE IF NOT EXISTS `office_departments` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `head_user_id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_workspace` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 9. 小组
-- ========================================
CREATE TABLE IF NOT EXISTS `office_groups` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `leader_user_id` VARCHAR(36),
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 10. 组织成员
-- ========================================
CREATE TABLE IF NOT EXISTS `office_members` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `display_name` VARCHAR(100) NOT NULL,
    `role` ENUM('member','team_lead','department_head') NOT NULL DEFAULT 'member',
    `group_id` VARCHAR(36),
    `manager_user_id` VARCHAR(36),
    `active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_workspace_user` (`workspace_id`, `user_id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 11. 站内通知
-- ========================================
CREATE TABLE IF NOT EXISTS `office_notifications` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `recipient_id` VARCHAR(36) NOT NULL,
    `notification_type` VARCHAR(30) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `content` TEXT,
    `source_type` VARCHAR(30),
    `source_id` VARCHAR(36),
    `is_read` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_recipient` (`workspace_id`, `recipient_id`, `is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
