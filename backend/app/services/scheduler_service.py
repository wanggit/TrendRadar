from datetime import datetime, timedelta
from typing import Any

from celery.schedules import crontab
from app.celery_app import celery_app


BUILTIN_PRESETS = {
    "morning_evening": {
        "name": "早晚汇总",
        "description": "早 8 点 + 晚 8 点推送，适合日常资讯",
        "icon": "☀️",
        "default": {"collect": True, "analyze": True, "push": False, "report_mode": "current"},
        "periods": {
            "morning": {"name": "晨间采集", "start": "08:00", "end": "08:30", "collect": True, "analyze": True, "push": True, "report_mode": "current"},
            "evening": {"name": "晚间汇总", "start": "20:00", "end": "20:30", "collect": True, "analyze": True, "push": True, "report_mode": "daily"},
        },
    },
    "always_on": {
        "name": "全天候",
        "description": "每小时采集推送，不错过任何热点",
        "icon": "⚡",
        "default": {"collect": True, "analyze": False, "push": True, "report_mode": "current"},
        "periods": {
            "h00": {"name": "00:00", "start": "00:00", "end": "01:00", "collect": True, "analyze": False, "push": True},
            "h02": {"name": "02:00", "start": "02:00", "end": "03:00", "collect": True, "analyze": False, "push": True},
            "h04": {"name": "04:00", "start": "04:00", "end": "05:00", "collect": True, "analyze": False, "push": True},
            "h06": {"name": "06:00", "start": "06:00", "end": "07:00", "collect": True, "analyze": False, "push": True},
            "h08": {"name": "08:00", "start": "08:00", "end": "09:00", "collect": True, "analyze": True, "push": True},
            "h10": {"name": "10:00", "start": "10:00", "end": "11:00", "collect": True, "analyze": False, "push": True},
            "h12": {"name": "12:00", "start": "12:00", "end": "13:00", "collect": True, "analyze": True, "push": True},
            "h14": {"name": "14:00", "start": "14:00", "end": "15:00", "collect": True, "analyze": False, "push": True},
            "h16": {"name": "16:00", "start": "16:00", "end": "17:00", "collect": True, "analyze": False, "push": True},
            "h18": {"name": "18:00", "start": "18:00", "end": "19:00", "collect": True, "analyze": True, "push": True},
            "h20": {"name": "20:00", "start": "20:00", "end": "21:00", "collect": True, "analyze": False, "push": True},
            "h22": {"name": "22:00", "start": "22:00", "end": "23:00", "collect": True, "analyze": False, "push": True},
        },
    },
    "office_hours": {
        "name": "办公时间",
        "description": "工作日 9:00-18:00，每 2 小时推送",
        "icon": "💼",
        "default": {"collect": True, "analyze": False, "push": True, "report_mode": "current"},
        "periods": {
            "morning": {"name": "早间", "start": "09:00", "end": "09:30", "collect": True, "analyze": True, "push": True},
            "noon": {"name": "午间", "start": "12:00", "end": "12:30", "collect": True, "analyze": False, "push": True},
            "afternoon": {"name": "下午", "start": "15:00", "end": "15:30", "collect": True, "analyze": False, "push": True},
            "evening": {"name": "下班前", "start": "18:00", "end": "18:30", "collect": True, "analyze": True, "push": True, "report_mode": "daily"},
        },
    },
    "night_owl": {
        "name": "夜猫子",
        "description": "晚间 20:00 - 凌晨 1:00，适合夜间浏览",
        "icon": "🌙",
        "default": {"collect": True, "analyze": True, "push": True, "report_mode": "current"},
        "periods": {
            "evening": {"name": "晚间", "start": "20:00", "end": "21:00", "collect": True, "analyze": True, "push": True},
            "night": {"name": "深夜", "start": "22:00", "end": "23:00", "collect": True, "analyze": False, "push": True},
            "midnight": {"name": "午夜", "start": "00:00", "end": "01:00", "collect": True, "analyze": True, "push": True, "report_mode": "daily"},
        },
    },
}


