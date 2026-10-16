"""What every sign-in provider provides, so Keycloak and the screens need no per-provider code.

Keycloak signs people in; each provider here is one way into it, registered in Keycloak as an
identity provider under the provider's `id` (also the login page's `kc_idp_hint` and the last part
of the redirect URI). A provider is exactly the parts that differ:

* the directory connector whose stored values it signs in with (`connector`): Microsoft Entra ID
  uses the app registration that reads the directory, Google Workspace the domain and OAuth client
  on its card, so an admin enters everything once, on the connector;
* the Keycloak identity-provider type and config those values become (`keycloak`).

Adding one is a package beside `microsoft_entra/` and a line in `identity/__init__.py`.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import ClassVar


class IdentityProvider(ABC):
    #: Keycloak alias, the login page's provider id, and the end of the redirect URI.
    id: ClassVar[str]
    #: What admins see: "Microsoft Entra ID".
    name: ClassVar[str]
    #: The sign-in button: "Continue with Microsoft".
    button: ClassVar[str]
    #: The connector whose stored values this provider signs in with.
    connector: ClassVar[str]
    #: One line for the sign-in settings.
    guide: ClassVar[str]

    @abstractmethod
    def keycloak(self, values: Mapping[str, str]) -> tuple[str, dict[str, str]]:
        """The Keycloak identity-provider type (`providerId`) and config for these values.

        A blank secret is left out, so Keycloak keeps the one it has.
        """
