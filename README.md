# Blossom Agent Base

OpenClaw gateway configuration for the Blossom platform. This repo version-controls the `~/.openclaw/` directory that runs on GCP Compute Engine.

> **For AI agents**: See [CLAUDE.md](./CLAUDE.md) for structured context.

## System Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────┐     ┌─────────────────┐
│ blossom-frontend│────▶│  blossomclaw-staging VM                  │────▶│ blossom-backend │
│ (Next.js/Vercel)│     │  ├─ default user :18789 → Blossom        │     │ (FastAPI on GCP)│
│                 │     │  └─ hexclad_au   :18790 → HexClad AU     │     │                 │
└─────────────────┘     └──────────────────────────────────────────┘     └─────────────────┘
```

Each brand runs as an isolated OpenClaw process under its own Linux user on a dedicated port. One VM, zero extra infra cost.

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
brands/                         # Per-brand overrides
└── hexclad_au/
    ├── brand.json              # Brand metadata (id, region, deploy target)
    ├── .env.example            # Required secrets for this brand
    └── workspace/
        └── USER.md             # Brand context overlaid onto config/workspace/
infra/vm/                       # VM setup templates (manual one-time install)
├── openclaw-hexclad-au.service # systemd unit for HexClad AU process
├── hexclad-deploy.sudoers      # Sudoers rules for CI deploy
└── setup-hexclad-au.sh         # Automated VM setup script
```

## Infrastructure

- **Staging VM**: `blossomclaw-staging` (australia-southeast1-b, e2-medium)
- **GCP Project**: gen-lang-client-0112051341
- **CI/CD**: GitHub Actions deploys `config/` to the target user's `~/.openclaw/` on push

### Brand Instances

| Brand | Linux User | Port | Branch | systemd Service |
|-------|-----------|------|--------|-----------------|
| Blossom (default) | default SSH user | 18789 | `staging` / `main` | — (managed by openclaw) |
| HexClad AU | `hexclad_au` | 18790 | `hexclad_au` | `openclaw-hexclad-au` |

Each brand instance has full process isolation: separate Linux user, home directory, `.openclaw/` config, `.env` secrets, and port. The deploy workflow routes branches to the correct user/port automatically.

## Local Development

```bash
# SSH tunnel to the default Blossom gateway
gcloud compute ssh blossomclaw-staging \
  --zone=australia-southeast1-b \
  -- -L 18789:127.0.0.1:18789 -N

# SSH tunnel to the HexClad AU gateway
gcloud compute ssh blossomclaw-staging \
  --zone=australia-southeast1-b \
  -- -L 18790:127.0.0.1:18790 -N

# Both gateways accessible at http://127.0.0.1:<port>
```

## Deployment

Push to a branch triggers CI/CD that:
1. Detects the target brand from the branch name (`staging`/`main` = default, `hexclad_au` = HexClad AU)
2. Applies brand workspace overlay (copies `brands/<brand>/workspace/*` over `config/workspace/`)
3. Patches `openclaw.json` gateway port for the brand
4. Strips cron runtime state to avoid overwriting live scheduling
5. Packages `config/` as a tarball (excluding `workspace/memory/` to preserve runtime agent memories)
6. SCPs to the GCP instance and extracts to the target user's `~/.openclaw/`
7. Substitutes `${OPENCLAW_GATEWAY_TOKEN}` and `${HOME}` from the instance `.env`
8. Restarts the appropriate service (`systemctl` for brands, `openclaw gateway restart` for default)

### Adding a New Brand

1. Create `brands/<brand_id>/` with `brand.json`, `.env.example`, and `workspace/` overlay files
2. Add the branch name to `.github/workflows/deploy.yml` triggers and the `case` block
3. Create VM setup files in `infra/vm/` (systemd service, sudoers rules)
4. Run `infra/vm/setup-<brand>.sh` on the target VM
5. Fill in `/home/<brand_user>/.openclaw/.env` with secrets
6. Push to the brand branch to trigger the first deploy

## Secret Management

Secrets are **never committed**. They live in `~/.openclaw/.env` on each instance.

See `.env.example` for required variables.

## Related

- [blossom-frontend](https://github.com/paperbark-org/blossom-frontend)
- [blossom-backend](https://github.com/paperbark-org/blossom-backend)
