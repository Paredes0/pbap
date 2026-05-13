"""
audit_lib.config - Configuration loading and validation.
Loads pipeline_config.yaml and categories_config.yaml.
"""

import os
import sys
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Try to import yaml, provide helpful error if missing
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def _find_config_file(config_path, script_dir=None):
    """Resolve config file path (absolute or relative to script dir)."""
    if os.path.isabs(config_path) and os.path.exists(config_path):
        return config_path
    if script_dir:
        candidate = os.path.join(script_dir, config_path)
        if os.path.exists(candidate):
            return candidate
    # Try relative to this module's parent dir
    module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(module_dir, config_path)
    if os.path.exists(candidate):
        return candidate
    raise FileNotFoundError(f"Config file not found: {config_path}")


def load_pipeline_config(config_path="pipeline_config.yaml"):
    """Load and validate master pipeline config (tools)."""
    resolved = _find_config_file(config_path)
    log.info(f"Loading pipeline config: {resolved}")
    with open(resolved, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Validate required sections
    assert "global" in cfg, "pipeline_config.yaml must have 'global' section"
    assert "tools" in cfg, "pipeline_config.yaml must have 'tools' section"

    # Set defaults
    g = cfg["global"]
    g.setdefault("random_seed", 42)
    g.setdefault("min_length", 5)
    g.setdefault("max_length", 100)
    g.setdefault("standard_aa", "ACDEFGHIKLMNPQRSTVWY")
    g.setdefault("max_retries", 3)
    g.setdefault("retry_delays", [5, 15, 45])
    g.setdefault("cdhit_thresholds", [0.40, 0.60, 0.80])
    g.setdefault("base_output_dir", "Dataset_Bioactividad")

    return cfg


def load_category_config(config_path="categories_config.yaml"):
    """Load and validate category config (bioactivity categories)."""
    resolved = _find_config_file(config_path)
    log.info(f"Loading category config: {resolved}")
    with open(resolved, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert "categories" in cfg, "categories_config.yaml must have 'categories' section"
    return cfg


def get_tool_config(tool_id, pipeline_config):
    """Get config for a specific tool, merging with global defaults."""
    tools = pipeline_config.get("tools", {})
    if tool_id not in tools:
        available = list(tools.keys())
        raise KeyError(f"Tool '{tool_id}' not found. Available: {available}")

    tool_cfg = tools[tool_id].copy()
    tool_cfg["tool_id"] = tool_id

    # Merge global defaults
    g = pipeline_config.get("global", {})
    tool_cfg.setdefault("length_range", [g.get("min_length", 5), g.get("max_length", 100)])

    return tool_cfg


def get_tools_for_category(category, pipeline_config):
    """Return list of tool_ids belonging to a category."""
    tools = pipeline_config.get("tools", {})
    return [tid for tid, tcfg in tools.items() if tcfg.get("category") == category]


def get_all_categories(pipeline_config):
    """Return set of unique categories from all tools."""
    tools = pipeline_config.get("tools", {})
    return sorted(set(tcfg.get("category", "unknown") for tcfg in tools.values()))


def get_base_output_dir(pipeline_config):
    """Get absolute path to base output directory."""
    g = pipeline_config.get("global", {})
    base = g.get("base_output_dir", "Dataset_Bioactividad")
    if os.path.isabs(base):
        return base
    # Relative to config file's directory
    module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(module_dir, base)
