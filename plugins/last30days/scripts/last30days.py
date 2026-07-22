#!/usr/bin/env python3
"""
last30days - Research a topic from the last 30 days on Reddit + X + YouTube + Web.

Usage:
    python3 last30days.py <topic> [options]

Options:
    --mock              Use fixtures instead of real API calls
    --emit=MODE         Output mode: compact|json|md|context|path (default: compact)
    --sources=MODE      Source selection: auto|reddit|x|both (default: auto)
    --quick             Faster research with fewer sources (8-12 each)
    --deep              Comprehensive research with more sources (50-70 Reddit, 40-60 X)
    --debug             Enable verbose debug logging
    --diagnose          Show source availability diagnostics and exit
"""

import argparse
import atexit
import contextlib
import json
import os
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

# Add lib to path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ---------------------------------------------------------------------------
# Global timeout & child process management
# ---------------------------------------------------------------------------
_child_pids: set = set()
_child_pids_lock = threading.Lock()

TIMEOUT_PROFILES = {
    "quick": {
        "global": 90,
        "future": 30,
        "reddit_future": 60,
        "youtube_future": 60,
        "http": 15,
        "enrich_per": 8,
        "enrich_total": 30,
        "enrich_max_items": 10,
    },
    "default": {
        "global": 180,
        "future": 60,
        "reddit_future": 90,
        "youtube_future": 90,
        "http": 30,
        "enrich_per": 15,
        "enrich_total": 45,
        "enrich_max_items": 15,
    },
    "deep": {
        "global": 300,
        "future": 90,
        "reddit_future": 120,
        "youtube_future": 120,
        "http": 30,
        "enrich_per": 15,
        "enrich_total": 60,
        "enrich_max_items": 25,
    },
}


def register_child_pid(pid: int):
    """Track a child process for cleanup."""
    with _child_pids_lock:
        _child_pids.add(pid)


def unregister_child_pid(pid: int):
    """Remove a child process from tracking."""
    with _child_pids_lock:
        _child_pids.discard(pid)


def _cleanup_children():
    """Kill all tracked child processes."""
    with _child_pids_lock:
        pids = list(_child_pids)
    for pid in pids:
        with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
            os.killpg(os.getpgid(pid), signal.SIGTERM)


atexit.register(_cleanup_children)


def _install_global_timeout(timeout_seconds: int):
    """Install a global timeout watchdog.

    Uses SIGALRM on Unix, threading.Timer as fallback.
    """
    if hasattr(signal, "SIGALRM"):

        def _handler(signum, frame):
            sys.stderr.write(
                f"\n[TIMEOUT] Global timeout ({timeout_seconds}s) exceeded. Cleaning up.\n"
            )
            sys.stderr.flush()
            _cleanup_children()
            sys.exit(1)

        signal.signal(signal.SIGALRM, _handler)
        signal.alarm(timeout_seconds)
    else:
        # Windows fallback
        def _watchdog():
            sys.stderr.write(
                f"\n[TIMEOUT] Global timeout ({timeout_seconds}s) exceeded. Cleaning up.\n"
            )
            sys.stderr.flush()
            _cleanup_children()
            os._exit(1)

        timer = threading.Timer(timeout_seconds, _watchdog)
        timer.daemon = True
        timer.start()


from lib import (  # noqa: E402
    dates,
    dedupe,
    entity_extract,
    env,
    http,
    models,
    normalize,
    openai_reddit,
    reddit_enrich,
    render,
    schema,
    score,
    ui,
    websearch,
    xai_x,
    youtube_yt,
)


@dataclass
class ResearchResult:
    """Output from run_research() — raw items, API responses, and errors."""

    reddit_items: list = field(default_factory=list)
    x_items: list = field(default_factory=list)
    youtube_items: list = field(default_factory=list)
    web_items: list = field(default_factory=list)
    web_needed: bool = False
    raw_openai: dict | None = None
    raw_xai: dict | None = None
    raw_reddit_enriched: list = field(default_factory=list)
    reddit_error: str | None = None
    x_error: str | None = None
    youtube_error: str | None = None
    web_error: str | None = None


