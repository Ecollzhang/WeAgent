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

-- ========================================
-- Capability library tables
-- ========================================
CREATE TABLE IF NOT EXISTS `capabilities` (
    `user_id` VARCHAR(36) DEFAULT NULL,
    `type` ENUM('skill', 'tool', 'mcp', 'plugin') NOT NULL,
    `name` VARCHAR(120) NOT NULL,
    `slug` VARCHAR(160) NOT NULL,
    `description` TEXT,
    `source` VARCHAR(50) NOT NULL DEFAULT 'user',
    `source_ref` VARCHAR(500) DEFAULT NULL,
    `is_builtin` TINYINT(1) NOT NULL DEFAULT 0,
    `latest_version_id` VARCHAR(36) DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_capability_user_slug` (`user_id`, `slug`),
    KEY `ix_capabilities_user_id` (`user_id`),
    KEY `ix_capabilities_type` (`type`),
    KEY `ix_capabilities_slug` (`slug`),
    KEY `ix_capabilities_source` (`source`),
    KEY `ix_capabilities_latest_version_id` (`latest_version_id`),
    CONSTRAINT `capabilities_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `capability_versions` (
    `capability_id` VARCHAR(36) NOT NULL,
    `version` VARCHAR(50) NOT NULL,
    `content` TEXT,
    `manifest` JSON DEFAULT NULL,
    `permissions` JSON DEFAULT NULL,
    `meta` JSON DEFAULT NULL,
    `checksum` VARCHAR(128) DEFAULT NULL,
    `created_by` VARCHAR(36) DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_capability_version` (`capability_id`, `version`),
    KEY `ix_capability_versions_capability_id` (`capability_id`),
    KEY `created_by` (`created_by`),
    CONSTRAINT `capability_versions_ibfk_1` FOREIGN KEY (`capability_id`) REFERENCES `capabilities` (`id`),
    CONSTRAINT `capability_versions_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `agent_capability_bindings` (
    `agent_id` VARCHAR(36) NOT NULL,
    `capability_id` VARCHAR(36) NOT NULL,
    `capability_version_id` VARCHAR(36) NOT NULL,
    `enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `version_policy` ENUM('pinned', 'follow_latest') NOT NULL DEFAULT 'pinned',
    `granted_permissions` JSON DEFAULT NULL,
    `authorization_snapshot` JSON DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_agent_capability` (`agent_id`, `capability_id`),
    KEY `ix_agent_capability_bindings_agent_id` (`agent_id`),
    KEY `ix_agent_capability_bindings_capability_id` (`capability_id`),
    KEY `ix_agent_capability_bindings_version_id` (`capability_version_id`),
    CONSTRAINT `agent_capability_bindings_ibfk_1` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`),
    CONSTRAINT `agent_capability_bindings_ibfk_2` FOREIGN KEY (`capability_id`) REFERENCES `capabilities` (`id`),
    CONSTRAINT `agent_capability_bindings_ibfk_3` FOREIGN KEY (`capability_version_id`) REFERENCES `capability_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `capability_call_records` (
    `session_id` VARCHAR(100) NOT NULL,
    `run_id` VARCHAR(100) DEFAULT NULL,
    `agent_id` VARCHAR(36) NOT NULL,
    `capability_id` VARCHAR(36) NOT NULL,
    `capability_version_id` VARCHAR(36) NOT NULL,
    `call_type` VARCHAR(30) NOT NULL DEFAULT 'tool',
    `tool_name` VARCHAR(160) NOT NULL DEFAULT '',
    `permissions_used` JSON DEFAULT NULL,
    `input_summary` JSON DEFAULT NULL,
    `output_summary` JSON DEFAULT NULL,
    `status` ENUM('started', 'completed', 'failed') NOT NULL DEFAULT 'started',
    `error` TEXT,
    `started_at` DATETIME DEFAULT NULL,
    `completed_at` DATETIME DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    KEY `ix_capability_call_records_session_id` (`session_id`),
    KEY `ix_capability_call_records_run_id` (`run_id`),
    KEY `ix_capability_call_records_agent_id` (`agent_id`),
    KEY `ix_capability_call_records_capability_id` (`capability_id`),
    KEY `ix_capability_call_records_version_id` (`capability_version_id`),
    KEY `ix_capability_call_records_call_type` (`call_type`),
    KEY `ix_capability_call_records_status` (`status`),
    CONSTRAINT `capability_call_records_ibfk_1` FOREIGN KEY (`capability_id`) REFERENCES `capabilities` (`id`),
    CONSTRAINT `capability_call_records_ibfk_2` FOREIGN KEY (`capability_version_id`) REFERENCES `capability_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `plugin_install_records` (
    `user_id` VARCHAR(36) NOT NULL,
    `plugin_capability_id` VARCHAR(36) NOT NULL,
    `plugin_version_id` VARCHAR(36) NOT NULL,
    `source` VARCHAR(50) NOT NULL DEFAULT 'npx',
    `source_ref` VARCHAR(500) DEFAULT NULL,
    `package_name` VARCHAR(240) DEFAULT NULL,
    `package_version` VARCHAR(80) DEFAULT NULL,
    `status` ENUM('installed', 'failed', 'removed') NOT NULL DEFAULT 'installed',
    `manifest` JSON DEFAULT NULL,
    `included_capabilities` JSON DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_plugin_install_version` (`user_id`, `plugin_capability_id`, `plugin_version_id`),
    KEY `ix_plugin_install_records_user_id` (`user_id`),
    KEY `ix_plugin_install_records_capability_id` (`plugin_capability_id`),
    KEY `ix_plugin_install_records_version_id` (`plugin_version_id`),
    KEY `ix_plugin_install_records_source` (`source`),
    KEY `ix_plugin_install_records_status` (`status`),
    CONSTRAINT `plugin_install_records_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
    CONSTRAINT `plugin_install_records_ibfk_2` FOREIGN KEY (`plugin_capability_id`) REFERENCES `capabilities` (`id`),
    CONSTRAINT `plugin_install_records_ibfk_3` FOREIGN KEY (`plugin_version_id`) REFERENCES `capability_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `skill_revision_drafts` (
    `source_skill_id` VARCHAR(36) NOT NULL,
    `source_version_id` VARCHAR(36) NOT NULL,
    `session_id` VARCHAR(100) NOT NULL,
    `agent_id` VARCHAR(36) NOT NULL,
    `diff` JSON DEFAULT NULL,
    `full_markdown` TEXT NOT NULL,
    `status` ENUM('pending_review', 'published', 'forked', 'rejected') NOT NULL DEFAULT 'pending_review',
    `reviewed_at` DATETIME DEFAULT NULL,
    `id` VARCHAR(36) NOT NULL,
    `created_at` DATETIME NOT NULL,
    `updated_at` DATETIME NOT NULL,
    PRIMARY KEY (`id`),
    KEY `ix_skill_revision_drafts_source_skill_id` (`source_skill_id`),
    KEY `ix_skill_revision_drafts_source_version_id` (`source_version_id`),
    KEY `ix_skill_revision_drafts_session_id` (`session_id`),
    KEY `ix_skill_revision_drafts_agent_id` (`agent_id`),
    KEY `ix_skill_revision_drafts_status` (`status`),
    CONSTRAINT `skill_revision_drafts_ibfk_1` FOREIGN KEY (`source_skill_id`) REFERENCES `capabilities` (`id`),
    CONSTRAINT `skill_revision_drafts_ibfk_2` FOREIGN KEY (`source_version_id`) REFERENCES `capability_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
