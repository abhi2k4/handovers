"""Application settings loaded from environment variables and the repository-root `.env`."""

from datetime import datetime
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.2.0"
# The app is served under this path; the site root is the landing page.
APP_BASE = "/dashboard"

_HERE = Path(__file__).resolve()
# app/backend/core/config.py -> repository root is parents[3] in a checkout.
_REPO_ROOT = _HERE.parents[3] if len(_HERE.parents) > 3 else Path("/app")


def _env_files() -> tuple[Path, ...]:
    """Repository-root `.env` when running from a checkout, plus `.env` in the working directory."""
    return (_REPO_ROOT / ".env", Path(".env"))


def _default_graph_dir() -> Path:
    for candidate in (_REPO_ROOT / "graph", Path("/app/graph")):
        if candidate.is_dir():
            return candidate
    return _REPO_ROOT / "graph"


class Settings(BaseSettings):
    """Runtime configuration. Environment variables override values from `.env`."""

    model_config = SettingsConfigDict(
        env_file=_env_files(), env_file_encoding="utf-8", extra="ignore"
    )

    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_password: SecretStr | None = None

    handovers_tenant: str = Field(default="northwind", pattern=r"^[a-z0-9][a-z0-9_-]{0,62}$")
    graph_dir: Path = Field(default_factory=_default_graph_dir)

    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    # Pinned clock for deterministic demo and benchmark runs (ISO-8601). Empty = real clock.
    demo_now: str = ""

    # LLM: "groq" (OpenAI-compatible API), "vertex" (Gemini on Vertex AI), "anthropic", or "none"
    # (deterministic templates only).
    llm_provider: str = "none"
    llm_model: str = "gemini-2.5-flash"
    gcp_project: str = ""
    gcp_location: str = "global"
    gcloud_account: str = ""  # local dev only: which gcloud account mints Vertex tokens
    anthropic_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None

    # Encrypts credentials entered in the app (connectors, sign-in providers) and seals sign-in
    # attempts. Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    app_secret_key: SecretStr = SecretStr("")

    # Sign-in (core/keycloak.py, api/auth.py). Off when KEYCLOAK_URL is empty: then the demo
    # "View as" switcher is the only identity, as before.
    keycloak_url: str = ""  # how the backend reaches Keycloak, e.g. http://localhost:8180
    keycloak_public_url: str = (
        ""  # how the browser reaches it (token issuer); defaults to keycloak_url
    )
    keycloak_realm: str = "handovers"
    keycloak_client_id: str = "handovers-backend"
    keycloak_client_secret: SecretStr = SecretStr("handovers-dev-client-secret")
    app_public_url: str = "http://localhost:5173"  # where the browser opens the app

    # Let visitors explore as the demo personas without signing in (the live link for judges).
    allow_guest: bool = True
    # Local demo only: gives every employee a Keycloak account with this password, so anyone can
    # sign in as Nisha, Aditi... Leave empty anywhere real (people sign in with Google/Microsoft).
    demo_user_password: SecretStr = SecretStr("")
    # The platform admin: the Handovers team account that configures an organisation (integrations,
    # sign-in). Not an employee; created in Keycloak at startup when the password is set.
    platform_admin_email: str = "admin@handovers.local"
    platform_admin_password: SecretStr = SecretStr("")
    session_max_age_seconds: int = 12 * 3600
    session_cookie_secure: bool = False  # true behind HTTPS

    # Data connectors (connectors/). Each one is active when all its settings are set, either here
    # or in the app (Integrations, stored encrypted in the graph; the app's values win). Tokens stay
    # on the server and never reach the browser. Setup per platform: docs/connectors.md.
    github_token: SecretStr | None = None
    github_repos: str = ""  # owner/repo, comma-separated
    slack_bot_token: SecretStr | None = None
    slack_channels: str = ""  # channel ids, comma-separated
    jira_base_url: str = ""  # https://<site>.atlassian.net
    jira_email: str = ""
    jira_api_token: SecretStr | None = None
    jira_projects: str = ""  # project keys, comma-separated
    hubspot_token: SecretStr | None = None
    notion_token: SecretStr | None = None
    salesforce_instance_url: str = ""  # https://<domain>.my.salesforce.com
    salesforce_token: SecretStr | None = None
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_client_secret: SecretStr | None = None
    google_domain: str = ""
    google_admin_email: str = ""
    google_service_account_key: SecretStr | None = None
    google_client_id: str = ""
    google_client_secret: SecretStr | None = None

    # Lets the UI reload the synthetic dataset (demo deployments only).
    allow_reset: bool = False

    # Background jobs (services/jobs.py): the worker runs inside the backend process.
    jobs_enabled: bool = True
    jobs_poll_seconds: float = Field(default=30.0, ge=1.0, le=3600.0)

    # WhatsApp alerts (Meta WhatsApp Cloud API). Empty token: alerts show in the app only.
    whatsapp_token: SecretStr | None = None
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = ""  # echoed back when Meta verifies the webhook
    whatsapp_template: str = ""  # approved one-variable template, used outside the 24-hour window
    whatsapp_api_version: str = "v21.0"

    # Email alerts over SMTP. In Docker the default is the bundled Mailpit (a local inbox at
    # http://localhost:8025); running on the host, set SMTP_HOST=localhost. Empty host: no email.
    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: SecretStr | None = None
    smtp_from: str = ""

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

    @property
    def whatsapp_enabled(self) -> bool:
        return bool(
            self.whatsapp_token
            and self.whatsapp_token.get_secret_value()
            and self.whatsapp_phone_id
        )

    # Load the synthetic dataset into an empty tenant graph at startup.
    seed_on_start: bool = False

    @property
    def tenant_graph(self) -> str:
        """FalkorDB graph key for the configured tenant (one graph per tenant)."""
        return f"handovers__{self.handovers_tenant}"

    @property
    def sso_enabled(self) -> bool:
        return bool(self.keycloak_url.strip())

    @property
    def keycloak_issuer(self) -> str:
        """The realm as the browser sees it: the issuer in every token."""
        base = (self.keycloak_public_url or self.keycloak_url).rstrip("/")
        return f"{base}/realms/{self.keycloak_realm}"

    @property
    def keycloak_internal_realm_url(self) -> str:
        return f"{self.keycloak_url.rstrip('/')}/realms/{self.keycloak_realm}"

    @property
    def oidc_redirect_uri(self) -> str:
        return f"{self.app_public_url.rstrip('/')}/api/auth/callback"

    def app_url(self, path: str = "/") -> str:
        """A page of the app: it lives under /dashboard; / is the landing page."""
        return f"{self.app_public_url.rstrip('/')}{APP_BASE}{'' if path == '/' else path}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def demo_now_ms(self) -> int | None:
        if not self.demo_now.strip():
            return None
        return int(datetime.fromisoformat(self.demo_now.strip()).timestamp() * 1000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
