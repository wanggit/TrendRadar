# coding=utf-8
"""
本地存储后端 - MySQL + TXT/HTML

使用 MySQL 作为主存储，支持可选的 TXT 快照和 HTML 报告
"""

import pymysql
import shutil
import pytz
import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from trendradar.storage.base import StorageBackend, NewsData, RSSItem, RSSData
from trendradar.storage.sqlite_mixin import MySQLStorageMixin
from trendradar.utils.time import (
    DEFAULT_TIMEZONE,
    get_configured_time,
    format_date_folder,
    format_time_filename,
)


class LocalStorageBackend(MySQLStorageMixin, StorageBackend):
    """
    本地存储后端

    使用 MySQL 数据库存储新闻数据，支持：
    - 统一 MySQL 数据库存储
    - 可选的 TXT 快照（用于调试）
    - HTML 报告生成
    """

    def __init__(
        self,
        data_dir: str = "output",
        enable_txt: bool = True,
        enable_html: bool = True,
        timezone: str = DEFAULT_TIMEZONE,
        mysql_config: Optional[Dict] = None,
    ):
        """
        初始化本地存储后端

        Args:
            data_dir: 数据目录路径（用于 TXT/HTML 快照）
            enable_txt: 是否启用 TXT 快照
            enable_html: 是否启用 HTML 报告
            timezone: 时区配置
            mysql_config: MySQL 连接配置
        """
        self.data_dir = Path(data_dir)
        self.enable_txt = enable_txt
        self.enable_html = enable_html
        self.timezone = timezone

        # MySQL 连接配置
        self.mysql_config = mysql_config or {
            "host": os.environ.get("MYSQL_HOST", "192.168.25.64"),
            "port": int(os.environ.get("MYSQL_PORT", "3306")),
            "user": os.environ.get("MYSQL_USER", "root"),
            "password": os.environ.get("MYSQL_PASSWORD", "wanggang"),
            "database": os.environ.get("MYSQL_DATABASE", "trendradar"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }

        self._connection: Optional[pymysql.Connection] = None

    @property
    def backend_name(self) -> str:
        return "local"

    @property
    def supports_txt(self) -> bool:
        return self.enable_txt

    # ========================================
    # MySQLStorageMixin 抽象方法实现
    # ========================================

    def _get_configured_time(self) -> datetime:
        """获取配置时区的当前时间"""
        return get_configured_time(self.timezone)

    def _format_date_folder(self, date: Optional[str] = None) -> str:
        """格式化日期文件夹名 (ISO 格式: YYYY-MM-DD)"""
        return format_date_folder(date, self.timezone)

    def _format_time_filename(self) -> str:
        """格式化时间文件名 (格式: HH-MM)"""
        return format_time_filename(self.timezone)

    def _get_connection(self) -> pymysql.Connection:
        """
        获取 MySQL 数据库连接（单例）

        Returns:
            MySQL 连接
        """
        if self._connection is None or not self._connection.open:
            try:
                self._connection = pymysql.connect(**self.mysql_config)
                # 初始化表结构
                self._init_tables(self._connection, "news")
                self._init_tables(self._connection, "rss")
            except Exception as e:
                print(f"[本地存储] MySQL 连接失败: {e}")
                raise

        return self._connection

    # ========================================
    # StorageBackend 接口实现（委托给 mixin）
    # ========================================

    def save_news_data(self, data: NewsData) -> bool:
        """保存新闻数据到 MySQL"""
        success, new_count, updated_count, title_changed_count, off_list_count = \
            self._save_news_data_impl(data, "[本地存储]")

        if success:
            # 输出详细的存储统计日志
            log_parts = [f"[本地存储] 处理完成：新增 {new_count} 条"]
            if updated_count > 0:
                log_parts.append(f"更新 {updated_count} 条")
            if title_changed_count > 0:
                log_parts.append(f"标题变更 {title_changed_count} 条")
            if off_list_count > 0:
                log_parts.append(f"脱榜 {off_list_count} 条")
            print("，".join(log_parts))

        return success

    def get_today_all_data(self, date: Optional[str] = None) -> Optional[NewsData]:
        """获取指定日期的所有新闻数据（合并后）"""
        return self._get_today_all_data_impl(date)

    def get_latest_crawl_data(self, date: Optional[str] = None) -> Optional[NewsData]:
        """获取最新一次抓取的数据"""
        return self._get_latest_crawl_data_impl(date)

    def detect_new_titles(self, current_data: NewsData) -> Dict[str, Dict]:
        """检测新增的标题"""
        return self._detect_new_titles_impl(current_data)

    def is_first_crawl_today(self, date: Optional[str] = None) -> bool:
        """检查是否是当天第一次抓取"""
        return self._is_first_crawl_today_impl(date)

    def get_crawl_times(self, date: Optional[str] = None) -> List[str]:
        """获取指定日期的所有抓取时间列表"""
        return self._get_crawl_times_impl(date)

    # ========================================
    # 时间段执行记录（调度系统）
    # ========================================

    def has_period_executed(self, date_str: str, period_key: str, action: str) -> bool:
        """检查指定时间段的某个 action 是否已执行"""
        return self._has_period_executed_impl(date_str, period_key, action)

    def record_period_execution(self, date_str: str, period_key: str, action: str) -> bool:
        """记录时间段的 action 执行"""
        success = self._record_period_execution_impl(date_str, period_key, action)
        if success:
            now_str = self._get_configured_time().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[本地存储] 时间段执行记录已保存: {period_key}/{action} at {now_str}")
        return success

    # ========================================
    # RSS 数据存储方法
    # ========================================

    def save_rss_data(self, data: RSSData) -> bool:
        """保存 RSS 数据到 MySQL"""
        success, new_count, updated_count = self._save_rss_data_impl(data, "[本地存储]")

        if success:
            # 输出统计日志
            log_parts = [f"[本地存储] RSS 处理完成：新增 {new_count} 条"]
            if updated_count > 0:
                log_parts.append(f"更新 {updated_count} 条")
            print("，".join(log_parts))

        return success

    def get_rss_data(self, date: Optional[str] = None) -> Optional[RSSData]:
        """获取指定日期的所有 RSS 数据"""
        return self._get_rss_data_impl(date)

    def detect_new_rss_items(self, current_data: RSSData) -> Dict[str, List[RSSItem]]:
        """检测新增的 RSS 条目"""
        return self._detect_new_rss_items_impl(current_data)

    def get_latest_rss_data(self, date: Optional[str] = None) -> Optional[RSSData]:
        """获取最新一次抓取的 RSS 数据"""
        return self._get_latest_rss_data_impl(date)

    # ========================================
    # AI 智能筛选
    # ========================================

    def get_active_ai_filter_tags(self, date=None, interests_file="ai_interests.txt"):
        return self._get_active_tags_impl(date, interests_file)

    def get_latest_prompt_hash(self, date=None, interests_file="ai_interests.txt"):
        return self._get_latest_prompt_hash_impl(date, interests_file)

    def get_latest_ai_filter_tag_version(self, date=None):
        return self._get_latest_tag_version_impl(date)

    def deprecate_all_ai_filter_tags(self, date=None, interests_file="ai_interests.txt"):
        return self._deprecate_all_tags_impl(date, interests_file)

    def save_ai_filter_tags(self, tags, version, prompt_hash, date=None, interests_file="ai_interests.txt"):
        return self._save_tags_impl(date, tags, version, prompt_hash, interests_file)

    def save_ai_filter_results(self, results, date=None):
        return self._save_filter_results_impl(date, results)

    def get_active_ai_filter_results(self, date=None, interests_file="ai_interests.txt"):
        return self._get_active_filter_results_impl(date, interests_file)

    def deprecate_specific_ai_filter_tags(self, tag_ids, date=None):
        return self._deprecate_specific_tags_impl(date, tag_ids)

    def update_ai_filter_tags_hash(self, interests_file, new_hash, date=None):
        return self._update_tags_hash_impl(date, interests_file, new_hash)

    def update_ai_filter_tag_descriptions(self, tag_updates, date=None, interests_file="ai_interests.txt"):
        return self._update_tag_descriptions_impl(date, tag_updates, interests_file)

    def update_ai_filter_tag_priorities(self, tag_priorities, date=None, interests_file="ai_interests.txt"):
        return self._update_tag_priorities_impl(date, tag_priorities, interests_file)

    def save_analyzed_news(self, news_ids, source_type, interests_file, prompt_hash, matched_ids, date=None):
        return self._save_analyzed_news_impl(date, news_ids, source_type, interests_file, prompt_hash, matched_ids)

    def get_analyzed_news_ids(self, source_type="hotlist", date=None, interests_file="ai_interests.txt"):
        return self._get_analyzed_news_ids_impl(date, source_type, interests_file)

    def clear_analyzed_news(self, date=None, interests_file="ai_interests.txt"):
        return self._clear_analyzed_news_impl(date, interests_file)

    def clear_unmatched_analyzed_news(self, date=None, interests_file="ai_interests.txt"):
        return self._clear_unmatched_analyzed_news_impl(date, interests_file)

    def get_all_news_ids(self, date=None):
        return self._get_all_news_ids_impl(date)

    def get_all_rss_ids(self, date=None):
        return self._get_all_rss_ids_impl(date)

    # ========================================
    # 本地特有功能：TXT/HTML 快照
    # ========================================

    def save_txt_snapshot(self, data: NewsData) -> Optional[str]:
        """保存 TXT 快照"""
        if not self.enable_txt:
            return None

        try:
            date_folder = self._format_date_folder(data.date)
            txt_dir = self.data_dir / "txt" / date_folder
            txt_dir.mkdir(parents=True, exist_ok=True)

            file_path = txt_dir / f"{data.crawl_time}.txt"

            with open(file_path, "w", encoding="utf-8") as f:
                for source_id, news_list in data.items.items():
                    source_name = data.id_to_name.get(source_id, source_id)

                    if source_name and source_name != source_id:
                        f.write(f"{source_id} | {source_name}\n")
                    else:
                        f.write(f"{source_id}\n")

                    sorted_news = sorted(news_list, key=lambda x: x.rank)

                    for item in sorted_news:
                        line = f"{item.rank}. {item.title}"
                        if item.url:
                            line += f" [URL:{item.url}]"
                        if item.mobile_url:
                            line += f" [MOBILE:{item.mobile_url}]"
                        f.write(line + "\n")

                    f.write("\n")

                if data.failed_ids:
                    f.write("==== 以下ID请求失败 ====\n")
                    for failed_id in data.failed_ids:
                        f.write(f"{failed_id}\n")

            print(f"[本地存储] TXT 快照已保存: {file_path}")
            return str(file_path)

        except Exception as e:
            print(f"[本地存储] 保存 TXT 快照失败: {e}")
            return None

    def save_html_report(self, html_content: str, filename: str) -> Optional[str]:
        """保存 HTML 报告"""
        if not self.enable_html:
            return None

        try:
            date_folder = self._format_date_folder()
            html_dir = self.data_dir / "html" / date_folder
            html_dir.mkdir(parents=True, exist_ok=True)

            file_path = html_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"[本地存储] HTML 报告已保存: {file_path}")
            return str(file_path)

        except Exception as e:
            print(f"[本地存储] 保存 HTML 报告失败: {e}")
            return None

    # ========================================
    # 本地特有功能：资源清理
    # ========================================

    def cleanup(self) -> None:
        """清理资源（关闭数据库连接）"""
        if self._connection and self._connection.open:
            try:
                self._connection.close()
                print("[本地存储] MySQL 连接已关闭")
            except Exception as e:
                print(f"[本地存储] 关闭连接失败: {e}")

        self._connection = None

    def cleanup_old_data(self, retention_days: int) -> int:
        """
        清理过期数据

        MySQL 模式下清理数据库中的旧日期数据，以及本地的 TXT/HTML 快照

        Args:
            retention_days: 保留天数（0 表示不清理）

        Returns:
            删除的记录/文件数量
        """
        if retention_days <= 0:
            return 0

        deleted_count = 0
        cutoff_date = self._get_configured_time() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        try:
            # 清理 MySQL 中的旧数据
            conn = self._get_connection()
            cursor = conn.cursor()

            # 删除旧日期的新闻相关数据
            cursor.execute("DELETE FROM news_items WHERE date < %s", (cutoff_str,))
            deleted_count += cursor.rowcount

            cursor.execute("DELETE FROM crawl_records WHERE date < %s", (cutoff_str,))
            deleted_count += cursor.rowcount

            cursor.execute("DELETE FROM period_executions WHERE execution_date < %s", (cutoff_str,))
            deleted_count += cursor.rowcount

            # RSS 数据
            cursor.execute("DELETE FROM rss_items WHERE date < %s", (cutoff_str,))
            deleted_count += cursor.rowcount

            cursor.execute("DELETE FROM rss_crawl_records WHERE date < %s", (cutoff_str,))
            deleted_count += cursor.rowcount

            cursor.execute("DELETE FROM rss_push_records WHERE date < %s", (cutoff_str,))
            deleted_count += cursor.rowcount

            conn.commit()

            if deleted_count > 0:
                print(f"[本地存储] MySQL 清理了 {deleted_count} 条过期记录")

            # 清理本地快照目录 (txt/, html/)
            def parse_date_from_name(name: str) -> Optional[datetime]:
                name = name.replace('.db', '')
                try:
                    date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', name)
                    if date_match:
                        return datetime(
                            int(date_match.group(1)),
                            int(date_match.group(2)),
                            int(date_match.group(3)),
                            tzinfo=pytz.timezone(self.timezone)
                        )
                except Exception:
                    pass
                return None

            if not self.data_dir.exists():
                return deleted_count

            for snapshot_type in ["txt", "html"]:
                snapshot_dir = self.data_dir / snapshot_type
                if not snapshot_dir.exists():
                    continue

                for date_folder in snapshot_dir.iterdir():
                    if not date_folder.is_dir() or date_folder.name.startswith('.'):
                        continue

                    folder_date = parse_date_from_name(date_folder.name)
                    if folder_date and folder_date < cutoff_date:
                        try:
                            shutil.rmtree(date_folder)
                            deleted_count += 1
                            print(f"[本地存储] 清理过期数据: {snapshot_type}/{date_folder.name}")
                        except Exception as e:
                            print(f"[本地存储] 删除目录失败 {date_folder}: {e}")

            if deleted_count > 0:
                print(f"[本地存储] 共清理 {deleted_count} 个过期记录/文件/目录")

            return deleted_count

        except Exception as e:
            print(f"[本地存储] 清理过期数据失败: {e}")
            return deleted_count

    def __del__(self):
        """析构函数，确保关闭连接"""
        self.cleanup()
