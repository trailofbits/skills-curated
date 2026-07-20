---
name: using-hermes-tweet
version: 0.1.8
description: |
  Guides Hermes Agent sessions that use Hermes Tweet for X/Twitter search,
  account reads, monitored workflows, giveaway audits, and approval-gated
  account actions. Use when Hermes Tweet is installed in the Hermes runtime and
  the user asks to inspect X/Twitter, find the right route, or understand why
  read or action tools are unavailable.
---

# Using Hermes Tweet

Hermes Tweet is a native Hermes Agent plugin for X/Twitter workflows. Use this
skill only when the user is operating a Hermes Agent runtime where Hermes Tweet
can expose its tools.

Hermes Tweet is MIT licensed. It uses Xquik, a hosted closed-source service.
Xquik is an independent third-party service and is not affiliated with X Corp.

## When to Use

- The user asks for X/Twitter search, profile reads, trends, mentions, media,
  giveaway evidence, or monitored social listening through Hermes Agent.
- The user needs to find the correct Hermes Tweet route before calling a tool.
- The user asks why `tweet_read` or `tweet_action` is unavailable.
- The user is using Hermes Desktop, CLI, TUI, or a remote gateway profile and
  needs to understand where Hermes Tweet must be installed and configured.
- The workflow needs a clear split between read-only research and
  account-changing actions.

## When NOT to Use

- The user wants a generic Claude Code X/Twitter scraper or direct X API helper.
- The Hermes runtime does not have Hermes Tweet installed and enabled.
- The task is only a normal web search, social media copywriting task, or
  unrelated marketing workflow.
- The user asks for TweetClaw-specific routes, Xquik-only implementation
  details, or unsupported internal routing behavior.
- The task would change an account and the user has not approved the exact
  action.

## Quick Start

1. Confirm Hermes Tweet is installed and enabled in the Hermes runtime.
2. Use `tweet_explore` first to find the route.
3. Use `tweet_read` only for public read-only catalog entries.
4. Use `tweet_action` only for private reads, writes, monitors, webhooks,
   extraction jobs, media, draws, or other account-affecting routes after the
   user approves the endpoint and payload.
5. If a tool is missing, explain the runtime gate instead of asking for secrets
   in chat.

## Tool Selection

Use this order:

1. `tweet_explore` for discovery. It does not require an API key.
2. `tweet_read` for catalog-listed read-only `GET` routes.
3. `tweet_action` for non-`GET` routes or private account state, only when the
   action gate is enabled and the user approved the operation.

Never guess endpoint paths. Do not call routes that are absent from the catalog.

## Runtime Checks

- If Hermes lists the plugin as not enabled, tell the user to enable
  `hermes-tweet` in the Hermes plugin manager.
- If `tweet_read` is unavailable, explain that the Hermes runtime needs its API
  key configured outside chat.
- If `tweet_action` is unavailable, explain that account-changing actions are
  intentionally gated and disabled unless the runtime enables them.
- If the user is on Hermes Desktop with a remote gateway profile, install and
  configure Hermes Tweet on the remote Hermes host, because that is where plugin
  code runs.

## Safety Rules

- Never ask for API keys, signing keys, passwords, cookies, TOTP secrets, or
  session material.
- Never put credentials in tool arguments, examples, issue bodies, logs, or
  prompts.
- Keep read-only workflows read-only unless the user explicitly requests and
  approves an action.
- Do not use billing, credit top-up, support-ticket, API-key, account
  connection, or re-authentication routes.
- For posting, deleting, following, DMs, profile changes, monitors, webhooks,
  extraction jobs, media, and draws, summarize the exact endpoint and payload
  before calling `tweet_action`.

## Examples

Search public X/Twitter posts:

```json
{"query":"tweet search","method":"GET"}
```

Then call `tweet_read` only after `tweet_explore` returns a matching read-only
catalog path.

Prepare a user-approved post:

```json
{"query":"post tweet","include_actions":true}
```

Then call `tweet_action` only after the user confirms the route, account, text,
and reason for the post.

## Attribution

Source: https://github.com/Xquik-dev/hermes-tweet

The source project is MIT licensed. This marketplace package adapts the public
Hermes Tweet skill guidance for Claude Code users who also operate Hermes Agent.
