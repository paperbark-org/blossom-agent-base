# Blossom Agent Base

OpenClaw gateway configuration for the Blossom platform.

## What This Is

This repo version-controls the `~/.openclaw/` configuration directory that runs
on GCP Compute Engine instances. It contains:

- Gateway config (`openclaw.json`)
- Agent configs
- Custom plugin (`blossom-tools`)
- Workspace files (agent personality, tools, context docs)
- Audience intelligence modules
- HikerAPI context documentation

## Infrastructure

- **Staging VM**: `blossomclaw-staging` (GCP, australia-southeast1-b)
- **Project**: gen-lang-client-0112051341
- Multiple brand instances run on the same VM as isolated Linux users on separate ports

| Brand | User | Port | Branch | Systemd Service |
|-------|------|------|--------|-----------------|
| Blossom (default) | `eli_paperbark_ai` | 18789 | `staging` / `main` | `openclaw-gateway` |
| HexClad AU | `hexclad_au` | 18790 | `hexclad_au` | `openclaw-hexclad-au` |

## Repo Structure

- `config/` maps to `~/.openclaw/` on the target instance
- `brands/<brand_id>/workspace/` contains brand-specific overrides overlaid at deploy time
- `infra/vm/` contains systemd and sudoers templates for VM setup
- Secrets live in `.env` on each instance user — never committed

## Deployment

### How it works

Push to a deploy branch triggers `.github/workflows/deploy.yml`:

1. **Validate** — all JSON files are syntax-checked
2. **Configure target** — branch determines instance, user, port, and brand
3. **Brand overlay** — for brand branches, `brands/<id>/workspace/` files are copied into `config/workspace/`
4. **Port patch** — for brand branches, `gateway.port` is updated in `openclaw.json`
5. **Strip state** — cron job runtime state is removed to avoid overwriting live scheduling
6. **Package** — `config/` is tarred, excluding `workspace/memory/` and `workspace/MEMORY.md` (agent memory is preserved across deploys)
7. **Deploy** — tarball is SCP'd to VM, extracted to the target user's `~/.openclaw/`, placeholders (`${HOME}`, `${OPENCLAW_GATEWAY_TOKEN}`) are substituted, and the systemd service is restarted

### Deploy targets

| Branch | VM User | Service Restarted |
|--------|---------|-------------------|
| `staging` (or any non-brand) | `eli_paperbark_ai` | `openclaw-gateway` |
| `hexclad_au` | `hexclad_au` | `openclaw-hexclad-au` |
| `main` | (production — not yet provisioned) | — |

### What is NOT overwritten on deploy

- `workspace/memory/` — agent memory directory
- `workspace/MEMORY.md` — agent memory file
- `.env` — secrets file (managed manually on the VM)
- Files not in the tarball are left untouched (tar extract is additive)

## Git Workflow

- PRs for default Blossom target `staging` — never target `main` unless explicitly told
- Brand branches (`hexclad_au`) deploy directly to their brand instance on the staging VM
- Push to `staging` deploys default Blossom to staging
- Push to `main` deploys default Blossom to production (when provisioned)
- Push to `hexclad_au` deploys HexClad AU brand instance

## Adding a New Brand

1. Create `brands/<brand_id>/brand.json` with brand metadata
2. Create `brands/<brand_id>/workspace/` with brand-specific workspace files
3. Add a case in `deploy.yml` for the new branch with `DEPLOY_USER`, `DEPLOY_PORT`, and `BRAND`
4. Run the VM setup script (see `infra/vm/setup-hexclad-au.sh` as template)
5. Add the branch to the `on.push.branches` list in `deploy.yml`
