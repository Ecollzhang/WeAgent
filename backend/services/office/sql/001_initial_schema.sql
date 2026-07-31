-- 智慧办公领域初始结构。可在空的 weagent_office 库重复执行。
-- 正常启动服务也会由 SQLAlchemy 建表；本文件用于受控迁移和环境部署记录。
CREATE TABLE IF NOT EXISTS office_meetings (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, organizer_id VARCHAR(36) NOT NULL, title VARCHAR(200) NOT NULL,
  agenda TEXT, participants JSON, location VARCHAR(200), start_time DATETIME, end_time DATETIME,
  transcript TEXT, minutes TEXT, resolutions JSON,
  status ENUM('scheduled','ongoing','completed','cancelled') NOT NULL DEFAULT 'scheduled',
  INDEX ix_office_meetings_workspace_id (workspace_id), INDEX ix_office_meetings_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_action_items (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  meeting_id VARCHAR(36) NOT NULL, workspace_id VARCHAR(36) NOT NULL, creator_id VARCHAR(36) NOT NULL,
  assignee_id VARCHAR(36), assignee_name VARCHAR(100), title VARCHAR(200) NOT NULL, description TEXT,
  due_date DATETIME, priority ENUM('low','medium','high') DEFAULT 'medium',
  status ENUM('pending','in_progress','done','cancelled') NOT NULL DEFAULT 'pending', schedule_id VARCHAR(36),
  CONSTRAINT fk_office_action_meeting FOREIGN KEY (meeting_id) REFERENCES office_meetings(id) ON DELETE CASCADE,
  INDEX ix_office_actions_workspace_id (workspace_id), INDEX ix_office_actions_due_date (due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_schedules (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, user_id VARCHAR(36) NOT NULL, title VARCHAR(200) NOT NULL,
  description TEXT, event_type ENUM('meeting','task','reminder','other') NOT NULL DEFAULT 'task',
  start_time DATETIME NOT NULL, end_time DATETIME NOT NULL,
  priority ENUM('low','medium','high') DEFAULT 'medium',
  status ENUM('pending','done','cancelled') NOT NULL DEFAULT 'pending', meeting_id VARCHAR(36), action_item_id VARCHAR(36),
  INDEX ix_office_schedules_workspace_id (workspace_id), INDEX ix_office_schedules_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_documents (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, user_id VARCHAR(36) NOT NULL, meeting_id VARCHAR(36), title VARCHAR(200) NOT NULL,
  document_type ENUM('notice','report','request','letter','minutes','other') NOT NULL, content TEXT,
  template_id VARCHAR(36), status ENUM('draft','reviewing','approved','published','archived') NOT NULL DEFAULT 'draft',
  reviewer_id VARCHAR(36), review_comment TEXT, published_at DATETIME,
  INDEX ix_office_documents_workspace_id (workspace_id), INDEX ix_office_documents_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_doc_templates (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36), creator_id VARCHAR(36), name VARCHAR(200) NOT NULL,
  document_type ENUM('notice','report','request','letter','minutes','other') NOT NULL,
  content TEXT NOT NULL, format_spec TEXT, is_system BOOLEAN NOT NULL DEFAULT FALSE,
  INDEX ix_office_templates_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS office_approvals (
  id VARCHAR(36) PRIMARY KEY, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  workspace_id VARCHAR(36) NOT NULL, document_id VARCHAR(36), title VARCHAR(200) NOT NULL,
  approval_type VARCHAR(50), initiator_id VARCHAR(36) NOT NULL, current_step INT NOT NULL DEFAULT 1,
  steps JSON, history JSON, status ENUM('pending','approved','rejected','cancelled') NOT NULL DEFAULT 'pending',
  INDEX ix_office_approvals_workspace_id (workspace_id), INDEX ix_office_approvals_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
