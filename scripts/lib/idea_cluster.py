"""Idea clustering for market signal detection."""

import re
from typing import List, Set

from . import schema


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_ngrams(text: str, n: int = 3) -> Set[str]:
    """Get character n-grams from text."""
    text = normalize_text(text)
    if len(text) < n:
        return {text}
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _find_root(parent: List[int], i: int) -> int:
    """Union-Find: find root with path compression."""
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent: List[int], rank: List[int], a: int, b: int):
    """Union-Find: union by rank."""
    ra, rb = _find_root(parent, a), _find_root(parent, b)
    if ra == rb:
        return
    if rank[ra] < rank[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    if rank[ra] == rank[rb]:
        rank[ra] += 1


def cluster_ideas(
    items: List[schema.SaaSIdeaItem],
    threshold: float = 0.3,
) -> List[schema.SaaSIdeaItem]:
    """Group similar ideas using Jaccard similarity on idea_summary.

    Uses Union-Find for transitive clustering. Threshold is lower than
    dedupe (0.3 vs 0.7) to group related ideas, not just duplicates.

    Cluster size determines market_signal score:
    - 1 thread = 25 (single signal)
    - 2 threads = 50
    - 3 threads = 75
    - 4+ threads = 100 (strong market signal)

    Args:
        items: List of SaaSIdeaItem
        threshold: Similarity threshold (default 0.3)

    Returns:
        Items with updated market_signal and cluster_id
    """
    if len(items) <= 1:
        for item in items:
            item.market_signal = 25
            item.cluster_id = 0
        return items

    n = len(items)

    # Pre-compute n-grams for idea_summary
    ngrams = [get_ngrams(item.idea_summary) for item in items]

    # Union-Find
    parent = list(range(n))
    rank = [0] * n

    # Compare all pairs
    for i in range(n):
        for j in range(i + 1, n):
            sim = jaccard_similarity(ngrams[i], ngrams[j])
            if sim >= threshold:
                _union(parent, rank, i, j)

    # Compute cluster sizes
    clusters = {}
    for i in range(n):
        root = _find_root(parent, i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(i)

    # Assign cluster_id and market_signal
    for cluster_id, (root, members) in enumerate(clusters.items()):
        cluster_size = len(members)
        market_signal = min(cluster_size * 25, 100)
        for idx in members:
            items[idx].cluster_id = cluster_id
            items[idx].market_signal = market_signal

    return items
