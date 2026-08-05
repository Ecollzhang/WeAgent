-- WeAgent Education Chat Integration
-- Target: MySQL 8.x
-- Run against an installation where the core database is `weagent` and the
-- Education database is `weagent_edu`. If deployments use different names,
-- replace the two schema qualifiers before execution.
--
-- Application startup migrations remain authoritative and idempotent. This
-- script is the explicit operator migration for pre-existing deployments.

USE `weagent`;

ALTER TABLE `conversations`
    ADD COLUMN `sandbox_agent_service_views` JSON NULL
    COMMENT 'Server-issued per-Agent microservice snapshots';

UPDATE `conversations`
SET `sandbox_agent_service_views` = JSON_OBJECT()
WHERE `sandbox_agent_service_views` IS NULL;

INSERT INTO `grayscale_config`
    (`config_key`, `config_name`, `config_type`, `domain`,
     `enabled`, `visible`, `domains`, `description`)
SELECT
    'feature.education.chat.enabled', 'Education chat', 'feature', 'edu',
    1, 1, NULL, 'Enable course-bound Education conversations'
WHERE NOT EXISTS (
    SELECT 1 FROM `grayscale_config`
    WHERE `config_key` = 'feature.education.chat.enabled'
      AND `domain` = 'edu'
);

INSERT INTO `grayscale_config`
    (`config_key`, `config_name`, `config_type`, `domain`,
     `enabled`, `visible`, `domains`, `description`)
SELECT
    'feature.education.rag.enabled', 'Education course knowledge search',
    'feature', 'edu', 1, 1, NULL,
    'Enable course-scoped RAG for authorized Education Agents'
WHERE NOT EXISTS (
    SELECT 1 FROM `grayscale_config`
    WHERE `config_key` = 'feature.education.rag.enabled'
      AND `domain` = 'edu'
);

INSERT INTO `grayscale_config`
    (`config_key`, `config_name`, `config_type`, `domain`,
     `enabled`, `visible`, `domains`, `description`)
SELECT
    'feature.education.chat.manual_create',
    'Education manual conversation', 'feature', 'edu',
    1, 1, NULL, 'Enable manual EDU conversation bootstrap'
WHERE NOT EXISTS (
    SELECT 1 FROM `grayscale_config`
    WHERE `config_key` = 'feature.education.chat.manual_create'
      AND `domain` = 'edu'
);

INSERT INTO `grayscale_config`
    (`config_key`, `config_name`, `config_type`, `domain`,
     `enabled`, `visible`, `domains`, `description`)
SELECT
    'feature.education.chat.tools', 'Education chat tools', 'feature', 'edu',
    1, 1, NULL, 'Enable course-scoped Education Agent tools'
WHERE NOT EXISTS (
    SELECT 1 FROM `grayscale_config`
    WHERE `config_key` = 'feature.education.chat.tools'
      AND `domain` = 'edu'
);

INSERT INTO `grayscale_config`
    (`config_key`, `config_name`, `config_type`, `domain`,
     `enabled`, `visible`, `domains`, `description`)
SELECT
    'ui.chat.card.education', 'Education business cards', 'ui', 'common',
    1, 1, JSON_ARRAY('edu'), 'Render trusted Education tool-result cards'
WHERE NOT EXISTS (
    SELECT 1 FROM `grayscale_config`
    WHERE `config_key` = 'ui.chat.card.education'
      AND `domain` = 'common'
);

USE `weagent_edu`;

CREATE TABLE IF NOT EXISTS `edu_conversation_bindings` (
    `id` VARCHAR(36) NOT NULL,
    `conversation_id` VARCHAR(36) NOT NULL,
    `actor_user_id` VARCHAR(100) NOT NULL,
    `course_id` VARCHAR(36) NULL,
    `lesson_id` VARCHAR(36) NULL,
    `membership_role_snapshot` VARCHAR(20) NULL,
    `binding_mode` VARCHAR(30) NOT NULL DEFAULT 'manual',
    `material_policy` VARCHAR(30) NOT NULL DEFAULT 'course_only',
    `agent_service_views` JSON NOT NULL,
    `source_route` JSON NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_edu_conversation_bindings_conversation_id`
        (`conversation_id`),
    KEY `ix_edu_conversation_bindings_actor_user_id` (`actor_user_id`),
    KEY `ix_edu_conversation_bindings_course_id` (`course_id`),
    KEY `ix_edu_conversation_bindings_lesson_id` (`lesson_id`),
    KEY `ix_edu_conversation_bindings_status` (`status`),
    CONSTRAINT `fk_edu_conversation_binding_course`
        FOREIGN KEY (`course_id`) REFERENCES `edu_courses` (`id`)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `edu_tool_grants`
    ADD COLUMN `agent_ids` JSON NULL,
    ADD COLUMN `lesson_id` VARCHAR(36) NULL,
    ADD COLUMN `confirmed_actions` JSON NULL;

UPDATE `edu_tool_grants`
SET `confirmed_actions` = JSON_ARRAY()
WHERE `confirmed_actions` IS NULL;

-- Historical product runs become durable Education bindings. The application
-- migration performs the richer Agent-policy projection; this SQL fallback
-- intentionally grants only EDU until the next authenticated runtime refresh.
INSERT INTO `edu_conversation_bindings`
    (`id`, `conversation_id`, `actor_user_id`, `course_id`, `lesson_id`,
     `membership_role_snapshot`, `binding_mode`, `material_policy`,
     `agent_service_views`, `source_route`, `status`)
SELECT
    UUID(), r.`conversation_id`, r.`requested_by`, r.`course_id`, r.`lesson_id`,
    COALESCE(m.`role`, 'student'), 'product', 'authorized_knowledge',
    JSON_OBJECT(), NULL, 'active'
FROM `edu_agent_runs` r
LEFT JOIN `edu_course_memberships` m
  ON m.`course_id` = r.`course_id`
 AND m.`user_id` = r.`requested_by`
 AND m.`status` = 'active'
LEFT JOIN `edu_conversation_bindings` b
  ON b.`conversation_id` = r.`conversation_id`
WHERE r.`conversation_id` IS NOT NULL
  AND b.`id` IS NULL;

USE `weagent`;

UPDATE `conversations` c
JOIN `weagent_edu`.`edu_conversation_bindings` b
  ON b.`conversation_id` = c.`id`
SET
    c.`kb_domain` = 'edu',
    c.`project_id` = NULL,
    c.`services` = JSON_ARRAY('edu', 'rag'),
    c.`sandbox_agent_service_views` =
      COALESCE(b.`agent_service_views`, JSON_OBJECT());
