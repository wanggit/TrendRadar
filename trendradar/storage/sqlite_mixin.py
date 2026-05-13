# coding=utf-8
"""
MySQL 存储 Mixin

提供共用的 MySQL 数据库操作逻辑，供 LocalStorageBackend 复用。
"""

import pymysql
from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from trendradar.storage.base import NewsItem, NewsData, RSSItem, RSSData
from trendradar.utils.url import normalize_url


class MySQLStorageMixin:
    """
    MySQL 存储操作 Mixin

    子类需要实现以下抽象方法：
    - _get_connection() -> pymysql.Connection
    - _get_configured_time() -> datetime
    - _format_date_folder(date) -> str
    - _format_time_filename() -> str
    """

    # ========================================
    # 抽象方法 - 子类必须实现
    # ========================================

    @abstractmethod
    def _get_connection(self) -> pymysql.Connection:
        """获取数据库连接"""
        pass

    @abstractmethod
    def _get_configured_time(self) -> datetime:
        """获取配置时区的当前时间"""
        pass

    @abstractmethod
    def _format_date_folder(self, date: Optional[str] = None) -> str:
        """格式化日期文件夹名 (ISO 格式: YYYY-MM-DD)"""
        pass

    @abstractmethod
    def _format_time_filename(self) -> str:
        """格式化时间文件名 (格式: HH-MM)"""
        pass

    # ========================================
    # Schema 管理
    # ========================================

    def _get_schema_path(self, db_type: str = "news") -> str:
        """
        获取 schema.sql 文件路径

        Args:
            db_type: 数据库类型 ("news" 或 "rss")

        Returns:
            schema 文件路径
        """
        import os
        if db_type == "rss":
            return os.path.join(os.path.dirname(__file__), "rss_schema.sql")
        return os.path.join(os.path.dirname(__file__), "schema.sql")

    def _get_ai_filter_schema_path(self) -> str:
        """获取 AI 筛选 schema 文件路径"""
        import os
        return os.path.join(os.path.dirname(__file__), "ai_filter_schema.sql")

    def _init_tables(self, conn: pymysql.Connection, db_type: str = "news") -> None:
        """
        从 schema.sql 初始化数据库表结构

        Args:
            conn: 数据库连接
            db_type: 数据库类型 ("news" 或 "rss")
        """
        schema_path = self._get_schema_path(db_type)

        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            # MySQL 不支持 executescript，需要逐条执行
            for statement in schema_sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        conn.execute(statement)
                    except pymysql.err.ProgrammingError:
                        pass  # 表已存在等
        else:
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        # news 库额外加载 AI 筛选表结构
        if db_type == "news":
            ai_filter_schema = self._get_ai_filter_schema_path()
            if os.path.exists(ai_filter_schema):
                with open(ai_filter_schema, "r", encoding="utf-8") as f:
                    ai_schema_sql = f.read()
                for statement in ai_schema_sql.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            conn.execute(statement)
                        except pymysql.err.ProgrammingError:
                            pass

        conn.commit()

    # ========================================
    # 新闻数据存储
    # ========================================

    def _save_news_data_impl(self, data: NewsData, log_prefix: str = "[存储]") -> tuple[bool, int, int, int, int]:
        """
        保存新闻数据到 MySQL（核心实现）

        Args:
            data: 新闻数据
            log_prefix: 日志前缀

        Returns:
            (success, new_count, updated_count, title_changed_count, off_list_count)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
            date_str = self._format_date_folder(data.date)

            # 首先同步平台信息到 platforms 表
            for source_id, source_name in data.id_to_name.items():
                cursor.execute("""
                    INSERT INTO platforms (id, name, updated_at)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        updated_at = VALUES(updated_at)
                """, (source_id, source_name, now_str))

            # 统计计数器
            new_count = 0
            updated_count = 0
            title_changed_count = 0
            success_sources = []

            for source_id, news_list in data.items.items():
                success_sources.append(source_id)

                for item in news_list:
                    try:
                        normalized_url = normalize_url(item.url, source_id) if item.url else ""

                        if normalized_url:
                            cursor.execute("""
                                SELECT id, title FROM news_items
                                WHERE date = %s AND url = %s AND platform_id = %s
                            """, (date_str, normalized_url, source_id))
                            existing = cursor.fetchone()

                            if existing:
                                existing_id, existing_title = existing

                                if existing_title != item.title:
                                    cursor.execute("""
                                        INSERT INTO title_changes
                                        (news_item_id, old_title, new_title, changed_at)
                                        VALUES (%s, %s, %s, %s)
                                    """, (existing_id, existing_title, item.title, now_str))
                                    title_changed_count += 1

                                cursor.execute("""
                                    INSERT INTO rank_history
                                    (news_item_id, rank, crawl_time, created_at)
                                    VALUES (%s, %s, %s, %s)
                                """, (existing_id, item.rank, data.crawl_time, now_str))

                                cursor.execute("""
                                    UPDATE news_items SET
                                        title = %s,
                                        rank = %s,
                                        mobile_url = %s,
                                        last_crawl_time = %s,
                                        crawl_count = crawl_count + 1,
                                        updated_at = %s
                                    WHERE id = %s
                                """, (item.title, item.rank, item.mobile_url,
                                      data.crawl_time, now_str, existing_id))
                                updated_count += 1
                            else:
                                cursor.execute("""
                                    INSERT INTO news_items
                                    (date, title, platform_id, rank, url, mobile_url,
                                     first_crawl_time, last_crawl_time, crawl_count,
                                     created_at, updated_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                                """, (date_str, item.title, source_id, item.rank, normalized_url,
                                      item.mobile_url, data.crawl_time, data.crawl_time,
                                      now_str, now_str))
                                new_id = cursor.lastrowid
                                cursor.execute("""
                                    INSERT INTO rank_history
                                    (news_item_id, rank, crawl_time, created_at)
                                    VALUES (%s, %s, %s, %s)
                                """, (new_id, item.rank, data.crawl_time, now_str))
                                new_count += 1
                        else:
                            cursor.execute("""
                                INSERT INTO news_items
                                (date, title, platform_id, rank, url, mobile_url,
                                 first_crawl_time, last_crawl_time, crawl_count,
                                 created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                            """, (date_str, item.title, source_id, item.rank, "",
                                  item.mobile_url, data.crawl_time, data.crawl_time,
                                  now_str, now_str))
                            new_id = cursor.lastrowid
                            cursor.execute("""
                                INSERT INTO rank_history
                                (news_item_id, rank, crawl_time, created_at)
                                VALUES (%s, %s, %s, %s)
                            """, (new_id, item.rank, data.crawl_time, now_str))
                            new_count += 1

                    except pymysql.Error as e:
                        print(f"{log_prefix} 保存新闻条目失败 [{item.title[:30]}...]: {e}")

            total_items = new_count + updated_count

            # ========================================
            # 脱榜检测
            # ========================================
            off_list_count = 0

            cursor.execute("""
                SELECT crawl_time FROM crawl_records
                WHERE date = %s AND crawl_time < %s
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (date_str, data.crawl_time))
            prev_record = cursor.fetchone()

            if prev_record:
                prev_crawl_time = prev_record[0]

                for source_id in success_sources:
                    current_urls = set()
                    for item in data.items.get(source_id, []):
                        normalized_url = normalize_url(item.url, source_id) if item.url else ""
                        if normalized_url:
                            current_urls.add(normalized_url)

                    cursor.execute("""
                        SELECT id, url FROM news_items
                        WHERE date = %s AND platform_id = %s
                          AND last_crawl_time = %s
                          AND url != ''
                    """, (date_str, source_id, prev_crawl_time))

                    for row in cursor.fetchall():
                        news_id, url = row[0], row[1]
                        if url not in current_urls:
                            cursor.execute("""
                                INSERT INTO rank_history
                                (news_item_id, rank, crawl_time, created_at)
                                VALUES (%s, 0, %s, %s)
                            """, (news_id, data.crawl_time, now_str))
                            off_list_count += 1

            # 记录抓取信息
            cursor.execute("""
                INSERT INTO crawl_records
                (date, crawl_time, total_items, created_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_items = VALUES(total_items),
                    created_at = VALUES(created_at)
            """, (date_str, data.crawl_time, total_items, now_str))

            cursor.execute("""
                SELECT id FROM crawl_records WHERE date = %s AND crawl_time = %s
            """, (date_str, data.crawl_time))
            record_row = cursor.fetchone()
            if record_row:
                crawl_record_id = record_row[0]

                for source_id in success_sources:
                    cursor.execute("""
                        INSERT INTO crawl_source_status
                        (crawl_record_id, platform_id, status)
                        VALUES (%s, %s, 'success')
                        ON DUPLICATE KEY UPDATE status = VALUES(status)
                    """, (crawl_record_id, source_id))

                for failed_id in data.failed_ids:
                    cursor.execute("""
                        INSERT IGNORE INTO platforms (id, name, updated_at)
                        VALUES (%s, %s, %s)
                    """, (failed_id, failed_id, now_str))

                    cursor.execute("""
                        INSERT INTO crawl_source_status
                        (crawl_record_id, platform_id, status)
                        VALUES (%s, %s, 'failed')
                        ON DUPLICATE KEY UPDATE status = VALUES(status)
                    """, (crawl_record_id, failed_id))

            conn.commit()

            return True, new_count, updated_count, title_changed_count, off_list_count

        except Exception as e:
            print(f"{log_prefix} 保存失败: {e}")
            return False, 0, 0, 0, 0

    def _get_today_all_data_impl(self, date: Optional[str] = None) -> Optional[NewsData]:
        """获取指定日期的所有新闻数据（合并后）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT n.id, n.title, n.platform_id, p.name as platform_name,
                       n.rank, n.url, n.mobile_url,
                       n.first_crawl_time, n.last_crawl_time, n.crawl_count
                FROM news_items n
                LEFT JOIN platforms p ON n.platform_id = p.id
                WHERE n.date = %s
                ORDER BY n.platform_id, n.last_crawl_time
            """, (date_str,))

            rows = cursor.fetchall()
            if not rows:
                return None

            news_ids = [row[0] for row in rows]

            rank_history_map: Dict[int, List[int]] = {}
            rank_timeline_map: Dict[int, List[Dict[str, Any]]] = {}
            if news_ids:
                placeholders = ",".join(["%s"] * len(news_ids))
                cursor.execute(f"""
                    SELECT rh.news_item_id, rh.rank, rh.crawl_time
                    FROM rank_history rh
                    JOIN news_items ni ON rh.news_item_id = ni.id
                    WHERE rh.news_item_id IN ({placeholders})
                      AND NOT (rh.rank = 0 AND rh.crawl_time > ni.last_crawl_time)
                    ORDER BY rh.news_item_id, rh.crawl_time
                """, news_ids)
                for rh_row in cursor.fetchall():
                    news_id, rank, crawl_time = rh_row[0], rh_row[1], rh_row[2]

                    if news_id not in rank_history_map:
                        rank_history_map[news_id] = []
                    if rank != 0 and rank not in rank_history_map[news_id]:
                        rank_history_map[news_id].append(rank)

                    if news_id not in rank_timeline_map:
                        rank_timeline_map[news_id] = []
                    time_part = crawl_time.split()[1][:5] if ' ' in crawl_time else crawl_time[:5]
                    rank_timeline_map[news_id].append({
                        "time": time_part,
                        "rank": rank if rank != 0 else None
                    })

            items: Dict[str, List[NewsItem]] = {}
            id_to_name: Dict[str, str] = {}
            crawl_date = date_str

            for row in rows:
                news_id = row[0]
                platform_id = row[2]
                title = row[1]
                platform_name = row[3] or platform_id

                id_to_name[platform_id] = platform_name

                if platform_id not in items:
                    items[platform_id] = []

                ranks = rank_history_map.get(news_id, [row[4]])
                rank_timeline = rank_timeline_map.get(news_id, [])

                items[platform_id].append(NewsItem(
                    title=title,
                    source_id=platform_id,
                    source_name=platform_name,
                    rank=row[4],
                    url=row[5] or "",
                    mobile_url=row[6] or "",
                    crawl_time=row[8],
                    ranks=ranks,
                    first_time=row[7],
                    last_time=row[8],
                    count=row[9],
                    rank_timeline=rank_timeline,
                ))

            cursor.execute("""
                SELECT DISTINCT css.platform_id
                FROM crawl_source_status css
                JOIN crawl_records cr ON css.crawl_record_id = cr.id
                WHERE cr.date = %s AND css.status = 'failed'
            """, (date_str,))
            failed_ids = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT crawl_time FROM crawl_records
                WHERE date = %s
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (date_str,))

            time_row = cursor.fetchone()
            crawl_time = time_row[0] if time_row else self._format_time_filename()

            return NewsData(
                date=crawl_date,
                crawl_time=crawl_time,
                items=items,
                id_to_name=id_to_name,
                failed_ids=failed_ids,
            )

        except Exception as e:
            print(f"[存储] 读取数据失败: {e}")
            return None

    def _get_latest_crawl_data_impl(self, date: Optional[str] = None) -> Optional[NewsData]:
        """获取最新一次抓取的数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT crawl_time FROM crawl_records
                WHERE date = %s
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (date_str,))

            time_row = cursor.fetchone()
            if not time_row:
                return None

            latest_time = time_row[0]

            cursor.execute("""
                SELECT n.id, n.title, n.platform_id, p.name as platform_name,
                       n.rank, n.url, n.mobile_url,
                       n.first_crawl_time, n.last_crawl_time, n.crawl_count
                FROM news_items n
                LEFT JOIN platforms p ON n.platform_id = p.id
                WHERE n.date = %s AND n.last_crawl_time = %s
            """, (date_str, latest_time))

            rows = cursor.fetchall()
            if not rows:
                return None

            news_ids = [row[0] for row in rows]

            rank_history_map: Dict[int, List[int]] = {}
            rank_timeline_map: Dict[int, List[Dict[str, Any]]] = {}
            if news_ids:
                placeholders = ",".join(["%s"] * len(news_ids))
                cursor.execute(f"""
                    SELECT rh.news_item_id, rh.rank, rh.crawl_time
                    FROM rank_history rh
                    JOIN news_items ni ON rh.news_item_id = ni.id
                    WHERE rh.news_item_id IN ({placeholders})
                      AND NOT (rh.rank = 0 AND rh.crawl_time > ni.last_crawl_time)
                    ORDER BY rh.news_item_id, rh.crawl_time
                """, news_ids)
                for rh_row in cursor.fetchall():
                    news_id, rank, crawl_time = rh_row[0], rh_row[1], rh_row[2]

                    if news_id not in rank_history_map:
                        rank_history_map[news_id] = []
                    if rank != 0 and rank not in rank_history_map[news_id]:
                        rank_history_map[news_id].append(rank)

                    if news_id not in rank_timeline_map:
                        rank_timeline_map[news_id] = []
                    time_part = crawl_time.split()[1][:5] if ' ' in crawl_time else crawl_time[:5]
                    rank_timeline_map[news_id].append({
                        "time": time_part,
                        "rank": rank if rank != 0 else None
                    })

            items: Dict[str, List[NewsItem]] = {}
            id_to_name: Dict[str, str] = {}
            crawl_date = date_str

            for row in rows:
                news_id = row[0]
                platform_id = row[2]
                platform_name = row[3] or platform_id
                id_to_name[platform_id] = platform_name

                if platform_id not in items:
                    items[platform_id] = []

                ranks = rank_history_map.get(news_id, [row[4]])
                rank_timeline = rank_timeline_map.get(news_id, [])

                items[platform_id].append(NewsItem(
                    title=row[1],
                    source_id=platform_id,
                    source_name=platform_name,
                    rank=row[4],
                    url=row[5] or "",
                    mobile_url=row[6] or "",
                    crawl_time=row[8],
                    ranks=ranks,
                    first_time=row[7],
                    last_time=row[8],
                    count=row[9],
                    rank_timeline=rank_timeline,
                ))

            cursor.execute("""
                SELECT css.platform_id
                FROM crawl_source_status css
                JOIN crawl_records cr ON css.crawl_record_id = cr.id
                WHERE cr.date = %s AND cr.crawl_time = %s AND css.status = 'failed'
            """, (date_str, latest_time))

            failed_ids = [row[0] for row in cursor.fetchall()]

            return NewsData(
                date=crawl_date,
                crawl_time=latest_time,
                items=items,
                id_to_name=id_to_name,
                failed_ids=failed_ids,
            )

        except Exception as e:
            print(f"[存储] 获取最新数据失败: {e}")
            return None

    def _detect_new_titles_impl(self, current_data: NewsData) -> Dict[str, Dict]:
        """检测新增的标题"""
        try:
            historical_data = self._get_today_all_data_impl(current_data.date)

            if not historical_data:
                new_titles = {}
                for source_id, news_list in current_data.items.items():
                    new_titles[source_id] = {item.title: item for item in news_list}
                return new_titles

            current_time = current_data.crawl_time

            historical_titles: Dict[str, set] = {}
            for source_id, news_list in historical_data.items.items():
                historical_titles[source_id] = set()
                for item in news_list:
                    first_time = item.first_time or item.crawl_time
                    if first_time < current_time:
                        historical_titles[source_id].add(item.title)

            has_historical_data = any(len(titles) > 0 for titles in historical_titles.values())
            if not has_historical_data:
                return {}

            new_titles = {}
            for source_id, news_list in current_data.items.items():
                hist_set = historical_titles.get(source_id, set())
                for item in news_list:
                    if item.title not in hist_set:
                        if source_id not in new_titles:
                            new_titles[source_id] = {}
                        new_titles[source_id][item.title] = item

            return new_titles

        except Exception as e:
            print(f"[存储] 检测新标题失败: {e}")
            return {}

    def _is_first_crawl_today_impl(self, date: Optional[str] = None) -> bool:
        """检查是否是当天第一次抓取"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT COUNT(*) as count FROM crawl_records
                WHERE date = %s
            """, (date_str,))

            row = cursor.fetchone()
            count = row[0] if row else 0

            return count <= 1

        except Exception as e:
            print(f"[存储] 检查首次抓取失败: {e}")
            return True

    def _get_crawl_times_impl(self, date: Optional[str] = None) -> List[str]:
        """获取指定日期的所有抓取时间列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT crawl_time FROM crawl_records
                WHERE date = %s
                ORDER BY crawl_time
            """, (date_str,))

            rows = cursor.fetchall()
            return [row[0] for row in rows]

        except Exception as e:
            print(f"[存储] 获取抓取时间列表失败: {e}")
            return []

    # ========================================
    # 时间段执行记录（调度系统）
    # ========================================

    def _has_period_executed_impl(self, date_str: str, period_key: str, action: str) -> bool:
        """检查指定时间段的某个 action 今天是否已执行"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 1 FROM period_executions
                WHERE execution_date = %s AND period_key = %s AND action = %s
            """, (date_str, period_key, action))

            return cursor.fetchone() is not None

        except Exception as e:
            print(f"[存储] 检查时间段执行记录失败: {e}")
            return False

    def _record_period_execution_impl(self, date_str: str, period_key: str, action: str) -> bool:
        """记录时间段的 action 执行"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT IGNORE INTO period_executions (execution_date, period_key, action, executed_at)
                VALUES (%s, %s, %s, %s)
            """, (date_str, period_key, action, now_str))

            conn.commit()
            return True

        except Exception as e:
            print(f"[存储] 记录时间段执行失败: {e}")
            return False

    # ========================================
    # RSS 数据存储
    # ========================================

    def _save_rss_data_impl(self, data: RSSData, log_prefix: str = "[存储]") -> tuple[bool, int, int]:
        """保存 RSS 数据到 MySQL"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
            date_str = self._format_date_folder(data.date)

            for feed_id, feed_name in data.id_to_name.items():
                cursor.execute("""
                    INSERT INTO rss_feeds (id, name, updated_at)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        updated_at = VALUES(updated_at)
                """, (feed_id, feed_name, now_str))

            new_count = 0
            updated_count = 0

            for feed_id, rss_list in data.items.items():
                for item in rss_list:
                    try:
                        if item.url:
                            cursor.execute("""
                                SELECT id, title FROM rss_items
                                WHERE date = %s AND url = %s AND feed_id = %s
                            """, (date_str, item.url, feed_id))
                            existing = cursor.fetchone()

                            if existing:
                                existing_id = existing[0]
                                cursor.execute("""
                                    UPDATE rss_items SET
                                        title = %s,
                                        published_at = %s,
                                        summary = %s,
                                        author = %s,
                                        last_crawl_time = %s,
                                        crawl_count = crawl_count + 1,
                                        updated_at = %s
                                    WHERE id = %s
                                """, (item.title, item.published_at, item.summary,
                                      item.author, data.crawl_time, now_str, existing_id))
                                updated_count += 1
                            else:
                                cursor.execute("""
                                    INSERT INTO rss_items
                                    (date, title, feed_id, url, published_at, summary, author,
                                     first_crawl_time, last_crawl_time, crawl_count,
                                     created_at, updated_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        title = VALUES(title),
                                        published_at = VALUES(published_at),
                                        summary = VALUES(summary),
                                        author = VALUES(author),
                                        last_crawl_time = VALUES(last_crawl_time),
                                        crawl_count = crawl_count + 1,
                                        updated_at = VALUES(updated_at)
                                """, (date_str, item.title, feed_id, item.url, item.published_at,
                                      item.summary, item.author, data.crawl_time,
                                      data.crawl_time, now_str, now_str))
                                new_count += 1
                        else:
                            try:
                                cursor.execute("""
                                    INSERT INTO rss_items
                                    (date, title, feed_id, url, published_at, summary, author,
                                     first_crawl_time, last_crawl_time, crawl_count,
                                     created_at, updated_at)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                                """, (date_str, item.title, feed_id, "", item.published_at,
                                      item.summary, item.author, data.crawl_time,
                                      data.crawl_time, now_str, now_str))
                                new_count += 1
                            except pymysql.err.IntegrityError:
                                pass

                    except pymysql.Error as e:
                        print(f"{log_prefix} 保存 RSS 条目失败 [{item.title[:30]}...]: {e}")

            total_items = new_count + updated_count

            cursor.execute("""
                INSERT INTO rss_crawl_records
                (date, crawl_time, total_items, created_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_items = VALUES(total_items),
                    created_at = VALUES(created_at)
            """, (date_str, data.crawl_time, total_items, now_str))

            cursor.execute("""
                SELECT id FROM rss_crawl_records WHERE date = %s AND crawl_time = %s
            """, (date_str, data.crawl_time))
            record_row = cursor.fetchone()
            if record_row:
                crawl_record_id = record_row[0]

                for feed_id in data.items.keys():
                    cursor.execute("""
                        INSERT INTO rss_crawl_status
                        (crawl_record_id, feed_id, status)
                        VALUES (%s, %s, 'success')
                        ON DUPLICATE KEY UPDATE status = VALUES(status)
                    """, (crawl_record_id, feed_id))

                for failed_id in data.failed_ids:
                    cursor.execute("""
                        INSERT IGNORE INTO rss_feeds (id, name, updated_at)
                        VALUES (%s, %s, %s)
                    """, (failed_id, failed_id, now_str))

                    cursor.execute("""
                        INSERT INTO rss_crawl_status
                        (crawl_record_id, feed_id, status)
                        VALUES (%s, %s, 'failed')
                        ON DUPLICATE KEY UPDATE status = VALUES(status)
                    """, (crawl_record_id, failed_id))

            conn.commit()

            return True, new_count, updated_count

        except Exception as e:
            print(f"{log_prefix} 保存 RSS 数据失败: {e}")
            return False, 0, 0

    def _get_rss_data_impl(self, date: Optional[str] = None) -> Optional[RSSData]:
        """获取指定日期的所有 RSS 数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT i.id, i.title, i.feed_id, f.name as feed_name,
                       i.url, i.published_at, i.summary, i.author,
                       i.first_crawl_time, i.last_crawl_time, i.crawl_count
                FROM rss_items i
                LEFT JOIN rss_feeds f ON i.feed_id = f.id
                WHERE i.date = %s
                ORDER BY i.published_at DESC
            """, (date_str,))

            rows = cursor.fetchall()
            if not rows:
                return None

            items: Dict[str, List[RSSItem]] = {}
            id_to_name: Dict[str, str] = {}
            crawl_date = date_str

            for row in rows:
                feed_id = row[2]
                feed_name = row[3] or feed_id

                id_to_name[feed_id] = feed_name

                if feed_id not in items:
                    items[feed_id] = []

                items[feed_id].append(RSSItem(
                    title=row[1],
                    feed_id=feed_id,
                    feed_name=feed_name,
                    url=row[4] or "",
                    published_at=row[5] or "",
                    summary=row[6] or "",
                    author=row[7] or "",
                    crawl_time=row[9],
                    first_time=row[8],
                    last_time=row[9],
                    count=row[10],
                ))

            cursor.execute("""
                SELECT crawl_time FROM rss_crawl_records
                WHERE date = %s
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (date_str,))
            time_row = cursor.fetchone()
            crawl_time = time_row[0] if time_row else self._format_time_filename()

            cursor.execute("""
                SELECT DISTINCT cs.feed_id
                FROM rss_crawl_status cs
                JOIN rss_crawl_records cr ON cs.crawl_record_id = cr.id
                WHERE cr.date = %s AND cs.status = 'failed'
            """, (date_str,))
            failed_ids = [row[0] for row in cursor.fetchall()]

            return RSSData(
                date=crawl_date,
                crawl_time=crawl_time,
                items=items,
                id_to_name=id_to_name,
                failed_ids=failed_ids,
            )

        except Exception as e:
            print(f"[存储] 读取 RSS 数据失败: {e}")
            return None

    def _detect_new_rss_items_impl(self, current_data: RSSData) -> Dict[str, List[RSSItem]]:
        """检测新增的 RSS 条目"""
        try:
            historical_data = self._get_rss_data_impl(current_data.date)

            if not historical_data:
                return current_data.items.copy()

            current_time = current_data.crawl_time

            historical_urls: Dict[str, set] = {}
            for feed_id, rss_list in historical_data.items.items():
                historical_urls[feed_id] = set()
                for item in rss_list:
                    first_time = item.first_time or item.crawl_time
                    if first_time < current_time:
                        if item.url:
                            historical_urls[feed_id].add(item.url)

            has_historical_data = any(len(urls) > 0 for urls in historical_urls.values())
            if not has_historical_data:
                return {}

            new_items: Dict[str, List[RSSItem]] = {}
            for feed_id, rss_list in current_data.items.items():
                hist_set = historical_urls.get(feed_id, set())
                for item in rss_list:
                    if item.url and item.url not in hist_set:
                        if feed_id not in new_items:
                            new_items[feed_id] = []
                        new_items[feed_id].append(item)

            return new_items

        except Exception as e:
            print(f"[存储] 检测新 RSS 条目失败: {e}")
            return {}

    def _get_latest_rss_data_impl(self, date: Optional[str] = None) -> Optional[RSSData]:
        """获取最新一次抓取的 RSS 数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT crawl_time FROM rss_crawl_records
                WHERE date = %s
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (date_str,))

            time_row = cursor.fetchone()
            if not time_row:
                return None

            latest_time = time_row[0]

            cursor.execute("""
                SELECT i.id, i.title, i.feed_id, f.name as feed_name,
                       i.url, i.published_at, i.summary, i.author,
                       i.first_crawl_time, i.last_crawl_time, i.crawl_count
                FROM rss_items i
                LEFT JOIN rss_feeds f ON i.feed_id = f.id
                WHERE i.date = %s AND i.last_crawl_time = %s
                ORDER BY i.published_at DESC
            """, (date_str, latest_time))

            rows = cursor.fetchall()
            if not rows:
                return None

            items: Dict[str, List[RSSItem]] = {}
            id_to_name: Dict[str, str] = {}
            crawl_date = date_str

            for row in rows:
                feed_id = row[2]
                feed_name = row[3] or feed_id

                id_to_name[feed_id] = feed_name

                if feed_id not in items:
                    items[feed_id] = []

                items[feed_id].append(RSSItem(
                    title=row[1],
                    feed_id=feed_id,
                    feed_name=feed_name,
                    url=row[4] or "",
                    published_at=row[5] or "",
                    summary=row[6] or "",
                    author=row[7] or "",
                    crawl_time=row[9],
                    first_time=row[8],
                    last_time=row[9],
                    count=row[10],
                ))

            cursor.execute("""
                SELECT cs.feed_id
                FROM rss_crawl_status cs
                JOIN rss_crawl_records cr ON cs.crawl_record_id = cr.id
                WHERE cr.date = %s AND cr.crawl_time = %s AND cs.status = 'failed'
            """, (date_str, latest_time))

            failed_ids = [row[0] for row in cursor.fetchall()]

            return RSSData(
                date=crawl_date,
                crawl_time=latest_time,
                items=items,
                id_to_name=id_to_name,
                failed_ids=failed_ids,
            )

        except Exception as e:
            print(f"[存储] 获取最新 RSS 数据失败: {e}")
            return None

    # ========================================
    # AI 智能筛选 - 标签管理
    # ========================================

    def _get_active_tags_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> List[Dict[str, Any]]:
        """获取指定兴趣文件的 active 标签列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, tag, description, version, prompt_hash, priority
                FROM ai_filter_tags
                WHERE status = 'active' AND interests_file = %s
                ORDER BY priority ASC, id ASC
            """, (interests_file,))

            return [
                {
                    "id": row[0], "tag": row[1], "description": row[2],
                    "version": row[3], "prompt_hash": row[4], "priority": row[5],
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            print(f"[AI筛选] 获取标签失败: {e}")
            return []

    def _get_latest_prompt_hash_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> Optional[str]:
        """获取指定兴趣文件最新版本标签的 prompt_hash"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT prompt_hash FROM ai_filter_tags
                WHERE status = 'active' AND interests_file = %s
                ORDER BY version DESC
                LIMIT 1
            """, (interests_file,))
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"[AI筛选] 获取 prompt_hash 失败: {e}")
            return None

    def _get_latest_tag_version_impl(self, date: Optional[str] = None) -> int:
        """获取最新版本号"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT MAX(version) FROM ai_filter_tags
            """)
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        except Exception as e:
            print(f"[AI筛选] 获取版本号失败: {e}")
            return 0

    def _deprecate_all_tags_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> int:
        """将指定兴趣文件的 active 标签和关联的分类结果标记为 deprecated"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "SELECT id FROM ai_filter_tags WHERE status = 'active' AND interests_file = %s",
                (interests_file,)
            )
            tag_ids = [row[0] for row in cursor.fetchall()]

            if not tag_ids:
                return 0

            placeholders = ",".join(["%s"] * len(tag_ids))
            cursor.execute(f"""
                UPDATE ai_filter_tags
                SET status = 'deprecated', deprecated_at = %s
                WHERE id IN ({placeholders})
            """, [now_str] + tag_ids)
            tag_count = cursor.rowcount

            cursor.execute(f"""
                UPDATE ai_filter_results
                SET status = 'deprecated', deprecated_at = %s
                WHERE tag_id IN ({placeholders}) AND status = 'active'
            """, [now_str] + tag_ids)

            conn.commit()
            print(f"[AI筛选] 已废弃 {tag_count} 个标签及关联分类结果")
            return tag_count
        except Exception as e:
            print(f"[AI筛选] 废弃标签失败: {e}")
            return 0

    def _save_tags_impl(
        self, date: Optional[str], tags: List[Dict], version: int, prompt_hash: str,
        interests_file: str = "ai_interests.txt"
    ) -> int:
        """保存新提取的标签"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

            count = 0
            for idx, tag_data in enumerate(tags, start=1):
                priority = tag_data.get("priority", idx)
                try:
                    priority = int(priority)
                except (TypeError, ValueError):
                    priority = idx
                cursor.execute("""
                    INSERT INTO ai_filter_tags
                    (tag, description, priority, version, prompt_hash, interests_file, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    tag_data["tag"],
                    tag_data.get("description", ""),
                    priority,
                    version,
                    prompt_hash,
                    interests_file,
                    now_str,
                ))
                count += 1

            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 保存标签失败: {e}")
            return 0

    def _deprecate_specific_tags_impl(
        self, date: Optional[str], tag_ids: List[int]
    ) -> int:
        """废弃指定 ID 的标签及其关联分类结果"""
        if not tag_ids:
            return 0
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

            placeholders = ",".join(["%s"] * len(tag_ids))

            cursor.execute(f"""
                UPDATE ai_filter_tags
                SET status = 'deprecated', deprecated_at = %s
                WHERE id IN ({placeholders})
            """, [now_str] + tag_ids)
            tag_count = cursor.rowcount

            cursor.execute(f"""
                UPDATE ai_filter_results
                SET status = 'deprecated', deprecated_at = %s
                WHERE tag_id IN ({placeholders}) AND status = 'active'
            """, [now_str] + tag_ids)

            conn.commit()
            return tag_count
        except Exception as e:
            print(f"[AI筛选] 废弃指定标签失败: {e}")
            return 0

    def _update_tags_hash_impl(
        self, date: Optional[str], interests_file: str, new_hash: str
    ) -> int:
        """更新指定兴趣文件所有 active 标签的 prompt_hash"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE ai_filter_tags
                SET prompt_hash = %s
                WHERE interests_file = %s AND status = 'active'
            """, (new_hash, interests_file))
            count = cursor.rowcount

            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 更新标签 hash 失败: {e}")
            return 0

    def _update_tag_descriptions_impl(
        self, date: Optional[str], tag_updates: List[Dict],
        interests_file: str = "ai_interests.txt"
    ) -> int:
        """按 tag 名匹配，更新 active 标签的 description 字段"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            count = 0
            for t in tag_updates:
                tag_name = t.get("tag", "")
                description = t.get("description", "")
                if not tag_name:
                    continue
                cursor.execute("""
                    UPDATE ai_filter_tags
                    SET description = %s
                    WHERE tag = %s AND interests_file = %s AND status = 'active'
                """, (description, tag_name, interests_file))
                count += cursor.rowcount

            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 更新标签描述失败: {e}")
            return 0

    def _update_tag_priorities_impl(
        self, date: Optional[str], tag_priorities: List[Dict],
        interests_file: str = "ai_interests.txt"
    ) -> int:
        """按 tag 名匹配，更新 active 标签的 priority 字段"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            count = 0
            for t in tag_priorities:
                tag_name = t.get("tag", "")
                priority = t.get("priority")
                if not tag_name:
                    continue
                try:
                    priority = int(priority)
                except (TypeError, ValueError):
                    continue
                cursor.execute("""
                    UPDATE ai_filter_tags
                    SET priority = %s
                    WHERE tag = %s AND interests_file = %s AND status = 'active'
                """, (priority, tag_name, interests_file))
                count += cursor.rowcount

            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 更新标签优先级失败: {e}")
            return 0

    def _save_analyzed_news_impl(
        self, date: Optional[str], news_ids: List[int], source_type: str,
        interests_file: str, prompt_hash: str, matched_ids: set
    ) -> int:
        """批量记录已分析的新闻"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

            count = 0
            for nid in news_ids:
                try:
                    cursor.execute("""
                        INSERT INTO ai_filter_analyzed_news
                        (news_item_id, source_type, interests_file, prompt_hash, matched, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            prompt_hash = VALUES(prompt_hash),
                            matched = VALUES(matched),
                            created_at = VALUES(created_at)
                    """, (
                        nid, source_type, interests_file, prompt_hash,
                        1 if nid in matched_ids else 0,
                        now_str,
                    ))
                    count += 1
                except Exception:
                    pass

            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 保存已分析记录失败: {e}")
            return 0

    def _get_analyzed_news_ids_impl(
        self, date: Optional[str] = None, source_type: str = "hotlist",
        interests_file: str = "ai_interests.txt"
    ) -> set:
        """获取已分析过的新闻 ID 集合"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT news_item_id FROM ai_filter_analyzed_news
                WHERE source_type = %s AND interests_file = %s
            """, (source_type, interests_file))

            return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            print(f"[AI筛选] 获取已分析ID失败: {e}")
            return set()

    def _clear_analyzed_news_impl(
        self, date: Optional[str] = None, interests_file: str = "ai_interests.txt"
    ) -> int:
        """清除指定兴趣文件的所有已分析记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM ai_filter_analyzed_news
                WHERE interests_file = %s
            """, (interests_file,))

            count = cursor.rowcount
            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 清除已分析记录失败: {e}")
            return 0

    def _clear_unmatched_analyzed_news_impl(
        self, date: Optional[str] = None, interests_file: str = "ai_interests.txt"
    ) -> int:
        """清除不匹配的已分析记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM ai_filter_analyzed_news
                WHERE interests_file = %s AND matched = 0
            """, (interests_file,))

            count = cursor.rowcount
            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 清除不匹配记录失败: {e}")
            return 0

    def _save_filter_results_impl(
        self, date: Optional[str], results: List[Dict]
    ) -> int:
        """批量保存分类结果"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")

            count = 0
            for r in results:
                try:
                    cursor.execute("""
                        INSERT INTO ai_filter_results
                        (news_item_id, source_type, tag_id, relevance_score, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        r["news_item_id"],
                        r.get("source_type", "hotlist"),
                        r["tag_id"],
                        r.get("relevance_score", 0.0),
                        now_str,
                    ))
                    count += 1
                except pymysql.err.IntegrityError:
                    pass

            conn.commit()
            return count
        except Exception as e:
            print(f"[AI筛选] 保存分类结果失败: {e}")
            return 0

    def _get_active_filter_results_impl(self, date: Optional[str] = None, interests_file: str = "ai_interests.txt") -> List[Dict[str, Any]]:
        """获取指定兴趣文件的 active 分类结果"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    r.news_item_id, r.source_type, r.tag_id, r.relevance_score,
                    t.tag, t.description as tag_description, t.priority,
                    n.title, n.platform_id as source_id, p.name as source_name,
                    n.url, n.mobile_url, n.rank,
                    n.first_crawl_time, n.last_crawl_time, n.crawl_count
                FROM ai_filter_results r
                JOIN ai_filter_tags t ON r.tag_id = t.id
                JOIN news_items n ON r.news_item_id = n.id
                LEFT JOIN platforms p ON n.platform_id = p.id
                WHERE r.status = 'active' AND r.source_type = 'hotlist'
                    AND t.status = 'active' AND t.interests_file = %s
                ORDER BY t.priority ASC, t.id ASC, r.relevance_score DESC
            """, (interests_file,))

            results = []
            hotlist_news_ids = []
            for row in cursor.fetchall():
                results.append({
                    "news_item_id": row[0], "source_type": row[1],
                    "tag_id": row[2], "relevance_score": row[3],
                    "tag": row[4], "tag_description": row[5], "tag_priority": row[6],
                    "title": row[7], "source_id": row[8],
                    "source_name": row[9] or row[8],
                    "url": row[10] or "", "mobile_url": row[11] or "",
                    "rank": row[12],
                    "first_time": row[13], "last_time": row[14],
                    "count": row[15],
                })
                hotlist_news_ids.append(row[0])

            ranks_map: Dict[int, List[int]] = {}
            if hotlist_news_ids:
                unique_ids = list(set(hotlist_news_ids))
                placeholders = ",".join(["%s"] * len(unique_ids))
                cursor.execute(f"""
                    SELECT news_item_id, rank FROM rank_history
                    WHERE news_item_id IN ({placeholders}) AND rank != 0
                """, unique_ids)
                for rh_row in cursor.fetchall():
                    nid, rank = rh_row[0], rh_row[1]
                    if nid not in ranks_map:
                        ranks_map[nid] = []
                    if rank not in ranks_map[nid]:
                        ranks_map[nid].append(rank)

            for item in results:
                item["ranks"] = ranks_map.get(item["news_item_id"], [item["rank"]])

            try:
                cursor.execute("""
                    SELECT r.news_item_id, r.tag_id, r.relevance_score,
                           t.tag, t.description, t.priority
                    FROM ai_filter_results r
                    JOIN ai_filter_tags t ON r.tag_id = t.id
                    WHERE r.status = 'active' AND r.source_type = 'rss'
                        AND t.status = 'active' AND t.interests_file = %s
                    ORDER BY t.priority ASC, t.id ASC, r.relevance_score DESC
                """, (interests_file,))

                rss_filter_rows = cursor.fetchall()
                if rss_filter_rows:
                    rss_ids = [row[0] for row in rss_filter_rows]
                    placeholders = ",".join(["%s"] * len(rss_ids))
                    cursor.execute(f"""
                        SELECT i.id, i.title, i.feed_id, f.name as feed_name,
                               i.url, i.published_at
                        FROM rss_items i
                        LEFT JOIN rss_feeds f ON i.feed_id = f.id
                        WHERE i.id IN ({placeholders})
                    """, rss_ids)

                    rss_info = {row[0]: row for row in cursor.fetchall()}

                    for fr_row in rss_filter_rows:
                        rss_id = fr_row[0]
                        info = rss_info.get(rss_id)
                        if info:
                            results.append({
                                "news_item_id": rss_id,
                                "source_type": "rss",
                                "tag_id": fr_row[1],
                                "relevance_score": fr_row[2],
                                "tag": fr_row[3],
                                "tag_description": fr_row[4],
                                "tag_priority": fr_row[5],
                                "title": info[1],
                                "source_id": info[2],
                                "source_name": info[3] or info[2],
                                "url": info[4] or "",
                                "mobile_url": "",
                                "rank": 0,
                                "ranks": [],
                                "first_time": info[5] or "",
                                "last_time": info[5] or "",
                                "count": 1,
                            })
            except Exception:
                pass

            return results
        except Exception as e:
            print(f"[AI筛选] 获取分类结果失败: {e}")
            return []

    def _get_all_news_ids_impl(self, date: Optional[str] = None) -> List[Dict]:
        """获取当日所有新闻的 id 和标题"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT n.id, n.title, n.platform_id, p.name as platform_name
                FROM news_items n
                LEFT JOIN platforms p ON n.platform_id = p.id
                WHERE n.date = %s
                ORDER BY n.id
            """, (date_str,))

            return [
                {
                    "id": row[0], "title": row[1],
                    "source_id": row[2], "source_name": row[3] or row[2],
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            print(f"[AI筛选] 获取新闻列表失败: {e}")
            return []

    def _get_all_rss_ids_impl(self, date: Optional[str] = None) -> List[Dict]:
        """获取当日所有 RSS 条目的 id 和标题"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            date_str = self._format_date_folder(date)

            cursor.execute("""
                SELECT i.id, i.title, i.feed_id, f.name as feed_name, i.published_at
                FROM rss_items i
                LEFT JOIN rss_feeds f ON i.feed_id = f.id
                WHERE i.date = %s
                ORDER BY i.id
            """, (date_str,))

            return [
                {
                    "id": row[0], "title": row[1],
                    "source_id": row[2], "source_name": row[3] or row[2],
                    "published_at": row[4] or "",
                }
                for row in cursor.fetchall()
            ]
        except Exception as e:
            print(f"[AI筛选] 获取 RSS 列表失败: {e}")
            return []
