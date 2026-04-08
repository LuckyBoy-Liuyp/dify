"""
Configuration for external knowledge platform integration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class KnowledgePlatformConfig(BaseSettings):
    """
    Configuration for knowledge platform API integration.
    """

    KNOWLEDGE_PLATFORM_BASE_URL: str = Field(
        description="Base URL for knowledge platform API",
        default="",
    )

    KNOWLEDGE_PLATFORM_SYNC_ENABLED: bool = Field(
        description="Enable sync to knowledge platform",
        default=False,
    )

    KNOWLEDGE_PLATFORM_APP_KEY: str = Field(
        description="App key for knowledge platform authentication",
        default="",
    )

    KNOWLEDGE_PLATFORM_APP_SECRET: str = Field(
        description="App secret for knowledge platform signature generation",
        default="",
    )
