# SCV Scan

Audits Solidity codebases for smart contract vulnerabilities using a four-phase workflow (cheatsheet loading, codebase sweep, deep validation, reporting) covering 36 vulnerability classes.

## Install

```
/plugin install trailofbits/skills-curated/plugins/scv-scan
```

## Prerequisites

None. The skill uses grep/ripgrep for scanning and reads Solidity files directly.

## What It Covers

The skill references 36 vulnerability classes including:

- Reentrancy (single-function, cross-function, cross-contract, read-only)
- Integer overflow/underflow (unchecked blocks, assembly, type downcasts)
- Access control (missing modifiers, unprotected initializers)
- Signature vulnerabilities (replay, malleability, ecrecover null address)
- Delegatecall to untrusted callee
- DoS (gas limit, unexpected revert)
- Frontrunning / transaction-ordering dependence
- Hash collisions with abi.encodePacked
- Weak randomness sources
- And 27 more — see `references/CHEATSHEET.md` for the full list

## How It Works

1. **Load Cheatsheet** — Reads a condensed lookup table of all 36 vulnerability classes with grep-able keywords
2. **Codebase Sweep** — Syntactic grep scan + semantic read-through for logic bugs
3. **Deep Validation** — For each candidate, reads the full reference file and walks through detection heuristics and false-positive conditions
4. **Report** — Confirmed findings output with severity, code snippets, and fix recommendations

## Credits

- **Source:** [kadenzipfel/scv-scan](https://github.com/kadenzipfel/scv-scan)
- **Author:** kadenzipfel
- **Vulnerability data:** [smart-contract-vulnerabilities](https://github.com/kadenzipfel/smart-contract-vulnerabilities)
- **License:** Not specified
