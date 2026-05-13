"""
audit_lib - Shared library for peptide bioactivity pipeline audit system.

Modules:
    config            - YAML config loading (pipeline_config, categories_config)
    tool_runner       - Tool execution engine (micromamba subprocess orchestration)
    tool_length_range - Per-tool length range inference from training data
    downloader        - Model weights download (Zenodo, HuggingFace, manual)
    uniprot_client    - UniProt REST API with pagination/retry/checkpointing
    sequence_utils    - Sequence validation, habitat, length bins, subfragments
    cdhit_utils       - CD-HIT / CD-HIT-2D with SSH dispatch
    length_sampling   - Natural length distribution sampling
    state_manager     - Incremental audit state (.audit_state.json)
    provenance        - JSON provenance files
    db_parsers        - Parsers for DBAASP, APD3, ConoServer, Hemolytik, etc.
    logging_setup     - Logging configuration
"""

__version__ = "2.0.0"

__all__ = [
    "config",
    "tool_runner",
    "tool_length_range",
    "downloader",
    "sequence_utils",
    "uniprot_client",
    "cdhit_utils",
    "length_sampling",
    "state_manager",
    "provenance",
    "db_parsers",
    "logging_setup",
]