def load_fixture(name: str) -> dict:
    """Load a fixture file."""
    fixture_path = SCRIPT_DIR.parent / "fixtures" / name
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    return {}


def _search_reddit(
    topic: str,
    config: dict,
    selected_models: dict,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search Reddit via OpenAI (runs in thread).

    Returns:
        Tuple of (reddit_items, raw_openai, error)
    """
    raw_openai = None
    reddit_error = None

    if mock:
        raw_openai = load_fixture("openai_sample.json")
    else:
        try:
            raw_openai = openai_reddit.search_reddit(
                config["OPENAI_API_KEY"],
                selected_models["openai"],
                topic,
                from_date,
                to_date,
                depth=depth,
            )
        except http.HTTPError as e:
            raw_openai = {"error": str(e)}
            reddit_error = f"API error: {e}"
        except Exception as e:
            raw_openai = {"error": str(e)}
            reddit_error = f"{type(e).__name__}: {e}"

    # Parse response
    reddit_items = openai_reddit.parse_reddit_response(raw_openai or {})

    # Quick retry with simpler query if few results
    if len(reddit_items) < 5 and not mock and not reddit_error:
        core = openai_reddit._extract_core_subject(topic)
        if core.lower() != topic.lower():
            try:
                retry_raw = openai_reddit.search_reddit(
                    config["OPENAI_API_KEY"],
                    selected_models["openai"],
                    core,
                    from_date,
                    to_date,
                    depth=depth,
                )
                retry_items = openai_reddit.parse_reddit_response(retry_raw)
                # Add items not already found (by URL)
                existing_urls = {item.get("url") for item in reddit_items}
                for item in retry_items:
                    if item.get("url") not in existing_urls:
                        reddit_items.append(item)
            except Exception as exc:
                sys.stderr.write(f"[Reddit] Retry failed: {exc}\n")

    # Subreddit-targeted fallback if still < 3 results
    if len(reddit_items) < 3 and not mock and not reddit_error:
        sub_query = openai_reddit._build_subreddit_query(topic)
        try:
            sub_raw = openai_reddit.search_reddit(
                config["OPENAI_API_KEY"],
                selected_models["openai"],
                sub_query,
                from_date,
                to_date,
                depth=depth,
            )
            sub_items = openai_reddit.parse_reddit_response(sub_raw)
            existing_urls = {item.get("url") for item in reddit_items}
            for item in sub_items:
                if item.get("url") not in existing_urls:
                    reddit_items.append(item)
        except Exception as exc:
            sys.stderr.write(f"[Reddit] Subreddit fallback failed: {exc}\n")

    return reddit_items, raw_openai, reddit_error


def _search_x(
    topic: str,
    config: dict,
    selected_models: dict,
    from_date: str,
    to_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Search X via xAI API (runs in thread).

    Returns:
        Tuple of (x_items, raw_response, error)
    """
    raw_response = None
    x_error = None

    if mock:
        raw_response = load_fixture("xai_sample.json")
        x_items = xai_x.parse_x_response(raw_response or {})
        return x_items, raw_response, x_error

    try:
        raw_response = xai_x.search_x(
            config["XAI_API_KEY"],
            selected_models["xai"],
            topic,
            from_date,
            to_date,
            depth=depth,
        )
    except http.HTTPError as e:
        raw_response = {"error": str(e)}
        x_error = f"API error: {e}"
    except Exception as e:
        raw_response = {"error": str(e)}
        x_error = f"{type(e).__name__}: {e}"

    x_items = xai_x.parse_x_response(raw_response or {})

    return x_items, raw_response, x_error


def _search_youtube(
    topic: str,
    from_date: str,
    to_date: str,
    depth: str,
) -> tuple:
    """Search YouTube via yt-dlp (runs in thread).

    Returns:
        Tuple of (youtube_items, youtube_error)
    """
    youtube_error = None

    try:
        response = youtube_yt.search_and_transcribe(
            topic,
            from_date,
            to_date,
            depth=depth,
        )
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"

    youtube_items = youtube_yt.parse_youtube_response(response)

    if response.get("error"):
        youtube_error = response["error"]

    return youtube_items, youtube_error


def _search_web(
    topic: str,
    config: dict,
    from_date: str,
    to_date: str,
    depth: str,
) -> tuple:
    """Search the web via native API backend (runs in thread).

    Uses the best available backend: Parallel AI > Brave > OpenRouter.

    Returns:
        Tuple of (web_items, web_error)
        web_items are raw dicts ready for websearch.normalize_websearch_items()
    """
    from lib import brave_search, openrouter_search, parallel_search

    backend = env.get_web_search_source(config)
    if not backend:
        return [], "No web search API keys configured"

    web_error = None
    raw_results = []

    try:
        if backend == "parallel":
            raw_results = parallel_search.search_web(
                topic,
                from_date,
                to_date,
                config["PARALLEL_API_KEY"],
                depth=depth,
            )
        elif backend == "brave":
            raw_results = brave_search.search_web(
                topic,
                from_date,
                to_date,
                config["BRAVE_API_KEY"],
                depth=depth,
            )
        elif backend == "openrouter":
            raw_results = openrouter_search.search_web(
                topic,
                from_date,
                to_date,
                config["OPENROUTER_API_KEY"],
                depth=depth,
            )
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"

    # Add IDs and date_confidence for websearch.normalize_websearch_items()
    for i, item in enumerate(raw_results):
        item.setdefault("id", f"W{i + 1}")
        if item.get("date") and not item.get("date_confidence"):
            item["date_confidence"] = "med"
        elif not item.get("date"):
            item["date_confidence"] = "low"
        item.setdefault("why_relevant", "")

    return raw_results, web_error


def _run_supplemental(
    topic: str,
    reddit_items: list,
    x_items: list,
    from_date: str,
    to_date: str,
    depth: str,
    progress: ui.ProgressDisplay = None,
    skip_reddit: bool = False,
) -> list:
    """Run Phase 2 supplemental Reddit searches based on entities from Phase 1.

    Extracts subreddits from initial results, then runs targeted
    searches to find additional content the broad search missed.

    Args:
        topic: Original search topic
        reddit_items: Phase 1 Reddit items (raw dicts)
        x_items: Phase 1 X items (raw dicts)
        from_date: Start date
        to_date: End date
        depth: Research depth
        progress: Optional progress display
        skip_reddit: If True, skip Reddit supplemental (e.g. rate-limited)

    Returns:
        List of supplemental Reddit items.
    """
    # Depth-dependent caps
    if depth == "default":
        max_subs = 3
        count_per = 3
    else:  # deep
        max_subs = 5
        count_per = 5

    # Extract entities from Phase 1 results
    entities = entity_extract.extract_entities(
        reddit_items,
        x_items,
        max_handles=0,
        max_subreddits=max_subs,
    )

    has_subs = entities["reddit_subreddits"] and not skip_reddit

    if not has_subs:
        return []

    parts = [f"r/{', r/'.join(entities['reddit_subreddits'][:3])}"]
    sys.stderr.write(f"[Phase 2] Drilling into {' + '.join(parts)}\n")
    sys.stderr.flush()

    supplemental_reddit = []

    # Collect existing URLs to avoid adding duplicates before dedupe
    existing_urls = set()
    for item in reddit_items:
        existing_urls.add(item.get("url", ""))
    for item in x_items:
        existing_urls.add(item.get("url", ""))

    try:
        raw_reddit = openai_reddit.search_subreddits(
            entities["reddit_subreddits"],
            topic,
            from_date,
            to_date,
            count_per,
        )
        supplemental_reddit = [
            item for item in raw_reddit if item.get("url", "") not in existing_urls
        ]
    except TimeoutError:
        sys.stderr.write("[Phase 2] Supplemental Reddit timed out\n")
    except Exception as e:
        sys.stderr.write(f"[Phase 2] Supplemental Reddit error: {e}\n")

    if supplemental_reddit:
        sys.stderr.write(f"[Phase 2] +{len(supplemental_reddit)} Reddit\n")
        sys.stderr.flush()

    return supplemental_reddit


def run_research(
    topic: str,
    sources: str,
    config: dict,
    selected_models: dict,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock: bool = False,
    progress: ui.ProgressDisplay = None,
    run_youtube: bool = False,
    timeouts: dict = None,
) -> ResearchResult:
    """Run the research pipeline.

    Returns:
        ResearchResult with raw items, API responses, and per-source errors.
        web_needed is True when the assistant should run its own web search
        (no native web search API keys configured).
    """
    if timeouts is None:
        timeouts = TIMEOUT_PROFILES[depth]
    future_timeout = timeouts["future"]

    reddit_items = []
    x_items = []
    youtube_items = []
    web_items = []
    raw_openai = None
    raw_xai = None
    raw_reddit_enriched = []
    reddit_error = None
    x_error = None
    youtube_error = None
    web_error = None

    # Determine web search mode
    do_web = sources in ("all", "web", "reddit-web", "x-web")
    web_backend = env.get_web_search_source(config) if do_web else None
    web_needed = do_web and not web_backend

    # Web-only mode
    if sources == "web":
        if web_backend:
            # Native web search available — run it
            sys.stderr.write(f"[web] Searching via {web_backend}\n")
            sys.stderr.flush()
            try:
                web_items, web_error = _search_web(topic, config, from_date, to_date, depth)
                if web_error and progress:
                    progress.show_error(f"Web error: {web_error}")
            except Exception as e:
                web_error = f"{type(e).__name__}: {e}"
                if progress:
                    progress.show_error(f"Web error: {e}")
            sys.stderr.write(f"[web] {len(web_items)} results\n")
            sys.stderr.flush()
        else:
            # No native backend — assistant handles WebSearch
            if progress:
                progress.start_web_only()
                progress.end_web_only()
        # Still run YouTube in web-only mode if yt-dlp is available
        if run_youtube:
            if progress:
                progress.start_youtube()
            try:
                youtube_items, youtube_error = _search_youtube(topic, from_date, to_date, depth)
                if youtube_error and progress:
                    progress.show_error(f"YouTube error: {youtube_error}")
            except Exception as e:
                youtube_error = f"{type(e).__name__}: {e}"
                if progress:
                    progress.show_error(f"YouTube error: {e}")
            if progress:
                progress.end_youtube(len(youtube_items))
        return ResearchResult(
            youtube_items=youtube_items,
            web_items=web_items,
            web_needed=web_needed,
            youtube_error=youtube_error,
            web_error=web_error,
        )

    # Determine which searches to run
    do_reddit = sources in ("both", "reddit", "all", "reddit-web")
    do_x = sources in ("both", "x", "all", "x-web")

    # Run Reddit, X, YouTube, and Web searches in parallel
    reddit_future = None
    x_future = None
    youtube_future = None
    web_future = None
    max_workers = 2 + (1 if run_youtube else 0) + (1 if web_backend else 0)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit searches
        if do_reddit:
            if progress:
                progress.start_reddit()
            reddit_future = executor.submit(
                _search_reddit, topic, config, selected_models, from_date, to_date, depth, mock
            )

        if do_x:
            if progress:
                progress.start_x()
            x_future = executor.submit(
                _search_x, topic, config, selected_models, from_date, to_date, depth, mock
            )

        if run_youtube:
            if progress:
                progress.start_youtube()
            youtube_future = executor.submit(_search_youtube, topic, from_date, to_date, depth)

        if web_backend:
            sys.stderr.write(f"[web] Searching via {web_backend}\n")
            sys.stderr.flush()
            web_future = executor.submit(_search_web, topic, config, from_date, to_date, depth)

        # Collect results (with timeouts to prevent indefinite blocking)
        if reddit_future:
            reddit_timeout = timeouts.get("reddit_future", future_timeout)
            try:
                reddit_items, raw_openai, reddit_error = reddit_future.result(
                    timeout=reddit_timeout
                )
                if reddit_error and progress:
                    progress.show_error(f"Reddit error: {reddit_error}")
            except TimeoutError:
                reddit_error = f"Reddit search timed out after {reddit_timeout}s"
                if progress:
                    progress.show_error(reddit_error)
            except Exception as e:
                reddit_error = f"{type(e).__name__}: {e}"
                if progress:
                    progress.show_error(f"Reddit error: {e}")
            if progress:
                progress.end_reddit(len(reddit_items))

        if x_future:
            try:
                x_items, raw_xai, x_error = x_future.result(timeout=future_timeout)
                if x_error and progress:
                    progress.show_error(f"X error: {x_error}")
            except TimeoutError:
                x_error = f"X search timed out after {future_timeout}s"
                if progress:
                    progress.show_error(x_error)
            except Exception as e:
                x_error = f"{type(e).__name__}: {e}"
                if progress:
                    progress.show_error(f"X error: {e}")
            if progress:
                progress.end_x(len(x_items))

        if youtube_future:
            yt_timeout = timeouts.get("youtube_future", future_timeout)
            try:
                youtube_items, youtube_error = youtube_future.result(timeout=yt_timeout)
                if youtube_error and progress:
                    progress.show_error(f"YouTube error: {youtube_error}")
            except TimeoutError:
                youtube_error = f"YouTube search timed out after {yt_timeout}s"
                if progress:
                    progress.show_error(youtube_error)
            except Exception as e:
                youtube_error = f"{type(e).__name__}: {e}"
                if progress:
                    progress.show_error(f"YouTube error: {e}")
            if progress:
                progress.end_youtube(len(youtube_items))

        if web_future:
            try:
                web_items, web_error = web_future.result(timeout=future_timeout)
                if web_error and progress:
                    progress.show_error(f"Web error: {web_error}")
            except TimeoutError:
                web_error = f"Web search timed out after {future_timeout}s"
                if progress:
                    progress.show_error(web_error)
            except Exception as e:
                web_error = f"{type(e).__name__}: {e}"
                if progress:
                    progress.show_error(f"Web error: {e}")
            sys.stderr.write(f"[web] {len(web_items)} results\n")
            sys.stderr.flush()

    # Enrich Reddit items with real data (parallel, capped)
    enrich_max = timeouts["enrich_max_items"]
    enrich_total_timeout = timeouts["enrich_total"]
    items_to_enrich = reddit_items[:enrich_max]
    rate_limited = False  # Set True if Reddit returns 429 during enrichment

    if items_to_enrich:
        if progress:
            progress.start_reddit_enrich(1, len(items_to_enrich))

        if mock:
            # Sequential mock enrichment (fast, no need for parallelism)
            for i, item in enumerate(items_to_enrich):
                if progress and i > 0:
                    progress.update_reddit_enrich(i + 1, len(items_to_enrich))
                try:
                    mock_thread = load_fixture("reddit_thread_sample.json")
                    reddit_items[i] = reddit_enrich.enrich_reddit_item(item, mock_thread)
                except Exception as e:
                    if progress:
                        progress.show_error(f"Enrich failed for {item.get('url', 'unknown')}: {e}")
                raw_reddit_enriched.append(reddit_items[i])
        else:
            # Parallel enrichment with bounded concurrency and total timeout
            # Uses short HTTP timeout (10s) and 1 retry to fail fast on 429
            completed_count = 0
            rate_limited = False
            with ThreadPoolExecutor(max_workers=5) as enrich_pool:
                futures = {
                    enrich_pool.submit(reddit_enrich.enrich_reddit_item, item): i
                    for i, item in enumerate(items_to_enrich)
                }
                try:
                    for future in as_completed(futures, timeout=enrich_total_timeout):
                        idx = futures[future]
                        completed_count += 1
                        if progress:
                            progress.update_reddit_enrich(completed_count, len(items_to_enrich))
                        try:
                            reddit_items[idx] = future.result(timeout=timeouts["enrich_per"])
                        except reddit_enrich.RedditRateLimitError:
                            rate_limited = True
                            if progress:
                                progress.show_error(
                                    "Reddit rate-limited (429) — skipping remaining enrichment"
                                )
                            # Cancel remaining futures and bail
                            for f in futures:
                                f.cancel()
                            break
                        except Exception as e:
                            if progress:
                                fail_url = items_to_enrich[idx].get("url", "unknown")
                                progress.show_error(f"Enrich failed for {fail_url}: {e}")
                        raw_reddit_enriched.append(reddit_items[idx])
                except TimeoutError:
                    if progress:
                        progress.show_error(
                            f"Enrichment timed out after {enrich_total_timeout}s "
                            f"({completed_count}/{len(items_to_enrich)} done)"
                        )
                    # Keep unenriched items as-is
                    for idx in futures.values():
                        if reddit_items[idx] not in raw_reddit_enriched:
                            raw_reddit_enriched.append(reddit_items[idx])

        if progress:
            progress.end_reddit_enrich()

    # Phase 2: Supplemental search based on entities from Phase 1
    # Skip on --quick (speed matters), mock mode, or if Reddit is rate-limiting
    if depth != "quick" and not mock and (reddit_items or x_items):
        sup_reddit = _run_supplemental(
            topic,
            reddit_items,
            x_items,
            from_date,
            to_date,
            depth,
            progress,
            skip_reddit=rate_limited,
        )
        if sup_reddit:
            reddit_items.extend(sup_reddit)

    return ResearchResult(
        reddit_items=reddit_items,
        x_items=x_items,
        youtube_items=youtube_items,
        web_items=web_items,
        web_needed=web_needed,
        raw_openai=raw_openai,
        raw_xai=raw_xai,
        raw_reddit_enriched=raw_reddit_enriched,
        reddit_error=reddit_error,
        x_error=x_error,
        youtube_error=youtube_error,
        web_error=web_error,
    )


_SOURCE_TO_MODE = {
    "all": "all",
    "both": "both",
    "reddit": "reddit-only",
    "reddit-web": "reddit-web",
    "x": "x-only",
    "x-web": "x-web",
    "web": "web-only",
}


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Research a topic from the last N days on Reddit + X"
    )
    parser.add_argument("topic", nargs="?", help="Topic to research")
    parser.add_argument("--mock", action="store_true", help="Use fixtures")
    parser.add_argument(
        "--emit",
        choices=["compact", "json", "md", "context", "path"],
        default="compact",
        help="Output mode",
    )
    parser.add_argument(
        "--sources",
        choices=["auto", "reddit", "x", "both"],
        default="auto",
        help="Source selection",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Faster research with fewer sources (8-12 each)",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Comprehensive research with more sources (50-70 Reddit, 40-60 X)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--include-web",
        action="store_true",
        help="Include general web search alongside Reddit/X (lower weighted)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        choices=range(1, 31),
        metavar="N",
        help="Number of days to look back (1-30, default: 30)",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Show source availability diagnostics and exit",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SECS",
        help="Global timeout in seconds (default: 180, quick: 90, deep: 300)",
    )
    return parser.parse_args()


