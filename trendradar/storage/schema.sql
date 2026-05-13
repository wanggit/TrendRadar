-- TrendRadar 数据库表结构 (MySQL)

-- ============================================
-- 平台信息表
-- ============================================
CREATE TABLE IF NOT EXISTS platforms (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    is_active TINYINT(1) DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================
-- 新闻条目表
-- ============================================
CREATE TABLE IF NOT EXISTS news_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    platform_id VARCHAR(255) NOT NULL,
    rank INT NOT NULL,
    url VARCHAR(2000) DEFAULT '',
    mobile_url VARCHAR(2000) DEFAULT '',
    first_crawl_time VARCHAR(50) NOT NULL,
    last_crawl_time VARCHAR(50) NOT NULL,
    crawl_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (platform_id) REFERENCES platforms(id),
    UNIQUE KEY uk_date_url_platform (date, url, platform_id)
);

-- ============================================
-- 标题变更历史表
-- ============================================
CREATE TABLE IF NOT EXISTS title_changes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    news_item_id INT NOT NULL,
    old_title TEXT NOT NULL,
    new_title TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (news_item_id) REFERENCES news_items(id)
);

-- ============================================
-- 排名历史表
-- ============================================
CREATE TABLE IF NOT EXISTS rank_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    news_item_id INT NOT NULL,
    rank INT NOT NULL,
    crawl_time VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (news_item_id) REFERENCES news_items(id)
);

-- ============================================
-- 抓取记录表
-- ============================================
CREATE TABLE IF NOT EXISTS crawl_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date VARCHAR(20) NOT NULL,
    crawl_time VARCHAR(50) NOT NULL,
    total_items INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_crawl_time (date, crawl_time)
);

-- ============================================
-- 抓取来源状态表
-- ============================================
CREATE TABLE IF NOT EXISTS crawl_source_status (
    crawl_record_id INT NOT NULL,
    platform_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    PRIMARY KEY (crawl_record_id, platform_id),
    FOREIGN KEY (crawl_record_id) REFERENCES crawl_records(id),
    FOREIGN KEY (platform_id) REFERENCES platforms(id)
);

-- ============================================
-- 时间段执行记录表
-- ============================================
CREATE TABLE IF NOT EXISTS period_executions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    execution_date VARCHAR(20) NOT NULL,
    period_key VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_period_action (execution_date, period_key, action)
);

-- ============================================
-- 索引定义
-- ============================================
CREATE INDEX idx_news_date ON news_items(date);
CREATE INDEX idx_news_platform ON news_items(platform_id);
CREATE INDEX idx_news_crawl_time ON news_items(last_crawl_time);
CREATE INDEX idx_news_title ON news_items(title);
CREATE INDEX idx_crawl_status_record ON crawl_source_status(crawl_record_id);
CREATE INDEX idx_rank_history_news ON rank_history(news_item_id);
CREATE INDEX idx_crawl_records_date ON crawl_records(date);
CREATE INDEX idx_period_exec_lookup ON period_executions(execution_date, period_key, action);
