"""Output rendering for saas-radar skill."""

import json
from pathlib import Path
from typing import List, Optional

from . import schema

OUTPUT_DIR = Path.home() / ".local" / "share" / "saas-radar" / "out"


def ensure_output_dir():
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _format_count(n: int) -> str:
    """Format a count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def render_compact(report: schema.SaaSReport, limit: int = 20, missing_keys: str = "none") -> str:
    """Render compact output for Claude to synthesize.

    Args:
        report: SaaS report data
        limit: Max items to show
        missing_keys: 'both', 'reddit', 'x', or 'none'

    Returns:
        Compact markdown string
    """
    lines = []

    # Header
    lines.append(f"## SaaS Radar: Ideas from the Last 180 Days")
    lines.append("")
    lines.append(f"**Topic:** {report.topic}")
    lines.append(f"**Date Range:** {report.range_from} to {report.range_to}")
    lines.append(f"**Mode:** {report.mode}")
    if report.openai_model_used:
        lines.append(f"**OpenAI Model:** {report.openai_model_used}")
    if report.xai_model_used:
        lines.append(f"**xAI Model:** {report.xai_model_used}")
    lines.append("")

    # Coverage tips
    if missing_keys == "x":
        lines.append("*Tip: Add XAI_API_KEY for X/Twitter data and better signal triangulation.*")
        lines.append("")
    elif missing_keys == "reddit":
        lines.append("*Tip: Add OPENAI_API_KEY for Reddit data and better signal triangulation.*")
        lines.append("")

    # Growing Subreddits section
    if report.growth_signals:
        lines.append("### Growing Subreddits")
        lines.append("")
        for i, g in enumerate(report.growth_signals):
            lines.append(
                f"{i+1}. r/{g.subreddit} ({g.acceleration:.1f}x acceleration, "
                f"{_format_count(g.subscribers)} subs, {_format_count(g.active_users)} active)"
            )
        lines.append("")

    # Error sections
    if report.reddit_error:
        lines.append(f"**Reddit Error:** {report.reddit_error}")
        lines.append("")
    if report.x_error:
        lines.append(f"**X Error:** {report.x_error}")
        lines.append("")

    # Top SaaS Ideas
    if not report.items:
        lines.append("### Top SaaS Ideas")
        lines.append("")
        lines.append("*No relevant SaaS ideas found. Try a different topic or broader search.*")
        lines.append("")
    else:
        lines.append("### Top SaaS Ideas")
        lines.append("")

        for item in report.items[:limit]:
            # Header line: S1 (92) [WISH] r/microsaas | 2026-01-15 | growth:3.1x | 482pts 67cmt
            signal_label = item.signal_type.upper()

            # Source info
            if item.source == "reddit":
                source_str = f"r/{item.subreddit}" if item.subreddit else "reddit"
            else:
                source_str = f"@{item.author_handle}" if item.author_handle else "x.com"

            date_str = item.date or "date unknown"

            # Growth
            growth_str = f"growth:{item.subreddit_growth:.1f}x" if item.subreddit_growth > 1.0 else ""

            # Engagement
            eng_parts = []
            if item.engagement:
                eng = item.engagement
                if eng.score is not None:
                    eng_parts.append(f"{eng.score}pts")
                if eng.num_comments is not None:
                    eng_parts.append(f"{eng.num_comments}cmt")
                if eng.likes is not None:
                    eng_parts.append(f"{eng.likes}likes")
                if eng.reposts is not None:
                    eng_parts.append(f"{eng.reposts}rt")
            eng_str = " ".join(eng_parts)

            # Build header
            header_parts = [f"{source_str}", date_str]
            if growth_str:
                header_parts.append(growth_str)
            if eng_str:
                header_parts.append(eng_str)

            lines.append(f"**{item.id}** ({item.score}) [{signal_label}] {' | '.join(header_parts)}")

            # Title/quote
            lines.append(f'  "{item.title}"')

            # Idea summary
            if item.idea_summary:
                lines.append(f"  Idea: {item.idea_summary}")

            # Target audience
            if item.target_audience:
                lines.append(f"  Audience: {item.target_audience}")

            # Market signal
            if item.market_signal > 25:
                cluster_count = item.market_signal // 25
                lines.append(f"  Market signal: {cluster_count} similar threads (cluster:{item.market_signal})")

            # URL
            lines.append(f"  {item.url}")

            # Comment insights
            if item.comment_insights:
                lines.append(f"  Insights:")
                for insight in item.comment_insights[:3]:
                    lines.append(f"    - \"{insight}\"")

            lines.append("")

    return "\n".join(lines)


def write_outputs(
    report: schema.SaaSReport,
    raw_openai: Optional[dict] = None,
    raw_xai: Optional[dict] = None,
    raw_reddit_enriched: Optional[list] = None,
):
    """Write all output files.

    Args:
        report: Report data
        raw_openai: Raw OpenAI API response
        raw_xai: Raw xAI API response
        raw_reddit_enriched: Raw enriched Reddit thread data
    """
    ensure_output_dir()

    # report.json
    with open(OUTPUT_DIR / "report.json", 'w') as f:
        json.dump(report.to_dict(), f, indent=2)

    # Raw responses
    if raw_openai:
        with open(OUTPUT_DIR / "raw_openai.json", 'w') as f:
            json.dump(raw_openai, f, indent=2)

    if raw_xai:
        with open(OUTPUT_DIR / "raw_xai.json", 'w') as f:
            json.dump(raw_xai, f, indent=2)

    if raw_reddit_enriched:
        with open(OUTPUT_DIR / "raw_reddit_threads_enriched.json", 'w') as f:
            json.dump(raw_reddit_enriched, f, indent=2)
