"""
audit_lib.provenance - Provenance and reproducibility tracking.
"""

import json
import os
import sys
import platform
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def generate_provenance(output_dir, script_name, category=None, tool_id=None,
                        parameters=None, queries=None, counts=None,
                        output_stats=None, errors=None, extra=None):
    """Generate JSON provenance file for full reproducibility.
    
    Args:
        output_dir: Directory to write provenance file
        script_name: Name of the script generating this provenance
        category: Bioactivity category (if applicable)
        tool_id: Tool ID (if applicable)
        parameters: Dict of parameters used
        queries: Dict of queries executed with record counts
        counts: Dict of step-by-step record counts (pipeline stages)
        output_stats: Dict of final output statistics
        errors: List of error strings
        extra: Dict of additional metadata
    
    Returns:
        Path to generated provenance file
    """
    import pandas as pd
    import requests as req_lib
    
    provenance = {
        "script": script_name,
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_seed": parameters.get("random_seed", 42) if parameters else 42,
        "category": category,
        "tool_id": tool_id,
        "parameters": parameters or {},
        "queries_executed": queries or {},
        "pipeline_counts": counts or {},
        "output_stats": output_stats or {},
        "errors": errors or [],
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "pandas_version": pd.__version__,
            "requests_version": req_lib.__version__,
        },
    }
    
    if extra:
        provenance.update(extra)

    tag = tool_id or category or "general"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PROVENANCE_{script_name}_{tag}_{timestamp}.json"
    prov_path = os.path.join(output_dir, filename)
    
    os.makedirs(output_dir, exist_ok=True)
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False, default=str)
    
    log.info(f"Provenance saved: {prov_path}")
    return prov_path
