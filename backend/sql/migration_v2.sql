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
ALTER TABLE `conversations` ADD COLUMN IF NOT EXISTS `workspace_id` VARCHAR(36) DEFAULT NULL AFTER `user_id`;

-- ========================================
-- 4. 灰度配置种子数据
-- ========================================

-- ---------- 智能研发 (rd) ----------
INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible) VALUES
-- UI 侧边栏
('ui.sidebar.projects', '侧边栏-项目管理', 'ui', 'rd', 1, 1),
('ui.sidebar.repos', '侧边栏-代码仓库', 'ui', 'rd', 1, 1),
('ui.sidebar.reviews', '侧边栏-代码审查', 'ui', 'rd', 1, 1),
('ui.sidebar.builds', '侧边栏-构建历史', 'ui', 'rd', 0, 0),
-- UI 聊天工具栏
('ui.chat.toolbar.project_init', '聊天工具栏-项目初始化', 'ui', 'rd', 1, 1),
('ui.chat.toolbar.code_review', '聊天工具栏-代码审查', 'ui', 'rd', 1, 1),
-- UI 欢迎页
('ui.workspace.welcome_rd', '工作空间首页-研发欢迎页', 'ui', 'rd', 1, 1),
-- 功能
('feature.project.create', '功能-创建项目', 'feature', 'rd', 1, 1),
('feature.repo.connect', '功能-连接外部仓库', 'feature', 'rd', 1, 1),
('feature.review.auto', '功能-自动代码审查', 'feature', 'rd', 1, 1),
('feature.cicd.status', '功能-CI/CD状态查询', 'feature', 'rd', 0, 0),
-- Agent 类别（已有功能 → 研发领域灰度）
('agent.cat_code', 'Agent类别-编程', 'agent', 'rd', 1, 1),
('agent.cat_doc', 'Agent类别-文档', 'agent', 'rd', 1, 1),
('agent.cat_test', 'Agent类别-测试', 'agent', 'rd', 1, 1),
('agent.cat_design', 'Agent类别-设计', 'agent', 'rd', 1, 1),
('agent.cat_data', 'Agent类别-数据分析', 'agent', 'rd', 1, 1),
-- Agent
('agent.architect', 'Agent-架构师', 'agent', 'rd', 1, 1),
('agent.developer', 'Agent-开发工程师', 'agent', 'rd', 1, 1),
('agent.tester', 'Agent-测试工程师', 'agent', 'rd', 1, 1),
('agent.data_analyst', 'Agent-数据分析师', 'agent', 'rd', 1, 1),
('agent.doc_writer_rd', 'Agent-技术文档助手', 'agent', 'rd', 1, 1),
-- 已有前端功能映射研发灰度
('ui.sidebar.agents', '侧边栏-Agent管理', 'ui', 'rd', 1, 1),
('ui.sidebar.tools', '侧边栏-工具集', 'ui', 'rd', 1, 1),
('ui.sidebar.favorites', '侧边栏-收藏', 'ui', 'rd', 1, 1),
-- 工具
('tool.code_executor', '工具-代码执行器', 'tool', 'rd', 1, 1),
('tool.dependency_analyzer', '工具-依赖分析器', 'tool', 'rd', 1, 1);

