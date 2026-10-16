"""Data connectors: one package per platform, registered here.

Adding a platform is a package beside `github/` with a `connector.py` implementing `Connector`
(connectors/base.py), and one line below. The Integrations page lists whatever is registered.
"""

from connectors.base import Connector
from connectors.entra import Entra
from connectors.github import GitHub
from connectors.google_workspace import GoogleWorkspace
from connectors.hubspot import HubSpot
from connectors.jira import Jira
from connectors.notion import Notion
from connectors.salesforce import Salesforce
from connectors.slack import Slack

# Order shown on the Integrations page: directory first (it creates the people), then work tools.
REGISTRY: dict[str, Connector] = {
    c.id: c
    for c in (
        Entra(),
        GoogleWorkspace(),
        Slack(),
        GitHub(),
        Jira(),
        Notion(),
        HubSpot(),
        Salesforce(),
    )
}

#: Shown on the Integrations page as "coming soon" (name, category); not connectable yet.
PLANNED: dict[str, tuple[str, str]] = {
    "orangehrm": ("OrangeHRM", "hr"),
    "confluence": ("Confluence", "docs"),
    "google_drive": ("Google Drive", "docs"),
    "linear": ("Linear", "tickets"),
    "gitlab": ("GitLab", "code"),
    "zendesk": ("Zendesk", "tickets"),
}
