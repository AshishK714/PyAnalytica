"""YAML course configuration loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class CourseConfig:
    """Course-specific configuration."""
    course_name: str = "PyAnalytica"
    institution: str = ""
    theme: str = "default"
    bundled_datasets: list[str] = field(default_factory=lambda: ["diamonds", "tips", "titanic"])
    menus: dict[str, Any] = field(default_factory=lambda: {
        "data": True,
        "describe": True,
        "relate": True,
        "model": True,
        "learn": True,
        "homework": True,
        "report": True,
        "advanced": True,
        "ai": False,
    })
    prompts_enabled: bool = False
    custom_prompts: list[dict] = field(default_factory=list)
    ai_config: dict = field(default_factory=dict)


def load_config(path: str | Path | None = None) -> CourseConfig:
    """Load a course configuration from a YAML file.

    If no path is given, returns the default configuration.
    """
    if path is None:
        return CourseConfig()

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    if not HAS_YAML:
        raise ImportError("PyYAML is required to load config files: pip install pyyaml")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError("Config file must be a YAML mapping")

    config = CourseConfig()

    course = raw.get("course", {})
    if isinstance(course, dict):
        config.course_name = course.get("name", config.course_name)
        config.institution = course.get("institution", config.institution)

    config.theme = raw.get("theme", config.theme)

    datasets = raw.get("datasets", {})
    if isinstance(datasets, dict):
        config.bundled_datasets = datasets.get("bundled", config.bundled_datasets)

    menus = raw.get("menus", {})
    if isinstance(menus, dict):
        config.menus.update(menus)

    prompts = raw.get("prompts", {})
    if isinstance(prompts, dict):
        config.prompts_enabled = prompts.get("enabled", config.prompts_enabled)
        config.custom_prompts = prompts.get("custom", config.custom_prompts)

    ai = raw.get("ai", {})
    if isinstance(ai, dict):
        config.ai_config = ai

    return config


def is_menu_visible(config: CourseConfig, menu: str) -> bool:
    """Check if a menu should be visible given the current date.

    Menu config can be:
    - True/False: always visible/hidden
    - dict with 'visible' and optional 'after_date': date-gated
    """
    menu_val = config.menus.get(menu, False)

    if isinstance(menu_val, bool):
        return menu_val

    if isinstance(menu_val, dict):
        visible = menu_val.get("visible", False)
        if not visible:
            return False
        after_date = menu_val.get("after_date")
        if after_date is None:
            return True
        if isinstance(after_date, str):
            after_date = date.fromisoformat(after_date)
        elif isinstance(after_date, datetime):
            after_date = after_date.date()
        return date.today() >= after_date

    return bool(menu_val)
