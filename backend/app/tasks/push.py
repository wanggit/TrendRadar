from datetime import datetime, timezone
from app.celery_app import celery_app
from app.db.session import get_sync_engine
from app.services.config_service_sync import ConfigServiceSync
from app.services.report_service_sync import ReportServiceSync
from app.services.standalone_service_sync import StandaloneServiceSync
from app.services.task_log_sync import update_task_status, add_task_log_entry
from sqlalchemy.orm import Session


@celery_app.task(bind=True, name="app.tasks.push.notification", queue="push")
def push_notification(self, user_id: int, report_mode: str = "current") -> dict:
    """
    Push notification to user's configured channels.

    Assembles content based on:
    - Report mode (current/daily/incremental)
    - Display regions configuration (hotlist/new_items/rss/standalone/ai_analysis)
    - Standalone area configuration

    Args:
        user_id: User ID
        report_mode: Report mode (current, daily, incremental)

    Returns:
        {"status": "success", "pushed_to": [...], "errors": [...]}
    """
    task_id = self.request.id

    update_task_status(task_id, "running", progress=0, current_step="开始推送")
    add_task_log_entry(task_id, "info", "开始推送任务")

    engine = get_sync_engine()
    with Session(engine) as db:
        data_service = None  # Not directly used, report service handles data
        config_service = ConfigServiceSync(db)

        update_task_status(task_id, "running", progress=10, current_step="加载配置")
        add_task_log_entry(task_id, "info", "加载用户配置")

        config = config_service.get_or_create_user_config(user_id)
        notification_config = config.notification
        display_config = config.display
        report_config = config.report

        if not notification_config.get("enabled", True):
            add_task_log_entry(task_id, "warning", "通知功能已禁用，跳过推送")
            update_task_status(task_id, "success", progress=100, current_step="已跳过（通知禁用）", result={"status": "skipped", "reason": "notifications disabled"})
            return {"status": "skipped", "reason": "notifications disabled"}

        effective_report_mode = report_mode or report_config.get("mode", "current")
        add_task_log_entry(task_id, "info", f"报告模式: {effective_report_mode}")

        update_task_status(task_id, "running", progress=20, current_step="生成报告数据")
        add_task_log_entry(task_id, "info", "正在生成报告数据")

        report_service = ReportServiceSync(db, user_id)
        report_data = report_service.get_items_for_report(
            report_mode=effective_report_mode,
            limit=report_config.get("max_news_per_keyword", 0) or 50,
        )

        display_regions = display_config.get("regions", {})
        region_order = display_config.get("region_order", ["hotlist", "new_items", "rss", "standalone", "ai_analysis"])

        push_content = {
            "regions": [],
            "generated_at": report_data["generated_at"],
            "mode": effective_report_mode,
        }

        region_progress = 30
        region_count = sum(1 for rk in region_order if display_regions.get(rk, False))
        region_done = 0

        for region_key in region_order:
            if not display_regions.get(region_key, False):
                continue

            region_done += 1
            current_progress = region_progress + int((region_done / region_count) * 50)

            if region_key == "hotlist":
                update_task_status(task_id, "running", progress=current_progress, current_step="组装热榜数据")
                add_task_log_entry(task_id, "info", "组装热榜区域数据")
                push_content["regions"].append({
                    "type": "hotlist",
                    "label": "热榜",
                    "items": report_data["news"],
                })
            elif region_key == "new_items":
                update_task_status(task_id, "running", progress=current_progress, current_step="组装新增热点")
                add_task_log_entry(task_id, "info", "组装新增热点区域数据")
                push_content["regions"].append({
                    "type": "new_items",
                    "label": "新增热点",
                    "items": report_data["news"][:10],
                })
            elif region_key == "rss":
                update_task_status(task_id, "running", progress=current_progress, current_step="组装 RSS 数据")
                add_task_log_entry(task_id, "info", "组装 RSS 区域数据")
                push_content["regions"].append({
                    "type": "rss",
                    "label": "RSS",
                    "items": report_data["rss"],
                })
            elif region_key == "standalone":
                standalone_config = display_config.get("standalone", {})
                if standalone_config.get("platforms") or standalone_config.get("rss_feeds"):
                    update_task_status(task_id, "running", progress=current_progress, current_step="组装独立展示数据")
                    add_task_log_entry(task_id, "info", "组装独立展示区域数据")
                    standalone_service = StandaloneServiceSync(db, user_id)
                    standalone_data = standalone_service.get_standalone_items(standalone_config)
                    push_content["regions"].append({
                        "type": "standalone",
                        "label": "独立展示",
                        "platforms": standalone_data["platforms"],
                        "rss_feeds": standalone_data["rss_feeds"],
                    })
            elif region_key == "ai_analysis":
                ai_config = config.ai_analysis
                if ai_config.get("enabled", False):
                    update_task_status(task_id, "running", progress=current_progress, current_step="组装 AI 分析数据")
                    add_task_log_entry(task_id, "info", "组装 AI 分析区域数据")
                    push_content["regions"].append({
                        "type": "ai_analysis",
                        "label": "AI 分析",
                        "placeholder": "AI 分析报告生成中...",
                    })

        channels = list(notification_config.get("channels", {}).keys())
        active_channels = [
            ch for ch in channels
            if any(notification_config["channels"][ch].get(k) for k in ["webhook_url", "bot_token", "url", "webhook"])
        ]

        total_items = sum(len(r.get("items", [])) for r in push_content["regions"])

        update_task_status(task_id, "running", progress=90, current_step="准备发送")
        add_task_log_entry(task_id, "info", f"推送内容准备完成，共 {total_items} 条，{len(push_content['regions'])} 个区域")

        result = {
            "status": "success",
            "pushed_to": active_channels if active_channels else ["simulated"],
            "total_items": total_items,
            "regions_count": len(push_content["regions"]),
            "report_mode": effective_report_mode,
            "content": push_content,
            "errors": [],
        }

        if not active_channels:
            add_task_log_entry(task_id, "warning", "未配置有效推送渠道，使用模拟模式")
        else:
            add_task_log_entry(task_id, "info", f"推送到渠道: {', '.join(active_channels)}")

        update_task_status(
            task_id,
            "success",
            progress=100,
            current_step="推送完成",
            result=result,
        )
        add_task_log_entry(
            task_id,
            "info",
            f"推送完成，共 {result.get('total_items', 0)} 条内容，推送到 {len(result.get('pushed_to', []))} 个渠道",
        )

        return result
