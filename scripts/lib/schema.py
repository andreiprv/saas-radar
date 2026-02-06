"""Data schemas for saas-radar skill."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class Engagement:
    """Engagement metrics."""
    # Reddit fields
    score: Optional[int] = None
    num_comments: Optional[int] = None
    upvote_ratio: Optional[float] = None

    # X fields
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        d = {}
        if self.score is not None:
            d['score'] = self.score
        if self.num_comments is not None:
            d['num_comments'] = self.num_comments
        if self.upvote_ratio is not None:
            d['upvote_ratio'] = self.upvote_ratio
        if self.likes is not None:
            d['likes'] = self.likes
        if self.reposts is not None:
            d['reposts'] = self.reposts
        if self.replies is not None:
            d['replies'] = self.replies
        if self.quotes is not None:
            d['quotes'] = self.quotes
        return d if d else None


@dataclass
class Comment:
    """Reddit comment."""
    score: int
    date: Optional[str]
    author: str
    excerpt: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'score': self.score,
            'date': self.date,
            'author': self.author,
            'excerpt': self.excerpt,
            'url': self.url,
        }


@dataclass
class SubScores:
    """Component scores (5-factor for SaaS ideas)."""
    idea_quality: int = 0
    engagement: int = 0
    market_signal: int = 0
    growth: int = 0
    recency: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            'idea_quality': self.idea_quality,
            'engagement': self.engagement,
            'market_signal': self.market_signal,
            'growth': self.growth,
            'recency': self.recency,
        }


@dataclass
class GrowthSignal:
    """Subreddit growth metrics."""
    subreddit: str
    subscribers: int
    active_users: int
    vitality: float           # active/subscribers
    acceleration: float       # post rate recent/older
    engagement_accel: float   # avg score recent/avg score older
    recent_count: int
    older_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'subreddit': self.subreddit,
            'subscribers': self.subscribers,
            'active_users': self.active_users,
            'vitality': round(self.vitality, 4),
            'acceleration': round(self.acceleration, 2),
            'engagement_accel': round(self.engagement_accel, 2),
            'recent_count': self.recent_count,
            'older_count': self.older_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GrowthSignal":
        return cls(
            subreddit=data['subreddit'],
            subscribers=data.get('subscribers', 0),
            active_users=data.get('active_users', 0),
            vitality=data.get('vitality', 0.0),
            acceleration=data.get('acceleration', 1.0),
            engagement_accel=data.get('engagement_accel', 1.0),
            recent_count=data.get('recent_count', 0),
            older_count=data.get('older_count', 0),
        )


@dataclass
class SaaSIdeaItem:
    """Unified SaaS idea item (Reddit or X source)."""
    id: str
    title: str
    url: str
    source: str                        # "reddit" or "x"
    subreddit: str = ""                # empty for X
    author_handle: str = ""            # empty for Reddit
    date: Optional[str] = None
    date_confidence: str = "low"
    signal_type: str = "problem"       # problem|wish|building|feature_gap|workflow
    idea_summary: str = ""
    target_audience: str = ""
    subreddit_growth: float = 1.0      # acceleration from growth scan
    market_signal: int = 25            # cluster score 0-100
    cluster_id: int = -1
    engagement: Optional[Engagement] = None
    top_comments: List[Comment] = field(default_factory=list)
    comment_insights: List[str] = field(default_factory=list)
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'subreddit': self.subreddit,
            'author_handle': self.author_handle,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'signal_type': self.signal_type,
            'idea_summary': self.idea_summary,
            'target_audience': self.target_audience,
            'subreddit_growth': round(self.subreddit_growth, 2),
            'market_signal': self.market_signal,
            'cluster_id': self.cluster_id,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'top_comments': [c.to_dict() for c in self.top_comments],
            'comment_insights': self.comment_insights,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class SaaSReport:
    """Full SaaS idea discovery report."""
    topic: str
    range_from: str
    range_to: str
    generated_at: str
    mode: str
    openai_model_used: Optional[str] = None
    xai_model_used: Optional[str] = None
    growth_signals: List[GrowthSignal] = field(default_factory=list)
    items: List[SaaSIdeaItem] = field(default_factory=list)
    reddit_error: Optional[str] = None
    x_error: Optional[str] = None
    from_cache: bool = False
    cache_age_hours: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'topic': self.topic,
            'range': {
                'from': self.range_from,
                'to': self.range_to,
            },
            'generated_at': self.generated_at,
            'mode': self.mode,
            'openai_model_used': self.openai_model_used,
            'xai_model_used': self.xai_model_used,
            'growth_signals': [g.to_dict() for g in self.growth_signals],
            'items': [item.to_dict() for item in self.items],
        }
        if self.reddit_error:
            d['reddit_error'] = self.reddit_error
        if self.x_error:
            d['x_error'] = self.x_error
        if self.from_cache:
            d['from_cache'] = self.from_cache
        if self.cache_age_hours is not None:
            d['cache_age_hours'] = self.cache_age_hours
        return d


def create_saas_report(
    topic: str,
    from_date: str,
    to_date: str,
    mode: str,
    openai_model: Optional[str] = None,
    xai_model: Optional[str] = None,
) -> SaaSReport:
    """Create a new SaaS report with metadata."""
    return SaaSReport(
        topic=topic,
        range_from=from_date,
        range_to=to_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        openai_model_used=openai_model,
        xai_model_used=xai_model,
    )
