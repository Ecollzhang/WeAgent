-- ========================================
-- WeAgent RD Service — 数据库初始化脚本
-- 数据库: weagent_rd
-- 方式: mysql -u root -p < init.sql
-- ========================================

CREATE DATABASE IF NOT EXISTS `weagent_rd`
  DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `weagent_rd`;

-- ========================================
-- 1. 项目
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_projects` (
    `id` VARCHAR(36) NOT NULL,
    `workspace_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT,
    `cover_url` VARCHAR(500),
    `tech_stack` JSON,
    `coding_standards` TEXT,
    `status` ENUM('active','archived') DEFAULT 'active',
    `visibility` ENUM('private','team','public') DEFAULT 'team',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 2. 项目成员
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_project_members` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `role` ENUM('owner','admin','developer','viewer') DEFAULT 'developer',
    `joined_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_project_user` (`project_id`, `user_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 3. 迭代
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_iterations` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `goal` TEXT,
    `start_date` DATE,
    `end_date` DATE,
    `status` ENUM('planning','active','completed','cancelled') DEFAULT 'planning',
    `sort_order` INT DEFAULT 0,
    `progress_manual` INT COMMENT '手动设置的进度 0-100',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 4. 需求
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_requirements` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `iteration_id` VARCHAR(36),
    `parent_id` VARCHAR(36),
    `title` VARCHAR(300) NOT NULL,
    `description` TEXT,
    `acceptance_criteria` TEXT,
    `priority` ENUM('p0','p1','p2','p3') DEFAULT 'p2',
    `status` ENUM('backlog','todo','in_progress','in_review','done','closed') DEFAULT 'backlog',
    `type` ENUM('feature','enhancement','bugfix','tech_debt','research') DEFAULT 'feature',
    `story_points` INT DEFAULT 0,
    `labels` JSON,
    `developer_id` VARCHAR(36),
    `designer_id` VARCHAR(36),
    `tester_id` VARCHAR(36),
    `start_date` DATE,
    `due_date` DATE,
    `completed_at` DATETIME,
    `created_by` VARCHAR(36),
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    INDEX `idx_iteration` (`iteration_id`),
    INDEX `idx_parent` (`parent_id`),
    INDEX `idx_status` (`status`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`iteration_id`) REFERENCES `rd_iterations`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`parent_id`) REFERENCES `rd_requirements`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 5. 需求分配人
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_requirement_assignees` (
    `id` VARCHAR(36) NOT NULL,
    `requirement_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `role` ENUM('primary','reviewer','tester') DEFAULT 'primary',
    `assigned_at` DATETIME DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_req_user_role` (`requirement_id`, `user_id`, `role`),
    FOREIGN KEY (`requirement_id`) REFERENCES `rd_requirements`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 6. 缺陷
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_bugs` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `iteration_id` VARCHAR(36),
    `requirement_id` VARCHAR(36),
    `title` VARCHAR(300) NOT NULL,
    `description` TEXT,
    `expected_behavior` TEXT,
    `actual_behavior` TEXT,
    `severity` ENUM('blocker','critical','major','minor','trivial') DEFAULT 'major',
    `priority` ENUM('p0','p1','p2','p3') DEFAULT 'p2',
    `status` ENUM('open','confirmed','in_progress','fixed','verified','closed','wont_fix') DEFAULT 'open',
    `environment` VARCHAR(200),
    `browser_info` VARCHAR(200),
    `os_info` VARCHAR(200),
    `developer_id` VARCHAR(36),
    `designer_id` VARCHAR(36),
    `tester_id` VARCHAR(36),
    `attachments` JSON,
    `labels` JSON,
    `created_by` VARCHAR(36),
    `fixed_at` DATETIME,
    `verified_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    INDEX `idx_iteration` (`iteration_id`),
    INDEX `idx_requirement` (`requirement_id`),
    INDEX `idx_status` (`status`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`iteration_id`) REFERENCES `rd_iterations`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`requirement_id`) REFERENCES `rd_requirements`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 7. 缺陷分配人
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_bug_assignees` (
    `id` VARCHAR(36) NOT NULL,
    `bug_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `role` ENUM('fixer','reviewer','tester') DEFAULT 'fixer',
    `assigned_at` DATETIME DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_bug_user_role` (`bug_id`, `user_id`, `role`),
    FOREIGN KEY (`bug_id`) REFERENCES `rd_bugs`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 8. 缺陷-需求关联表（多对多）
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_bug_requirements` (
    `bug_id` VARCHAR(36) NOT NULL,
    `requirement_id` VARCHAR(36) NOT NULL,
    PRIMARY KEY (`bug_id`, `requirement_id`),
    FOREIGN KEY (`bug_id`) REFERENCES `rd_bugs`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`requirement_id`) REFERENCES `rd_requirements`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 9. 评论
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_comments` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `target_type` ENUM('requirement','bug','iteration') NOT NULL,
    `target_id` VARCHAR(36) NOT NULL,
    `parent_id` VARCHAR(36),
    `content` TEXT NOT NULL,
    `content_type` ENUM('text','markdown','system') DEFAULT 'markdown',
    `author_id` VARCHAR(36),
    `is_pinned` TINYINT(1) DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at` DATETIME,
    PRIMARY KEY (`id`),
    INDEX `idx_target` (`target_type`, `target_id`),
    INDEX `idx_parent` (`parent_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`parent_id`) REFERENCES `rd_comments`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 10. 分支
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_branches` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `repo_id` VARCHAR(36),
    `branch_name` VARCHAR(200) NOT NULL,
    `base_branch` VARCHAR(200) DEFAULT 'main',
    `source_type` ENUM('requirement','bug') NOT NULL,
    `source_id` VARCHAR(36) NOT NULL,
    `status` ENUM('active','merged','closed') DEFAULT 'active',
    `created_by` VARCHAR(36),
    `merged_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    INDEX `idx_source` (`source_type`, `source_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 11. GitHub OAuth 配置（单行表）
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_github_oauth_config` (
    `id` VARCHAR(36) NOT NULL DEFAULT 'default',
    `client_id` VARCHAR(200) NOT NULL,
    `client_secret` TEXT NOT NULL,
    `redirect_uri` VARCHAR(500) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 12. GitHub Token
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_github_tokens` (
    `id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `github_user` VARCHAR(100) NOT NULL,
    `access_token` TEXT NOT NULL,
    `token_type` VARCHAR(50) DEFAULT 'bearer',
    `scopes` VARCHAR(500),
    `expires_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 13. 代码仓库
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_repos` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `github_id` BIGINT NOT NULL,
    `owner` VARCHAR(200) NOT NULL,
    `repo_name` VARCHAR(200) NOT NULL,
    `full_name` VARCHAR(400) NOT NULL,
    `description` TEXT,
    `default_branch` VARCHAR(100) DEFAULT 'main',
    `language` VARCHAR(50),
    `html_url` VARCHAR(500),
    `clone_url` VARCHAR(500),
    `private` TINYINT(1) DEFAULT 0,
    `status` ENUM('active','archived') DEFAULT 'active',
    `synced_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 14. 活动日志
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_activity_logs` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `target_type` ENUM('requirement','bug','iteration','project','review','branch') NOT NULL,
    `target_id` VARCHAR(36) NOT NULL,
    `action` ENUM('created','updated','status_changed','assigned','commented','deleted') NOT NULL,
    `actor_id` VARCHAR(36),
    `old_value` JSON,
    `new_value` JSON,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    INDEX `idx_target` (`target_type`, `target_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 15. 代码审查
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_reviews` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `repo_id` VARCHAR(36),
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT,
    `code_content` TEXT NOT NULL,
    `file_paths` JSON,
    `language` VARCHAR(50),
    `branch` VARCHAR(200),
    `commit_sha` VARCHAR(40),
    `review_method` VARCHAR(20) NOT NULL DEFAULT 'script',
    `status` ENUM('pending','reviewing','completed','failed') DEFAULT 'pending',
    `summary` TEXT,
    `overall_score` FLOAT,
    `scores` JSON,
    `agent_conversation_id` VARCHAR(36),
    `created_by` VARCHAR(36),
    `reviewed_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 16. 审查问题
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_review_issues` (
    `id` VARCHAR(36) NOT NULL,
    `review_id` VARCHAR(36) NOT NULL,
    `severity` ENUM('critical','warning','suggestion') NOT NULL,
    `category` ENUM('security','style','logic','performance') NOT NULL,
    `file_path` VARCHAR(500),
    `line_start` INT,
    `line_end` INT,
    `title` VARCHAR(300) NOT NULL,
    `description` TEXT,
    `suggestion` TEXT,
    `code_snippet` TEXT,
    `fixed_snippet` TEXT,
    `status` ENUM('open','fixed','ignored') DEFAULT 'open',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_review` (`review_id`),
    FOREIGN KEY (`review_id`) REFERENCES `rd_reviews`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 17. 模型配置
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_model_configs` (
    `id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `api_key` TEXT,
    `base_url` VARCHAR(500),
    `model` VARCHAR(100) NOT NULL DEFAULT 'gpt-4o',
    `custom_model` VARCHAR(100) NOT NULL DEFAULT '',
    `temperature` FLOAT NOT NULL DEFAULT 0.7,
    `max_tokens` INT NOT NULL DEFAULT 4096,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 18. 构建
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_builds` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `repo_id` VARCHAR(36),
    `build_number` INT NOT NULL,
    `build_type` VARCHAR(20) NOT NULL DEFAULT 'push',
    `status` ENUM('pending','running','success','failed','cancelled') DEFAULT 'pending',
    `commit_hash` VARCHAR(40),
    `commit_message` VARCHAR(500),
    `branch` VARCHAR(200),
    `workflow_id` VARCHAR(100),
    `github_run_id` BIGINT,
    `started_at` DATETIME,
    `finished_at` DATETIME,
    `duration_seconds` INT,
    `created_by` VARCHAR(36),
    `error_summary` TEXT,
    `preview_url` VARCHAR(500),
    `artifacts` JSON,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    INDEX `idx_repo` (`repo_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`repo_id`) REFERENCES `rd_repos`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 19. 构建步骤
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_build_steps` (
    `id` VARCHAR(36) NOT NULL,
    `build_id` VARCHAR(36) NOT NULL,
    `step_name` VARCHAR(100) NOT NULL,
    `step_order` INT NOT NULL,
    `status` ENUM('pending','running','success','failed','skipped') DEFAULT 'pending',
    `command` VARCHAR(500),
    `duration_seconds` INT,
    `log` TEXT,
    PRIMARY KEY (`id`),
    INDEX `idx_build` (`build_id`),
    FOREIGN KEY (`build_id`) REFERENCES `rd_builds`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 20. 项目文件
-- ========================================
CREATE TABLE IF NOT EXISTS `rd_project_files` (
    `id` VARCHAR(36) NOT NULL,
    `project_id` VARCHAR(36) NOT NULL,
    `conversation_id` VARCHAR(36),
    `file_name` VARCHAR(500) NOT NULL,
    `file_path` VARCHAR(1000) NOT NULL,
    `content` TEXT,
    `file_type` VARCHAR(50),
    `size` INT DEFAULT 0,
    `version` INT DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_project` (`project_id`),
    FOREIGN KEY (`project_id`) REFERENCES `rd_projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
