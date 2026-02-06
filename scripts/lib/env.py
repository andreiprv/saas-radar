"""Environment and API key management for saas-radar skill."""

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_DIR = Path.home() / ".config" / "saas-radar"
CONFIG_FILE = CONFIG_DIR / ".env"
CACHE_DIR = Path.home() / ".cache" / "saas-radar"
SETUP_CACHE_FILE = CACHE_DIR / "setup.json"
SETUP_CACHE_TTL_HOURS = 24


def load_env_file(path: Path) -> Dict[str, str]:
    """Load environment variables from a file."""
    env = {}
    if not path.exists():
        return env

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                if key and value:
                    env[key] = value
    return env


def get_config() -> Dict[str, Any]:
    """Load configuration from ~/.config/saas-radar/.env and environment."""
    # Load from config file first
    file_env = load_env_file(CONFIG_FILE)

    # Environment variables override file
    config = {
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY') or file_env.get('OPENAI_API_KEY'),
        'XAI_API_KEY': os.environ.get('XAI_API_KEY') or file_env.get('XAI_API_KEY'),
        'OPENAI_MODEL_POLICY': os.environ.get('OPENAI_MODEL_POLICY') or file_env.get('OPENAI_MODEL_POLICY', 'auto'),
        'OPENAI_MODEL_PIN': os.environ.get('OPENAI_MODEL_PIN') or file_env.get('OPENAI_MODEL_PIN'),
        'XAI_MODEL_POLICY': os.environ.get('XAI_MODEL_POLICY') or file_env.get('XAI_MODEL_POLICY', 'latest'),
        'XAI_MODEL_PIN': os.environ.get('XAI_MODEL_PIN') or file_env.get('XAI_MODEL_PIN'),
    }

    return config


def config_exists() -> bool:
    """Check if configuration file exists."""
    return CONFIG_FILE.exists()


def get_available_sources(config: Dict[str, Any]) -> str:
    """Determine which sources are available based on API keys.

    Returns: 'both', 'reddit', 'x', or 'none'
    """
    has_openai = bool(config.get('OPENAI_API_KEY'))
    has_xai = bool(config.get('XAI_API_KEY'))

    if has_openai and has_xai:
        return 'both'
    elif has_openai:
        return 'reddit'
    elif has_xai:
        return 'x'
    else:
        return 'none'


def get_missing_keys(config: Dict[str, Any]) -> str:
    """Determine which API keys are missing.

    Returns: 'both', 'reddit', 'x', or 'none'
    """
    has_openai = bool(config.get('OPENAI_API_KEY'))
    has_xai = bool(config.get('XAI_API_KEY'))

    if has_openai and has_xai:
        return 'none'
    elif has_openai:
        return 'x'  # Missing xAI key
    elif has_xai:
        return 'reddit'  # Missing OpenAI key
    else:
        return 'both'  # Missing both keys


def validate_sources(requested: str, available: str) -> tuple[str, Optional[str]]:
    """Validate requested sources against available keys.

    Args:
        requested: 'auto', 'reddit', 'x', or 'both'
        available: Result from get_available_sources()

    Returns:
        Tuple of (effective_sources, error_message)
    """
    if available == 'none':
        return 'none', "No API keys configured. Add OPENAI_API_KEY and/or XAI_API_KEY to ~/.config/saas-radar/.env"

    if requested == 'auto':
        return available, None

    if requested == 'both':
        if available != 'both':
            missing = 'xAI' if available == 'reddit' else 'OpenAI'
            return 'none', f"Requested both sources but {missing} key is missing. Use --sources=auto to use available keys."
        return 'both', None

    if requested == 'reddit':
        if available == 'x':
            return 'none', "Requested Reddit but only xAI key is available."
        return 'reddit', None

    if requested == 'x':
        if available == 'reddit':
            return 'none', "Requested X but only OpenAI key is available."
        return 'x', None

    return requested, None


def load_setup_cache() -> Optional[Dict[str, Any]]:
    """Load cached setup snapshot if valid.

    Returns the cached dict if:
    - setup.json exists and is < 24 hours old
    - .env has not been modified since the cache was written

    Returns None otherwise, forcing a fresh config check.
    """
    if not SETUP_CACHE_FILE.exists():
        return None

    try:
        cache_mtime = SETUP_CACHE_FILE.stat().st_mtime
    except OSError:
        return None

    # Invalidate if .env is newer than cache
    if CONFIG_FILE.exists():
        try:
            env_mtime = CONFIG_FILE.stat().st_mtime
            if env_mtime > cache_mtime:
                return None
        except OSError:
            pass

    # Check TTL
    age_hours = (time.time() - cache_mtime) / 3600
    if age_hours >= SETUP_CACHE_TTL_HOURS:
        return None

    try:
        with open(SETUP_CACHE_FILE, 'r') as f:
            data = json.load(f)
        # Validate expected keys
        if all(k in data for k in ("available", "missing_keys", "models")):
            return data
        return None
    except (json.JSONDecodeError, OSError):
        return None


def save_setup_cache(data: Dict[str, Any]) -> None:
    """Write setup snapshot to cache. Silently fails on write errors."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(SETUP_CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass
