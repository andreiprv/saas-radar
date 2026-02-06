"""Near-duplicate detection for saas-radar skill."""

import re
from typing import List, Set, Tuple

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


def find_duplicates(
    items: List[schema.SaaSIdeaItem],
    threshold: float = 0.7,
) -> List[Tuple[int, int]]:
    """Find near-duplicate pairs in items.

    Args:
        items: List of items to check
        threshold: Similarity threshold (0-1)

    Returns:
        List of (i, j) index pairs where i < j
    """
    duplicates = []

    # Pre-compute n-grams on title
    ngrams = [get_ngrams(item.title) for item in items]

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            similarity = jaccard_similarity(ngrams[i], ngrams[j])
            if similarity >= threshold:
                duplicates.append((i, j))

    return duplicates


def dedupe_saas(
    items: List[schema.SaaSIdeaItem],
    threshold: float = 0.7,
) -> List[schema.SaaSIdeaItem]:
    """Remove near-duplicates, keeping highest-scored item.

    Args:
        items: List of items (should be pre-sorted by score descending)
        threshold: Similarity threshold

    Returns:
        Deduplicated items
    """
    if len(items) <= 1:
        return items

    dup_pairs = find_duplicates(items, threshold)

    to_remove = set()
    for i, j in dup_pairs:
        if items[i].score >= items[j].score:
            to_remove.add(j)
        else:
            to_remove.add(i)

    return [item for idx, item in enumerate(items) if idx not in to_remove]
