# wooyun-legacy

Web vulnerability testing methodology distilled from 88,636 real-world
cases from the WooYun vulnerability database (2010-2016).

## Installation

```
/plugin marketplace add trailofbits/skills-curated
/plugin menu
```

Select **wooyun-legacy** from the plugin list.

## Usage

The skill activates automatically when performing:

- Penetration testing or vulnerability assessment
- Security-focused code review
- Vulnerability research
- Security test case development

## Coverage

### Full References (methodology + bypass techniques + case analysis)

| Category | Cases | File |
|----------|-------|------|
| SQL Injection | 27,732 | `references/sql-injection.md` |
| XSS | 7,532 | `references/xss.md` |
| Command Execution | 6,826 | `references/command-execution.md` |
| File Upload | 2,711 | `references/file-upload.md` |
| Path Traversal | 2,854 | `references/path-traversal.md` |
| Unauthorized Access | 14,377 | `references/unauthorized-access.md` |
| Information Disclosure | 7,337 | `references/info-disclosure.md` |
| Business Logic Flaws | 8,292 | `references/logic-flaws.md` |

### Testing Checklists (empirical patterns from case data)

| Category | File |
|----------|------|
| SQL Injection | `references/checklists/sql-injection-checklist.md` |
| XSS | `references/checklists/xss-checklist.md` |
| Command Execution | `references/checklists/command-execution-checklist.md` |
| File Upload | `references/checklists/file-upload-checklist.md` |
| Path Traversal | `references/checklists/path-traversal-checklist.md` |
| Unauthorized Access | `references/checklists/unauthorized-access-checklist.md` |
| Information Disclosure | `references/checklists/info-disclosure-checklist.md` |
| Business Logic Flaws | `references/checklists/logic-flaws-checklist.md` |
| CSRF | `references/checklists/csrf-checklist.md` |
| SSRF | `references/checklists/ssrf-checklist.md` |
| Weak Passwords | `references/checklists/weak-password-checklist.md` |
| Misconfiguration | `references/checklists/misconfig-checklist.md` |
| RCE | `references/checklists/rce-checklist.md` |
| XXE | `references/checklists/xxe-checklist.md` |

### Methodology Case Studies (anonymized)

| Case Study | File |
|------------|------|
| Financial institution attack chain | `references/bank-penetration.md` |
| Telecom carrier penetration | `references/telecom-penetration.md` |

## Attribution

This plugin is based on [wooyun-legacy](https://github.com/tanweai/wooyun-legacy)
by tanweai and the wooyun-legacy contributors. The original knowledge
base was built from the WooYun open vulnerability disclosure platform
(2010-2016).

Content has been translated from Chinese to English, anonymized (vendor
names, IP addresses, and domains replaced with generic descriptions),
and restructured into the Claude Code plugin format.

## License

This plugin is licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
(Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International).

This license differs from the repository-level license. You may share
and adapt this material for non-commercial purposes, with attribution,
under the same license terms.

## Disclaimer

This knowledge base is provided for educational purposes and authorized
security testing only. Use only against systems you have explicit
permission to test. The authors are not responsible for misuse.
