from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_config import UserConfig
from app.models.system_config import SystemConfig
from app.models.ai_prompt import AIPrompt
from app.schemas.config import (
    FullUserConfig,
    ConfigUpdateRequest,
    PlatformSource,
    PlatformsConfig,
    RSSConfig,
    ReportConfig,
    FilterStrategy,
    AIFilterConfig,
    DisplayConfig,
    NotificationConfig,
    ScheduleConfig,
    TimelineConfig,
    AIAnalysisConfig,
    AITranslationConfig,
    StorageConfig,
    AdvancedConfig,
    SystemAIConfig,
    RuntimeConfig,
)


class ConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_config(self, user_id: int) -> UserConfig | None:
        result = await self.db.execute(select(UserConfig).where(UserConfig.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create_user_config(self, user_id: int) -> UserConfig:
        config = await self.get_user_config(user_id)
        if config:
            return config
        config = UserConfig(user_id=user_id)
        self.db.add(config)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            config = await self.get_user_config(user_id)
            if config:
                return config
            raise
        await self.db.refresh(config)
        return config

    async def get_ai_prompt(self, user_id: int, prompt_type: str) -> str:
        result = await self.db.execute(
            select(AIPrompt).where(AIPrompt.user_id == user_id, AIPrompt.prompt_type == prompt_type)
        )
        prompt = result.scalar_one_or_none()
        return prompt.content if prompt else ""

    async def set_ai_prompt(self, user_id: int, prompt_type: str, content: str) -> AIPrompt:
        result = await self.db.execute(
            select(AIPrompt).where(AIPrompt.user_id == user_id, AIPrompt.prompt_type == prompt_type)
        )
        prompt = result.scalar_one_or_none()
        if prompt:
            prompt.content = content
        else:
            prompt = AIPrompt(user_id=user_id, prompt_type=prompt_type, content=content)
            self.db.add(prompt)
        await self.db.flush()
        await self.db.refresh(prompt)
        return prompt

    async def update_user_config(self, user_id: int, update_data: ConfigUpdateRequest) -> UserConfig:
        config = await self.get_or_create_user_config(user_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(config, key):
                if isinstance(value, dict):
                    setattr(config, key, value)
                else:
                    setattr(config, key, value)

        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def get_ai_prompts(self, user_id: int) -> dict:
        return {
            "interests_content": await self.get_ai_prompt(user_id, "interests"),
            "classify_prompt": await self.get_ai_prompt(user_id, "classify"),
            "extract_prompt": await self.get_ai_prompt(user_id, "extract"),
            "update_tags_prompt": await self.get_ai_prompt(user_id, "update_tags"),
            "analysis_prompt": await self.get_ai_prompt(user_id, "analysis"),
        }

    async def set_ai_prompts(self, user_id: int, prompts: dict) -> None:
        # Map schema field names to prompt types
        field_to_type = {
            "interests_content": "interests",
            "classify_prompt": "classify",
            "extract_prompt": "extract",
            "update_tags_prompt": "update_tags",
            "prompt_content": "analysis",
        }
        for field_name, content in prompts.items():
            if content is not None and field_name in field_to_type:
                prompt_type = field_to_type[field_name]
                await self.set_ai_prompt(user_id, prompt_type, content)

    def to_full_config(self, config: UserConfig) -> FullUserConfig:
        return FullUserConfig(
            timezone=config.timezone,
            platforms=PlatformsConfig(**config.platforms) if config.platforms else PlatformsConfig(),
            rss=RSSConfig(**config.rss) if config.rss else RSSConfig(),
            report=ReportConfig(**config.report) if config.report else ReportConfig(),
            filter_strategy=FilterStrategy(**config.filter_strategy) if config.filter_strategy else FilterStrategy(),
            ai_filter=AIFilterConfig(**config.ai_filter) if config.ai_filter else AIFilterConfig(),
            display=DisplayConfig(**config.display) if config.display else DisplayConfig(),
            notification=NotificationConfig(**config.notification) if config.notification else NotificationConfig(),
            schedule=ScheduleConfig(**config.schedule) if config.schedule else ScheduleConfig(),
            timeline=TimelineConfig(**config.timeline) if config.timeline else TimelineConfig(),
            frequency_words=config.frequency_words or "",
            ai_analysis=AIAnalysisConfig(**config.ai_analysis) if config.ai_analysis else AIAnalysisConfig(),
            ai_translation=AITranslationConfig(**config.ai_translation) if config.ai_translation else AITranslationConfig(),
            storage=StorageConfig(**config.storage) if config.storage else StorageConfig(),
            advanced=AdvancedConfig(**config.advanced) if config.advanced else AdvancedConfig(),
        )

    async def get_system_ai_config(self) -> SystemAIConfig:
        from app.core.config import get_settings
        settings = get_settings()
        return SystemAIConfig(
            model=settings.AI_MODEL,
            api_base=settings.AI_API_BASE,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS,
            timeout=settings.AI_TIMEOUT,
        )

    async def get_runtime_config(self, user_id: int) -> RuntimeConfig:
        config = await self.get_or_create_user_config(user_id)
        user_config = self.to_full_config(config)
        ai_config = await self.get_system_ai_config()
        return RuntimeConfig(user_config=user_config, ai_config=ai_config)
