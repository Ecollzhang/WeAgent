-- WeAgent 数据库初始化脚本
-- 使用前请先创建数据库:
--   CREATE DATABASE IF NOT EXISTS weagent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ========================================
-- 用户表
-- ========================================
CREATE TABLE IF NOT EXISTS `users` (
    `username` VARCHAR(80) NOT NULL,
    `email` VARCHAR(120) NOT NULL,
    `password_hash` VARCHAR(256) NOT NULL,
    `avatar_url` VARCHAR(500) DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `ix_users_username` (`username`),
    UNIQUE KEY `ix_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Agent 分类表
-- ========================================
CREATE TABLE IF NOT EXISTS `agent_categories` (
    `name` VARCHAR(100) NOT NULL,
    `icon` VARCHAR(50) DEFAULT NULL,
    `color` VARCHAR(20) DEFAULT NULL,
    `user_id` VARCHAR(36) DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    KEY `user_id` (`user_id`),
    CONSTRAINT `agent_categories_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Agent 表
-- ========================================
CREATE TABLE IF NOT EXISTS `agents` (
    `name` VARCHAR(100) NOT NULL,
    `avatar_url` VARCHAR(500) DEFAULT NULL,
    `avatar_color` VARCHAR(20) DEFAULT NULL,
    `capability_tags` JSON DEFAULT NULL,
    `agent_type` ENUM('external', 'custom') NOT NULL,
    `adapter_name` VARCHAR(50) NOT NULL,
    `config` JSON DEFAULT NULL,
    `system_prompt` TEXT,
    `skill` TEXT,
    `created_by` VARCHAR(36) DEFAULT NULL,
    `user_id` VARCHAR(36) DEFAULT NULL,
    `class_id` VARCHAR(36) DEFAULT NULL,
    `tool_ids` JSON DEFAULT NULL,
    `is_public` TINYINT(1) DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    KEY `created_by` (`created_by`),
    KEY `user_id` (`user_id`),
    KEY `class_id` (`class_id`),
    CONSTRAINT `agents_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`),
    CONSTRAINT `agents_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
    CONSTRAINT `agents_ibfk_3` FOREIGN KEY (`class_id`) REFERENCES `agent_categories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 会话表
-- ========================================
CREATE TABLE IF NOT EXISTS `conversations` (
    `title` VARCHAR(200) NOT NULL,
    `type` ENUM('single', 'group') NOT NULL,
    `owner_id` VARCHAR(36) NOT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    KEY `owner_id` (`owner_id`),
    CONSTRAINT `conversations_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 会话参与者表
-- ========================================
CREATE TABLE IF NOT EXISTS `conversation_participants` (
    `conversation_id` VARCHAR(36) NOT NULL,
    `participant_type` ENUM('user', 'agent') NOT NULL,
    `participant_id` VARCHAR(36) NOT NULL,
    `participant_name` VARCHAR(200) DEFAULT NULL,
    `participant_avatar` VARCHAR(500) DEFAULT NULL,
    `participant_color` VARCHAR(20) DEFAULT NULL,
    `joined_at` DATETIME DEFAULT (now()),
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_conversation_participant` (`conversation_id`, `participant_type`, `participant_id`),
    CONSTRAINT `conversation_participants_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 产物表 (必须先于 messages 创建)
-- ========================================
CREATE TABLE IF NOT EXISTS `artifacts` (
    `message_id` VARCHAR(36) DEFAULT NULL,
    `artifact_type` ENUM('code', 'webpage', 'document', 'ppt', 'diff') NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `content` TEXT,
    `language` VARCHAR(50) DEFAULT NULL,
    `preview_url` VARCHAR(500) DEFAULT NULL,
    `deploy_url` VARCHAR(500) DEFAULT NULL,
    `version` INT DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    KEY `message_id` (`message_id`),
    CONSTRAINT `artifacts_ibfk_1` FOREIGN KEY (`message_id`) REFERENCES `messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 消息表 (包含 elements 列)
-- ========================================
CREATE TABLE IF NOT EXISTS `messages` (
    `conversation_id` VARCHAR(36) NOT NULL,
    `sender_type` ENUM('user', 'agent') NOT NULL,
    `sender_id` VARCHAR(36) NOT NULL,
    `content` TEXT NOT NULL,
    `message_type` ENUM('text', 'code', 'image', 'file', 'artifact_card', 'diff_card') NOT NULL,
    `artifact_id` VARCHAR(36) DEFAULT NULL,
    `parent_message_id` VARCHAR(36) DEFAULT NULL,
    `is_pinned` TINYINT(1) DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    `elements` JSON DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `ix_messages_conversation_id` (`conversation_id`),
    KEY `artifact_id` (`artifact_id`),
    KEY `parent_message_id` (`parent_message_id`),
    CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`),
    CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`artifact_id`) REFERENCES `artifacts` (`id`),
    CONSTRAINT `messages_ibfk_3` FOREIGN KEY (`parent_message_id`) REFERENCES `messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Agent 工具表
-- ========================================
CREATE TABLE IF NOT EXISTS `agent_tools` (
    `name` VARCHAR(100) NOT NULL,
    `value` VARCHAR(100) NOT NULL,
    `category` VARCHAR(50) DEFAULT NULL,
    `icon` VARCHAR(50) DEFAULT NULL,
    `color` VARCHAR(20) DEFAULT NULL,
    `description` TEXT,
    `params` JSON DEFAULT NULL,
    `user_id` VARCHAR(36) DEFAULT NULL,
    `is_builtin` TINYINT(1) DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    KEY `user_id` (`user_id`),
    CONSTRAINT `agent_tools_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
