"""Sign-in providers: one package per provider, registered here (see identity/base.py).

Keycloak does the signing in; services/identity.py registers these providers in it. The login page
offers whichever are registered and enabled.
"""

from identity.base import IdentityProvider
from identity.google_workspace import GoogleWorkspace
from identity.microsoft_entra import MicrosoftEntra

REGISTRY: dict[str, IdentityProvider] = {p.id: p for p in (MicrosoftEntra(), GoogleWorkspace())}

#: Shown as "coming soon"; not connectable yet.
PLANNED: dict[str, str] = {"okta": "Okta", "auth0": "Auth0"}
