"""5-factor scoring for saas-radar skill."""

import math
from typing import List, Optional

from . import dates, schema

# 5-factor weights
WEIGHT_IDEA_QUALITY = 0.30
WEIGHT_ENGAGEMENT = 0.25
WEIGHT_MARKET_SIGNAL = 0.20
WEIGHT_GROWTH = 0.15
WEIGHT_RECENCY = 0.10

# Signal type base scores
SIGNAL_TYPE_SCORES = {
    "wish": 90,
    "problem": 80,
    "feature_gap": 75,
    "building": 70,
    "workflow": 65,
}

# Penalties
UNKNOWN_ENGAGEMENT_PENALTY = 10
LOW_DATE_CONFIDENCE_PENALTY = 10

# Default engagement score when unknown
DEFAULT_ENGAGEMENT = 35


def log1p_safe(x: Optional[int]) -> float:
    """Safe log1p that handles None and negative values."""
    if x is None or x < 0:
        return 0.0
    return math.log1p(x)


def normalize_to_100(values: List[Optional[float]], default: float = 50) -> List[Optional[float]]:
    """Normalize a list of values to 0-100 scale."""
    valid = [v for v in values if v is not None]
    if not valid:
        return [default if v is None else 50 for v in values]

    min_val = min(valid)
    max_val = max(valid)
    range_val = max_val - min_val

    if range_val == 0:
        return [50 if v is None else 50 for v in values]

    result = []
    for v in values:
        if v is None:
            result.append(None)
        else:
            normalized = ((v - min_val) / range_val) * 100
            result.append(normalized)

    return result


def compute_reddit_engagement_raw(engagement: Optional[schema.Engagement]) -> Optional[float]:
    """Compute raw engagement score for Reddit item.

    Formula: 0.55*log1p(score) + 0.40*log1p(num_comments) + 0.05*(upvote_ratio*10)
    """
    if engagement is None:
        return None

    if engagement.score is None and engagement.num_comments is None:
        return None

    score = log1p_safe(engagement.score)
    comments = log1p_safe(engagement.num_comments)
    ratio = (engagement.upvote_ratio or 0.5) * 10

    return 0.55 * score + 0.40 * comments + 0.05 * ratio


def compute_x_engagement_raw(engagement: Optional[schema.Engagement]) -> Optional[float]:
    """Compute raw engagement score for X item.

    Formula: 0.55*log1p(likes) + 0.25*log1p(reposts) + 0.15*log1p(replies) + 0.05*log1p(quotes)
    """
    if engagement is None:
        return None

    if engagement.likes is None and engagement.reposts is None:
        return None

    likes = log1p_safe(engagement.likes)
    reposts = log1p_safe(engagement.reposts)
    replies = log1p_safe(engagement.replies)
    quotes = log1p_safe(engagement.quotes)

    return 0.55 * likes + 0.25 * reposts + 0.15 * replies + 0.05 * quotes


def _compute_idea_quality(item: schema.SaaSIdeaItem) -> int:
    """Compute idea quality score based on signal type and target audience."""
    base = SIGNAL_TYPE_SCORES.get(item.signal_type, 65)

    # Bonus for specific target audience
    if item.target_audience and len(item.target_audience) > 10:
        base = min(base + 10, 100)

    return base


def _compute_growth_score(acceleration: float) -> int:
    """Convert subreddit acceleration to 0-100 score."""
    if acceleration >= 3.0:
        return 100
    elif acceleration >= 2.0:
        return 80
    elif acceleration >= 1.5:
        return 60
    elif acceleration >= 1.2:
        return 40
    elif acceleration >= 1.0:
        return 20
    else:
        return 0


def score_saas_items(items: List[schema.SaaSIdeaItem]) -> List[schema.SaaSIdeaItem]:
    """Compute 5-factor scores for SaaS idea items.

    Factors:
        - Idea quality (30%): Signal type + target audience specificity
        - Engagement (25%): Reddit/X engagement metrics
        - Market signal (20%): Cluster size from idea_cluster
        - Growth rate (15%): Subreddit acceleration
        - Recency (10%): Linear decay over 180 days

    Args:
        items: List of SaaSIdeaItem (must have market_signal set from clustering)

    Returns:
        Items with updated scores and subscores
    """
    if not items:
        return items

    # Compute raw engagement scores (source-aware)
    eng_raw = []
    for item in items:
        if item.source == "reddit":
            eng_raw.append(compute_reddit_engagement_raw(item.engagement))
        else:
            eng_raw.append(compute_x_engagement_raw(item.engagement))

    # Normalize engagement to 0-100
    eng_normalized = normalize_to_100(eng_raw)

    for i, item in enumerate(items):
        # Factor 1: Idea quality
        idea_quality = _compute_idea_quality(item)

        # Factor 2: Engagement
        if eng_normalized[i] is not None:
            eng_score = int(eng_normalized[i])
        else:
            eng_score = DEFAULT_ENGAGEMENT

        # Factor 3: Market signal (already set by cluster_ideas)
        market_signal = item.market_signal

        # Factor 4: Growth rate
        growth = _compute_growth_score(item.subreddit_growth)

        # Factor 5: Recency (180-day window)
        recency = dates.recency_score(item.date, max_days=180)

        # Store subscores
        item.subs = schema.SubScores(
            idea_quality=idea_quality,
            engagement=eng_score,
            market_signal=market_signal,
            growth=growth,
            recency=recency,
        )

        # Weighted composite
        overall = (
            WEIGHT_IDEA_QUALITY * idea_quality +
            WEIGHT_ENGAGEMENT * eng_score +
            WEIGHT_MARKET_SIGNAL * market_signal +
            WEIGHT_GROWTH * growth +
            WEIGHT_RECENCY * recency
        )

        # Penalties
        if eng_raw[i] is None:
            overall -= UNKNOWN_ENGAGEMENT_PENALTY

        if item.date_confidence == "low":
            overall -= LOW_DATE_CONFIDENCE_PENALTY

        item.score = max(0, min(100, int(overall)))

    return items


def sort_items(items: List[schema.SaaSIdeaItem]) -> List[schema.SaaSIdeaItem]:
    """Sort items by score descending, then date, then source priority.

    Args:
        items: List of items to sort

    Returns:
        Sorted items
    """
    def sort_key(item):
        score = -item.score
        date = item.date or "0000-00-00"
        date_key = -int(date.replace("-", ""))
        source_priority = 0 if item.source == "reddit" else 1
        return (score, date_key, source_priority, item.title)

    return sorted(items, key=sort_key)
