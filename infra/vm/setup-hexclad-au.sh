#!/usr/bin/env bash
# One-time VM setup for HexClad AU instance
# Run on blossomclaw-staging as a user with sudo access
set -euo pipefail

BRAND_USER="hexclad_au"
BRAND_PORT="18790"

echo "=== Creating ${BRAND_USER} user ==="
sudo useradd -m -s /bin/bash "${BRAND_USER}" 2>/dev/null || echo "User already exists"

echo "=== Setting up .openclaw directory ==="
sudo -u "${BRAND_USER}" mkdir -p "/home/${BRAND_USER}/.openclaw"

echo "=== Creating .env placeholder ==="
if ! sudo -u "${BRAND_USER}" test -f "/home/${BRAND_USER}/.openclaw/.env"; then
  sudo -u "${BRAND_USER}" tee "/home/${BRAND_USER}/.openclaw/.env" > /dev/null << 'ENV'
# Fill in values — see brands/hexclad_au/.env.example in the repo
BLOSSOM_BRAND_ID=hexclad_au
BLOSSOM_BRAND_NAME=HexClad Australia
ANTHROPIC_API_KEY=
BLOSSOM_API_URL=
BLOSSOM_INTERNAL_KEY=
BLOSSOM_USER_ID=
HIKER_API_KEY=
BRAVE_API_KEY=
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME=instagram_influencers
OPENAI_API_KEY=
OPENCLAW_GATEWAY_TOKEN=
ENV
  echo "  .env created — fill in secrets before first deploy"
else
  echo "  .env already exists, skipping"
fi

echo "=== Verifying openclaw binary is accessible ==="
if sudo -u "${BRAND_USER}" command -v openclaw &>/dev/null; then
  echo "  openclaw found: $(sudo -u "${BRAND_USER}" which openclaw)"
else
  echo "  WARNING: openclaw not in ${BRAND_USER}'s PATH"
  echo "  Ensure /usr/local/bin/openclaw exists or update the systemd ExecStart path"
fi

echo "=== Installing systemd service ==="
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
sudo cp "${SCRIPT_DIR}/openclaw-hexclad-au.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable openclaw-hexclad-au
echo "  Service installed (not started — run first deploy to populate config)"

echo "=== Installing sudoers rule ==="
DEPLOY_USER="$(whoami)"
sed "s/DEPLOY_USER/${DEPLOY_USER}/g" "${SCRIPT_DIR}/hexclad-deploy.sudoers" \
  | sudo tee /etc/sudoers.d/hexclad-deploy > /dev/null
sudo chmod 440 /etc/sudoers.d/hexclad-deploy
sudo visudo -cf /etc/sudoers.d/hexclad-deploy
echo "  Sudoers rule installed for deploy user: ${DEPLOY_USER}"

echo "=== Opening firewall port ${BRAND_PORT} (optional — skip if using SSH tunnel) ==="
echo "  To open: gcloud compute firewall-rules create allow-openclaw-hexclad \\"
echo "    --allow=tcp:${BRAND_PORT} --target-tags=openclaw --direction=INGRESS"
echo "  Or use SSH tunnel: ssh -L ${BRAND_PORT}:localhost:${BRAND_PORT} <instance>"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Fill in /home/${BRAND_USER}/.openclaw/.env with real secrets"
echo "  2. Push to hexclad_au branch to trigger first deploy"
echo "  3. Verify: curl -H 'Authorization: Bearer <token>' http://localhost:${BRAND_PORT}/v1/chat/completions"
