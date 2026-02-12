---
name: ghidra-headless
description: >-
  Reverse engineers binaries using Ghidra's headless analyzer. Use when
  decompiling executables, extracting functions, strings, symbols, or
  analyzing call graphs from compiled binaries without the Ghidra GUI.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# Ghidra Headless Analysis

Perform automated reverse engineering using Ghidra's `analyzeHeadless` tool.
Import binaries, run analysis, decompile to C code, and extract useful
information.

## When to Use

- Decompiling a binary to C pseudocode for review
- Extracting function signatures, strings, or symbols from executables
- Analyzing call graphs to understand binary control flow
- Triaging unknown binaries or firmware images
- Batch-analyzing multiple binaries for comparison
- Security auditing compiled code without source access

## When NOT to Use

- Source code is available — read it directly instead
- Interactive debugging is needed — use GDB, LLDB, or Ghidra GUI
- The binary is a .NET assembly — use dnSpy or ILSpy
- The binary is Java bytecode — use jadx or cfr
- Dynamic analysis is required — use a debugger or sandbox

## Quick Reference

| Task | Command |
|------|---------|
| Full analysis with all exports | `{baseDir}/scripts/ghidra-analyze.sh -s ExportAll.java -o ./output binary` |
| Decompile to C code | `{baseDir}/scripts/ghidra-analyze.sh -s ExportDecompiled.java -o ./output binary` |
| List functions | `{baseDir}/scripts/ghidra-analyze.sh -s ExportFunctions.java -o ./output binary` |
| Extract strings | `{baseDir}/scripts/ghidra-analyze.sh -s ExportStrings.java -o ./output binary` |
| Get call graph | `{baseDir}/scripts/ghidra-analyze.sh -s ExportCalls.java -o ./output binary` |
| Export symbols | `{baseDir}/scripts/ghidra-analyze.sh -s ExportSymbols.java -o ./output binary` |
| Find Ghidra path | `{baseDir}/scripts/find-ghidra.sh` |

## Prerequisites

- **Ghidra** must be installed. On macOS: `brew install --cask ghidra`
- **Java** (OpenJDK 17+) must be available

The skill automatically locates Ghidra in common installation paths. Set
`GHIDRA_HOME` environment variable if Ghidra is installed in a non-standard
location.

## Main Wrapper Script

```bash
{baseDir}/scripts/ghidra-analyze.sh [options] <binary>
```

Wrapper that handles project creation/cleanup and provides a simpler
interface to `analyzeHeadless`.

**Options:**
- `-o, --output <dir>` — Output directory for results (default: current dir)
- `-s, --script <name>` — Post-analysis script to run (can be repeated)
- `-a, --script-args <args>` — Arguments for the last specified script
- `--script-path <path>` — Additional script search path
- `-p, --processor <id>` — Processor/architecture (e.g., `x86:LE:32:default`)
- `-c, --cspec <id>` — Compiler spec (e.g., `gcc`, `windows`)
- `--no-analysis` — Skip auto-analysis (faster, but less info)
- `--timeout <seconds>` — Analysis timeout per file
- `--keep-project` — Keep the Ghidra project after analysis
- `--project-dir <dir>` — Directory for Ghidra project (default: /tmp)
- `--project-name <name>` — Project name (default: auto-generated)
- `-v, --verbose` — Verbose output

## Built-in Export Scripts

### ExportAll.java

Runs summary, decompilation, function list, strings, and interesting-pattern
exports. Does not include call graph or symbols — run ExportCalls.java and
ExportSymbols.java separately if needed. Best for initial analysis.

**Output files:**
- `{name}_summary.txt` — Overview: architecture, memory sections, function counts
- `{name}_decompiled.c` — All functions decompiled to C
- `{name}_functions.json` — Function list with signatures and calls
- `{name}_strings.txt` — All strings found (plain text; use ExportStrings.java for JSON)
- `{name}_interesting.txt` — Functions matching security-relevant patterns

```bash
{baseDir}/scripts/ghidra-analyze.sh -s ExportAll.java -o ./analysis firmware.bin
```

### ExportDecompiled.java

Decompile all functions to C pseudocode.

**Output:** `{name}_decompiled.c`

### ExportFunctions.java

Export function list as JSON with addresses, signatures, parameters, and
call relationships.

**Output:** `{name}_functions.json`

### ExportStrings.java

Extract all strings (ASCII, Unicode) with addresses.

**Output:** `{name}_strings.json`

### ExportCalls.java

Export function call graph showing caller/callee relationships. Includes
full call graph, potential entry points, and most frequently called functions.

**Output:** `{name}_calls.json`

### ExportSymbols.java

Export all symbols: imports, exports, and internal symbols.

**Output:** `{name}_symbols.json`

## Common Workflows

### Analyze an Unknown Binary

```bash
mkdir -p ./analysis
{baseDir}/scripts/ghidra-analyze.sh -s ExportAll.java -o ./analysis unknown_binary
cat ./analysis/unknown_binary_summary.txt
cat ./analysis/unknown_binary_interesting.txt
```

### Analyze Firmware

```bash
{baseDir}/scripts/ghidra-analyze.sh \
    -p "ARM:LE:32:v7" \
    -s ExportAll.java \
    -o ./firmware_analysis \
    firmware.bin
```

### Quick Function Listing

```bash
{baseDir}/scripts/ghidra-analyze.sh --no-analysis -s ExportFunctions.java -o . program
cat program_functions.json | jq '.functions[] | "\(.address): \(.name)"'
```

### Find Specific Patterns

```bash
# After running ExportDecompiled, search for patterns
grep -n "password\|secret\|key" output_decompiled.c
grep -n "strcpy\|sprintf\|gets" output_decompiled.c
```

## Architecture/Processor IDs

Common processor IDs for the `-p` option:

| Architecture | Processor ID |
|-------------|--------------|
| x86 32-bit | `x86:LE:32:default` |
| x86 64-bit | `x86:LE:64:default` |
| ARM 32-bit | `ARM:LE:32:v7` |
| ARM 64-bit | `AARCH64:LE:64:v8A` |
| MIPS 32-bit | `MIPS:BE:32:default` or `MIPS:LE:32:default` |
| PowerPC | `PowerPC:BE:32:default` |

## Troubleshooting

### Ghidra Not Found

```bash
{baseDir}/scripts/find-ghidra.sh
# Or set GHIDRA_HOME if in non-standard location
export GHIDRA_HOME=/path/to/ghidra_11.x_PUBLIC
```

### Analysis Takes Too Long

```bash
{baseDir}/scripts/ghidra-analyze.sh --timeout 300 -s ExportAll.java binary
# Or skip analysis for quick export
{baseDir}/scripts/ghidra-analyze.sh --no-analysis -s ExportSymbols.java binary
```

### Out of Memory

Set before running:
```bash
export MAXMEM=4G
```

### Wrong Architecture Detected

Explicitly specify the processor:
```bash
{baseDir}/scripts/ghidra-analyze.sh -p "ARM:LE:32:v7" -s ExportAll.java firmware.bin
```

## Tips

1. **Start with ExportAll.java** — gives everything; the summary helps orient
2. **Check interesting.txt** — highlights security-relevant functions automatically
3. **Use jq for JSON parsing** — JSON exports are designed to be machine-readable
4. **Decompilation isn't perfect** — use as a guide, cross-reference with disassembly
5. **Large binaries take time** — use `--timeout` and consider `--no-analysis` for quick scans
