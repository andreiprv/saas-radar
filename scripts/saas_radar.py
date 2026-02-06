#!/usr/bin/env python3
"""
saas-radar - Discover micro-SaaS ideas from Reddit + X threads.

Usage:
    python3 saas_radar.py <topic> [options]

Options:
    --mock              Use fixtures instead of real API calls
    --emit=MODE         Output mode: compact|json (default: compact)
    --sources=MODE      Source selection: auto|reddit|x|both (default: auto)
    --quick             Faster research with fewer sources
    --deep              Comprehensive research with more sources
    --debug             Enable verbose debug logging
"""

import argparse
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Force UTF-8 on Windows to handle Unicode from Reddit/X content
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add lib to path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from lib import (
    dates,
    dedupe,
    env,
    http,
    idea_cluster,
    models,
    normalize,
    openai_reddit,
    reddit_enrich,
    render,
    schema,
    score,
    subreddit_growth,
    ui,
    xai_x,
)


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
    growth_signals: list,
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
                growth_signals=growth_signals,
            )
        except http.HTTPError as e:
            raw_openai = {"error": str(e)}
            reddit_error = f"API error: {e}"
        except Exception as e:
            raw_openai = {"error": str(e)}
            reddit_error = f"{type(e).__name__}: {e}"

    reddit_items = openai_reddit.parse_reddit_response(raw_openai or {})

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
    """Search X via xAI (runs in thread).

    Returns:
        Tuple of (x_items, raw_xai, error)
    """
    raw_xai = None
    x_error = None

    if mock:
        raw_xai = load_fixture("xai_sample.json")
    else:
        try:
            raw_xai = xai_x.search_x(
                config["XAI_API_KEY"],
                selected_models["xai"],
                topic,
                from_date,
                to_date,
                depth=depth,
            )
        except http.HTTPError as e:
            raw_xai = {"error": str(e)}
            x_error = f"API error: {e}"
        except Exception as e:
            raw_xai = {"error": str(e)}
            x_error = f"{type(e).__name__}: {e}"

    x_items = xai_x.parse_x_response(raw_xai or {})

    return x_items, raw_xai, x_error


