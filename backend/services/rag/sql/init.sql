-- ========================================
-- WeAgent RAG Service — 数据库初始化脚本
-- 数据库: weagent_rag
-- 方式: mysql -u root -p < init.sql
-- ========================================

CREATE DATABASE IF NOT EXISTS `weagent_rag`
  DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `weagent_rag`;

-- ========================================
-- 1. 文档
-- ========================================
CREATE TABLE IF NOT EXISTS `rag_documents` (
    `id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL COMMENT '上传者',
    `workspace_id` VARCHAR(36) COMMENT '所属工作空间',
    `domain` VARCHAR(50) NOT NULL COMMENT 'rd / edu / office',
    `name` VARCHAR(500) NOT NULL COMMENT '文档名称',
    `source_type` ENUM('upload','url','scrape') NOT NULL,
    `source_url` VARCHAR(2000) COMMENT '来源URL',
    `file_type` VARCHAR(50) COMMENT 'pdf/txt/md/docx/csv等',
    `file_size` BIGINT COMMENT '文件字节数',
    `status` ENUM('pending','processing','ready','error') DEFAULT 'pending',
    `chunk_count` INT DEFAULT 0,
    `total_tokens` INT DEFAULT 0,
    `description` TEXT COMMENT '用户备注',
    `extra_meta` JSON COMMENT '原始网页标题/作者等',
    `created_at` DATETIME NOT NULL DEFAULT (now()),
    `updated_at` DATETIME NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_user` (`user_id`),
    INDEX `idx_workspace` (`workspace_id`),
    INDEX `idx_domain` (`domain`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 2. 文档分块
-- ========================================
CREATE TABLE IF NOT EXISTS `rag_chunks` (
    `id` VARCHAR(36) NOT NULL,
    `document_id` VARCHAR(36) NOT NULL,
    `chunk_index` INT NOT NULL COMMENT '分块序号',
    `content` TEXT NOT NULL COMMENT '分块文本',
    `token_count` INT DEFAULT 0,
    `vector_id` VARCHAR(200) COMMENT 'ChromaDB 中对应的向量ID',
    `page_number` INT COMMENT '来源页码',
    `extra_meta` JSON,
    PRIMARY KEY (`id`),
    INDEX `idx_document` (`document_id`),
    FOREIGN KEY (`document_id`) REFERENCES `rag_documents`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
