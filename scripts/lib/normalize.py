"""Normalization of raw API data to SaaSIdeaItem schema."""

from typing import Any, Dict, List

from . import dates, schema


def filter_by_date_range(
    items: List[schema.SaaSIdeaItem],
    from_date: str,
    to_date: str,
    require_date: bool = False,
) -> List[schema.SaaSIdeaItem]:
    """Hard filter: Remove items outside the date range.

    Args:
        items: List of items to filter
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        require_date: If True, also remove items with no date

    Returns:
        Filtered list
    """
    result = []
    for item in items:
        if item.date is None:
            if not require_date:
                result.append(item)
            continue

        if item.date < from_date:
            continue
        if item.date > to_date:
            continue

        result.append(item)

    return result


def normalize_reddit_saas_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
    growth_map: Dict[str, float],
) -> List[schema.SaaSIdeaItem]:
    """Normalize raw Reddit items to SaaSIdeaItem schema.

    Args:
        items: Raw Reddit items from API
        from_date: Start of date range
        to_date: End of date range
        growth_map: {subreddit: acceleration} from growth scan

    Returns:
        List of SaaSIdeaItem objects
    """
    normalized = []

    for item in items:
        # Parse engagement
        engagement = None
        eng_raw = item.get("engagement")
        if isinstance(eng_raw, dict):
            engagement = schema.Engagement(
                score=eng_raw.get("score"),
                num_comments=eng_raw.get("num_comments"),
                upvote_ratio=eng_raw.get("upvote_ratio"),
            )

        # Parse comments
        top_comments = []
        for c in item.get("top_comments", []):
            top_comments.append(schema.Comment(
                score=c.get("score", 0),
                date=c.get("date"),
                author=c.get("author", ""),
                excerpt=c.get("excerpt", ""),
                url=c.get("url", ""),
            ))

        # Date confidence
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        # Growth from subreddit
        subreddit = item.get("subreddit", "")
        subreddit_growth = growth_map.get(subreddit, 1.0)

        normalized.append(schema.SaaSIdeaItem(
            id=item.get("id", ""),
            title=item.get("title", ""),
            url=item.get("url", ""),
            source="reddit",
            subreddit=subreddit,
            date=date_str,
            date_confidence=date_confidence,
            signal_type=item.get("signal_type", "problem"),
            idea_summary=item.get("idea_summary", ""),
            target_audience=item.get("target_audience", ""),
            subreddit_growth=subreddit_growth,
            engagement=engagement,
            top_comments=top_comments,
            comment_insights=item.get("comment_insights", []),
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))

    return normalized


def normalize_x_saas_items(
    items: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
) -> List[schema.SaaSIdeaItem]:
    """Normalize raw X items to SaaSIdeaItem schema.

    Args:
        items: Raw X items from API
        from_date: Start of date range
        to_date: End of date range

    Returns:
        List of SaaSIdeaItem objects
    """
    normalized = []

    for item in items:
        # Parse engagement
        engagement = None
        eng_raw = item.get("engagement")
        if isinstance(eng_raw, dict):
            engagement = schema.Engagement(
                likes=eng_raw.get("likes"),
                reposts=eng_raw.get("reposts"),
                replies=eng_raw.get("replies"),
                quotes=eng_raw.get("quotes"),
            )

        # Date confidence
        date_str = item.get("date")
        date_confidence = dates.get_date_confidence(date_str, from_date, to_date)

        normalized.append(schema.SaaSIdeaItem(
            id=item.get("id", ""),
            title=item.get("text", "")[:200],  # Use text as title for X items
            url=item.get("url", ""),
            source="x",
            author_handle=item.get("author_handle", ""),
            date=date_str,
            date_confidence=date_confidence,
            signal_type=item.get("signal_type", "problem"),
            idea_summary=item.get("idea_summary", ""),
            target_audience=item.get("target_audience", ""),
            engagement=engagement,
            relevance=item.get("relevance", 0.5),
            why_relevant=item.get("why_relevant", ""),
        ))

    return normalized