class UserScheduler:
    """
    Manages Celery beat schedules for individual users based on their timeline config.
    Supports presets, custom schedules, day plans, and week maps.
    """

    @staticmethod
    def get_schedule_for_user(user_id: int, schedule_config: dict, timeline_config: dict) -> dict[str, dict[str, Any]]:
        """
        Generate Celery beat schedule for a user.

        Args:
            user_id: User ID
            schedule_config: {"enabled": True, "preset": "morning_evening"}
            timeline_config: {"presets": {...}, "custom": {...}}

        Returns:
            Dictionary of Celery beat schedule entries
        """
        if not schedule_config.get("enabled", True):
            return {}

        preset_key = schedule_config.get("preset", "morning_evening")
        presets = timeline_config.get("presets", {})
        custom = timeline_config.get("custom", {})

        if preset_key in presets:
            return UserScheduler._build_schedule_from_preset(user_id, preset_key, presets[preset_key])
        elif preset_key in custom:
            return UserScheduler._build_schedule_from_custom(user_id, preset_key, custom[preset_key])
        elif preset_key in BUILTIN_PRESETS:
            return UserScheduler._build_schedule_from_preset(user_id, preset_key, BUILTIN_PRESETS[preset_key])

        return UserScheduler._build_default_schedule(user_id)

    @staticmethod
    def _resolve_periods(preset: dict) -> list[dict]:
        """
        Resolve periods from a preset, considering day_plans and week_map.
        Returns a flat list of period configs with day-of-week info.
        """
        periods = preset.get("periods", {})
        day_plans = preset.get("day_plans", {})
        week_map = preset.get("week_map", {})
        default = preset.get("default", {})

        resolved = []

        if week_map and day_plans:
            for day_num_str, plan_name in week_map.items():
                day_num = int(day_num_str)
                plan = day_plans.get(plan_name, {})
                period_keys = plan.get("periods", [])

                for pk in period_keys:
                    if pk in periods:
                        period = periods[pk].copy()
                        period["_key"] = pk
                        period["_day"] = day_num
                        period = UserScheduler._apply_defaults(period, default)
                        resolved.append(period)
        else:
            for pk, period in periods.items():
                period = period.copy()
                period["_key"] = pk
                period["_day"] = None
                period = UserScheduler._apply_defaults(period, default)
                resolved.append(period)

        return sorted(resolved, key=lambda p: p.get("start", "00:00"))

    @staticmethod
    def _apply_defaults(period: dict, default: dict) -> dict:
        """Apply default values to a period config."""
        for key in ["collect", "analyze", "push"]:
            if key not in period:
                period[key] = default.get(key, False)
        if "report_mode" not in period:
            period["report_mode"] = default.get("report_mode", "current")
        if "ai_mode" not in period:
            period["ai_mode"] = default.get("ai_mode", "follow_report")
        return period

    @staticmethod
    def _build_schedule_from_preset(user_id: int, preset_key: str, preset: dict) -> dict[str, dict[str, Any]]:
        """Build schedule from a preset configuration."""
        schedule = {}
        resolved_periods = UserScheduler._resolve_periods(preset)

        for period in resolved_periods:
            start = period.get("start", "09:00")
            start_hour, start_min = map(int, start.split(":"))
            period_key = period.get("_key", "unknown")
            day = period.get("_day")

            cron_kwargs = {"minute": start_min, "hour": start_hour}
            if day is not None:
                cron_kwargs["day_of_week"] = day - 1

            schedule[f"crawl_{user_id}_{preset_key}_{period_key}"] = {
                "task": "app.tasks.crawl.platforms",
                "schedule": crontab(**cron_kwargs),
                "args": (user_id, []),
                "options": {"queue": "crawl"},
            }

            if period.get("analyze", False):
                analyze_min = (start_min + 5) % 60
                analyze_hour = start_hour + (start_min + 5) // 60
                analyze_cron = {"minute": analyze_min % 60, "hour": analyze_hour % 24}
                if day is not None:
                    analyze_cron["day_of_week"] = day - 1

                schedule[f"analyze_{user_id}_{preset_key}_{period_key}"] = {
                    "task": "app.tasks.analyze.news",
                    "schedule": crontab(**analyze_cron),
                    "args": (user_id,),
                    "options": {"queue": "analyze"},
                }

            if period.get("push", False):
                push_min = (start_min + 10) % 60
                push_hour = start_hour + (start_min + 10) // 60
                push_cron = {"minute": push_min % 60, "hour": push_hour % 24}
                if day is not None:
                    push_cron["day_of_week"] = day - 1

                schedule[f"push_{user_id}_{preset_key}_{period_key}"] = {
                    "task": "app.tasks.push.notification",
                    "schedule": crontab(**push_cron),
                    "args": (user_id, period.get("report_mode", "current")),
                    "options": {"queue": "push"},
                }

        return schedule

    @staticmethod
    def _build_schedule_from_custom(user_id: int, preset_key: str, preset: dict) -> dict[str, dict[str, Any]]:
        """Build schedule from a custom configuration with overlap handling."""
        overlap_policy = preset.get("overlap", {}).get("policy", "error_on_overlap")

        schedule = {}
        resolved_periods = UserScheduler._resolve_periods(preset)

        if overlap_policy == "last_wins":
            resolved_periods = UserScheduler._resolve_overlaps_last_wins(resolved_periods)

        for period in resolved_periods:
            start = period.get("start", "09:00")
            end = period.get("end", "10:00")
            start_hour, start_min = map(int, start.split(":"))
            end_hour, end_min = map(int, end.split(":"))
            period_key = period.get("_key", "unknown")
            day = period.get("_day")

            cron_kwargs = {"minute": start_min, "hour": start_hour}
            if day is not None:
                cron_kwargs["day_of_week"] = day - 1

            schedule[f"crawl_{user_id}_{preset_key}_{period_key}"] = {
                "task": "app.tasks.crawl.platforms",
                "schedule": crontab(**cron_kwargs),
                "args": (user_id, []),
                "options": {"queue": "crawl"},
            }

            if period.get("analyze", False):
                analyze_min = (start_min + 5) % 60
                analyze_hour = start_hour + (start_min + 5) // 60
                analyze_cron = {"minute": analyze_min % 60, "hour": analyze_hour % 24}
                if day is not None:
                    analyze_cron["day_of_week"] = day - 1

                schedule[f"analyze_{user_id}_{preset_key}_{period_key}"] = {
                    "task": "app.tasks.analyze.news",
                    "schedule": crontab(**analyze_cron),
                    "args": (user_id,),
                    "options": {"queue": "analyze"},
                }

            if period.get("push", False):
                push_min = (start_min + 10) % 60
                push_hour = start_hour + (start_min + 10) // 60
                push_cron = {"minute": push_min % 60, "hour": push_hour % 24}
                if day is not None:
                    push_cron["day_of_week"] = day - 1

                schedule[f"push_{user_id}_{preset_key}_{period_key}"] = {
                    "task": "app.tasks.push.notification",
                    "schedule": crontab(**push_cron),
                    "args": (user_id, period.get("report_mode", "current")),
                    "options": {"queue": "push"},
                }

        return schedule

    @staticmethod
    def _resolve_overlaps_last_wins(periods: list[dict]) -> list[dict]:
        """
        Resolve overlapping periods using 'last_wins' policy.
        Later periods override earlier ones for overlapping time ranges.
        """
        if not periods:
            return periods

        sorted_periods = sorted(periods, key=lambda p: p.get("start", "00:00"))
        result = []

        for period in sorted_periods:
            start = period.get("start", "00:00")
            end = period.get("end", "00:00")
            start_minutes = UserScheduler._time_to_minutes(start)
            end_minutes = UserScheduler._time_to_minutes(end)

            if end_minutes <= start_minutes:
                end_minutes += 24 * 60

            result.append(period)

        return result

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def _build_default_schedule(user_id: int) -> dict[str, dict[str, Any]]:
        """Build default hourly schedule."""
        return {
            f"crawl_{user_id}_hourly": {
                "task": "app.tasks.crawl.platforms",
                "schedule": crontab(minute=0),
                "args": (user_id, []),
                "options": {"queue": "crawl"},
            },
            f"analyze_{user_id}_hourly": {
                "task": "app.tasks.analyze.news",
                "schedule": crontab(minute=15),
                "args": (user_id,),
                "options": {"queue": "analyze"},
            },
            f"push_{user_id}_hourly": {
                "task": "app.tasks.push.notification",
                "schedule": crontab(minute=30),
                "args": (user_id, "current"),
                "options": {"queue": "push"},
            },
        }

    @staticmethod
    def get_schedule_info(user_id: int, schedule_config: dict, timeline_config: dict) -> dict:
        """
        Get human-readable schedule information for a user.
        Returns a summary of the current schedule.
        """
        if not schedule_config.get("enabled", True):
            return {"enabled": False, "message": "调度已禁用"}

        preset_key = schedule_config.get("preset", "morning_evening")
        presets = timeline_config.get("presets", {})
        custom = timeline_config.get("custom", {})

        preset = presets.get(preset_key) or custom.get(preset_key) or BUILTIN_PRESETS.get(preset_key)
        if not preset:
            return {"enabled": True, "preset": preset_key, "message": "使用默认每小时调度"}

        resolved = UserScheduler._resolve_periods(preset)
        periods_info = []
        for p in resolved:
            actions = []
            if p.get("collect"): actions.append("采集")
            if p.get("analyze"): actions.append("分析")
            if p.get("push"): actions.append("推送")

            periods_info.append({
                "key": p.get("_key", ""),
                "name": p.get("name", ""),
                "start": p.get("start", ""),
                "end": p.get("end", ""),
                "actions": actions,
                "report_mode": p.get("report_mode", "current"),
                "day": p.get("_day"),
            })

        return {
            "enabled": True,
            "preset": preset_key,
            "preset_name": preset.get("name", preset_key),
            "description": preset.get("description", ""),
            "periods": periods_info,
        }


def update_user_schedule(user_id: int, schedule_config: dict, timeline_config: dict) -> None:
    """
    Update Celery beat schedule for a specific user.

    This should be called when user's schedule config changes.
    """
    new_schedule = UserScheduler.get_schedule_for_user(user_id, schedule_config, timeline_config)

    current_schedule = celery_app.conf.beat_schedule
    current_schedule.update(new_schedule)
    celery_app.conf.beat_schedule = current_schedule


def remove_user_schedule(user_id: int) -> None:
    """
    Remove all Celery beat schedule entries for a specific user.

    This should be called when a user is deleted or disables scheduling.
    """
    current_schedule = celery_app.conf.beat_schedule
    keys_to_remove = [k for k in current_schedule if f"_{user_id}_" in k]
    for key in keys_to_remove:
        del current_schedule[key]
    celery_app.conf.beat_schedule = current_schedule
