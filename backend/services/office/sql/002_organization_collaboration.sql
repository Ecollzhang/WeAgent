-- 智慧办公组织协作重构：部门、小组、成员与站内通知。
-- 适用于现有 weagent_office 库；已有会议/公文数据不删除。
-- 旧库需补会议链接字段时执行：ALTER TABLE office_meetings ADD COLUMN meeting_link VARCHAR(1000) DEFAULT '';
CREATE TABLE IF NOT EXISTS office_departments (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, name VARCHAR(100) NOT NULL, head_user_id VARCHAR(36) NOT NULL,
  UNIQUE KEY uq_office_department_workspace (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_groups (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, name VARCHAR(100) NOT NULL, leader_user_id VARCHAR(36),
  INDEX ix_office_groups_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_members (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, user_id VARCHAR(36) NOT NULL, display_name VARCHAR(100) NOT NULL,
  role ENUM('member','team_lead','department_head') NOT NULL DEFAULT 'member',
  group_id VARCHAR(36), manager_user_id VARCHAR(36), active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE KEY uq_office_member_workspace_user (workspace_id,user_id),
  INDEX ix_office_members_workspace_id (workspace_id), INDEX ix_office_members_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_notifications (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, recipient_id VARCHAR(36) NOT NULL, notification_type VARCHAR(30) NOT NULL,
  title VARCHAR(200) NOT NULL, content TEXT, source_type VARCHAR(30), source_id VARCHAR(36),
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  INDEX ix_office_notifications_recipient (workspace_id,recipient_id,is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
