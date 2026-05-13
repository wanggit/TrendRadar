from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import json
import io

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, UserTier
from app.services.config_service import ConfigService
from app.schemas.config import (
    FullUserConfig,
    ConfigUpdateRequest,
    RuntimeConfig,
    SystemAIConfig,
)
from app.core.constants import TIER_LIMITS

router = APIRouter(prefix="/config", tags=["configuration"])


def _check_tier_limit(user: User, limit_key: str, current_count: int):
    limits = TIER_LIMITS.get(user.tier, TIER_LIMITS[UserTier.FREE])
    max_val = limits.get(limit_key, -1)
    if max_val > 0 and current_count >= max_val:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{user.tier.value} 用户最多 {max_val} 个",
        )


@router.get("/", response_model=FullUserConfig)
async def get_full_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    full_config = service.to_full_config(config)
    
    # 填充 AI 提示词内容
    prompts = await service.get_ai_prompts(current_user.id)
    if full_config.ai_filter:
        for key, value in prompts.items():
            if key != "analysis_prompt" and value and hasattr(full_config.ai_filter, key):
                setattr(full_config.ai_filter, key, value)
    if full_config.ai_analysis and prompts.get("analysis_prompt"):
        full_config.ai_analysis.prompt_content = prompts["analysis_prompt"]

    return full_config


@router.put("/", response_model=FullUserConfig)
async def update_full_config(
    update_data: ConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    config = await service.update_user_config(current_user.id, update_data)

    # 保存 AI 提示词内容（只保存用户显式设置的字段）
    if update_data.ai_filter:
        # 获取用户显式设置的字段
        ai_filter_dict = update_data.ai_filter.model_dump(exclude_unset=True)
        prompt_fields = ["interests_content", "classify_prompt", "extract_prompt", "update_tags_prompt"]
        prompts_to_save = {}
        for field in prompt_fields:
            if field in ai_filter_dict:
                value = ai_filter_dict[field]
                if value is not None:
                    prompts_to_save[field] = value
        if prompts_to_save:
            await service.set_ai_prompts(current_user.id, prompts_to_save)

    # 保存 AI 分析提示词内容
    if update_data.ai_analysis:
        ai_analysis_dict = update_data.ai_analysis.model_dump(exclude_unset=True)
        if "prompt_content" in ai_analysis_dict and ai_analysis_dict["prompt_content"] is not None:
            await service.set_ai_prompt(current_user.id, "analysis", ai_analysis_dict["prompt_content"])

    full_config = service.to_full_config(config)

    # 填充 AI 提示词内容
    prompts = await service.get_ai_prompts(current_user.id)
    if full_config.ai_filter:
        for key, value in prompts.items():
            if key != "analysis_prompt" and value and hasattr(full_config.ai_filter, key):
                setattr(full_config.ai_filter, key, value)
    if full_config.ai_analysis and prompts.get("analysis_prompt"):
        full_config.ai_analysis.prompt_content = prompts["analysis_prompt"]
    
    return full_config


@router.get("/runtime", response_model=RuntimeConfig)
async def get_runtime_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    return await service.get_runtime_config(current_user.id)


@router.get("/ai-system", response_model=SystemAIConfig)
async def get_system_ai_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    return await service.get_system_ai_config()


@router.get("/platforms")
async def get_platforms_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    return config.platforms


@router.put("/platforms")
async def update_platforms_config(
    platforms: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limits = TIER_LIMITS.get(current_user.tier, TIER_LIMITS[UserTier.FREE])
    max_platforms = limits.get("max_platforms", -1)
    if max_platforms > 0:
        enabled_count = sum(1 for p in platforms.values() if isinstance(p, dict) and p.get("enabled", True))
        if enabled_count > max_platforms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{current_user.tier.value} 用户最多 {max_platforms} 个平台",
            )

    service = ConfigService(db)
    update_data = ConfigUpdateRequest(platforms=platforms)
    config = await service.update_user_config(current_user.id, update_data)
    return config.platforms


@router.get("/rss")
async def get_rss_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    return config.rss


@router.put("/rss")
async def update_rss_config(
    rss: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    update_data = ConfigUpdateRequest(rss=rss)
    config = await service.update_user_config(current_user.id, update_data)
    return config.rss


@router.get("/schedule")
async def get_schedule_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    return config.schedule


@router.put("/schedule")
async def update_schedule_config(
    schedule: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    update_data = ConfigUpdateRequest(schedule=schedule)
    config = await service.update_user_config(current_user.id, update_data)
    return config.schedule


@router.get("/notification")
async def get_notification_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    return config.notification


@router.put("/notification")
async def update_notification_config(
    notification: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    limits = TIER_LIMITS.get(current_user.tier, TIER_LIMITS[UserTier.FREE])
    max_channels = limits.get("max_notification_channels", -1)
    if max_channels > 0:
        channels = notification.get("channels", {})
        enabled_count = sum(1 for ch in channels.values() if isinstance(ch, dict) and ch.get("enabled", False))
        if enabled_count > max_channels:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{current_user.tier.value} 用户最多 {max_channels} 个推送渠道",
            )

    service = ConfigService(db)
    update_data = ConfigUpdateRequest(notification=notification)
    config = await service.update_user_config(current_user.id, update_data)
    return config.notification


@router.get("/frequency-words")
async def get_frequency_words(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    return {"frequency_words": config.frequency_words}


@router.put("/frequency-words")
async def update_frequency_words(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConfigService(db)
    update_data = ConfigUpdateRequest(frequency_words=data.get("frequency_words", ""))
    config = await service.update_user_config(current_user.id, update_data)
    return {"frequency_words": config.frequency_words}


@router.get("/export")
async def export_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export full user config as JSON/YAML file."""
    from fastapi.responses import JSONResponse

    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    full_config = service.to_full_config(config)

    return JSONResponse(
        content=full_config.model_dump(),
        headers={
            "Content-Disposition": f"attachment; filename=trendradar-config-user{current_user.id}.json"
        },
    )


@router.post("/import")
async def import_config(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import config from uploaded JSON file."""
    content = await file.read()
    try:
        config_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    service = ConfigService(db)

    update_fields = {}
    valid_fields = [
        "timezone", "platforms", "rss", "report", "filter_strategy",
        "ai_filter", "display", "notification", "schedule", "timeline",
        "frequency_words", "ai_analysis", "ai_translation", "storage", "advanced",
    ]

    for field in valid_fields:
        if field in config_data:
            update_fields[field] = config_data[field]

    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid config fields found")

    update_data = ConfigUpdateRequest(**update_fields)
    config = await service.update_user_config(current_user.id, update_data)
    return service.to_full_config(config)


@router.get("/diff")
async def get_config_diff(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get config diff between current and default values."""
    service = ConfigService(db)
    config = await service.get_or_create_user_config(current_user.id)
    current = service.to_full_config(config)

    defaults = FullUserConfig()
    current_dict = current.model_dump()
    default_dict = defaults.model_dump()

    diff = {"modified": {}, "unchanged": []}

    for key in current_dict:
        if current_dict[key] != default_dict[key]:
            diff["modified"][key] = {
                "current": current_dict[key],
                "default": default_dict[key],
            }
        else:
            diff["unchanged"].append(key)

    return diff
