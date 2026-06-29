---
name: hermes-tweet
version: 0.1.6
description: |
  Use Hermes Tweet when a Claude Code session needs to install, configure,
  validate, or operate the public Hermes Agent X/Twitter plugin. Guides agents
  through read-first tool selection, runtime-only secret handling, remote
  gateway setup, and explicit approval before account-changing actions.
allowed-tools:
  - Read
  - Grep
---

# Hermes Tweet

Hermes Tweet is a public Hermes Agent plugin for X/Twitter workflows. This skill
helps Claude Code reason about the plugin safely without bundling the runtime
package or any credentials.

## When to Use

Use this skill when the user asks for Hermes Agent help involving X/Twitter
research, account context, social listening, launch monitoring, support triage,
creator research, brand research, giveaway audits, media workflows, or
controlled publishing through Hermes Tweet.

Use it when the task is about:

- Installing or enabling `hermes-tweet` in a Hermes Agent runtime.
- Checking why Hermes Agent does not show the Hermes Tweet toolset.
- Choosing between `tweet_explore`, `tweet_read`, and `tweet_action`.
- Keeping X/Twitter reads separate from private or account-changing actions.
- Configuring a remote Hermes gateway where plugin tools execute on another host.

## When NOT to Use

- General X/Twitter research that does not involve Hermes Agent or Hermes Tweet.
- Direct API scripting outside Hermes Agent's plugin toolset.
- Posting, deleting, following, sending DMs, changing profiles, or creating
  monitors without explicit user approval.
- Collecting API keys, cookies, passwords, TOTP codes, or session material in chat.
- Bypassing Hermes Tweet by guessing endpoint URLs or making direct HTTP fallbacks.

## Operating Rules

Start with `tweet_explore` whenever the endpoint or capability is unclear. Treat
the returned catalog as the source of truth for valid `/api/v1/...` paths.

Use `tweet_read` for catalog-listed read-only routes. Prefer it for unattended,
scheduled, monitoring, and research workflows.

Use `tweet_action` only for private reads or account-changing operations after
the user approves the exact route, payload shape, and side effect. Explain that
actions are intentionally gated by `HERMES_TWEET_ENABLE_ACTIONS=true`.

Never ask for `XQUIK_API_KEY` values in chat. Ask the user to set
`XQUIK_API_KEY` in the Hermes runtime environment or in `~/.hermes/.env`.

For remote gateway or Desktop profiles, configure Hermes Tweet on the remote
Hermes host. The chat surface is not necessarily where plugin tools execute.

## Install And Validate

Recommended Hermes Agent install:

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
```

If the plugin was installed without enabling it:

```bash
hermes plugins enable hermes-tweet
```

Validate the active runtime:

```bash
hermes plugins list
hermes tools list
```

Expected gating:

- `tweet_explore` is available without `XQUIK_API_KEY`.
- `tweet_read` requires `XQUIK_API_KEY`.
- `tweet_action` stays hidden or disabled unless `HERMES_TWEET_ENABLE_ACTIONS=true`.

## Examples

Input: "Use Hermes to find recent X posts about our launch."

Agent path: start with `tweet_explore` for tweet search routes, then use
`tweet_read` against the catalog-listed read route.

Input: "Post this approved update from the brand account."

Agent path: confirm the account, route, payload, and side effect first. Use
`tweet_action` only if `HERMES_TWEET_ENABLE_ACTIONS=true` in the Hermes runtime.

Input: "Hermes Desktop cannot see Hermes Tweet on my gateway."

Agent path: explain that plugin code runs on the gateway host. Check that
`hermes-tweet` is installed, enabled, and configured there, then validate with
`hermes plugins list` and `hermes tools list`.

## Safety Checklist

- Use only Hermes Tweet tools, not direct HTTP fallbacks.
- Keep secrets in runtime environment files, never in prompts or tool arguments.
- Confirm the route and payload before any action call.
- Keep action tools disabled by default.
- Do not use admin, billing, credit top-up, support-ticket, API-key, account
  connection, or re-authentication routes.
- Stop instead of retrying writes through alternate routes after auth, policy,
  or account-state errors.

## Attribution

This guidance is based on the public
[Xquik-dev/hermes-tweet](https://github.com/Xquik-dev/hermes-tweet) project.
The upstream runtime package is MIT licensed; this curated plugin contains only
Claude Code guidance for safe Hermes Agent use.
