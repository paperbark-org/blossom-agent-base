# Blossom Agent Base

OpenClaw gateway configuration for the Blossom platform. This repo version-controls the `~/.openclaw/` directory that runs on GCP Compute Engine.

> **For AI agents**: See [CLAUDE.md](./CLAUDE.md) for structured context.

## System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ blossom-frontend│────▶│ blossom-agent-base│────▶│ blossom-backend │
│ (Next.js/Vercel)│     │ (OpenClaw on GCP) │     │ (FastAPI on GCP)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

| Repo | Purpose | Deployed to |
|------|---------|-------------|
| [blossom-frontend](https://github.com/paperbark-org/blossom-frontend) | Next.js app, Clerk auth, chat UI | Vercel |
| **blossom-agent-base** (this repo) | OpenClaw gateway — agent config, tools, workspace | GCP Compute Engine |
| [blossom-backend](https://github.com/paperbark-org/blossom-backend) | Shared intelligence API — search, scoring, audience intelligence | GCP Cloud Run |

## What This Does

- Exposes an OpenAI-compatible `/v1/chat/completions` endpoint
- Frontend sends chat messages here via `OPENCLAW_GATEWAY_URL`
- Gateway orchestrates LLM calls and tool use (search, scoring, audience intelligence) against the backend's internal API

## Repo Structure

```
config/                         # Maps to ~/.openclaw/ on the instance
├── openclaw.json               # Main gateway config (secrets templated)
├── AGENTS.md                   # Agent documentation
├── agents/blossom/             # Blossom agent config
├── extensions/blossom-tools/   # Custom OpenClaw plugin
├── workspace/                  # Agent workspace (personality, tools, context)
│   ├── IDENTITY.md, SOUL.md    # Agent personality
│   ├── TOOLS.md, AGENTS.md     # Capability docs
│   ├── hikerapi/               # HikerAPI query tools
│   └── tools/                  # Custom tools (creator_audit.py)
├── audience_intelligence/      # Python analysis modules
├── hiker_api_context/          # HikerAPI documentation
├── cron/                       # Scheduled jobs
├── canvas/                     # Canvas UI
└── completions/                # Shell completions
```

## Infrastructure

- **Staging instance**: `blossomclaw-staging` (australia-southeast1-b, e2-medium)
- **GCP Project**: gen-lang-client-0112051341
- **CI/CD**: GitHub Actions deploys `config/` to `~/.openclaw/` on push

## Local Development

```bash
# SSH tunnel to the remote gateway
gcloud compute ssh blossomclaw-staging \
  --zone=australia-southeast1-b \
  -- -L 18789:127.0.0.1:18789 -N

# Gateway is now accessible at http://127.0.0.1:18789
```

## Deployment

Push to `staging` triggers CI/CD that:
1. Packages `config/` as a tarball
2. SCPs to the GCP instance
3. Extracts to `~/.openclaw/`
4. Substitutes `${OPENCLAW_GATEWAY_TOKEN}` and `${HOME}` placeholders
5. Restarts the gateway

### Manual Deploy

```bash
# Package and upload
tar czf /tmp/openclaw-deploy.tar.gz -C config .
gcloud compute scp /tmp/openclaw-deploy.tar.gz \
  blossomclaw-staging:/tmp/openclaw-deploy.tar.gz \
  --zone=australia-southeast1-b

# Extract and restart on instance
gcloud compute ssh blossomclaw-staging \
  --zone=australia-southeast1-b \
  --command="tar xzf /tmp/openclaw-deploy.tar.gz -C ~/.openclaw/ && rm /tmp/openclaw-deploy.tar.gz"
```

## Secret Management

Secrets are **never committed**. They live in `~/.openclaw/.env` on each instance.

See `.env.example` for required variables.

## Related

- [blossom-frontend](https://github.com/paperbark-org/blossom-frontend)
- [blossom-backend](https://github.com/paperbark-org/blossom-backend)