def _resolve_depth(args: argparse.Namespace) -> str:
    """Determine research depth from CLI flags."""
    if args.quick and args.deep:
        print("Error: Cannot use both --quick and --deep", file=sys.stderr)
        sys.exit(1)
    if args.quick:
        return "quick"
    if args.deep:
        return "deep"
    return "default"


def _resolve_sources(
    args: argparse.Namespace,
    config: dict,
) -> str:
    """Validate and resolve the effective source set."""
    if args.mock:
        return "both" if args.sources == "auto" else args.sources

    available = env.get_available_sources(config)
    sources, error = env.validate_sources(args.sources, available, args.include_web)
    if error:
        if "WebSearch fallback" in error:
            print(f"Note: {error}", file=sys.stderr)
        else:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)
    return sources


def _select_models(args: argparse.Namespace, config: dict) -> dict:
    """Select OpenAI and xAI models (real or mock)."""
    if args.mock:
        mock_openai_models = load_fixture("models_openai_sample.json").get("data", [])
        mock_xai_models = load_fixture("models_xai_sample.json").get("data", [])
        return models.get_models(
            {"OPENAI_API_KEY": "mock", "XAI_API_KEY": "mock", **config},
            mock_openai_models,
            mock_xai_models,
        )
    return models.get_models(config)


