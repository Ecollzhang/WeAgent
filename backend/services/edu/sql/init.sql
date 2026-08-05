-- ========================================
-- WeAgent Education Service — 数据库初始化脚本
-- 数据库: weagent_edu
-- 方式: mysql -u root -p < init.sql
-- ========================================

CREATE DATABASE IF NOT EXISTS `weagent_edu`
  DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `weagent_edu`;

-- ========================================
-- 1. 课程
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_courses` (
    `id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `subject_code` VARCHAR(50) NOT NULL,
    `grade_band` VARCHAR(50) NOT NULL,
    `description` TEXT NOT NULL,
    `owner_user_id` VARCHAR(100) NOT NULL,
    `subject_pack_version_id` VARCHAR(100),
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_courses_owner` (`owner_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 2. 课程成员
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_course_memberships` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(100) NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `invited_by` VARCHAR(100),
    `joined_at` DATETIME,
    `removed_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_course_user` (`course_id`, `user_id`),
    INDEX `idx_edu_course_memberships_user` (`user_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 3. 课程成员档案（课程内显示名）
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_course_member_profiles` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(100) NOT NULL,
    `display_name` VARCHAR(80) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_course_member_profile` (`course_id`, `user_id`),
    INDEX `idx_edu_course_member_profiles_user` (`user_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 4. 课程邀请码
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_course_invitations` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL,
    `created_by` VARCHAR(100) NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `max_uses` INT NOT NULL DEFAULT 30,
    `used_count` INT NOT NULL DEFAULT 0,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_edu_course_invitations_token` (`token_hash`),
    INDEX `idx_edu_course_invitations_course` (`course_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 5. 课程单元
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_course_units` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `position` INT NOT NULL DEFAULT 0,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_course_units_course` (`course_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 6. 课时
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_lessons` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `unit_id` VARCHAR(36),
    `title` VARCHAR(200) NOT NULL,
    `learning_domain` VARCHAR(20) NOT NULL,
    `theme_code` VARCHAR(100) NOT NULL,
    `text_genre_code` VARCHAR(100) NOT NULL,
    `lesson_type_code` VARCHAR(100) NOT NULL,
    `duration_minutes` INT NOT NULL,
    `position` INT NOT NULL DEFAULT 0,
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `current_published_version_id` VARCHAR(36),
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_lessons_course` (`course_id`),
    INDEX `idx_edu_lessons_unit` (`unit_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`unit_id`) REFERENCES `edu_course_units`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 7. 课时活动
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_lesson_activities` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36) NOT NULL,
    `activity_type` VARCHAR(30) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `position` INT NOT NULL DEFAULT 0,
    `content_version_id` VARCHAR(36),
    `student_payload` JSON NOT NULL,
    `teacher_payload` JSON NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_lesson_activities_course` (`course_id`),
    INDEX `idx_edu_lesson_activities_lesson` (`lesson_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 8. 资产（二进制文件）
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assets` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36),
    `owner_user_id` VARCHAR(100) NOT NULL,
    `purpose` VARCHAR(50) NOT NULL DEFAULT 'course_material',
    `title` VARCHAR(200) NOT NULL,
    `original_filename` VARCHAR(255) NOT NULL,
    `media_type` VARCHAR(120) NOT NULL,
    `byte_size` INT NOT NULL,
    `sha256` VARCHAR(64) NOT NULL,
    `visibility_scope` VARCHAR(30) NOT NULL DEFAULT 'course_teacher',
    `storage_backend` VARCHAR(30) NOT NULL DEFAULT 'database',
    `blob_bytes` LONGBLOB NOT NULL,
    `source_agent_run_id` VARCHAR(100),
    `source_sandbox_path` VARCHAR(1000),
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `archived_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_assets_course` (`course_id`),
    INDEX `idx_edu_assets_lesson` (`lesson_id`),
    INDEX `idx_edu_assets_owner` (`owner_user_id`),
    INDEX `idx_edu_assets_sha256` (`sha256`),
    INDEX `idx_edu_assets_visibility` (`visibility_scope`),
    INDEX `idx_edu_assets_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 9. 教育内容
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_contents` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36),
    `kind` VARCHAR(40) NOT NULL,
    `owner_user_id` VARCHAR(100) NOT NULL,
    `visibility_scope` VARCHAR(30) NOT NULL DEFAULT 'course_teacher',
    `current_version_id` VARCHAR(36),
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_contents_course` (`course_id`),
    INDEX `idx_edu_contents_lesson` (`lesson_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 10. 教育内容版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_content_versions` (
    `id` VARCHAR(36) NOT NULL,
    `content_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `schema_name` VARCHAR(100) NOT NULL,
    `schema_version` VARCHAR(30) NOT NULL DEFAULT '1.0',
    `source_json` JSON NOT NULL,
    `rendered_html` TEXT,
    `parent_version_id` VARCHAR(36),
    `change_summary` VARCHAR(500) NOT NULL DEFAULT '',
    `created_by_user_id` VARCHAR(100) NOT NULL,
    `source_agent_run_id` VARCHAR(100),
    `checksum` VARCHAR(64) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_content_version` (`content_id`, `version_number`),
    INDEX `idx_edu_content_versions_content` (`content_id`),
    FOREIGN KEY (`content_id`) REFERENCES `edu_contents`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 11. 教学材料
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_materials` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36) NOT NULL,
    `owner_user_id` VARCHAR(100) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `original_filename` VARCHAR(255) NOT NULL,
    `extension` VARCHAR(20) NOT NULL,
    `mime_type` VARCHAR(120) NOT NULL,
    `storage_path` VARCHAR(1000),
    `asset_id` VARCHAR(36),
    `file_size` INT NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_materials_course` (`course_id`),
    INDEX `idx_edu_materials_lesson` (`lesson_id`),
    INDEX `idx_edu_materials_asset` (`asset_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`asset_id`) REFERENCES `edu_assets`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 12. 已发布课时版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_published_lesson_versions` (
    `id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `lesson_plan_version_id` VARCHAR(36),
    `student_release_manifest` JSON NOT NULL,
    `teacher_evaluation_manifest` JSON NOT NULL,
    `idempotency_key` VARCHAR(100) NOT NULL,
    `published_by` VARCHAR(100) NOT NULL,
    `published_at` DATETIME NOT NULL DEFAULT (now()),
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_lesson_publish_version` (`lesson_id`, `version_number`),
    UNIQUE KEY `uq_edu_lesson_publish_key` (`lesson_id`, `idempotency_key`),
    INDEX `idx_edu_published_lesson_versions_lesson` (`lesson_id`),
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 13. 作业
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assignments` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `kind` VARCHAR(20) NOT NULL,
    `instruction_json` JSON NOT NULL,
    `evaluation_json` JSON NOT NULL,
    `source_asset_ids` JSON NOT NULL,
    `max_score` FLOAT NOT NULL DEFAULT 100.0,
    `max_attempts` INT NOT NULL DEFAULT 1,
    `allow_revision_after_feedback` TINYINT(1) NOT NULL DEFAULT 1,
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `published_by` VARCHAR(100),
    `published_at` DATETIME,
    `current_version_id` VARCHAR(36),
    `published_version_id` VARCHAR(36),
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_assignments_course` (`course_id`),
    INDEX `idx_edu_assignments_lesson` (`lesson_id`),
    INDEX `idx_edu_assignments_current_version` (`current_version_id`),
    INDEX `idx_edu_assignments_published_version` (`published_version_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 14. 作业内容版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assignment_content_versions` (
    `id` VARCHAR(36) NOT NULL,
    `assignment_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `kind` VARCHAR(20) NOT NULL,
    `instruction_json` JSON NOT NULL,
    `evaluation_json` JSON NOT NULL,
    `source_asset_ids` JSON NOT NULL,
    `max_score` FLOAT NOT NULL DEFAULT 100.0,
    `max_attempts` INT NOT NULL DEFAULT 1,
    `allow_revision_after_feedback` TINYINT(1) NOT NULL DEFAULT 1,
    `created_by` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `published_at` DATETIME,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_assignment_content_version` (`assignment_id`, `version_number`),
    INDEX `idx_edu_assignment_content_versions_assignment` (`assignment_id`),
    FOREIGN KEY (`assignment_id`) REFERENCES `edu_assignments`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 15. 作业导入任务
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assignment_import_jobs` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36) NOT NULL,
    `source_asset_id` VARCHAR(36) NOT NULL,
    `requested_by` VARCHAR(100) NOT NULL,
    `mode` VARCHAR(20) NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'uploaded',
    `extractor_code` VARCHAR(50),
    `extracted_text` TEXT,
    `draft_json` JSON NOT NULL,
    `warnings` JSON NOT NULL,
    `error_summary` TEXT,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_assignment_import_jobs_course` (`course_id`),
    INDEX `idx_edu_assignment_import_jobs_lesson` (`lesson_id`),
    INDEX `idx_edu_assignment_import_jobs_asset` (`source_asset_id`),
    INDEX `idx_edu_assignment_import_jobs_user` (`requested_by`),
    INDEX `idx_edu_assignment_import_jobs_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`source_asset_id`) REFERENCES `edu_assets`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 16. 学生提交
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_submissions` (
    `id` VARCHAR(36) NOT NULL,
    `assignment_id` VARCHAR(36) NOT NULL,
    `student_user_id` VARCHAR(100) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `current_version_id` VARCHAR(36),
    `draft_answer_json` JSON,
    `draft_artifact_ids` JSON,
    `draft_updated_at` DATETIME,
    `attempt_count` INT NOT NULL DEFAULT 0,
    `submitted_at` DATETIME,
    `final_score` FLOAT,
    `graded_by` VARCHAR(100),
    `graded_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_assignment_student` (`assignment_id`, `student_user_id`),
    INDEX `idx_edu_submissions_assignment` (`assignment_id`),
    INDEX `idx_edu_submissions_student` (`student_user_id`),
    FOREIGN KEY (`assignment_id`) REFERENCES `edu_assignments`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 17. 提交版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_submission_versions` (
    `id` VARCHAR(36) NOT NULL,
    `submission_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `answer_json` JSON NOT NULL,
    `artifact_ids` JSON NOT NULL,
    `submitted_at` DATETIME NOT NULL DEFAULT (now()),
    `source_version_id` VARCHAR(36),
    `checksum` VARCHAR(64) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_submission_version` (`submission_id`, `version_number`),
    INDEX `idx_edu_submission_versions_submission` (`submission_id`),
    FOREIGN KEY (`submission_id`) REFERENCES `edu_submissions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 18. 审阅草稿
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_review_drafts` (
    `id` VARCHAR(36) NOT NULL,
    `submission_id` VARCHAR(36) NOT NULL,
    `submission_version_id` VARCHAR(36) NOT NULL,
    `rubric_scores` JSON NOT NULL,
    `feedback_json` JSON NOT NULL,
    `annotations` JSON NOT NULL,
    `score` FLOAT,
    `revision_requested` TINYINT(1) NOT NULL DEFAULT 0,
    `saved_by` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_review_draft_version_reviewer` (`submission_version_id`, `saved_by`),
    INDEX `idx_edu_review_drafts_submission` (`submission_id`),
    INDEX `idx_edu_review_drafts_version` (`submission_version_id`),
    INDEX `idx_edu_review_drafts_saved_by` (`saved_by`),
    FOREIGN KEY (`submission_id`) REFERENCES `edu_submissions`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`submission_version_id`) REFERENCES `edu_submission_versions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 19. 提交审阅分析
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_submission_review_analyses` (
    `id` VARCHAR(36) NOT NULL,
    `submission_id` VARCHAR(36) NOT NULL,
    `submission_version_id` VARCHAR(36) NOT NULL,
    `evaluation_checksum` VARCHAR(64) NOT NULL,
    `prompt_version` VARCHAR(30) NOT NULL,
    `agent_run_id` VARCHAR(36),
    `requested_by` VARCHAR(100) NOT NULL,
    `analysis_json` JSON NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'ready',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_submission_review_analysis_cache` (`submission_version_id`, `evaluation_checksum`, `prompt_version`),
    INDEX `idx_edu_submission_review_analyses_submission` (`submission_id`),
    INDEX `idx_edu_submission_review_analyses_version` (`submission_version_id`),
    INDEX `idx_edu_submission_review_analyses_checksum` (`evaluation_checksum`),
    INDEX `idx_edu_submission_review_analyses_agent` (`agent_run_id`),
    INDEX `idx_edu_submission_review_analyses_user` (`requested_by`),
    INDEX `idx_edu_submission_review_analyses_status` (`status`),
    FOREIGN KEY (`submission_id`) REFERENCES `edu_submissions`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`submission_version_id`) REFERENCES `edu_submission_versions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 20. 反馈
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_feedback` (
    `id` VARCHAR(36) NOT NULL,
    `submission_version_id` VARCHAR(36) NOT NULL,
    `feedback_json` JSON NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'released',
    `version_number` INT NOT NULL DEFAULT 1,
    `rubric_scores` JSON NOT NULL,
    `annotations` JSON NOT NULL,
    `revision_requested` TINYINT(1) NOT NULL DEFAULT 0,
    `score` FLOAT,
    `released_by` VARCHAR(100) NOT NULL,
    `released_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_edu_feedback_version` (`submission_version_id`),
    FOREIGN KEY (`submission_version_id`) REFERENCES `edu_submission_versions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 21. 学习事件
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_learning_events` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `actor_user_id` VARCHAR(100) NOT NULL,
    `event_type` VARCHAR(50) NOT NULL,
    `object_type` VARCHAR(50) NOT NULL,
    `object_id` VARCHAR(36) NOT NULL,
    `payload` JSON NOT NULL,
    `occurred_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_edu_learning_events_course` (`course_id`),
    INDEX `idx_edu_learning_events_actor` (`actor_user_id`),
    INDEX `idx_edu_learning_events_type` (`event_type`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 22. 测评题目
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assessment_items` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36),
    `title` VARCHAR(200) NOT NULL,
    `owner_user_id` VARCHAR(100) NOT NULL,
    `source_type` VARCHAR(30) NOT NULL DEFAULT 'teacher',
    `source_agent_run_id` VARCHAR(100),
    `current_version_id` VARCHAR(36),
    `published_version_id` VARCHAR(36),
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `published_by` VARCHAR(100),
    `published_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_assessment_items_course` (`course_id`),
    INDEX `idx_edu_assessment_items_lesson` (`lesson_id`),
    INDEX `idx_edu_assessment_items_owner` (`owner_user_id`),
    INDEX `idx_edu_assessment_items_agent_run` (`source_agent_run_id`),
    INDEX `idx_edu_assessment_items_published_version` (`published_version_id`),
    INDEX `idx_edu_assessment_items_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 23. 测评题目版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assessment_item_versions` (
    `id` VARCHAR(36) NOT NULL,
    `item_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `question_type` VARCHAR(30) NOT NULL,
    `prompt` TEXT NOT NULL,
    `options` JSON NOT NULL,
    `difficulty` VARCHAR(20) NOT NULL,
    `score` FLOAT NOT NULL,
    `knowledge_points` JSON NOT NULL,
    `grade_band` VARCHAR(50),
    `source_context` JSON NOT NULL,
    `stimulus_version_id` VARCHAR(36),
    `stimulus_order` INT,
    `checksum` VARCHAR(64) NOT NULL,
    `created_by_user_id` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_assessment_item_version` (`item_id`, `version_number`),
    INDEX `idx_edu_assessment_item_versions_item` (`item_id`),
    INDEX `idx_edu_assessment_item_versions_stimulus` (`stimulus_version_id`),
    FOREIGN KEY (`item_id`) REFERENCES `edu_assessment_items`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 24. 测评答案版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assessment_answer_versions` (
    `id` VARCHAR(36) NOT NULL,
    `item_version_id` VARCHAR(36) NOT NULL,
    `correct_answer` JSON NOT NULL,
    `explanation` TEXT NOT NULL,
    `rubric` JSON NOT NULL,
    `created_by_user_id` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_assessment_answer_item_version` (`item_version_id`),
    FOREIGN KEY (`item_version_id`) REFERENCES `edu_assessment_item_versions`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 25. 试卷
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assessment_papers` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `purpose` VARCHAR(30) NOT NULL DEFAULT 'practice',
    `owner_user_id` VARCHAR(100) NOT NULL,
    `generated_for_user_id` VARCHAR(100),
    `visibility_scope` VARCHAR(30) NOT NULL DEFAULT 'course_published',
    `current_version_id` VARCHAR(36),
    `published_version_id` VARCHAR(36),
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `published_by` VARCHAR(100),
    `published_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_assessment_papers_course` (`course_id`),
    INDEX `idx_edu_assessment_papers_owner` (`owner_user_id`),
    INDEX `idx_edu_assessment_papers_generated_for` (`generated_for_user_id`),
    INDEX `idx_edu_assessment_papers_visibility` (`visibility_scope`),
    INDEX `idx_edu_assessment_papers_published_version` (`published_version_id`),
    INDEX `idx_edu_assessment_papers_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 26. 试卷版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assessment_paper_versions` (
    `id` VARCHAR(36) NOT NULL,
    `paper_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `item_version_ids` JSON NOT NULL,
    `sections` JSON NOT NULL,
    `total_score` FLOAT NOT NULL,
    `duration_minutes` INT NOT NULL,
    `blueprint` JSON NOT NULL,
    `checksum` VARCHAR(64) NOT NULL,
    `created_by_user_id` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_assessment_paper_version` (`paper_id`, `version_number`),
    INDEX `idx_edu_assessment_paper_versions_paper` (`paper_id`),
    FOREIGN KEY (`paper_id`) REFERENCES `edu_assessment_papers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 27. 测评阅读材料
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assessment_stimuli` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36),
    `title` VARCHAR(240) NOT NULL,
    `stimulus_type` VARCHAR(30) NOT NULL DEFAULT 'reading_passage',
    `owner_user_id` VARCHAR(100) NOT NULL,
    `current_version_id` VARCHAR(36),
    `published_version_id` VARCHAR(36),
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft',
    `published_by` VARCHAR(100),
    `published_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_assessment_stimuli_course` (`course_id`),
    INDEX `idx_edu_assessment_stimuli_lesson` (`lesson_id`),
    INDEX `idx_edu_assessment_stimuli_owner` (`owner_user_id`),
    INDEX `idx_edu_assessment_stimuli_published_version` (`published_version_id`),
    INDEX `idx_edu_assessment_stimuli_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 28. 测评阅读材料版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_assessment_stimulus_versions` (
    `id` VARCHAR(36) NOT NULL,
    `stimulus_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `content_json` JSON NOT NULL,
    `source_refs` JSON NOT NULL,
    `language` VARCHAR(20),
    `word_or_character_count` INT NOT NULL DEFAULT 0,
    `checksum` VARCHAR(64) NOT NULL,
    `created_by_user_id` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_assessment_stimulus_version` (`stimulus_id`, `version_number`),
    INDEX `idx_edu_assessment_stimulus_versions_stimulus` (`stimulus_id`),
    FOREIGN KEY (`stimulus_id`) REFERENCES `edu_assessment_stimuli`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 29. 知识资源
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_knowledge_resources` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `asset_id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `resource_type` VARCHAR(40) NOT NULL DEFAULT 'reference',
    `visibility_scope` VARCHAR(30) NOT NULL DEFAULT 'course_teacher',
    `ingestion_status` VARCHAR(20) NOT NULL DEFAULT 'pending',
    `ingestion_error` VARCHAR(500),
    `rag_scope` VARCHAR(200) NOT NULL,
    `metadata_json` JSON NOT NULL,
    `owner_user_id` VARCHAR(100) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_knowledge_resources_course` (`course_id`),
    INDEX `idx_edu_knowledge_resources_asset` (`asset_id`),
    INDEX `idx_edu_knowledge_resources_visibility` (`visibility_scope`),
    INDEX `idx_edu_knowledge_resources_ingestion` (`ingestion_status`),
    INDEX `idx_edu_knowledge_resources_owner` (`owner_user_id`),
    INDEX `idx_edu_knowledge_resources_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`asset_id`) REFERENCES `edu_assets`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 30. 模拟考试尝试
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_mock_exam_attempts` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `paper_version_id` VARCHAR(36) NOT NULL,
    `student_user_id` VARCHAR(100) NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'in_progress',
    `answers_json` JSON NOT NULL,
    `evidence_json` JSON NOT NULL,
    `score` FLOAT,
    `max_score` FLOAT,
    `accuracy` FLOAT,
    `started_at` DATETIME NOT NULL DEFAULT (now()),
    `submitted_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_mock_exam_attempts_course` (`course_id`),
    INDEX `idx_edu_mock_exam_attempts_paper_version` (`paper_version_id`),
    INDEX `idx_edu_mock_exam_attempts_student` (`student_user_id`),
    INDEX `idx_edu_mock_exam_attempts_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`paper_version_id`) REFERENCES `edu_assessment_paper_versions`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 31. 弱点分析快照
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_weakness_snapshots` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `student_user_id` VARCHAR(100) NOT NULL,
    `data_state` VARCHAR(20) NOT NULL,
    `evidence` JSON NOT NULL,
    `weaknesses` JSON NOT NULL,
    `recommendations` JSON NOT NULL,
    `source_fingerprint` VARCHAR(64) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_edu_weakness_snapshots_course` (`course_id`),
    INDEX `idx_edu_weakness_snapshots_student` (`student_user_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 32. 课程思维导图
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_course_mind_maps` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `owner_user_id` VARCHAR(100) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `scope_type` VARCHAR(20) NOT NULL DEFAULT 'course',
    `lesson_ids` JSON NOT NULL,
    `current_version_id` VARCHAR(36),
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_course_mind_maps_course` (`course_id`),
    INDEX `idx_edu_course_mind_maps_owner` (`owner_user_id`),
    INDEX `idx_edu_course_mind_maps_scope` (`scope_type`),
    INDEX `idx_edu_course_mind_maps_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 33. 思维导图版本
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_course_mind_map_versions` (
    `id` VARCHAR(36) NOT NULL,
    `mind_map_id` VARCHAR(36) NOT NULL,
    `version_number` INT NOT NULL,
    `tree_json` JSON NOT NULL,
    `source_refs` JSON NOT NULL,
    `change_summary` VARCHAR(500) NOT NULL DEFAULT '',
    `checksum` VARCHAR(64) NOT NULL,
    `created_by_user_id` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_course_mind_map_version` (`mind_map_id`, `version_number`),
    INDEX `idx_edu_course_mind_map_versions_map` (`mind_map_id`),
    FOREIGN KEY (`mind_map_id`) REFERENCES `edu_course_mind_maps`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 34. 学生画像快照
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_student_insight_snapshots` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `student_user_id` VARCHAR(100) NOT NULL,
    `data_state` VARCHAR(20) NOT NULL,
    `summary_json` JSON NOT NULL,
    `evidence_json` JSON NOT NULL,
    `weaknesses_json` JSON NOT NULL,
    `recommendations_json` JSON NOT NULL,
    `generated_by_user_id` VARCHAR(100) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    INDEX `idx_edu_student_insight_snapshots_course` (`course_id`),
    INDEX `idx_edu_student_insight_snapshots_student` (`student_user_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 35. 工具授权
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_tool_grants` (
    `id` VARCHAR(36) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL,
    `course_id` VARCHAR(36),
    `actor_user_id` VARCHAR(100) NOT NULL,
    `actor_role` VARCHAR(20) NOT NULL,
    `allowed_tools` JSON NOT NULL,
    `confirmed_actions` JSON NOT NULL,
    `capability_ids` JSON NOT NULL,
    `agent_ids` JSON,
    `lesson_id` VARCHAR(36),
    `agent_run_id` VARCHAR(100),
    `conversation_id` VARCHAR(100),
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `expires_at` DATETIME NOT NULL,
    `last_used_at` DATETIME,
    `revoked_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_edu_tool_grants_token` (`token_hash`),
    INDEX `idx_edu_tool_grants_course` (`course_id`),
    INDEX `idx_edu_tool_grants_actor` (`actor_user_id`),
    INDEX `idx_edu_tool_grants_agent_run` (`agent_run_id`),
    INDEX `idx_edu_tool_grants_conversation` (`conversation_id`),
    INDEX `idx_edu_tool_grants_status` (`status`),
    INDEX `idx_edu_tool_grants_expires` (`expires_at`),
    INDEX `idx_edu_tool_grants_lesson` (`lesson_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`lesson_id`) REFERENCES `edu_lessons`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 36. 工作流定义
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_workflows` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `owner_user_id` VARCHAR(100) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `schema_version` VARCHAR(20) NOT NULL DEFAULT '1.0',
    `scope` VARCHAR(20) NOT NULL DEFAULT 'course',
    `execution_mode` VARCHAR(20) NOT NULL DEFAULT 'guided',
    `nodes` JSON NOT NULL,
    `edges` JSON NOT NULL,
    `required_approval_gates` JSON NOT NULL,
    `max_nodes` INT NOT NULL DEFAULT 30,
    `max_retries` INT NOT NULL DEFAULT 2,
    `max_parallelism` INT NOT NULL DEFAULT 4,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_workflows_course` (`course_id`),
    INDEX `idx_edu_workflows_owner` (`owner_user_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 37. Agent 运行记录
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_agent_runs` (
    `id` VARCHAR(36) NOT NULL,
    `course_id` VARCHAR(36) NOT NULL,
    `lesson_id` VARCHAR(36),
    `requested_by` VARCHAR(100) NOT NULL,
    `workflow_code` VARCHAR(100) NOT NULL,
    `workflow_name` VARCHAR(200) NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'pending',
    `conversation_id` VARCHAR(36),
    `sandbox_session_id` VARCHAR(100),
    `core_message_id` VARCHAR(36),
    `tool_grant_id` VARCHAR(36),
    `nodes` JSON NOT NULL,
    `input_payload` JSON NOT NULL,
    `output` JSON NOT NULL,
    `error_summary` TEXT,
    `started_at` DATETIME,
    `finished_at` DATETIME,
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_edu_agent_runs_course` (`course_id`),
    INDEX `idx_edu_agent_runs_lesson` (`lesson_id`),
    INDEX `idx_edu_agent_runs_requested_by` (`requested_by`),
    INDEX `idx_edu_agent_runs_status` (`status`),
    INDEX `idx_edu_agent_runs_conversation` (`conversation_id`),
    INDEX `idx_edu_agent_runs_sandbox` (`sandbox_session_id`),
    INDEX `ix_edu_agent_runs_tool_grant_id` (`tool_grant_id`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 38. 会话-课程绑定
-- ========================================
CREATE TABLE IF NOT EXISTS `edu_conversation_bindings` (
    `id` VARCHAR(36) NOT NULL,
    `conversation_id` VARCHAR(36) NOT NULL,
    `actor_user_id` VARCHAR(100) NOT NULL,
    `course_id` VARCHAR(36),
    `lesson_id` VARCHAR(36),
    `membership_role_snapshot` VARCHAR(20),
    `binding_mode` VARCHAR(30) NOT NULL DEFAULT 'manual',
    `material_policy` VARCHAR(30) NOT NULL DEFAULT 'course_only',
    `agent_service_views` JSON NOT NULL,
    `source_route` JSON,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_conversation_bindings_conversation_id` (`conversation_id`),
    INDEX `ix_edu_conversation_bindings_actor_user_id` (`actor_user_id`),
    INDEX `ix_edu_conversation_bindings_course_id` (`course_id`),
    INDEX `ix_edu_conversation_bindings_lesson_id` (`lesson_id`),
    INDEX `ix_edu_conversation_bindings_status` (`status`),
    FOREIGN KEY (`course_id`) REFERENCES `edu_courses`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
