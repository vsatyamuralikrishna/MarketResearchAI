"""
Load config from config.yaml (optional). Falls back to defaults.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.gemini_client import DEFAULT_MODELS

_config: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    global _config
    if _config is not None:
        return _config
    try:
        import yaml
        path = Path(__file__).resolve().parent.parent / "config.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _config = yaml.safe_load(f) or {}
        else:
            _config = {}
    except Exception:
        _config = {}
    return _config


def get_model(agent_key: str) -> str:
    """Return model name for agent (e.g. 'taxonomy', 'segment_specialist')."""
    cfg = _load_config()
    models = cfg.get("models") or {}
    return models.get(agent_key) or DEFAULT_MODELS.get(agent_key, "gemini-2.5-flash")


def get_max_categories() -> int | None:
    """Return max categories limit (0 or missing = None)."""
    cfg = _load_config()
    n = cfg.get("limits") or {}
    v = n.get("max_categories", 0)
    return None if v == 0 else v


def get_max_segments_per_category() -> int | None:
    """Return max segments per category (0 or missing = None)."""
    cfg = _load_config()
    n = cfg.get("limits") or {}
    v = n.get("max_segments_per_category", 0)
    return None if v == 0 else v