def _process_results(
    result: ResearchResult,
    topic: str,
    from_date: str,
    to_date: str,
    mode: str,
    selected_models: dict,
    progress: ui.ProgressDisplay,
) -> schema.Report:
    """Normalize, filter, score, sort, and dedupe raw research into a Report."""
    progress.start_processing()

    # Normalize
    norm_reddit = normalize.normalize_reddit_items(result.reddit_items, from_date, to_date)
    norm_x = normalize.normalize_x_items(result.x_items, from_date, to_date)
    norm_youtube = (
        normalize.normalize_youtube_items(result.youtube_items, from_date, to_date)
        if result.youtube_items
        else []
    )
    norm_web = (
        websearch.normalize_websearch_items(result.web_items, from_date, to_date)
        if result.web_items
        else []
    )

    # Hard date filter (safety net for old content that slipped through prompts).
    # YouTube skipped — youtube_yt.py already soft-filters, and video content
    # has a longer shelf life than tweets/posts.
    filt_reddit = normalize.filter_by_date_range(norm_reddit, from_date, to_date)
    filt_x = normalize.filter_by_date_range(norm_x, from_date, to_date)
    filt_youtube = norm_youtube
    filt_web = normalize.filter_by_date_range(norm_web, from_date, to_date) if norm_web else []

    # Score and sort
    scored_reddit = score.sort_items(score.score_reddit_items(filt_reddit))
    scored_x = score.sort_items(score.score_x_items(filt_x))
    scored_youtube = (
        score.sort_items(score.score_youtube_items(filt_youtube)) if filt_youtube else []
    )
    scored_web = score.sort_items(score.score_websearch_items(filt_web)) if filt_web else []

    # Dedupe
    deduped_reddit = dedupe.dedupe_reddit(scored_reddit)
    deduped_x = dedupe.dedupe_x(scored_x)
    deduped_youtube = dedupe.dedupe_youtube(scored_youtube) if scored_youtube else []
    deduped_web = websearch.dedupe_websearch(scored_web) if scored_web else []

    # Minimum result guarantee: keep top 3 by relevance if all were filtered out
    if not deduped_reddit and norm_reddit:
        sys.stderr.write(
            "[REDDIT WARNING] All results scored below threshold, keeping top 3 by relevance\n"
        )
        by_relevance = sorted(norm_reddit, key=lambda item: item.relevance, reverse=True)
        deduped_reddit = by_relevance[:3]

    progress.end_processing()

    # Build report
    report = schema.create_report(
        topic,
        from_date,
        to_date,
        mode,
        selected_models.get("openai"),
        selected_models.get("xai"),
    )
    report.reddit = deduped_reddit
    report.x = deduped_x
    report.youtube = deduped_youtube
    report.web = deduped_web
    report.reddit_error = result.reddit_error
    report.x_error = result.x_error
    report.youtube_error = result.youtube_error
    report.web_error = result.web_error
    report.context_snippet_md = render.render_context_snippet(report)

    render.write_outputs(report, result.raw_openai, result.raw_xai, result.raw_reddit_enriched)
    return report


