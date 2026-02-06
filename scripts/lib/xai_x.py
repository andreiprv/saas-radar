"""xAI API client for X (Twitter) SaaS idea discovery."""

import json
import re
import sys
from typing import Any, Dict, List, Optional

from . import http

XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"

DEPTH_CONFIG = {
    "quick": (8, 12),
    "default": (20, 30),
    "deep": (40, 60),
}


def _log_error(msg: str):
    """Log error to stderr."""
    sys.stderr.write(f"[X ERROR] {msg}\n")
    sys.stderr.flush()


SAAS_X_PROMPT = """You have access to real-time X (Twitter) data. Search for posts about SaaS ideas and micro-SaaS opportunities.

Topic focus: {topic}

Search for:
1. Indie hackers sharing what they're building
2. "Someone build this" or "I wish there was" tweets
3. People discussing SaaS pain points and tool gaps
4. Micro-SaaS launch announcements and reactions
5. "How do you handle X" tweets about business workflows
6. Threads about underserved markets or niche software needs

Focus on posts from {from_date} to {to_date}. Find {min_items}-{max_items} high-quality, relevant posts.

Classify each post's SIGNAL TYPE:
- "problem": Someone describing a pain point
- "wish": Wishing for a tool that doesn't exist
- "building": Someone building/launching a micro-SaaS
- "feature_gap": Complaining about missing features in existing tools
- "workflow": Describing a manual workflow that could be automated

IMPORTANT: Return ONLY valid JSON in this exact format, no other text:
{{
  "items": [
    {{
      "text": "Post text content (truncated if long)",
      "url": "https://x.com/user/status/...",
      "author_handle": "username",
      "date": "YYYY-MM-DD or null if unknown",
      "signal_type": "problem|wish|building|feature_gap|workflow",
      "idea_summary": "1-2 sentence SaaS opportunity",
      "target_audience": "Who would pay for this",
      "engagement": {{
        "likes": 100,
        "reposts": 25,
        "replies": 15,
        "quotes": 5
      }},
      "why_relevant": "Brief explanation of relevance",
      "relevance": 0.85
    }}
  ]
}}

Rules:
- relevance is 0.0 to 1.0 (1.0 = highly relevant)
- date must be YYYY-MM-DD format or null
- engagement can be null if unknown
- Include diverse voices/accounts
- Prefer posts with substantive content, not just links"""


def search_x(
    api_key: str,
    model: str,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search X for SaaS idea posts using xAI API.

    Args:
        api_key: xAI API key
        model: Model to use
        topic: Search topic
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: Research depth
        mock_response: Mock response for testing

    Returns:
        Raw API response
    """
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout = 90 if depth == "quick" else 120 if depth == "default" else 180

    payload = {
        "model": model,
        "tools": [
            {"type": "x_search"}
        ],
        "input": [
            {
                "role": "user",
                "content": SAAS_X_PROMPT.format(
                    topic=topic,
                    from_date=from_date,
                    to_date=to_date,
                    min_items=min_items,
                    max_items=max_items,
                ),
            }
        ],
    }

    return http.post(XAI_RESPONSES_URL, payload, headers=headers, timeout=timeout)


def parse_x_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse xAI response to extract SaaS idea items from X.

    Args:
        response: Raw API response

    Returns:
        List of item dicts with signal_type, idea_summary, target_audience
    """
    items = []

    if "error" in response and response["error"]:
        error = response["error"]
        err_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        _log_error(f"xAI API error: {err_msg}")
        return items

    output_text = ""
    if "output" in response:
        output = response["output"]
        if isinstance(output, str):
            output_text = output
        elif isinstance(output, list):
            for item in output:
                if isinstance(item, dict):
                    if item.get("type") == "message":
                        content = item.get("content", [])
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "output_text":
                                output_text = c.get("text", "")
                                break
                    elif "text" in item:
                        output_text = item["text"]
                elif isinstance(item, str):
                    output_text = item
                if output_text:
                    break

    if not output_text and "choices" in response:
        for choice in response["choices"]:
            if "message" in choice:
                output_text = choice["message"].get("content", "")
                break

    if not output_text:
        return items

    json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            items = data.get("items", [])
        except json.JSONDecodeError:
            pass

    valid_signal_types = {"problem", "wish", "building", "feature_gap", "workflow"}
    clean_items = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        url = item.get("url", "")
        if not url:
            continue

        # Parse engagement
        engagement = None
        eng_raw = item.get("engagement")
        if isinstance(eng_raw, dict):
            engagement = {
                "likes": int(eng_raw.get("likes", 0)) if eng_raw.get("likes") else None,
                "reposts": int(eng_raw.get("reposts", 0)) if eng_raw.get("reposts") else None,
                "replies": int(eng_raw.get("replies", 0)) if eng_raw.get("replies") else None,
                "quotes": int(eng_raw.get("quotes", 0)) if eng_raw.get("quotes") else None,
            }

        signal_type = str(item.get("signal_type", "problem")).strip().lower()
        if signal_type not in valid_signal_types:
            signal_type = "problem"

        clean_item = {
            "id": f"X{i+1}",
            "text": str(item.get("text", "")).strip()[:500],
            "url": url,
            "author_handle": str(item.get("author_handle", "")).strip().lstrip("@"),
            "date": item.get("date"),
            "signal_type": signal_type,
            "idea_summary": str(item.get("idea_summary", "")).strip(),
            "target_audience": str(item.get("target_audience", "")).strip(),
            "engagement": engagement,
            "why_relevant": str(item.get("why_relevant", "")).strip(),
            "relevance": min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
        }

        if clean_item["date"]:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(clean_item["date"])):
                clean_item["date"] = None

        clean_items.append(clean_item)

    return clean_items
