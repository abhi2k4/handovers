# app/backend/identity/

Sign-in providers: one package per provider, behind `IdentityProvider` (`base.py`), registered in
`__init__.py` with a `PLANNED` list (Okta, Auth0). Keycloak does the signing in;
`services/identity.py` registers each provider in it.

| Package | Keycloak provider | Pinned to | Values from |
|---|---|---|---|
| `microsoft_entra/` | OpenID Connect | the Entra tenant | the Entra connector card |
| `google_workspace/` | Google, with `hostedDomain` | the Workspace domain | the Google Workspace connector card |

Every provider is backed by a directory connector, so an admin enters the values once and the
people who can sign in are the people the directory lists. One provider is active at a time
(`enable` turns the others off, settings kept); saving a card turns its sign-in on only when none
is active; disconnecting removes it. Rule: [docs/connectors.md](../../../docs/connectors.md#one-active-provider-per-category). Details: [docs/identity-and-access.md](../../../docs/identity-and-access.md).
