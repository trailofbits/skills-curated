# SocialClaw

Schedule and publish social media posts across 13 platforms via SocialClaw.

## Installation

```
/plugin install trailofbits/skills-curated/plugins/socialclaw
```

## Usage

The skill activates when you ask Claude Code to schedule posts, connect social accounts, upload media for publishing, or inspect run status across social platforms.

**Supported platforms:** X, LinkedIn (profile + page), Instagram (Business + standalone), Facebook Pages, TikTok, Discord, Telegram, YouTube, Reddit, WordPress, Pinterest

## Requirements

1. A SocialClaw workspace API key — sign in at https://getsocialclaw.com/dashboard
2. Set `SC_API_KEY` in your environment
3. Connect your social accounts from the dashboard

## Example

```bash
export SC_API_KEY="<workspace-key>"
socialclaw accounts list --json
socialclaw assets upload --file ./image.png --json
socialclaw apply -f schedule.json --json
```

## Security

- Outbound requests go to `getsocialclaw.com` only
- Provider secrets are never handled by the agent — users connect accounts via OAuth in the SocialClaw dashboard
- Source: https://github.com/ndesv21/socialclaw
