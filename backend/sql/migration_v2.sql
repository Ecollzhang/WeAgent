-- ========================================
-- WeAgent Domain v2 — 领域隔离架构迁移脚本
-- 执行方式：mysql -u root -p weagent_shared < migration_v2.sql
-- 前提：weagent_shared 数据库已存在
-- ========================================

-- ========================================
-- 1. 工作空间表
-- ========================================
CREATE TABLE IF NOT EXISTS `workspaces` (
    `id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `domain` VARCHAR(50) NOT NULL COMMENT 'rd / edu / office',
    `sub_role` VARCHAR(20) DEFAULT '' COMMENT 'edu 领域区分: teacher / student',
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `icon` VARCHAR(50) DEFAULT 'default',
    `sort_order` INT DEFAULT 0,
    `status` ENUM('active', 'archived') DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_user` (`user_id`),
    INDEX `idx_domain` (`domain`),
    UNIQUE KEY `uk_user_domain_name` (`user_id`, `domain`, `name`),
    CONSTRAINT `workspaces_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 2. 灰度配置表
-- ========================================
CREATE TABLE IF NOT EXISTS `grayscale_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `config_key` VARCHAR(100) NOT NULL COMMENT '配置键，如 ui.sidebar.courses',
    `config_name` VARCHAR(200) NOT NULL COMMENT '中文名称',
    `config_type` ENUM('ui', 'feature', 'agent', 'tool') NOT NULL COMMENT '配置类型',
    `domain` VARCHAR(50) NOT NULL COMMENT 'rd / edu / office',
    `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '功能是否启用',
    `visible` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'UI是否可见',
    `domains` JSON NULL COMMENT 'common 域跨领域生效范围, e.g. ["rd","edu","office"]',
    `description` TEXT DEFAULT NULL COMMENT '配置说明',
    `metadata` JSON DEFAULT NULL COMMENT '扩展元数据',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_key_domain` (`config_key`, `domain`),
    INDEX `idx_domain` (`domain`),
    INDEX `idx_type` (`config_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 3. 扩展已有表字段（兼容存量数据库）
-- ========================================
-- workspaces 子角色
ALTER TABLE `workspaces` ADD COLUMN IF NOT EXISTS `sub_role` VARCHAR(20) DEFAULT '' COMMENT 'edu 领域区分: teacher / student' AFTER `domain`;
-- users 角色
ALTER TABLE `users` ADD COLUMN IF NOT EXISTS `role` VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT 'admin / user';
-- conversations 关联工作空间
ALTER TABLE `conversations` ADD COLUMN IF NOT EXISTS `workspace_id` VARCHAR(36) DEFAULT NULL;
-- conversations 知识库范围
ALTER TABLE `conversations` ADD COLUMN IF NOT EXISTS `kb_domain` VARCHAR(20) NOT NULL DEFAULT '';
ALTER TABLE `conversations` ADD COLUMN IF NOT EXISTS `kb_document_ids` JSON DEFAULT NULL;
-- conversations 领域服务 & 项目关联
ALTER TABLE `conversations` ADD COLUMN IF NOT EXISTS `services` JSON DEFAULT NULL COMMENT '启用的领域服务列表';
ALTER TABLE `conversations` ADD COLUMN IF NOT EXISTS `project_id` VARCHAR(36) DEFAULT NULL COMMENT '关联的RD项目ID';

-- ========================================
-- 4. 灰度配置种子数据
--   - domain='common' 的配置通过 domains JSON 字段控制跨领域生效范围
--   - domain='rd'/'edu'/'office' 的配置仅在该领域生效
--   - 侧边栏公共项 (agents/tools/favorites/knowledge) 已统一为 common+domains 模式
--   - 与 backend/app/__init__.py _seed_grayscale_configs() 保持一致
-- ========================================

-- 4a. grayscale_config 表新增 domains 字段（兼容老表）
ALTER TABLE `grayscale_config` ADD COLUMN IF NOT EXISTS `domains` JSON NULL COMMENT 'common 域跨领域生效范围, e.g. ["rd","edu","office"]' AFTER `visible`;

-- ---------- 公共 (common)：跨领域共享的 UI 配置 ----------
INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible, domains) VALUES
-- 聊天功能
('ui.chat.workspace', '聊天-工作目录', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.services', '聊天-预览服务', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.attachments', '聊天-上传文件', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
-- 聊天标签栏
('ui.chat.tabs.agent_config', '聊天标签-Agent配置', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.tabs.artifacts', '聊天标签-产物', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.tabs.logs', '聊天标签-日志', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.tabs.workflow', '聊天标签-工作流图', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.tabs.knowledge_base', '聊天标签-知识库', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
-- 侧边栏公共项（原 per-domain 重复，现统一为 common）
('ui.sidebar.agents', '侧边栏-我的Agent', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.sidebar.tools', '侧边栏-工具集', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.sidebar.favorites', '侧边栏-我的收藏', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.sidebar.knowledge', '侧边栏-知识库', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
-- 聊天领域卡片
('ui.chat.card.requirement', '聊天-需求卡片', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.card.bug', '聊天-缺陷卡片', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.card.iteration', '聊天-迭代卡片', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.card.project', '聊天-项目卡片', 'ui', 'common', 1, 1, '["rd","edu","office"]'),
('ui.chat.card.office', '聊天-办公卡片', 'ui', 'common', 1, 1, '["office"]')
ON DUPLICATE KEY UPDATE config_name=VALUES(config_name), domains=VALUES(domains);

-- ---------- 智能研发 (rd)：领域独有配置 ----------
INSERT IGNORE INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible) VALUES
-- UI 侧边栏
('ui.sidebar.projects', '侧边栏-项目管理', 'ui', 'rd', 1, 1),
('ui.sidebar.repos', '侧边栏-代码仓库', 'ui', 'rd', 1, 1),
('ui.sidebar.reviews', '侧边栏-代码审查', 'ui', 'rd', 1, 1),
('ui.sidebar.builds', '侧边栏-构建管理', 'ui', 'rd', 1, 1);

-- ---------- 智慧教育 (edu)：领域独有配置 ----------
INSERT IGNORE INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible) VALUES
-- UI 侧边栏
('ui.sidebar.courses', '侧边栏-课程管理', 'ui', 'edu', 1, 1),
('ui.sidebar.assignments', '侧边栏-作业系统', 'ui', 'edu', 1, 1),
('ui.sidebar.resources', '侧边栏-教学资源', 'ui', 'edu', 1, 1),
('ui.sidebar.grades', '侧边栏-成绩管理', 'ui', 'edu', 1, 1),
('ui.sidebar.students', '侧边栏-学生画像', 'ui', 'edu', 1, 1);

-- ---------- 智慧办公 (office)：领域独有配置 ----------
INSERT IGNORE INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible) VALUES
-- UI 侧边栏
('ui.sidebar.organization', '侧边栏-组织协同', 'ui', 'office', 1, 1),
('ui.sidebar.documents', '侧边栏-公文管理', 'ui', 'office', 1, 1),
('ui.sidebar.meetings', '侧边栏-会议管理', 'ui', 'office', 1, 1),
('ui.sidebar.approvals', '侧边栏-审批流程', 'ui', 'office', 1, 1),
('ui.sidebar.reports', '侧边栏-报表服务', 'ui', 'office', 1, 1),
('ui.sidebar.schedules', '侧边栏-日程管理', 'ui', 'office', 1, 1);

-- ========================================
-- 5. 已有数据迁移：老用户 → 默认研发空间
-- ========================================

-- 5a. 为每个已有用户创建"我的研发空间"
INSERT INTO workspaces (id, user_id, domain, name, description, icon, status, created_at, updated_at)
SELECT
    UUID() as id,
    u.id as user_id,
    'rd' as domain,
    '我的研发空间' as name,
    '系统自动创建的默认研发工作空间，包含您已有的所有会话和Agent' as description,
    'default' as icon,
    'active' as status,
    NOW() as created_at,
    NOW() as updated_at
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM workspaces w
    WHERE w.user_id COLLATE utf8mb4_unicode_ci = u.id COLLATE utf8mb4_unicode_ci
      AND w.domain = 'rd'
      AND w.name = '我的研发空间'
);

-- 5b. 将已有会话关联到对应用户的研发空间
UPDATE conversations c
SET workspace_id = (
    SELECT w.id FROM workspaces w
    WHERE w.user_id COLLATE utf8mb4_unicode_ci = c.owner_id COLLATE utf8mb4_unicode_ci
      AND w.domain = 'rd'
    LIMIT 1
)
WHERE c.workspace_id IS NULL;
