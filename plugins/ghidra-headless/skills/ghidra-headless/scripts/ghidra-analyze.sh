#!/bin/bash
# Wrapper script for Ghidra headless analysis
# Handles project creation/cleanup and provides a simpler interface

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find analyzeHeadless
ANALYZE_HEADLESS=$("$SCRIPT_DIR/find-ghidra.sh")
export GHIDRA_HOME
GHIDRA_HOME=$(dirname "$(dirname "$ANALYZE_HEADLESS")")

show_help() {
  cat <<'EOF'
Usage: ghidra-analyze.sh [options] <binary>

Analyze a binary file using Ghidra's headless analyzer.

Options:
  -o, --output <dir>       Output directory for results (default: current dir)
  -s, --script <name>      Post-analysis script to run (can be repeated)
  -a, --script-args <args> Arguments for the last specified script
  --script-path <path>     Additional script search path
  -p, --processor <id>     Processor/architecture (e.g., x86:LE:32:default)
  -c, --cspec <id>         Compiler spec (e.g., gcc, windows)
  --no-analysis            Skip auto-analysis
  --timeout <seconds>      Analysis timeout per file
  --keep-project           Keep the Ghidra project after analysis
  --project-dir <dir>      Directory for Ghidra project (default: /tmp)
  --project-name <name>    Project name (default: auto-generated)
  -v, --verbose            Verbose output
  -h, --help               Show this help

Built-in Scripts (use with -s):
  ExportDecompiled.java    Export all functions as decompiled C code
  ExportFunctions.java     Export function list with addresses and signatures
  ExportStrings.java       Export all strings found in the binary
  ExportCalls.java         Export function call graph
  ExportSymbols.java       Export all symbols and their addresses

Examples:
  # Basic analysis with decompilation output
  ghidra-analyze.sh -s ExportDecompiled.java -o ./output myprogram

  # Analyze with specific architecture
  ghidra-analyze.sh -p ARM:LE:32:v7 firmware.bin

  # Run multiple scripts
  ghidra-analyze.sh -s ExportFunctions.java -s ExportStrings.java binary

  # Keep project for later use
  ghidra-analyze.sh --keep-project --project-name MyProject binary
EOF
}

# Default values
OUTPUT_DIR="."
SCRIPTS=()
SCRIPT_ARGS=()
SCRIPT_PATH=""
PROCESSOR=""
CSPEC=""
NO_ANALYSIS=""
TIMEOUT=""
KEEP_PROJECT=false
PROJECT_DIR="/tmp"
PROJECT_NAME=""
VERBOSE=false
BINARY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -o | --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -s | --script)
      SCRIPTS+=("$2")
      shift 2
      ;;
    -a | --script-args)
      # Associate args with the last script
      if [[ ${#SCRIPTS[@]} -gt 0 ]]; then
        SCRIPT_ARGS+=("${#SCRIPTS[@]}:$2")
      fi
      shift 2
      ;;
    --script-path)
      SCRIPT_PATH="$2"
      shift 2
      ;;
    -p | --processor)
      PROCESSOR="$2"
      shift 2
      ;;
    -c | --cspec)
      CSPEC="$2"
      shift 2
      ;;
    --no-analysis)
      NO_ANALYSIS="-noanalysis"
      shift
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --keep-project)
      KEEP_PROJECT=true
      shift
      ;;
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    --project-name)
      PROJECT_NAME="$2"
      shift 2
      ;;
    -v | --verbose)
      VERBOSE=true
      shift
      ;;
    -h | --help)
      show_help
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
    *)
      BINARY="$1"
      shift
      ;;
  esac
done

if [[ -z "$BINARY" ]]; then
  echo "Error: No binary file specified" >&2
  show_help
  exit 1
fi

if [[ ! -f "$BINARY" ]]; then
  echo "Error: Binary file not found: $BINARY" >&2
  exit 1
fi

# Create output directory if needed
mkdir -p "$OUTPUT_DIR"

# Generate project name if not specified
if [[ -z "$PROJECT_NAME" ]]; then
  PROJECT_NAME="ghidra_$(basename "$BINARY" | tr '.' '_')_$$"
fi

# Build script path including our built-in scripts
BUILTIN_SCRIPTS="$SCRIPT_DIR/ghidra_scripts"
if [[ -n "$SCRIPT_PATH" ]]; then
  FULL_SCRIPT_PATH="$BUILTIN_SCRIPTS;$SCRIPT_PATH"
else
  FULL_SCRIPT_PATH="$BUILTIN_SCRIPTS"
fi

# Build command
CMD=("$ANALYZE_HEADLESS" "$PROJECT_DIR" "$PROJECT_NAME" -import "$BINARY")

# Add script path
CMD+=(-scriptPath "$FULL_SCRIPT_PATH")

# Add scripts
for i in "${!SCRIPTS[@]}"; do
  script="${SCRIPTS[$i]}"
  CMD+=(-postScript "$script")

  # Check if there are args for this script
  for arg_entry in ${SCRIPT_ARGS[@]+"${SCRIPT_ARGS[@]}"}; do
    idx="${arg_entry%%:*}"
    args="${arg_entry#*:}"
    if [[ "$idx" -eq $((i + 1)) ]]; then
      # Append script arguments
      # Intentional word splitting for script args
      # shellcheck disable=SC2206
      CMD+=($args)
    fi
  done
done

# Add output directory as environment variable for scripts
export GHIDRA_OUTPUT_DIR="$OUTPUT_DIR"

# Add processor if specified
if [[ -n "$PROCESSOR" ]]; then
  CMD+=(-processor "$PROCESSOR")
fi

# Add compiler spec if specified
if [[ -n "$CSPEC" ]]; then
  CMD+=(-cspec "$CSPEC")
fi

# Add no-analysis flag if specified
if [[ -n "$NO_ANALYSIS" ]]; then
  CMD+=("$NO_ANALYSIS")
fi

# Add timeout if specified
if [[ -n "$TIMEOUT" ]]; then
  CMD+=(-analysisTimeoutPerFile "$TIMEOUT")
fi

# Delete project after analysis unless keeping it
if [[ "$KEEP_PROJECT" != true ]]; then
  CMD+=(-deleteProject)
fi

# Add log file
LOG_FILE="$OUTPUT_DIR/ghidra_analysis.log"
CMD+=(-log "$LOG_FILE")

# Run the analysis
if [[ "$VERBOSE" == true ]]; then
  echo "Running: ${CMD[*]}"
fi

"${CMD[@]}" 2>&1 | tee "$OUTPUT_DIR/ghidra_output.log"

exit_code=${PIPESTATUS[0]}

if [[ $exit_code -eq 0 ]]; then
  echo ""
  echo "Analysis complete. Output files in: $OUTPUT_DIR"
  ls -la "$OUTPUT_DIR"
else
  echo "Analysis failed with exit code: $exit_code" >&2
  echo "Check log file: $LOG_FILE" >&2
fi

exit "$exit_code"