def _emit_result(
    report: schema.Report,
    emit_mode: str,
    web_needed: bool,
    topic: str,
    from_date: str,
    to_date: str,
    missing_keys: str,
    days: int,
    source_info: dict,
):
    """Render and print the final output."""
    if emit_mode == "compact":
        print(render.render_compact(report, missing_keys=missing_keys))
        print(render.render_source_status(report, source_info))
    elif emit_mode == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif emit_mode == "md":
        print(render.render_full_report(report))
    elif emit_mode == "context":
        print(report.context_snippet_md)
    elif emit_mode == "path":
        print(render.get_context_path())

    if web_needed:
        print("\n" + "=" * 60)
        print("### WEBSEARCH REQUIRED ###")
        print("=" * 60)
        print(f"Topic: {topic}")
        print(f"Date range: {from_date} to {to_date}")
        print("")
        print("Assistant: Use your web search tool to find 8-15 relevant web pages.")
        print("EXCLUDE: reddit.com, x.com, twitter.com (already covered above)")
        print(f"INCLUDE: blogs, docs, news, tutorials from the last {days} days")
        print("")
        print("After searching, synthesize WebSearch results WITH the Reddit/X")
        print("results above. WebSearch items should rank LOWER than comparable")
        print("Reddit/X items (they lack engagement metrics).")
        print("=" * 60)


