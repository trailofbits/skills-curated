---
name: socialclaw
description: Schedule and publish social media posts for AI agents across X, LinkedIn, Instagram, Facebook Pages, TikTok, Discord, Telegram, YouTube, Reddit, WordPress, and Pinterest via SocialClaw. Use when the user wants to connect social accounts, upload media, apply a post schedule, or inspect run analytics.
license: MIT
---

# SocialClaw

SocialClaw is a workspace-scoped social publishing service at `https://getsocialclaw.com`. This skill connects Claude Code to the SocialClaw API for agent-driven social publishing.

## Security Notes

- This skill makes outbound HTTPS requests to `getsocialclaw.com` only
- Authentication is via workspace API key (`SC_API_KEY`) — never provider secrets
- End users connect their own social accounts inside the SocialClaw dashboard
- No credentials are written to disk by this skill

## Runtime Requirements

- `SC_API_KEY` — workspace API key from `https://getsocialclaw.com/dashboard`
- Optional: `socialclaw` CLI (`npm install -g socialclaw`)
- Active trial or paid plan required for publishing

## Quick Start

```bash
# Set workspace API key
export SC_API_KEY="<workspace-key>"

# Verify access
curl -sS -H "Authorization: Bearer $SC_API_KEY" https://getsocialclaw.com/v1/keys/validate

# Or use the CLI
npm install -g socialclaw
socialclaw login --api-key <workspace-key>
socialclaw accounts list --json
```

## Workflow

1. **Get API key** — sign in at `https://getsocialclaw.com/dashboard`
2. **Connect accounts** — use `socialclaw accounts connect --provider <x|linkedin|...> --open`
3. **Upload media** — use `socialclaw assets upload --file <path> --json`
4. **Validate** — use `socialclaw validate -f schedule.json --json`
5. **Publish** — use `socialclaw apply -f schedule.json --json`
6. **Inspect** — use `socialclaw status --run-id <id>` and `socialclaw posts list`

## Supported Providers

X, LinkedIn (profile + page), Instagram (Business + standalone), Facebook Pages, TikTok, Discord, Telegram, YouTube, Reddit, WordPress, Pinterest

## Source

- GitHub: https://github.com/ndesv21/socialclaw
- npm: https://www.npmjs.com/package/socialclaw
