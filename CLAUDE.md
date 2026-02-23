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

- **Staging instance**: `blossomclaw-staging` (GCP, australia-southeast1-b)
- **Project**: gen-lang-client-0112051341

## Repo Structure

Files in `config/` map directly to `~/.openclaw/` on the target instance.
Secrets live in `.env` on the instance only — never committed.

## Git Workflow

- PRs always target `staging` — never target `main` unless explicitly told
- Branch flow: feature → staging → main
- Push to `staging` deploys to staging instance
- Push to `main` deploys to production instance (when provisioned)
