"""Subreddit growth signal scanner for saas-radar skill."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import http, schema

SAAS_SUBREDDITS = [
    "SaaS", "microsaas", "indiehackers", "startups", "Entrepreneur",
    "SideProject", "selfhosted", "nocode", "automation", "smallbusiness",
]

# Rate limit delay between subreddit requests
RATE_LIMIT_DELAY = 1.0


def _log(msg: str):
    """Log to stderr."""
    sys.stderr.write(f"[GROWTH] {msg}\n")
    sys.stderr.flush()


def fetch_subreddit_about(sub: str) -> Optional[Dict[str, Any]]:
    """Fetch subreddit metadata (subscribers, active users).

    Args:
        sub: Subreddit name (without r/)

    Returns:
        Dict with subscribers and active_user_count, or None on failure
    """
    url = f"https://www.reddit.com/r/{sub}/about.json"
    headers = {
        "User-Agent": http.USER_AGENT,
        "Accept": "application/json",
    }

    try:
        data = http.get(url, headers=headers)
        about = data.get("data", {})
        return {
            "subscribers": about.get("subscribers", 0),
            "active_users": about.get("active_user_count") or about.get("accounts_active") or 0,
        }
    except http.HTTPError as e:
        _log(f"Failed to fetch about for r/{sub}: {e}")
        return None


def fetch_subreddit_posts(sub: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
    """Fetch recent posts from a subreddit.

    Args:
        sub: Subreddit name (without r/)
        limit: Number of posts to fetch (max 100)

    Returns:
        List of post dicts with created_utc and score, or None on failure
    """
    url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit}&raw_json=1"
    headers = {
        "User-Agent": http.USER_AGENT,
        "Accept": "application/json",
    }

    try:
        data = http.get(url, headers=headers)
        children = data.get("data", {}).get("children", [])
        posts = []
        for child in children:
            post_data = child.get("data", {})
            created = post_data.get("created_utc")
            if created:
                posts.append({
                    "created_utc": created,
                    "score": post_data.get("score", 0),
                })
        return posts
    except http.HTTPError as e:
        _log(f"Failed to fetch posts for r/{sub}: {e}")
        return None


def compute_growth(
    about: Dict[str, Any],
    posts: List[Dict[str, Any]],
    subreddit: str,
    days: int = 180,
) -> schema.GrowthSignal:
    """Compute growth metrics from subreddit data.

    Splits posts into two halves: recent 90 days vs older 90 days.

    Args:
        about: Subreddit about data
        posts: List of posts with created_utc and score
        subreddit: Subreddit name
        days: Total window in days

    Returns:
        GrowthSignal with computed metrics
    """
    now = datetime.now(timezone.utc).timestamp()
    half_days = days / 2
    midpoint = now - (half_days * 86400)
    cutoff = now - (days * 86400)

    recent_posts = []
    older_posts = []

    for post in posts:
        ts = post.get("created_utc", 0)
        if ts >= midpoint:
            recent_posts.append(post)
        elif ts >= cutoff:
            older_posts.append(post)

    recent_count = len(recent_posts)
    older_count = len(older_posts)

    # Post rate acceleration
    acceleration = recent_count / max(older_count, 1)

    # Engagement acceleration
    avg_score_recent = sum(p.get("score", 0) for p in recent_posts) / max(recent_count, 1)
    avg_score_older = sum(p.get("score", 0) for p in older_posts) / max(older_count, 1)
    engagement_accel = avg_score_recent / max(avg_score_older, 0.1)

    # Vitality
    subscribers = about.get("subscribers", 0)
    active_users = about.get("active_users", 0)
    vitality = active_users / max(subscribers, 1)

    return schema.GrowthSignal(
        subreddit=subreddit,
        subscribers=subscribers,
        active_users=active_users,
        vitality=vitality,
        acceleration=acceleration,
        engagement_accel=engagement_accel,
        recent_count=recent_count,
        older_count=older_count,
    )


def scan_growth(
    mock: bool = False,
    subreddits: Optional[List[str]] = None,
    progress_callback=None,
) -> List[schema.GrowthSignal]:
    """Scan subreddits for growth signals.

    Args:
        mock: If True, load from fixtures
        subreddits: Override subreddit list
        progress_callback: Optional callback(current, total) for progress updates

    Returns:
        List of GrowthSignal sorted by acceleration descending
    """
    subs = subreddits or SAAS_SUBREDDITS

    if mock:
        return _load_mock_growth()

    signals = []
    for i, sub in enumerate(subs):
        if progress_callback:
            progress_callback(i + 1, len(subs))

        about = fetch_subreddit_about(sub)
        if not about:
            continue

        time.sleep(RATE_LIMIT_DELAY)

        posts = fetch_subreddit_posts(sub)
        if posts is None:
            continue

        signal = compute_growth(about, posts, sub)
        signals.append(signal)

        # Rate limit between subreddits
        if i < len(subs) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    # Sort by acceleration descending
    signals.sort(key=lambda s: s.acceleration, reverse=True)

    return signals


def _load_mock_growth() -> List[schema.GrowthSignal]:
    """Load mock growth data from fixtures."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "growth_sample.json"
    if not fixture_path.exists():
        return _generate_default_mock()

    try:
        with open(fixture_path) as f:
            data = json.load(f)
        return [schema.GrowthSignal.from_dict(g) for g in data]
    except (json.JSONDecodeError, OSError):
        return _generate_default_mock()


def _generate_default_mock() -> List[schema.GrowthSignal]:
    """Generate default mock growth signals."""
    return [
        schema.GrowthSignal("microsaas", 12400, 340, 0.0274, 3.1, 2.4, 62, 20),
        schema.GrowthSignal("automation", 89000, 1200, 0.0135, 2.8, 1.9, 78, 28),
        schema.GrowthSignal("SideProject", 45000, 890, 0.0198, 2.3, 1.7, 55, 24),
        schema.GrowthSignal("SaaS", 34000, 560, 0.0165, 2.1, 1.5, 48, 23),
        schema.GrowthSignal("indiehackers", 67000, 780, 0.0116, 1.8, 1.6, 45, 25),
        schema.GrowthSignal("nocode", 52000, 650, 0.0125, 1.6, 1.3, 40, 25),
        schema.GrowthSignal("startups", 120000, 1800, 0.0150, 1.4, 1.2, 50, 36),
        schema.GrowthSignal("selfhosted", 98000, 1400, 0.0143, 1.3, 1.1, 42, 32),
        schema.GrowthSignal("Entrepreneur", 150000, 2100, 0.0140, 1.1, 1.0, 38, 35),
        schema.GrowthSignal("smallbusiness", 110000, 1600, 0.0145, 1.0, 0.9, 35, 35),
    ]


def format_ranked_list(signals: List[schema.GrowthSignal]) -> str:
    """Format growth signals as ranked list for injection into prompts.

    Args:
        signals: Growth signals sorted by acceleration

    Returns:
        Formatted string for prompt injection
    """
    lines = []
    for i, s in enumerate(signals):
        lines.append(
            f"{i+1}. r/{s.subreddit} ({s.acceleration:.1f}x acceleration, "
            f"{_format_count(s.subscribers)} subs, {_format_count(s.active_users)} active)"
        )
    return "\n".join(lines)


def _format_count(n: int) -> str:
    """Format a count with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)
