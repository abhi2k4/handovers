# deployment/

Live deployment: one Compute Engine VM runs the root `docker-compose.yml` plus
[`compose.deploy.yml`](compose.deploy.yml), with Caddy terminating TLS. FalkorDB, the backend and
the FalkorDB Browser are bound to localhost on the VM; only Caddy (80/443) is public.

```bash
PROJECT=<gcp-project> scripts/deploy-gce.sh
```

The script is idempotent. On first run it creates:

| Resource | Purpose |
|---|---|
| Service account `handovers-runtime` | Only role: Vertex AI User (Gemini via the VM's metadata token; no keys on disk) |
| Firewall rule `handovers-web` | tcp:80, tcp:443 to instances tagged `handovers` |
| VM `handovers` | e2-medium, Debian 12, 30 GB |

Each run ships the committed tree (`git archive HEAD`) and a generated `.env` (random FalkorDB
password, `LLM_PROVIDER=vertex`, `SITE_ADDRESS=<ip>.sslip.io`), then runs
[`vm-setup.sh`](vm-setup.sh) on the VM: install Docker if needed, build, start, wait for health.
An empty graph is seeded with the sample company on first start (`SEED_ON_START=true`).

One site: the landing page is at `/` and the app at `/dashboard` (both from the frontend
container; see [`app/frontend/`](../app/frontend/README.md#routes)).

Live: **https://handovers.omisaur.app** (also https://34-100-187-124.sslip.io). The domain is an
A record on Vercel DNS (`vercel dns add omisaur.app handovers A <vm-ip>`); on the VM,
`SITE_ADDRESS="34-100-187-124.sslip.io, handovers.omisaur.app"` so Caddy serves and certifies both,
and `APP_PUBLIC_URL=https://handovers.omisaur.app` for links the backend sends.

Local setup does not live here; see the root [README](../README.md#setup).

## Keycloak (sign-in)

`keycloak/handovers-realm.json` is the realm Keycloak imports on its **first start only**: the
`handovers-backend` client (authorization code + PKCE, a service account that manages users and
identity providers), the light login theme, and no people. People come from the graph ("Sync
people" on Integrations); Google and Microsoft are added from the app, not the file.

| | bash | PowerShell |
|---|---|---|
| Start | `docker compose --profile auth up -d keycloak` | same |
| Admin console | `http://localhost:8180/admin` (`KC_BOOTSTRAP_ADMIN_*`) | same |
| Re-import the realm (local only, deletes Keycloak data) | `docker compose --profile auth rm -sf keycloak && docker volume rm handovers_keycloak_data` | same |

### On the live VM

Sign-in runs on the live site with `COMPOSE_PROFILES=auth`. Keycloak is served under `/auth` on the
same host (`KC_HTTP_RELATIVE_PATH=/auth` in `compose.deploy.yml`; Caddy proxies `/auth/*` and
returns 404 for `/auth/admin*`), so no extra DNS name or certificate is needed. The `.env` keys:

| Key | Live value |
|---|---|
| `COMPOSE_PROFILES` | `auth` |
| `KEYCLOAK_URL` | `http://keycloak:8180/auth` (any non-empty value turns sign-in on; the overlay sets the real one) |
| `KEYCLOAK_PUBLIC_URL` | `https://handovers.omisaur.app/auth` |
| `KEYCLOAK_CLIENT_SECRET`, `KC_BOOTSTRAP_ADMIN_PASSWORD`, `PLATFORM_ADMIN_PASSWORD`, `APP_SECRET_KEY` | random, generated on the VM |
| `SESSION_COOKIE_SECURE` | `true` |
| `DEMO_USER_PASSWORD` | empty: visitors explore as a guest; people sign in with Google or Microsoft once connected |

`scripts/deploy-gce.sh` writes these for a new VM. The platform admin signs in as
`PLATFORM_ADMIN_EMAIL` with `PLATFORM_ADMIN_PASSWORD` to set up connectors and alert channels:

| bash | PowerShell |
|---|---|
| `gcloud compute ssh handovers --zone=asia-south1-b --command 'sudo grep ^PLATFORM_ADMIN_ /opt/handovers/.env'` | same |

After shipping a changed `Caddyfile`, restart Caddy (`docker compose -f docker-compose.yml -f deployment/compose.deploy.yml restart caddy`): it is mounted as a single file, so the running container keeps the old copy.

Keycloak's admin console, over a tunnel: `gcloud compute ssh handovers --zone=asia-south1-b -- -N -L 8180:localhost:8180`,
then http://localhost:8180/auth/admin (`KC_BOOTSTRAP_ADMIN_*` from the VM's `.env`).

Anywhere but a laptop, set real values for `KEYCLOAK_CLIENT_SECRET`, `KC_BOOTSTRAP_ADMIN_PASSWORD`
and `APP_SECRET_KEY`, leave `DEMO_USER_PASSWORD` empty, set `KEYCLOAK_PUBLIC_URL` and
`APP_PUBLIC_URL` to the public addresses, and `SESSION_COOKIE_SECURE=true` behind HTTPS. Keycloak
runs in `start-dev` mode with its embedded database here; a production deployment uses `start`
with PostgreSQL and HTTPS.
