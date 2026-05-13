from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class TaskTriggerRequest(BaseModel):
    platform_ids: list[str] | None = None
    include_rss: bool = True


class TaskInfo(BaseModel):
    task: str
    task_id: str


class TaskTriggerResponse(BaseModel):
    status: str
    tasks: list[TaskInfo]


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None


class TaskLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class TaskLogResponse(BaseModel):
    id: int
    task_name: str
    task_id: str
    status: str
    progress: int
    current_step: str | None = None
    logs: list[TaskLogEntry] = []
    result: Any | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    duration_seconds: float | None = None

    model_config = {"from_attributes": True}


class TaskLogListResponse(BaseModel):
    total: int
    logs: list[TaskLogResponse]


class RunningTaskResponse(BaseModel):
    task_id: str
    task_name: str
    status: str
    progress: int
    current_step: str | None = None
    started_at: datetime | None = None
    elapsed_seconds: float | None = None


class ScheduleResponse(BaseModel):
    enabled: bool
    preset: str
    entries: list[str]


class SchedulePeriodInfo(BaseModel):
    key: str
    name: str
    start: str
    end: str
    actions: list[str]
    report_mode: str
    day: int | None = None


class ScheduleDetailResponse(BaseModel):
    enabled: bool
    preset: str
    preset_name: str = ""
    description: str = ""
    periods: list[SchedulePeriodInfo] = []
    message: str = ""


class AIReportResponse(BaseModel):
    id: int
    task_id: str | None = None
    core_trends: str = ""
    sentiment_controversy: str = ""
    signals: str = ""
    rss_insights: str = ""
    outlook_strategy: str = ""
    standalone_summaries: dict | None = None
    success: bool = False
    error: str | None = None
    method: str = "ai"
    total_news: int = 0
    analyzed_news: int = 0
    hotlist_count: int = 0
    rss_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class AIReportListResponse(BaseModel):
    total: int
    reports: list[AIReportResponse]
