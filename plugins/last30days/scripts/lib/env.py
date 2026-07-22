"""Environment and API key management for last30days skill."""

import os
from pathlib import Path
from typing import Any

# Allow override via environment variable for testing
# Set LAST30DAYS_CONFIG_DIR="" for clean/no-config mode
# Set LAST30DAYS_CONFIG_DIR="/path/to/dir" for custom config location
_config_override = os.environ.get("LAST30DAYS_CONFIG_DIR")
if _config_override == "":
    # Empty string = no config file (clean mode)
    CONFIG_DIR = None
    CONFIG_FILE = None
elif _config_override:
    CONFIG_DIR = Path(_config_override)
    CONFIG_FILE = CONFIG_DIR / ".env"
else:
    CONFIG_DIR = Path.home() / ".config" / "last30days"
    CONFIG_FILE = CONFIG_DIR / ".env"


def load_env_file(path: Path) -> dict[str, str]:
    """Load environment variables from a file."""
    env = {}
    if not path.exists():
        return env

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                if key and value:
                    env[key] = value
    return env


def get_config() -> dict[str, Any]:
    """Load configuration from ~/.config/last30days/.env and environment."""
    # Load from config file first (if configured)
    file_env = load_env_file(CONFIG_FILE) if CONFIG_FILE else {}

    # Build config: process.env > .env file
    keys = [
        ("OPENAI_API_KEY", None),
        ("XAI_API_KEY", None),
        ("OPENROUTER_API_KEY", None),
        ("PARALLEL_API_KEY", None),
        ("BRAVE_API_KEY", None),
        ("OPENAI_MODEL_POLICY", "auto"),
        ("OPENAI_MODEL_PIN", None),
        ("XAI_MODEL_POLICY", "latest"),
        ("XAI_MODEL_PIN", None),
    ]

    config = {}
    for key, default in keys:
        config[key] = os.environ.get(key) or file_env.get(key, default)

    return config


def config_exists() -> bool:
    """Check if configuration file exists."""
    return CONFIG_FILE is not None and CONFIG_FILE.exists()


def get_available_sources(config: dict[str, Any]) -> str:
    """Determine which sources are available based on API keys.

    Returns: 'all', 'both', 'reddit', 'reddit-web', 'x', 'x-web', 'web', or 'none'
    """
    has_openai = bool(config.get("OPENAI_API_KEY"))
    has_xai = bool(config.get("XAI_API_KEY"))
    has_web = has_web_search_keys(config)

    if has_openai and has_xai:
        return "all" if has_web else "both"
    elif has_openai:
        return "reddit-web" if has_web else "reddit"
    elif has_xai:
        return "x-web" if has_web else "x"
    elif has_web:
        return "web"
    else:
        return "web"  # Fallback: assistant WebSearch (no API keys needed)


def has_web_search_keys(config: dict[str, Any]) -> bool:
    """Check if any web search API keys are configured."""
    return bool(
        config.get("OPENROUTER_API_KEY")
        or config.get("PARALLEL_API_KEY")
        or config.get("BRAVE_API_KEY")
    )


def get_web_search_source(config: dict[str, Any]) -> str | None:
    """Determine the best available web search backend.

    Priority: Parallel AI > Brave > OpenRouter/Sonar Pro

    Returns: 'parallel', 'brave', 'openrouter', or None
    """
    if config.get("PARALLEL_API_KEY"):
        return "parallel"
    if config.get("BRAVE_API_KEY"):
        return "brave"
    if config.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return None


def get_missing_keys(config: dict[str, Any]) -> str:
    """Determine which sources are missing.

    Returns: 'all', 'both', 'reddit', 'x', 'web', or 'none'
    """
    has_openai = bool(config.get("OPENAI_API_KEY"))
    has_xai = bool(config.get("XAI_API_KEY"))
    has_web = has_web_search_keys(config)

    if has_openai and has_xai and has_web:
        return "none"
    elif has_openai and has_xai:
        return "web"  # Missing web search keys
    elif has_openai:
        return "x"  # Missing X source (and possibly web)
    elif has_xai:
        return "reddit"  # Missing OpenAI key (and possibly web)
    else:
        return "all"  # Missing everything


def validate_sources(
    requested: str, available: str, include_web: bool = False
) -> tuple[str, str | None]:
    """Validate requested sources against available keys.

    Args:
        requested: 'auto', 'reddit', 'x', 'both', or 'web'
        available: Result from get_available_sources()
        include_web: If True, add WebSearch to available sources

    Returns:
        Tuple of (effective_sources, error_message)
    """
    # No API keys at all
    if available == "none":
        if requested == "auto":
            return (
                "web",
                "No API keys configured. The assistant can still search"
                " the web if it has a search tool.",
            )
        elif requested == "web":
            return "web", None
        else:
            return (
                "web",
                "No API keys configured. Add keys to ~/.config/last30days/.env for Reddit/X.",
            )

    # Web-only mode (only web search API keys)
    if available == "web":
        if requested == "auto" or requested == "web":
            return "web", None
        else:
            return (
                "web",
                "Only web search keys configured."
                " Add OPENAI_API_KEY for Reddit, XAI_API_KEY for X.",
            )

    if requested == "auto":
        # Add web to sources if include_web is set
        if include_web:
            if available == "both":  # noqa: SIM116
                return "all", None  # reddit + x + web
            elif available == "reddit":
                return "reddit-web", None
            elif available == "x":
                return "x-web", None
        return available, None

    if requested == "web":
        return "web", None

    if requested == "both":
        if available not in ("both",):
            missing = "xAI" if available == "reddit" else "OpenAI"
            return (
                "none",
                f"Requested both sources but {missing} key is missing."
                " Use --sources=auto to use available keys.",
            )
        if include_web:
            return "all", None
        return "both", None

    if requested == "reddit":
        if available == "x":
            return "none", "Requested Reddit but only xAI key is available."
        if include_web:
            return "reddit-web", None
        return "reddit", None

    if requested == "x":
        if available == "reddit":
            return "none", "Requested X but only OpenAI key is available."
        if include_web:
            return "x-web", None
        return "x", None

    return requested, None


def get_x_source(config: dict[str, Any]) -> str | None:
    """Determine the available X/Twitter source.

    Args:
        config: Configuration dict from get_config()

    Returns:
        'xai' if XAI_API_KEY is configured,
        None if no X source available.
    """
    if config.get("XAI_API_KEY"):
        return "xai"

    return None


def is_ytdlp_available() -> bool:
    """Check if yt-dlp is installed for YouTube search."""
    from . import youtube_yt

    return youtube_yt.is_ytdlp_installed()


def get_x_source_status(config: dict[str, Any]) -> dict[str, Any]:
    """Get X source status for UI decisions.

    Returns:
        Dict with keys: source, xai_available
    """
    xai_available = bool(config.get("XAI_API_KEY"))

    return {
        "source": "xai" if xai_available else None,
        "xai_available": xai_available,
    }
