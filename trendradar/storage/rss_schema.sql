-- TrendRadar RSS 数据库表结构 (MySQL)

-- ============================================
-- RSS 源配置表
-- ============================================
CREATE TABLE IF NOT EXISTS rss_feeds (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    feed_url VARCHAR(2000) DEFAULT '',
    is_active TINYINT(1) DEFAULT 1,
    last_fetch_time VARCHAR(50),
    last_fetch_status VARCHAR(20),
    item_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================
-- RSS 条目表
-- ============================================
CREATE TABLE IF NOT EXISTS rss_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    feed_id VARCHAR(255) NOT NULL,
    url VARCHAR(2000) NOT NULL,
    published_at VARCHAR(50),
    summary TEXT,
    author VARCHAR(255),
    first_crawl_time VARCHAR(50) NOT NULL,
    last_crawl_time VARCHAR(50) NOT NULL,
    crawl_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (feed_id) REFERENCES rss_feeds(id),
    UNIQUE KEY uk_date_url_feed (date, url, feed_id)
);

-- ============================================
-- 抓取记录表
-- ============================================
CREATE TABLE IF NOT EXISTS rss_crawl_records (
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
CREATE TABLE IF NOT EXISTS rss_crawl_status (
    crawl_record_id INT NOT NULL,
    feed_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    PRIMARY KEY (crawl_record_id, feed_id),
    FOREIGN KEY (crawl_record_id) REFERENCES rss_crawl_records(id),
    FOREIGN KEY (feed_id) REFERENCES rss_feeds(id)
);

-- ============================================
-- 推送记录表
-- ============================================
CREATE TABLE IF NOT EXISTS rss_push_records (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date VARCHAR(20) NOT NULL UNIQUE,
    pushed TINYINT(1) DEFAULT 0,
    push_time VARCHAR(50),
    ai_analyzed TINYINT(1) DEFAULT 0,
    ai_analysis_time VARCHAR(50),
    ai_analysis_mode VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 索引定义
-- ============================================
CREATE INDEX idx_rss_date ON rss_items(date);
CREATE INDEX idx_rss_feed ON rss_items(feed_id);
CREATE INDEX idx_rss_published ON rss_items(published_at);
CREATE INDEX idx_rss_crawl_time ON rss_items(last_crawl_time);
CREATE INDEX idx_rss_title ON rss_items(title);
CREATE INDEX idx_rss_crawl_status_record ON rss_crawl_status(crawl_record_id);
CREATE INDEX idx_rss_crawl_records_date ON rss_crawl_records(date);
