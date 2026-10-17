# Playbook: Google Workspace sign-in and directory sync

A self-contained guide for adding "Sign in with Google, for one company's Workspace only" plus
people sync from Google Workspace to **any** web app. Written so it can be handed to another
engineer or AI assistant as the full brief. Handovers is the worked example; file paths in
*Reference implementation* point at it.

Sources: [Admin SDK overview](https://developers.google.com/workspace/admin),
[Admin settings](https://developers.google.com/workspace/admin/admin-settings),
[Directory API users.list](https://developers.google.com/workspace/admin/directory/reference/rest/v1/users/list),
[Domain-wide delegation](https://developers.google.com/identity/service-auth/domain-wide-delegation),
[OpenID Connect `hd` parameter](https://developers.google.com/identity/openid-connect/openid-connect#hd-param).

## 1. What you are building

Two independent capabilities that share one admin form:

| Capability | Google mechanism | Credential |
|---|---|---|
| **Sign-in** (people prove who they are) | OpenID Connect, restricted to the Workspace domain with `hd` | OAuth client (Web application): client ID + secret |
| **Directory sync** (who works here, titles, managers, who left) | Admin SDK Directory API `users.list` | Service account JSON key with **domain-wide delegation**, acting as a Workspace admin |

They need **different credentials**: an OAuth client cannot read the directory without a person's
consent, and a service account cannot sign people in. The admin enters both on one card, once.

Ground rules:

- **One domain only.** Ask Google for the domain (`hd=example.com`) *and* verify the `hd` claim in
  the ID token. The request parameter alone is only a UI hint; an attacker can remove it.
- **No sign-up by signing in.** Only people already in the synced directory may sign in. Match on
  email (lower-cased) and refuse unknown ones.
- **Read-only.** The directory scope is `admin.directory.user.readonly`. Never request write scopes.
- **Secrets never leave the server.** Store them encrypted (or in your identity broker); show them
  masked; never log them; error messages name the host and status, never the token.

## 2. Architecture choices

**A. With an identity broker (Keycloak, recommended if you have one).** Register Keycloak's
built-in **Google** identity provider with `hostedDomain` set. Keycloak sends `hd` and rejects
tokens whose `hd` claim differs. Your app keeps a single OIDC client (Keycloak). The login button
deep-links with `kc_idp_hint=google` to skip Keycloak's own page.

**B. Without a broker.** Use any OIDC library against `https://accounts.google.com`
(discovery: `/.well-known/openid-configuration`), authorization code + PKCE, scopes
`openid email profile`, params `hd=<domain>` and `prompt=select_account`. After verifying the ID token
(signature via Google JWKS, `iss`, `aud`, `exp`, `nonce`), **require `hd == <domain>` and
`email_verified == true`**, then look the email up in your directory.

Either way, directory sync is the same backend job (section 5).

## 3. Google-side setup (what the customer's admin does)

1. **Google Cloud Console** → choose or create a project → **APIs & Services → Library** → enable
   **Admin SDK API**.
2. **IAM & Admin → Service accounts** → Create (no project roles needed) → **Keys → Add key →
   Create new key → JSON**. Download it. Note the service account's numeric **client ID**
   (unique ID on its details page).
3. **admin.google.com** (super admin) → **Security → Access and data control → API controls →
   Manage domain-wide delegation → Add new**: that client ID, scope
   `https://www.googleapis.com/auth/admin.directory.user.readonly`. Takes effect in minutes,
   sometimes up to an hour.
4. Pick an **admin account to act as** (any admin with user read rights). Google requires directory
   reads to impersonate an admin; the service account alone gets 403.
5. For sign-in: **APIs & Services → OAuth consent screen** → User type **Internal** (only that
   Workspace can use it; no Google verification needed). Then **Credentials → Create credentials →
   OAuth client ID → Web application** → add your **authorized redirect URI**:
   - with Keycloak: `<KEYCLOAK_PUBLIC_URL>/realms/<realm>/broker/google/endpoint`
   - without: your app's callback, e.g. `https://app.example.com/api/auth/callback`

   Copy the client ID and secret.

What the admin then enters in your app (one form):

| Field | Example | Secret | Used for |
|---|---|---|---|
| Workspace domain | `example.com` | no | `hd` pinning and `users.list?domain=` |
| Admin to act as | `admin@example.com` | no | JWT `sub` (impersonation) |
| Service account key | the whole JSON file, pasted | yes | signing the token request |
| OAuth client ID | `123…apps.googleusercontent.com` | no | sign-in |
| OAuth client secret | `GOCSPX-…` | yes | sign-in |

Show the redirect URI in the app with a Copy button, since the admin must paste it into Google.

## 4. Sign-in config

**Keycloak identity provider** (admin REST API `POST /admin/realms/<realm>/identity-provider/instances`,
or `PUT …/instances/google` to update):

```json
{
  "alias": "google",
  "providerId": "google",
  "displayName": "Google",
  "enabled": true,
  "trustEmail": true,
  "storeToken": false,
  "firstBrokerLoginFlowAlias": "first broker login",
  "config": {
    "clientId": "<oauth client id>",
    "clientSecret": "<oauth client secret>",
    "hostedDomain": "example.com",
    "prompt": "select_account",
    "syncMode": "IMPORT"
  }
}
```

- `hostedDomain` is what pins the domain; Keycloak validates the `hd` claim.
- `prompt=select_account` shows Google's account picker every time; without it, signing in again after
  signing out silently reuses the same account.
- On update, merge with the existing `config` and leave out `clientSecret` when the admin left it
  blank, so "keep the stored secret" works.
- Keycloak cannot change an identity provider's `providerId` in place. If you are replacing an
  existing provider of another type under the same alias, delete it and then create it.
- To stop sign-up by signing in, either pre-create every directory person as a Keycloak user (by
  email) so the first-broker-login flow *links* to them, or reject unknown emails in your callback.
  Do both.

## 5. Directory sync

**Token (JWT bearer grant, RFC 7523)**: sign a JWT with the service account's private key (RS256)
and exchange it at `https://oauth2.googleapis.com/token`:

```python
import json, time, httpx, jwt  # PyJWT with the [crypto] extra

SCOPE = "https://www.googleapis.com/auth/admin.directory.user.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"

async def access_token(http: httpx.AsyncClient, key_json: str, admin_email: str) -> str:
    key = json.loads(key_json)                       # error if not JSON
    now = int(time.time())
    assertion = jwt.encode(
        {"iss": key["client_email"], "sub": admin_email, "scope": SCOPE,
         "aud": TOKEN_URL, "iat": now, "exp": now + 3600},
        key["private_key"], algorithm="RS256",       # raises jwt.PyJWTError on a bad key
    )
    r = await http.post(TOKEN_URL, data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
    r.raise_for_status()
    return r.json()["access_token"]
```

No Google SDK is needed. If you prefer one: `google-auth` with
`service_account.Credentials.from_service_account_info(info, scopes=[SCOPE]).with_subject(admin)`.

**Read people**: `GET https://admin.googleapis.com/admin/directory/v1/users?domain=<domain>&maxResults=500`,
following `nextPageToken`. Map each user:

| Your field | Directory API field |
|---|---|
| email (match key) | `primaryEmail` (lower-case it) |
| name | `name.fullName` |
| title, department | the `organizations[]` entry with `primary: true` (else the first): `title`, `department` |
| manager | `relations[]` entry with `type == "manager"`: `value` is the manager's email |
| left the company | `suspended == true` or `archived == true` |

Sync rules: full read each run (directories are small); upsert by email; mark suspended people as
departed (disable their sign-in account), never delete; resolve managers after all people exist.

**Test connection** (read-only, before saving): get a token, then `users.list` with `maxResults=1`
and `fields=users(id)`. Report a specific reason:

| Symptom | Message to show |
|---|---|
| Key is not JSON / lacks `client_email` or `private_key` | "The service account key is not valid JSON" / "has no client_email or private_key" |
| `jwt.encode` fails | "The service account's private key could not be read" |
| Token endpoint 400/401 (`unauthorized_client`) | delegation missing or wrong client ID or scope |
| `users.list` 403 | admin email is not an admin, or the Admin SDK API is not enabled |
| `users.list` 400 on `domain` | the domain is not this Workspace's |

Catch JWT and HTTP errors explicitly. A malformed key must give a readable message, not a 500.

## 6. Storage

- Save the five values as one record per connector, **encrypted at rest** (e.g. Fernet with a key
  from the environment). Return non-secret values as-is and secrets as `set: true` plus a mask
  (`••••1234`) only.
- A blank secret on save keeps the stored one.
- When the form is saved, update the sign-in provider if it is the active one, or turn it on if no
  provider is active (one active at a time: making one active turns the others off, settings kept).
  When it is disconnected, remove it. Saving the directory must not fail just because the broker is
  down; show a "Make active" action instead.
- Allow the same values from environment variables (`GOOGLE_DOMAIN`, `GOOGLE_ADMIN_EMAIL`,
  `GOOGLE_SERVICE_ACCOUNT_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) for server installs;
  values entered in the app win.

## 7. Tests (no network)

- Use a mock HTTP transport (`httpx.MockTransport`) with recorded Directory API pages (two pages, so
  pagination is covered).
- Generate a throwaway RSA key in the test (`cryptography`'s `rsa.generate_private_key`), put it in
  a fake key JSON, and in the mock token endpoint **decode the assertion with the public key**.
  Assert `sub` is the admin and `scope` is the read-only scope.
- Cases: mapping (title, department, manager, suspended → departed), check succeeds, non-JSON key,
  non-key `private_key`, "configured" only when every value is present.
- Sign-in: assert the identity-provider config has `hostedDomain`, and that a blank secret leaves
  `clientSecret` out.
- Manual end-to-end with dummy values: save the card, then follow `/login?provider=google` through the
  broker. The final redirect must go to `accounts.google.com/o/oauth2/v2/auth` with `hd=<domain>`.
  Remove the dummy values afterwards.

## 8. Checklist for a new project

- [ ] Settings for the five values (env names above), secrets typed as secret
- [ ] Connector: token (JWT bearer), `users.list` paging, mapping, `check()`
- [ ] Encrypted credential store, masked read-back, blank-keeps-secret
- [ ] Sign-in: broker IdP with `hostedDomain` (or direct OIDC with `hd` + `email_verified` checks)
- [ ] Unknown emails refused; directory people pre-provisioned in the broker
- [ ] Save hooks: refresh or (if none is active) turn on sign-in on save, remove on disconnect,
      "Make active" to switch (one active provider at a time)
- [ ] UI: one card with the redirect URI and a Copy button, Test connection, Connect and sync
- [ ] Tests from section 7; docs with the Google-side steps from section 3
- [ ] Never log tokens, keys or secrets; errors show host and status only

## Reference implementation (Handovers)

| Piece | File |
|---|---|
| Directory connector (token, users.list, mapping, check) | `app/backend/connectors/google_workspace/connector.py` |
| Sign-in provider (Keycloak config with `hostedDomain`) | `app/backend/identity/google_workspace/provider.py` |
| Provider contract and registry | `app/backend/identity/base.py`, `app/backend/identity/__init__.py` |
| Register in Keycloak on save, remove on disconnect | `app/backend/services/identity.py`, `app/backend/api/connectors.py` |
| Keycloak admin upsert (replace on type change) | `app/backend/core/keycloak.py` (`Admin.upsert_provider`) |
| Encrypted credential store | `app/backend/services/connector_config.py`, `app/backend/core/security.py` |
| Tests | `app/backend/tests/unit/test_connector_google_workspace.py`, `test_identity.py` |
| UI (card, Turn on/off, redirect URI) | `app/frontend/src/pages/IntegrationsPage.tsx`, `components/SignInSettings.tsx` |
| Admin setup steps | [connectors.md](connectors.md#google-workspace-user-directory-and-google-sign-in) |