-- ---------- 智慧教育 (edu) ----------
INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible) VALUES
-- UI 侧边栏
('ui.sidebar.agents', '侧边栏-Agent管理', 'ui', 'edu', 1, 1),
('ui.sidebar.tools', '侧边栏-工具集', 'ui', 'edu', 1, 1),
('ui.sidebar.favorites', '侧边栏-收藏', 'ui', 'edu', 1, 1),
('ui.sidebar.courses', '侧边栏-课程管理', 'ui', 'edu', 1, 1),
('ui.sidebar.assignments', '侧边栏-作业系统', 'ui', 'edu', 1, 1),
('ui.sidebar.resources', '侧边栏-教学资源', 'ui', 'edu', 1, 1),
('ui.sidebar.grades', '侧边栏-成绩管理', 'ui', 'edu', 1, 1),
('ui.sidebar.students', '侧边栏-学生画像', 'ui', 'edu', 1, 1),
-- UI 聊天工具栏
('ui.chat.toolbar.courseware', '聊天工具栏-课件制作', 'ui', 'edu', 1, 1),
('ui.chat.toolbar.exercise', '聊天工具栏-习题生成', 'ui', 'edu', 1, 1),
('ui.chat.toolbar.analytics', '聊天工具栏-学情分析', 'ui', 'edu', 1, 1),
-- UI 欢迎页
('ui.workspace.welcome_edu', '工作空间首页-教育欢迎页', 'ui', 'edu', 1, 1),
-- 功能
('feature.course.create', '功能-创建课程', 'feature', 'edu', 1, 1),
('feature.assignment.publish', '功能-发布作业', 'feature', 'edu', 1, 1),
('feature.assignment.auto_grade', '功能-自动批改', 'feature', 'edu', 1, 1),
('feature.analytics.report', '功能-学情报告', 'feature', 'edu', 1, 1),
('feature.bridge.teaching_learning', '功能-教学学习数据桥', 'feature', 'edu', 0, 0),
-- Agent
('agent.course_designer', 'Agent-课程设计师', 'agent', 'edu', 1, 1),
('agent.courseware_maker', 'Agent-课件制作师', 'agent', 'edu', 1, 1),
('agent.quiz_generator', 'Agent-习题生成器', 'agent', 'edu', 1, 1),
('agent.learning_analyst', 'Agent-学情分析师', 'agent', 'edu', 1, 1),
('agent.study_planner', 'Agent-学习规划师', 'agent', 'edu', 1, 1),
('agent.practice_coach', 'Agent-练习教练', 'agent', 'edu', 1, 1),
-- 工具
('tool.ppt_generator', '工具-PPT生成器', 'tool', 'edu', 1, 1),
('tool.quiz_engine', '工具-题库引擎', 'tool', 'edu', 1, 1),
('tool.knowledge_mapper', '工具-知识点映射器', 'tool', 'edu', 1, 1);

-- ---------- 智慧办公 (office) ----------
INSERT INTO grayscale_config (config_key, config_name, config_type, domain, enabled, visible) VALUES
-- UI 侧边栏
('ui.sidebar.agents', '侧边栏-Agent管理', 'ui', 'office', 1, 1),
('ui.sidebar.tools', '侧边栏-工具集', 'ui', 'office', 1, 1),
('ui.sidebar.favorites', '侧边栏-收藏', 'ui', 'office', 1, 1),
('ui.sidebar.documents', '侧边栏-公文管理', 'ui', 'office', 1, 1),
('ui.sidebar.meetings', '侧边栏-会议管理', 'ui', 'office', 1, 1),
('ui.sidebar.approvals', '侧边栏-审批流程', 'ui', 'office', 1, 1),
('ui.sidebar.reports', '侧边栏-报表服务', 'ui', 'office', 1, 1),
('ui.sidebar.schedules', '侧边栏-日程管理', 'ui', 'office', 1, 1),
-- UI 聊天工具栏
('ui.chat.toolbar.doc_draft', '聊天工具栏-公文起草', 'ui', 'office', 1, 1),
('ui.chat.toolbar.meeting_mins', '聊天工具栏-会议纪要', 'ui', 'office', 1, 1),
('ui.chat.toolbar.report_gen', '聊天工具栏-报表生成', 'ui', 'office', 1, 1),
-- UI 欢迎页
('ui.workspace.welcome_office', '工作空间首页-办公欢迎页', 'ui', 'office', 1, 1),
-- 功能
('feature.document.create', '功能-起草公文', 'feature', 'office', 1, 1),
('feature.document.review', '功能-公文审核', 'feature', 'office', 1, 1),
('feature.meeting.transcribe', '功能-会议转写', 'feature', 'office', 1, 1),
('feature.approval.flow', '功能-审批流转', 'feature', 'office', 1, 1),
('feature.report.template', '功能-报表模板', 'feature', 'office', 1, 1),
-- Agent
('agent.doc_writer_office', 'Agent-公文撰写助手', 'agent', 'office', 1, 1),
('agent.meeting_assistant', 'Agent-会议助理', 'agent', 'office', 1, 1),
('agent.report_analyst', 'Agent-报表分析助手', 'agent', 'office', 1, 1),
('agent.email_drafter', 'Agent-邮件起草助手', 'agent', 'office', 1, 1),
('agent.schedule_manager', 'Agent-日程管理助手', 'agent', 'office', 1, 1),
-- 工具
('tool.doc_template_engine', '工具-公文模板引擎', 'tool', 'office', 1, 1),
('tool.format_checker', '工具-格式检查器', 'tool', 'office', 1, 1),
('tool.transcript_parser', '工具-录音转写解析器', 'tool', 'office', 1, 1);

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
