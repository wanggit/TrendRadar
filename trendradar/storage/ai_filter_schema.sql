-- AI 智能筛选相关表结构 (MySQL)
-- 在 news 库中创建，与 news_items 同库

-- ============================================
-- AI 筛选兴趣标签表
-- 存储从用户兴趣描述中 AI 提取的结构化标签
-- 按版本管理，提示词变更时旧版本标记 deprecated
-- 支持多兴趣文件隔离（interests_file 区分不同文件的标签集）
-- ============================================
CREATE TABLE IF NOT EXISTS ai_filter_tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    tag VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    priority INT NOT NULL DEFAULT 9999,
    status VARCHAR(20) DEFAULT 'active',
    deprecated_at VARCHAR(50),
    version INT NOT NULL,
    prompt_hash VARCHAR(255) NOT NULL,
    interests_file VARCHAR(255) NOT NULL DEFAULT 'ai_interests.txt',
    created_at VARCHAR(50) NOT NULL
);

-- ============================================
-- AI 筛选分类结果表
-- 每条新闻 × 每个标签 = 一行
-- 引用 news_items.id 或 rss_items.id（通过 source_type 区分）
-- ============================================
CREATE TABLE IF NOT EXISTS ai_filter_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    news_item_id INT NOT NULL,
    source_type VARCHAR(20) NOT NULL DEFAULT 'hotlist',
    tag_id INT NOT NULL,
    relevance_score FLOAT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    deprecated_at VARCHAR(50),
    created_at VARCHAR(50) NOT NULL,
    UNIQUE KEY uk_news_source_tag (news_item_id, source_type, tag_id)
);

-- ============================================
-- AI 筛选已分析新闻记录表
-- 记录所有已被 AI 分析过的新闻（无论匹配与否）
-- 用于去重，避免重复发送给 AI 浪费 token
-- ============================================
CREATE TABLE IF NOT EXISTS ai_filter_analyzed_news (
    news_item_id INT NOT NULL,
    source_type VARCHAR(20) NOT NULL DEFAULT 'hotlist',
    interests_file VARCHAR(255) NOT NULL DEFAULT 'ai_interests.txt',
    prompt_hash VARCHAR(255) NOT NULL,
    matched TINYINT(1) NOT NULL DEFAULT 0,
    created_at VARCHAR(50) NOT NULL,
    PRIMARY KEY (news_item_id, source_type, interests_file)
);

-- ============================================
-- 索引
-- ============================================
CREATE INDEX idx_ai_filter_tags_status ON ai_filter_tags(status);
CREATE INDEX idx_ai_filter_tags_version ON ai_filter_tags(version);
CREATE INDEX idx_ai_filter_tags_file ON ai_filter_tags(interests_file, status);
CREATE INDEX idx_ai_filter_tags_priority ON ai_filter_tags(interests_file, status, priority);
CREATE INDEX idx_ai_filter_results_status ON ai_filter_results(status);
CREATE INDEX idx_ai_filter_results_news ON ai_filter_results(news_item_id, source_type);
CREATE INDEX idx_ai_filter_results_tag ON ai_filter_results(tag_id);
CREATE INDEX idx_analyzed_news_lookup ON ai_filter_analyzed_news(source_type, interests_file);
CREATE INDEX idx_analyzed_news_hash ON ai_filter_analyzed_news(interests_file, prompt_hash);
