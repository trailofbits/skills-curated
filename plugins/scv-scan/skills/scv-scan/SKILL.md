---
name: scv-scan
description: "Audits Solidity codebases for smart contract vulnerabilities using a four-phase workflow (cheatsheet loading, codebase sweep, deep validation, reporting) covering 36 vulnerability classes. Use when auditing Solidity contracts for security issues, performing smart contract vulnerability scans, or reviewing Solidity code for common exploit patterns."
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
  - Task
---

# Smart Contract Vulnerability Auditor

Systematically audit a Solidity codebase for vulnerabilities using a four-phase approach that balances thoroughness with efficiency.

## When to Use

- Auditing a Solidity codebase for security vulnerabilities before deployment
- Reviewing smart contract code for common exploit patterns (reentrancy, overflow, access control, etc.)
- Performing a structured vulnerability scan across an entire Solidity project
- Validating that a contract follows security best practices after modifications

## When NOT to Use

- Auditing non-Solidity smart contracts (Vyper, Rust/Anchor, Move) — patterns are Solidity-specific
- Reviewing off-chain code (JavaScript, TypeScript backends) — use general security review instead
- When the user only wants gas optimization or code style feedback — this focuses on exploitable vulnerabilities
- For formal verification of invariants — use tools like Certora, Halmos, or Echidna instead

## Rationalizations to Reject

- "The compiler version is >=0.8.0 so overflow isn't possible" — `unchecked` blocks, assembly, and type downcasts still wrap
- "It uses OpenZeppelin so it's safe" — integration bugs, incorrect inheritance order, and missing modifiers on custom functions are common
- "That function is internal so it can't be exploited" — internal functions called from external entry points inherit the caller's context
- "There's no ETH involved so reentrancy doesn't apply" — ERC721 `_safeMint`, ERC1155 safe transfers, and ERC777 hooks all trigger callbacks
- "The contract is upgradeable so we can fix it later" — `initialize()` without `initializer` modifier is itself a critical vulnerability

## Reference Structure

```
references/
  CHEATSHEET.md          # Condensed pattern reference — always read first
  reentrancy.md          # Full reference files — read selectively in Phase 3
  overflow-underflow.md
  ...
```

Each full reference file in `references/` has these sections:

- **Preconditions** — what must be true for the vulnerability to exist
- **Vulnerable Pattern** — annotated Solidity anti-pattern
- **Detection Heuristics** — step-by-step reasoning to confirm the vulnerability
- **False Positives** — when the pattern appears but isn't exploitable
- **Remediation** — how to fix it

## Audit Workflow

### Phase 1: Load the Cheatsheet

**Before touching any Solidity files**, read `{baseDir}/skills/scv-scan/references/CHEATSHEET.md` in full.

This file contains a condensed entry for every known vulnerability class: name, what to look for (syntactic and semantic), and default severity. Internalize these patterns — they are your detection surface for the sweep phase. Do NOT read any full reference files yet.

### Phase 2: Codebase Sweep

Perform two complementary passes over the codebase.

#### Pass A: Syntactic Grep Scan

Search for the trigger patterns listed in the cheatsheet under "Grep-able keywords". Use grep or ripgrep to find matches.

For each match, record: file, line number(s), matched pattern, and suspected vulnerability type(s).

#### Pass B: Structural / Semantic Analysis

This pass catches vulnerabilities that have no reliable grep signature. Read through the codebase searching for any relevant logic similar to that explained in the cheatsheet.

For each finding in this pass, record: file, line number(s), description of the concern, and suspected vulnerability type(s).

#### Compile Candidate List

Merge results from Pass A and Pass B into a deduplicated candidate list. Each entry should look like:

```
- File: `path/to/file.sol` L{start}-L{end}
- Suspected: [vulnerability-name] (from CHEATSHEET.md)
- Evidence: [brief description of what was found]
```

### Phase 3: Selective Deep Validation

For each candidate in the list:

1. **Read the full reference file** for the suspected vulnerability type (e.g., `{baseDir}/skills/scv-scan/references/reentrancy.md`). Read it now — not before.
2. **Walk through every Detection Heuristic step** against the actual code. Be precise — trace variable values, check modifiers, follow call chains.
3. **Check every False Positive condition**. If any false positive condition matches, discard the finding and note why.
4. **Cross-reference**: one code location can match multiple vulnerability types. If the cheatsheet maps the same pattern to multiple references, read and validate against each.
5. **Confirm or discard.** Only confirmed findings go into the final report.

### Phase 4: Report

For each confirmed finding, output:

```
### [Vulnerability Name]

**File:** `path/to/file.sol` L{start}-L{end}
**Severity:** Critical | High | Medium | Low | Informational

**Description:** What is vulnerable and why, in 1-3 sentences.

**Code:**
```solidity
// The vulnerable code snippet
```

**Recommendation:** Specific fix, referencing the Remediation section of the reference file.
```

After all findings, include a summary section:

```
## Summary

| Severity | Count |
|----------|-------|
| Critical | N     |
| High     | N     |
| Medium   | N     |
| Low      | N     |
| Info     | N     |
```

Write the final report to `scv-scan.md`.

## Severity Guidelines

- **Critical**: Direct loss of funds, unauthorized fund extraction, permanent freezing of funds
- **High**: Conditional fund loss, access control bypass, state corruption exploitable under realistic conditions
- **Medium**: Unlikely fund loss, griefing attacks, DoS on non-critical paths, value leak under edge conditions
- **Low**: Best practice violations, gas inefficiency, code quality issues with no direct exploit path
- **Informational**: Unused variables, style issues, documentation gaps

## Key Principles

- **Cheatsheet first, references on-demand.** Never read all full reference files upfront. The cheatsheet gives you ambient awareness; full references are for validation only.
- **Semantic > syntactic.** The hardest bugs don't grep. Cross-function reentrancy, missing access control, incorrect inheritance — these require reading and reasoning, not pattern matching.
- **Trace across boundaries.** Follow state across function calls, contract calls, and inheritance chains. Hidden external calls (safe mint/transfer hooks, ERC-777 callbacks) are as dangerous as explicit `.call()`.
- **One location, multiple bugs.** A single line can be vulnerable to reentrancy AND unchecked return value. Check all applicable references.
- **Version matters.** Always check `pragma solidity` — many vulnerabilities are version-dependent (e.g., overflow is checked by default in >=0.8.0).
- **False positives are noise.** Be rigorous about checking false positive conditions. A shorter report with high-confidence findings is more valuable than a long one padded with maybes.
