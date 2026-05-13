"""
audit_lib.logging_setup - Centralized logging configuration.
"""

import logging
import os
import sys
from datetime import datetime


def configure_logging(log_dir=None, script_name="audit", level=logging.INFO):
    """Configure logging with console and optional file output."""
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{script_name}_{timestamp}.log")
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt,
                        handlers=handlers)
    return logging.getLogger()
