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

| Brand | User | Port | Branch |
|-------|------|------|--------|
| Blossom (default) | default | 18789 | `staging` / `main` |
| HexClad AU | `hexclad_au` | 18790 | `hexclad_au` |

## Repo Structure

- `config/` maps to `~/.openclaw/` on the target instance
- `brands/<brand_id>/workspace/` contains brand-specific overrides overlaid at deploy time
- `infra/vm/` contains systemd and sudoers templates for VM setup
- Secrets live in `.env` on each instance user — never committed

## Git Workflow

- PRs for default Blossom target `staging` — never target `main` unless explicitly told
- Brand branches (`hexclad_au`) deploy directly to their brand instance on the staging VM
- Push to `staging` deploys default Blossom to staging
- Push to `main` deploys default Blossom to production (when provisioned)
- Push to `hexclad_au` deploys HexClad AU brand instance
