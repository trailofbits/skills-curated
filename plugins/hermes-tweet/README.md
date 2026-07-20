# hermes-tweet

Hermes Tweet guidance for Hermes Agent operators who need X/Twitter search,
account reads, monitored workflows, and approval-gated account actions.

Hermes Tweet is MIT licensed. It uses Xquik, a hosted closed-source service.
Xquik is an independent third-party service and is not affiliated with X Corp.

## Install

```text
/plugin install trailofbits/skills-curated/plugins/hermes-tweet
```

## Prerequisites

- Hermes Agent with the Hermes Tweet plugin installed and enabled.
- The Hermes runtime host configured with its required environment variables.
- Account-changing workflows approved by the user before action tools are used.

## What It Covers

- Finding the right Hermes Tweet route before making a call.
- Keeping read-only research separate from private or account-changing actions.
- Handling missing runtime credentials without asking for secrets in chat.
- Using Hermes Desktop, CLI, TUI, or gateway sessions with the same toolset.
- Avoiding unsupported billing, credential, re-authentication, and admin routes.

## Usage

Natural language examples:

- "Find recent X discussion about a launch."
- "Check public mentions before drafting a reply."
- "Use Hermes Tweet for a read-only giveaway audit."
- "Explain why tweet actions are unavailable in this session."

The skill is intentionally guidance-only. It adds no hooks or scripts and makes
no network calls by itself.

## Credits

Imported from Xquik-dev/hermes-tweet

Source: https://github.com/Xquik-dev/hermes-tweet

The source project is MIT licensed. This package adapts the public Hermes Tweet
skill guidance for this curated Claude Code marketplace.
