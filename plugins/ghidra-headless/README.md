# Ghidra Headless

Reverse engineer binaries using Ghidra's headless analyzer. Decompile executables, extract functions, strings, symbols, and analyze call graphs without GUI.

## Installation

```
/plugin install ghidra-headless
```

## Prerequisites

- [Ghidra](https://ghidra-sre.org/) installed (`brew install --cask ghidra` on macOS)
- Java (OpenJDK 17+)

## What It Covers

- Headless binary analysis via `analyzeHeadless` wrapper
- Decompilation to C pseudocode
- Function extraction with signatures and call relationships
- String and symbol extraction
- Call graph analysis
- Architecture-specific analysis (x86, ARM, MIPS, PowerPC)
- Batch analysis of multiple binaries

## Credits

Imported from [mitsuhiko/agent-stuff](https://github.com/mitsuhiko/agent-stuff/tree/main/skills/ghidra) by Armin Ronacher. Licensed under Apache-2.0.
