from pydantic import Field
from pydantic_settings import BaseSettings


class EnterpriseFeatureConfig(BaseSettings):
    """
    Configuration for enterprise-level features.
    **Before using, please contact business@dify.ai by email to inquire about licensing matters.**
    """

    ENTERPRISE_ENABLED: bool = Field(
        description="Enable or disable enterprise-level features."
        "Before using, please contact business@dify.ai by email to inquire about licensing matters.",
        default=False,
    )

    CAN_REPLACE_LOGO: bool = Field(
        description="Allow customization of the enterprise logo.",
        default=False,
    )

    # Enterprise Ticket SSO Configuration
    ENTERPRISE_TICKET_SERVER_URL: str = Field(
        description="Enterprise ticket server base URL for SSO integration",
        default="",
    )
    # Enterprise Ticket SSO Configuration
    ENTERPRISE_TICKET_SERVER_VALIDATE_URL: str = Field(
        description="Enterprise ticket server base URL for SSO integration",
        default="",
    )

    ENTERPRISE_TICKET_SECRET_KEY: str = Field(
        description="Secret key for authenticating with enterprise ticket server",
        default="",
    )

    ENTERPRISE_TICKET_TIMEOUT: int = Field(
        description="Timeout in seconds for ticket server requests",
        default=30,
    )

    ENABLE_TICKET_SSO: bool = Field(
        description="Enable enterprise ticket-based single sign-on",
        default=False,
    )

    # Optional: Separate appkey and appsecret if different from TICKET_SECRET_KEY
    ENTERPRISE_TICKET_APPKEY: str | None = Field(
        description="AppKey for ticket server authentication (optional, uses TICKET_SECRET_KEY if not provided)",
        default=None,
    )

    ENTERPRISE_TICKET_APPSECRET: str | None = Field(
        description=(
            "AppSecret for ticket server signature generation "
            "(optional, uses TICKET_SECRET_KEY if not provided)"
        ),
        default=None,
    )
