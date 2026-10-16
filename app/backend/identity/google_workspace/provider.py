"""Google Workspace: sign in with the organisation's Google accounts, one domain only.

Uses the Google Workspace connector's values (domain and OAuth client), so an admin enters them
once, on that card. Registered as Keycloak's built-in Google provider with `hostedDomain`: Google
is asked for that domain's accounts, and Keycloak refuses a token whose `hd` claim is anything else,
so a personal Gmail or another company's account cannot get in. In the OAuth client (Google Cloud
Console > APIs & Services > Credentials, type "Web application") add the redirect URI the sign-in
settings show (`.../broker/google/endpoint`).
"""

from collections.abc import Mapping

from identity.base import IdentityProvider


class GoogleWorkspace(IdentityProvider):
    # The alias stays "google": it is in the redirect URI registered in the OAuth client.
    id = "google"
    name = "Google Workspace"
    button = "Google"
    connector = "google_workspace"
    guide = "Uses the Google Workspace card under Directory: the same domain and OAuth client."

    def keycloak(self, values: Mapping[str, str]) -> tuple[str, dict[str, str]]:
        config = {
            "clientId": values["google_client_id"],
            "hostedDomain": values["google_domain"],
            "prompt": "select_account",
            "syncMode": "IMPORT",
        }
        if values.get("google_client_secret"):
            config["clientSecret"] = values["google_client_secret"]
        return "google", config
