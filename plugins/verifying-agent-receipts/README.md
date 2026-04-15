# Verifying Agent Receipts

Teaches agents to verify cryptographically signed decision receipts produced by agent governance tooling. Covers Ed25519 signature verification, hash-chain integrity, tamper diagnosis, Cedar policy digest matching, and offline verification via `@veritasacta/verify`.

## Install

```
/plugin install trailofbits/skills-curated/plugins/verifying-agent-receipts
```

## What This Skill Does

When Claude encounters a signed receipt — a JSON file produced by `protect-mcp`, Microsoft Agent Governance Toolkit, Cedar-enforced MCP gateways, or any other system following the [IETF Internet-Draft for signed decision receipts](https://datatracker.ietf.org/doc/draft-farley-acta-signed-receipts/) — this skill teaches it to:

1. **Verify the Ed25519 signature** using `@veritasacta/verify` (Apache-2.0, offline, no network)
2. **Walk the hash chain** — confirm `parent_receipt_id` links resolve correctly
3. **Diagnose failures precisely** — signature mismatch vs. chain break vs. malformed receipt
4. **Resist common shortcuts** — the Rationalizations to Reject section catches the mistakes auditors make under time pressure

## Standards This Skill Works With

- **Ed25519** — [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032)
- **JCS** — [RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785)
- **Cedar** — [AWS's open authorization engine](https://www.cedarpolicy.com/)
- **IETF draft-farley-acta-signed-receipts** — signed decision receipt wire format

## What This Skill Does NOT Do

This is a **guidance-only skill**. It does not ship hooks, run background services, or make network calls from Claude Code. It teaches Claude how to reason about signed receipts and how to drive the external `@veritasacta/verify` CLI when the user chooses to install it. Runtime enforcement (policy evaluation before tool execution, signing after) is a separate tool — [`protect-mcp`](https://www.npmjs.com/package/protect-mcp) — that users install independently.

## License

MIT. See [LICENSE](./LICENSE).
