"""Caching utilities for last30days skill."""

import contextlib
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "last30days"
DEFAULT_TTL_HOURS = 24
MODEL_CACHE_TTL_DAYS = 7


def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_key(topic: str, from_date: str, to_date: str, sources: str) -> str:
    """Generate a cache key from query parameters."""
    key_data = f"{topic}|{from_date}|{to_date}|{sources}"
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def get_cache_path(cache_key: str) -> Path:
    """Get path to cache file."""
    return CACHE_DIR / f"{cache_key}.json"


def is_cache_valid(cache_path: Path, ttl_hours: int = DEFAULT_TTL_HOURS) -> bool:
    """Check if cache file exists and is within TTL."""
    if not cache_path.exists():
        return False

    try:
        stat = cache_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        now = datetime.now(UTC)
        age_hours = (now - mtime).total_seconds() / 3600
        return age_hours < ttl_hours
    except OSError:
        return False


def load_cache(cache_key: str, ttl_hours: int = DEFAULT_TTL_HOURS) -> dict | None:
    """Load data from cache if valid."""
    cache_path = get_cache_path(cache_key)

    if not is_cache_valid(cache_path, ttl_hours):
        return None

    try:
        with open(cache_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_cache_age_hours(cache_path: Path) -> float | None:
    """Get age of cache file in hours."""
    if not cache_path.exists():
        return None
    try:
        stat = cache_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        now = datetime.now(UTC)
        return (now - mtime).total_seconds() / 3600
    except OSError:
        return None


def load_cache_with_age(cache_key: str, ttl_hours: int = DEFAULT_TTL_HOURS) -> tuple:
    """Load data from cache with age info.

    Returns:
        Tuple of (data, age_hours) or (None, None) if invalid
    """
    cache_path = get_cache_path(cache_key)

    if not is_cache_valid(cache_path, ttl_hours):
        return None, None

    age = get_cache_age_hours(cache_path)

    try:
        with open(cache_path) as f:
            return json.load(f), age
    except (json.JSONDecodeError, OSError):
        return None, None


def save_cache(cache_key: str, data: dict):
    """Save data to cache."""
    ensure_cache_dir()
    cache_path = get_cache_path(cache_key)

    try:
        with open(cache_path, "w") as f:
            json.dump(data, f)
    except OSError:
        pass  # Silently fail on cache write errors


def clear_cache():
    """Clear all cache files."""
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.json"):
            with contextlib.suppress(OSError):
                f.unlink()


# Model selection cache (longer TTL)
MODEL_CACHE_FILE = CACHE_DIR / "model_selection.json"


def load_model_cache() -> dict:
    """Load model selection cache."""
    if not is_cache_valid(MODEL_CACHE_FILE, MODEL_CACHE_TTL_DAYS * 24):
        return {}

    try:
        with open(MODEL_CACHE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_model_cache(data: dict):
    """Save model selection cache."""
    ensure_cache_dir()
    try:
        with open(MODEL_CACHE_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def get_cached_model(provider: str) -> str | None:
    """Get cached model selection for a provider."""
    cache = load_model_cache()
    return cache.get(provider)


def set_cached_model(provider: str, model: str):
    """Cache model selection for a provider."""
    cache = load_model_cache()
    cache[provider] = model
    cache["updated_at"] = datetime.now(UTC).isoformat()
    save_model_cache(cache)
