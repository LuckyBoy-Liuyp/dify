from configs.extra.archive_config import ArchiveStorageConfig
from configs.extra.knowledge_platform_config import KnowledgePlatformConfig
from configs.extra.notion_config import NotionConfig
from configs.extra.sentry_config import SentryConfig


class ExtraServiceConfig(
    # place the configs in alphabet order
    ArchiveStorageConfig,
    KnowledgePlatformConfig,
    NotionConfig,
    SentryConfig,
):
    pass