def main():
    parser = argparse.ArgumentParser(
        description="Discover micro-SaaS ideas from Reddit + X"
    )
    parser.add_argument("topic", nargs="?", help="Topic to search for SaaS ideas")
    parser.add_argument("--mock", action="store_true", help="Use fixtures")
    parser.add_argument(
        "--emit",
        choices=["compact", "json"],
        default="compact",
        help="Output mode",
    )
    parser.add_argument(
        "--sources",
        choices=["auto", "reddit", "x", "both"],
        default="auto",
        help="Source selection",
    )
    parser.add_argument("--quick", action="store_true", help="Fewer sources")
    parser.add_argument("--deep", action="store_true", help="More sources")
    parser.add_argument("--debug", action="store_true", help="Debug logging")

    args = parser.parse_args()

    # Enable debug logging
    if args.debug:
        os.environ["SAAS_RADAR_DEBUG"] = "1"
        from lib import http as http_module
        http_module.DEBUG = True

    # Determine depth
    if args.quick and args.deep:
        print("Error: Cannot use both --quick and --deep", file=sys.stderr)
        sys.exit(1)
    elif args.quick:
        depth = "quick"
    elif args.deep:
        depth = "deep"
    else:
        depth = "default"

    if not args.topic:
        print("Error: Please provide a topic.", file=sys.stderr)
        print("Usage: python3 saas_radar.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    # -- Phase 1: Config & Setup --

    config = env.get_config()
    available = env.get_available_sources(config)
    missing_keys = env.get_missing_keys(config)

    if args.mock:
        if args.sources == "auto":
            sources = "both"
        else:
            sources = args.sources
    else:
        sources, error = env.validate_sources(args.sources, available)
        if error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

    from_date, to_date = dates.get_date_range(180)

    # Initialize progress
    progress = ui.ProgressDisplay(args.topic, show_banner=True)

    if missing_keys != 'none' and not args.mock:
        progress.show_promo(missing_keys)

    # Select models
    if args.mock:
        mock_openai_models = load_fixture("models_openai_sample.json").get("data", [])
        mock_xai_models = load_fixture("models_xai_sample.json").get("data", [])
        selected_models = models.get_models(
            {"OPENAI_API_KEY": "mock", "XAI_API_KEY": "mock", **config},
            mock_openai_models,
            mock_xai_models,
        )
    else:
        selected_models = models.get_models(config)

    # Determine mode string
    if sources == "both":
        mode = "both"
    elif sources == "reddit":
        mode = "reddit-only"
    elif sources == "x":
        mode = "x-only"
    else:
        mode = sources

    # -- Phase 2: Subreddit Growth Scan --

    progress.start_growth_scan()
    growth_signals = subreddit_growth.scan_growth(
        mock=args.mock,
        progress_callback=progress.update_growth_scan,
    )
    progress.end_growth_scan(len(growth_signals))
    growth_map = {g.subreddit: g.acceleration for g in growth_signals}

    # -- Phase 3: Parallel Search (Reddit + X) --

    run_reddit = sources in ("both", "reddit")
    run_x = sources in ("both", "x")

    reddit_items = []
    x_items = []
    raw_openai = None
    raw_xai = None
    raw_reddit_enriched = []
    reddit_error = None
    x_error = None

    reddit_future = None
    x_future = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        if run_reddit:
            progress.start_reddit()
            reddit_future = executor.submit(
                _search_reddit, args.topic, config, selected_models,
                from_date, to_date, depth, args.mock, growth_signals
            )

        if run_x:
            progress.start_x()
            x_future = executor.submit(
                _search_x, args.topic, config, selected_models,
                from_date, to_date, depth, args.mock
            )

        if reddit_future:
            try:
                reddit_items, raw_openai, reddit_error = reddit_future.result()
                if reddit_error:
                    progress.show_error(f"Reddit: {reddit_error}")
            except Exception as e:
                reddit_error = f"{type(e).__name__}: {e}"
                progress.show_error(f"Reddit: {e}")
            progress.end_reddit(len(reddit_items))

        if x_future:
            try:
                x_items, raw_xai, x_error = x_future.result()
                if x_error:
                    progress.show_error(f"X: {x_error}")
            except Exception as e:
                x_error = f"{type(e).__name__}: {e}"
                progress.show_error(f"X: {e}")
            progress.end_x(len(x_items))

    # -- Phase 4: Reddit Enrichment --

    if reddit_items:
        progress.start_reddit_enrich(1, len(reddit_items))

        for i, item in enumerate(reddit_items):
            if i > 0:
                progress.update_reddit_enrich(i + 1, len(reddit_items))

            try:
                if args.mock:
                    mock_thread = load_fixture("reddit_thread_sample.json")
                    reddit_items[i] = reddit_enrich.enrich_reddit_item(item, mock_thread)
                else:
                    reddit_items[i] = reddit_enrich.enrich_reddit_item(item)
            except Exception as e:
                progress.show_error(f"Enrich failed for {item.get('url', 'unknown')}: {e}")

            raw_reddit_enriched.append(reddit_items[i])

        progress.end_reddit_enrich()

    # -- Phase 5: Processing --

    progress.start_processing()

    # Normalize
    normalized_reddit = normalize.normalize_reddit_saas_items(
        reddit_items, from_date, to_date, growth_map
    )
    normalized_x = normalize.normalize_x_saas_items(
        x_items, from_date, to_date
    )

    all_items = normalized_reddit + normalized_x

    # Date filter
    filtered = normalize.filter_by_date_range(all_items, from_date, to_date)

    # Cluster similar ideas
    clustered = idea_cluster.cluster_ideas(filtered)

    # Score
    scored = score.score_saas_items(clustered)

    # Sort
    sorted_items = score.sort_items(scored)

    # Dedupe
    deduped = dedupe.dedupe_saas(sorted_items)

    progress.end_processing()

    # -- Phase 6: Output --

    report = schema.create_saas_report(
        args.topic,
        from_date,
        to_date,
        mode,
        selected_models.get("openai"),
        selected_models.get("xai"),
    )
    report.items = deduped
    report.growth_signals = growth_signals
    report.reddit_error = reddit_error
    report.x_error = x_error

    # Write output files
    render.write_outputs(report, raw_openai, raw_xai, raw_reddit_enriched)

    # Show completion
    progress.show_complete(len(deduped), len(growth_signals))

    # Output to stdout
    if args.emit == "compact":
        print(render.render_compact(report, missing_keys=missing_keys))
    elif args.emit == "json":
        print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
