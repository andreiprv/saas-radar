"""OpenAI Responses API client for Reddit SaaS idea discovery."""

import json
import re
import sys
from typing import Any, Dict, List, Optional

from . import http, schema

# Fallback models when the selected model isn't accessible
MODEL_FALLBACK_ORDER = ["gpt-4o", "gpt-4o-mini"]


def _log_error(msg: str):
    """Log error to stderr."""
    sys.stderr.write(f"[REDDIT ERROR] {msg}\n")
    sys.stderr.flush()


def _log_info(msg: str):
    """Log info to stderr."""
    sys.stderr.write(f"[REDDIT] {msg}\n")
    sys.stderr.flush()


def _is_model_access_error(error: http.HTTPError) -> bool:
    """Check if error is due to model access/verification issues."""
    if error.status_code != 400:
        return False
    if not error.body:
        return False
    body_lower = error.body.lower()
    return any(phrase in body_lower for phrase in [
        "verified",
        "organization must be",
        "does not have access",
        "not available",
        "not found",
    ])


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

# Depth configurations: (min, max) threads to request
DEPTH_CONFIG = {
    "quick": (15, 25),
    "default": (30, 50),
    "deep": (70, 100),
}

SAAS_DISCOVERY_PROMPT = """Find Reddit threads where people express SaaS-related needs and ideas.

Look for threads where people:
1. PROBLEMS they want software to solve
2. WISHES for tools that don't exist ("I wish there was...")
3. People BUILDING micro-SaaS products
4. FEATURE REQUESTS / gaps in existing tools
5. People asking "how do you handle X?" for repetitive tasks

Focus on subreddits (ranked by growth):
{ranked_subreddit_list}

SEARCH STRATEGY (run multiple searches):
1. "[subreddit] wish there was a tool" site:reddit.com
2. "[subreddit] looking for software" site:reddit.com
3. "[subreddit] automate" site:reddit.com
4. "micro SaaS" OR "SaaS idea" site:reddit.com
5. "does anyone know a tool for" site:reddit.com
6. "{topic}" site:reddit.com

Additional topic-specific search: "{topic}" combined with the subreddits above.

Return as many relevant threads as you find. We filter by date server-side.

Find {min_items}-{max_items} threads. Return MORE rather than fewer.

Classify each thread's SIGNAL TYPE:
- "problem": User describes a pain point
- "wish": User wants a tool that doesn't exist
- "building": Someone is building/launched a micro-SaaS
- "feature_gap": Feature request about existing tool
- "workflow": Manual workflow that could be automated

REQUIRED: URLs must contain "/r/" AND "/comments/"
REJECT: developers.reddit.com, business.reddit.com

Return JSON:
{{
  "items": [
    {{
      "title": "Thread title",
      "url": "https://www.reddit.com/r/sub/comments/xyz/title/",
      "subreddit": "subreddit_name",
      "date": "YYYY-MM-DD or null",
      "signal_type": "problem|wish|building|feature_gap|workflow",
      "idea_summary": "1-2 sentence SaaS opportunity description",
      "target_audience": "Who would pay for this",
      "why_relevant": "Brief explanation",
      "relevance": 0.85
    }}
  ]
}}"""


def search_reddit(
    api_key: str,
    model: str,
    topic: str,
    from_date: str,
    to_date: str,
    depth: str = "default",
    growth_signals: Optional[List[schema.GrowthSignal]] = None,
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Search Reddit for SaaS idea threads using OpenAI Responses API.

    Args:
        api_key: OpenAI API key
        model: Model to use
        topic: Search topic
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        depth: Research depth - "quick", "default", or "deep"
        growth_signals: Growth signals for subreddit ranking
        mock_response: Mock response for testing

    Returns:
        Raw API response
    """
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])

    # Format ranked subreddit list
    if growth_signals:
        from . import subreddit_growth
        ranked_list = subreddit_growth.format_ranked_list(growth_signals)
    else:
        ranked_list = "\n".join(f"- r/{s}" for s in [
            "SaaS", "microsaas", "indiehackers", "startups", "Entrepreneur",
            "SideProject", "selfhosted", "nocode", "automation", "smallbusiness",
        ])

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout = 90 if depth == "quick" else 120 if depth == "default" else 180

    models_to_try = [model] + [m for m in MODEL_FALLBACK_ORDER if m != model]

    input_text = SAAS_DISCOVERY_PROMPT.format(
        topic=topic,
        ranked_subreddit_list=ranked_list,
        min_items=min_items,
        max_items=max_items,
    )

    last_error = None
    for current_model in models_to_try:
        payload = {
            "model": current_model,
            "tools": [
                {
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": ["reddit.com"]
                    }
                }
            ],
            "include": ["web_search_call.action.sources"],
            "input": input_text,
        }

        try:
            return http.post(OPENAI_RESPONSES_URL, payload, headers=headers, timeout=timeout)
        except http.HTTPError as e:
            last_error = e
            if _is_model_access_error(e):
                _log_info(f"Model {current_model} not accessible, trying fallback...")
                continue
            raise

    if last_error:
        _log_error(f"All models failed. Last error: {last_error}")
        raise last_error
    raise http.HTTPError("No models available")


def parse_reddit_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse OpenAI response to extract SaaS idea items.

    Args:
        response: Raw API response

    Returns:
        List of item dicts with signal_type, idea_summary, target_audience
    """
    items = []

    # Check for API errors first
    if "error" in response and response["error"]:
        error = response["error"]
        err_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        _log_error(f"OpenAI API error: {err_msg}")
        return items

    # Try to find the output text
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

    # Also check for choices (older format)
    if not output_text and "choices" in response:
        for choice in response["choices"]:
            if "message" in choice:
                output_text = choice["message"].get("content", "")
                break

    if not output_text:
        print(f"[REDDIT WARNING] No output text found in OpenAI response. Keys present: {list(response.keys())}", flush=True)
        return items

    # Extract JSON from the response
    json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            items = data.get("items", [])
        except json.JSONDecodeError:
            pass

    # Validate and clean items
    valid_signal_types = {"problem", "wish", "building", "feature_gap", "workflow"}
    clean_items = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        url = item.get("url", "")
        if not url or "reddit.com" not in url:
            continue

        signal_type = str(item.get("signal_type", "problem")).strip().lower()
        if signal_type not in valid_signal_types:
            signal_type = "problem"

        clean_item = {
            "id": f"R{i+1}",
            "title": str(item.get("title", "")).strip(),
            "url": url,
            "subreddit": str(item.get("subreddit", "")).strip().lstrip("r/"),
            "date": item.get("date"),
            "signal_type": signal_type,
            "idea_summary": str(item.get("idea_summary", "")).strip(),
            "target_audience": str(item.get("target_audience", "")).strip(),
            "why_relevant": str(item.get("why_relevant", "")).strip(),
            "relevance": min(1.0, max(0.0, float(item.get("relevance", 0.5)))),
        }

        # Validate date format
        if clean_item["date"]:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(clean_item["date"])):
                clean_item["date"] = None

        clean_items.append(clean_item)

    return clean_items
