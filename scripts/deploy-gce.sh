#!/usr/bin/env bash
# Deploy the current commit to a single Compute Engine VM (Docker Compose + Caddy TLS).
# Prereqs: gcloud authenticated for PROJECT. Idempotent: re-run to ship a new commit.
#
#   PROJECT=my-project scripts/deploy-gce.sh
#
# Creates (once): service account handovers-runtime (Vertex AI User only), firewall rule
# handovers-web (80/443 to tag "handovers"), VM "handovers" (e2-medium, Debian 12).
set -euo pipefail
set -x
cd "$(dirname "${BASH_SOURCE[0]}")/.."

PROJECT="${PROJECT:?set PROJECT}"
ZONE="${ZONE:-asia-south1-b}"
VM="${VM:-handovers}"
SA="handovers-runtime@${PROJECT}.iam.gserviceaccount.com"
G="gcloud --project=${PROJECT} --quiet"

$G iam service-accounts describe "$SA" >/dev/null 2>&1 ||
  $G iam service-accounts create handovers-runtime --display-name="Handovers runtime"
# Idempotent; --condition=None is required when the project policy already uses conditions.
$G projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:${SA}" \
  --role=roles/aiplatform.user --condition=None >/dev/null
$G compute firewall-rules describe handovers-web >/dev/null 2>&1 ||
  $G compute firewall-rules create handovers-web --network=default --allow=tcp:80,tcp:443 --target-tags=handovers
$G compute instances describe "$VM" --zone="$ZONE" >/dev/null 2>&1 ||
  $G compute instances create "$VM" --zone="$ZONE" --machine-type=e2-medium \
    --image-family=debian-12 --image-project=debian-cloud --boot-disk-size=30GB \
    --service-account="$SA" --scopes=cloud-platform --tags=handovers

IP="$($G compute instances describe "$VM" --zone="$ZONE" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')"
SITE="${IP//./-}.sslip.io"

# Ship the committed tree plus a generated .env (secrets never live in git).
git archive --format=tar.gz -o /tmp/handovers.tgz HEAD
if [[ ! -f /tmp/handovers.env ]]; then
  cp .env.example /tmp/handovers.env
  sed -i.bak \
    -e "s|^FALKORDB_PASSWORD=.*|FALKORDB_PASSWORD=$(openssl rand -hex 24)|" \
    -e "s|^LLM_PROVIDER=.*|LLM_PROVIDER=vertex|" \
    -e "s|^GCP_PROJECT=.*|GCP_PROJECT=${PROJECT}|" \
    -e "s|^ALLOW_RESET=.*|ALLOW_RESET=true|" \
    -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://${SITE}|" \
    -e "s|^APP_PUBLIC_URL=.*|APP_PUBLIC_URL=https://${SITE}|" \
    -e "s|^APP_SECRET_KEY=.*|APP_SECRET_KEY=$(openssl rand -hex 32)|" \
    -e "s|^KEYCLOAK_URL=.*|KEYCLOAK_URL=http://keycloak:8180/auth|" \
    -e "s|^KEYCLOAK_PUBLIC_URL=.*|KEYCLOAK_PUBLIC_URL=https://${SITE}/auth|" \
    -e "s|^KEYCLOAK_CLIENT_SECRET=.*|KEYCLOAK_CLIENT_SECRET=$(openssl rand -hex 24)|" \
    -e "s|^KC_BOOTSTRAP_ADMIN_PASSWORD=.*|KC_BOOTSTRAP_ADMIN_PASSWORD=$(openssl rand -hex 16)|" \
    -e "s|^PLATFORM_ADMIN_PASSWORD=.*|PLATFORM_ADMIN_PASSWORD=$(openssl rand -hex 12)|" \
    -e "s|^DEMO_USER_PASSWORD=.*|DEMO_USER_PASSWORD=|" \
    -e "s|^SESSION_COOKIE_SECURE=.*|SESSION_COOKIE_SECURE=true|" /tmp/handovers.env
  printf '\nSITE_ADDRESS=%s\nSEED_ON_START=true\n' "$SITE" >> /tmp/handovers.env
fi
$G compute scp --zone="$ZONE" /tmp/handovers.tgz /tmp/handovers.env deployment/vm-setup.sh "$VM":/tmp/
$G compute ssh "$VM" --zone="$ZONE" --command="sudo mkdir -p /opt/handovers && sudo tar -xzf /tmp/handovers.tgz -C /opt/handovers && sudo cp /tmp/handovers.env /opt/handovers/.env && sudo bash /tmp/vm-setup.sh"
echo "Live: https://${SITE} (landing page at /, the app at /dashboard)"
