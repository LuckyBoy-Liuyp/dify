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

    ENTERPRISE_REQUEST_TIMEOUT: int = Field(
        ge=1, description="Maximum timeout in seconds for enterprise requests", default=5
    )


class EnterpriseTelemetryConfig(BaseSettings):
    """
    Configuration for enterprise telemetry.
    """

    ENTERPRISE_TELEMETRY_ENABLED: bool = Field(
        description="Enable enterprise telemetry collection (also requires ENTERPRISE_ENABLED=true).",
        default=False,
    )

    ENTERPRISE_OTLP_ENDPOINT: str = Field(
        description="Enterprise OTEL collector endpoint.",
        default="",
    )

    ENTERPRISE_OTLP_HEADERS: str = Field(
        description="Auth headers for OTLP export (key=value,key2=value2).",
        default="",
    )

    ENTERPRISE_OTLP_PROTOCOL: str = Field(
        description="OTLP protocol: 'http' or 'grpc' (default: http).",
        default="http",
    )

    ENTERPRISE_OTLP_API_KEY: str = Field(
        description="Bearer token for enterprise OTLP export authentication.",
        default="",
    )

    ENTERPRISE_INCLUDE_CONTENT: bool = Field(
        description="Include input/output content in traces (privacy toggle).",
        # Setting the default value to False to avoid accidentally log PII data in traces.
        default=False,
    )

    ENTERPRISE_SERVICE_NAME: str = Field(
        description="Service name for OTEL resource.",
        default="dify",
    )

    ENTERPRISE_OTEL_SAMPLING_RATE: float = Field(
        description="Sampling rate for enterprise traces (0.0 to 1.0, default 1.0 = 100%).",
        default=1.0,
        ge=0.0,
        le=1.0,
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
