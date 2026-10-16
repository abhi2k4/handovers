"""Microsoft Entra ID: sign in with the organisation's Microsoft accounts, one tenant only.

The same app registration the Entra connector reads the directory with (tenant ID, client ID,
client secret), so an admin enters it once. Registered in Keycloak as a generic OpenID Connect
provider pinned to that tenant: unlike Keycloak's built-in "microsoft" provider, a personal or
another company's Microsoft account cannot get in. In the app registration add the redirect URI
the sign-in settings show (`.../broker/microsoft/endpoint`). Modelled on kenz-intent's Entra provider.
"""

from collections.abc import Mapping

from identity.base import IdentityProvider


class MicrosoftEntra(IdentityProvider):
    # The alias stays "microsoft": it is in the redirect URI registered in Entra.
    id = "microsoft"
    name = "Microsoft Entra ID"
    button = "Microsoft"
    connector = "entra"
    guide = "Uses the Microsoft Entra ID card under Directory: the same tenant, app and secret."

    def keycloak(self, values: Mapping[str, str]) -> tuple[str, dict[str, str]]:
        base = f"https://login.microsoftonline.com/{values['entra_tenant_id']}"
        config = {
            "issuer": f"{base}/v2.0",
            "authorizationUrl": f"{base}/oauth2/v2.0/authorize",
            "tokenUrl": f"{base}/oauth2/v2.0/token",
            "jwksUrl": f"{base}/discovery/v2.0/keys",
            "useJwksUrl": "true",
            "validateSignature": "true",
            "clientId": values["entra_client_id"],
            "clientAuthMethod": "client_secret_post",
            "defaultScope": "openid profile email",
            # Microsoft's account picker every time; otherwise signing in after signing out is
            # silently the same account again.
            "prompt": "select_account",
            # Claims from the ID token only: Graph's userinfo has no preferred_username.
            "disableUserInfo": "true",
            # Signing out of Handovers must not sign the person out of Outlook and Teams.
            "logoutUrl": "",
            "syncMode": "IMPORT",
        }
        if values.get("entra_client_secret"):
            config["clientSecret"] = values["entra_client_secret"]
        return "oidc", config
