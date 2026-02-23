---
name: ffuf-web-fuzzing
description: >-
  Expert guidance for ffuf web fuzzing during authorized penetration testing.
  Covers directory discovery, subdomain enumeration, parameter fuzzing,
  authenticated fuzzing with raw requests, auto-calibration, and result
  analysis. Use when running ffuf scans, analyzing ffuf output, or building
  fuzzing strategies for web targets.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# FFUF Web Fuzzing

Guidance for using ffuf (Fuzz Faster U Fool) effectively during authorized penetration testing.

## Prerequisites

ffuf must be installed: `brew install ffuf` (macOS) or `go install github.com/ffuf/ffuf/v2@latest`

## When to Use

- Running directory, file, or subdomain discovery against web targets
- Fuzzing API endpoints, parameters, or POST data
- Authenticated fuzzing with raw HTTP requests
- Analyzing ffuf JSON output for anomalies and interesting findings
- Building fuzzing strategies (wordlist selection, filtering, rate limiting)
- IDOR testing with authenticated sessions

## When NOT to Use

- Target system is not in scope or authorization is unclear
- Passive reconnaissance is more appropriate (use OSINT tools instead)
- The target is a production system and rate limiting hasn't been configured
- You need a full vulnerability scanner (use Burp Suite, Nuclei, etc.)
- Testing for logic flaws that require multi-step interaction

## Rationalizations to Reject

- "Auto-calibration is optional" -- `-ac` is mandatory. Without it, results are buried in false positives and analysis is wasted effort.
- "More threads = faster results" -- Hammering a target with `-t 200` triggers WAFs, gets you blocked, and may crash staging environments. Start with `-t 10 -rate 2` for production targets.
- "I'll filter later" -- Set up filtering before the scan. Running a 220k wordlist without filters and then trying to grep through the noise is backwards.
- "The default wordlist is fine" -- Wordlist selection is the most important decision. A generic wordlist misses technology-specific paths. See [references/wordlists.md](references/wordlists.md).
- "Raw requests are too much work" -- For authenticated fuzzing, `--request req.txt` is simpler and more reliable than chaining `-H` and `-b` flags. Capture once, fuzz many times.

## Critical Rules

1. **Always use `-ac`** (auto-calibration) unless you have a specific, documented reason not to
2. **Always save output** with `-o results.json` for later analysis
3. **Rate limit production targets** with `-rate` and `-t` flags
4. **Use `--request` for auth** -- raw request files beat command-line header chains
5. **Confirm authorization first** -- before running any scan, verify the user has written permission for the target. Ask if unclear.

## Core Concepts

### The FUZZ Keyword

```bash
# In URL path
ffuf -w wordlist.txt -u https://target.com/FUZZ -ac

# In headers
ffuf -w wordlist.txt -u https://target.com -H "Host: FUZZ.target.com" -ac

# In POST body
ffuf -w wordlist.txt -X POST -d "user=admin&pass=FUZZ" -u https://target.com/login -ac

# Multiple positions with custom keywords
ffuf -w endpoints.txt:EP -w ids.txt:ID -u https://target.com/EP/ID -mode pitchfork -ac
```

### Auto-Calibration

`-ac` automatically detects and filters repetitive false-positive responses. It adapts to the target's specific behavior and removes noise from dynamic content.

```bash
ffuf -w wordlist.txt -u https://target.com/FUZZ -ac        # Standard
ffuf -w wordlist.txt -u https://target.com/FUZZ -ach       # Per-host (multi-host scans)
ffuf -w wordlist.txt -u https://target.com/FUZZ -acc "404" # Custom calibration string
```

## Common Patterns

### Directory Discovery

```bash
ffuf -w /opt/SecLists/Discovery/Web-Content/raft-large-directories.txt \
     -u https://target.com/FUZZ -e .php,.html,.txt,.bak \
     -ac -c -v -o results.json
```

### Subdomain Enumeration

```bash
ffuf -w /opt/SecLists/Discovery/DNS/subdomains-top1million-5000.txt \
     -u https://FUZZ.target.com -ac -c -v -o results.json
```

### API Endpoint Discovery

```bash
ffuf -w /opt/SecLists/Discovery/Web-Content/api/api-endpoints.txt \
     -u https://api.target.com/v1/FUZZ \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" -mc 200,201 -ac -c
```

### Authenticated Fuzzing with Raw Requests

Capture a full authenticated request, save to `req.txt`, insert `FUZZ`:

```http
POST /api/v1/users/FUZZ HTTP/1.1
Host: target.com
Authorization: Bearer YOUR_TOKEN_HERE
Cookie: session=YOUR_SESSION_ID
Content-Type: application/json

{"action":"view","id":"1"}
```

```bash
ffuf --request req.txt -w wordlist.txt -ac -o results.json
```

See [references/request-templates.md](references/request-templates.md) for pre-built templates covering bearer tokens, session cookies, API keys, and GraphQL.

### Authenticated Fuzzing: Agent Workflow

Authenticated fuzzing requires real credentials that the agent cannot obtain independently. When the user asks for authenticated fuzzing:

1. Ask the user to provide ONE of:
   - A raw HTTP request file (`req.txt`) with auth headers already included
   - A curl command from browser DevTools (convert it to `req.txt` format)
   - Individual credentials (Bearer token, session cookie, API key)
2. If given a curl command, convert it to raw HTTP request format and write to `req.txt`
3. If given individual credentials, use a template from [references/request-templates.md](references/request-templates.md) and substitute real values
4. Never fabricate or guess authentication tokens

### IDOR Testing

```bash
ffuf --request req.txt -w <(seq 1 10000) -ac -mc 200 -o idor_results.json
```

## Rate Limiting

| Environment | Flags | Notes |
|-------------|-------|-------|
| Production (stealth) | `-rate 2 -t 10` | Avoid WAF triggers |
| Production (normal) | `-rate 10 -t 20` | Balanced |
| Staging/Dev | `-rate 50 -t 40` | Faster |
| Local/Lab | No limit, `-t 100` | Maximum speed |

## Analyzing Results

Save output as JSON (`-o results.json`), then read the file and focus on:

- **Anomalous status codes** -- anything other than the baseline 404/403
- **Size outliers** -- responses significantly larger or smaller than average
- **Interesting keywords** in URLs -- admin, api, backup, config, .git, .env
- **Timing anomalies** -- slow responses may indicate SQL injection or heavy processing
- **Follow-up targets** -- interesting findings warrant deeper fuzzing

Use `-fs` to filter by response size and `-fc` to filter by status code when auto-calibration isn't sufficient. Run `ffuf -h` for the full list of match/filter flags.

## References

- [Wordlist selection guide](references/wordlists.md) -- recommended SecLists by scenario
- [Authenticated request templates](references/request-templates.md) -- pre-built req.txt for bearer tokens, cookies, API keys
- [ffuf official docs](https://github.com/ffuf/ffuf/wiki)
- [SecLists](https://github.com/danielmiessler/SecLists)
