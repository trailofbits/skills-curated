# Hermes Tweet

Claude Code guidance for using the Hermes Tweet plugin with Hermes Agent.

## Installation

```
/plugin install trailofbits/skills-curated/plugins/hermes-tweet
```

## Usage

Use this skill when a Claude Code session needs to configure, validate, or
operate the public Hermes Tweet plugin for Hermes Agent X/Twitter workflows.

It helps the agent choose the least-privilege Hermes Tweet tool path:

- `tweet_explore` for catalog discovery
- `tweet_read` for catalog-listed read-only routes
- `tweet_action` only for private or account-changing routes after explicit approval

The skill also keeps `XQUIK_API_KEY` in the runtime environment, keeps
`HERMES_TWEET_ENABLE_ACTIONS` disabled unless the user intentionally enables
actions, and reminds remote gateway users to configure Hermes Tweet on the host
where Hermes tools execute.

## Scope

This plugin is a guidance wrapper for Claude Code. It does not include the
Hermes Tweet runtime package, hooks, helper scripts, API keys, or cached API
payloads.

Install the Hermes Agent plugin from the upstream project when the Hermes
runtime needs the actual tools:

```bash
hermes plugins install Xquik-dev/hermes-tweet --enable
hermes tools list
```

## Credits

Based on the public [Xquik-dev/hermes-tweet](https://github.com/Xquik-dev/hermes-tweet)
project. The upstream package is MIT licensed; this curated wrapper contains
only Claude Code usage guidance.