def _run_diagnose(config, x_source, has_ytdlp, web_source):
    """Print source availability diagnostics as JSON and exit."""
    diag = {
        "openai": bool(config.get("OPENAI_API_KEY")),
        "xai": bool(config.get("XAI_API_KEY")),
        "x_source": x_source,
        "youtube": has_ytdlp,
        "web_search_backend": web_source,
        "parallel_ai": bool(config.get("PARALLEL_API_KEY")),
        "brave": bool(config.get("BRAVE_API_KEY")),
        "openrouter": bool(config.get("OPENROUTER_API_KEY")),
    }
    print(json.dumps(diag, indent=2))
    sys.exit(0)


def _build_source_info(config, x_source, has_ytdlp, web_source):
    """Build dict of skip reasons for unavailable sources."""
    info = {}
    if not config.get("OPENAI_API_KEY"):
        info["reddit_skip_reason"] = "No OPENAI_API_KEY (add to ~/.config/last30days/.env)"
    if not x_source:
        info["x_skip_reason"] = "No XAI_API_KEY (add to ~/.config/last30days/.env)"
    if not has_ytdlp:
        info["youtube_skip_reason"] = "yt-dlp not installed — fix: brew install yt-dlp"
    if not web_source:
        info["web_skip_reason"] = (
            "assistant will use WebSearch (add BRAVE_API_KEY for native search)"
        )
    return info


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = _parse_args()

    if args.debug:
        os.environ["LAST30DAYS_DEBUG"] = "1"
        from lib import http as http_module

        http_module.DEBUG = True

    depth = _resolve_depth(args)
    timeouts = TIMEOUT_PROFILES[depth]
    _install_global_timeout(args.timeout or timeouts["global"])

    config = env.get_config()
    x_source = env.get_x_source(config)
    has_ytdlp = env.is_ytdlp_available()
    web_source = env.get_web_search_source(config)

    if args.diagnose:
        _run_diagnose(config, x_source, has_ytdlp, web_source)

    if not args.topic:
        print("Error: Please provide a topic to research.", file=sys.stderr)
        print("Usage: python3 last30days.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    progress = ui.ProgressDisplay(args.topic, show_banner=True)
    diag = {
        "openai": bool(config.get("OPENAI_API_KEY")),
        "xai": bool(config.get("XAI_API_KEY")),
        "x_source": x_source,
        "youtube": has_ytdlp,
        "web_search_backend": web_source,
    }
    ui.show_diagnostic_banner(diag)

    sources = _resolve_sources(args, config)
    from_date, to_date = dates.get_date_range(args.days)
    missing_keys = env.get_missing_keys(config)
    if missing_keys != "none":
        progress.show_promo(missing_keys, diag=diag)

    selected_models = _select_models(args, config)
    mode = _SOURCE_TO_MODE.get(sources, sources)

    result = run_research(
        args.topic,
        sources,
        config,
        selected_models,
        from_date,
        to_date,
        depth,
        args.mock,
        progress,
        run_youtube=has_ytdlp,
        timeouts=timeouts,
    )

    report = _process_results(
        result,
        args.topic,
        from_date,
        to_date,
        mode,
        selected_models,
        progress,
    )

    if sources == "web":
        progress.show_web_only_complete()
    else:
        progress.show_complete(len(report.reddit), len(report.x), len(report.youtube))

    source_info = _build_source_info(config, x_source, has_ytdlp, web_source)

    _emit_result(
        report,
        args.emit,
        result.web_needed,
        args.topic,
        from_date,
        to_date,
        missing_keys,
        args.days,
        source_info,
    )


if __name__ == "__main__":
    main()
