# deployment/keycloak/

`handovers-realm.json`: the Keycloak realm `handovers`, imported on Keycloak's **first** start only
(`docker compose` mounts it). It holds the `handovers-backend` client (secret from
`KEYCLOAK_CLIENT_SECRET`), the light login theme and no people: people are synced from the graph,
the platform admin is created at startup, and sign-in providers are added from the app. Later
changes go through the app or the Keycloak admin console, not this file. See
[deployment/README.md](../README.md).
