"""
audit_lib.state_manager - Incremental audit state management.
Tracks which tools have been audited and detects changes for re-auditing.
"""

import hashlib
import json
import os
import logging
import subprocess
from datetime import datetime, timezone

log = logging.getLogger(__name__)


class AuditStateManager:
    """Manages .audit_state.json for incremental re-auditing."""

    def __init__(self, state_file):
        self.state_file = state_file
        self.state = self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"schema_version": "1.0", "last_run": None,
                "tools": {}, "category_pools": {}}

    def save(self):
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
        log.info(f"Audit state saved: {self.state_file}")

    def compute_tool_hash(self, tool_id, tool_config):
        """Hash of repo URL + config to detect changes."""
        data = json.dumps({
            "tool_id": tool_id,
            "github_url": tool_config.get("github_url", ""),
            "category": tool_config.get("category", ""),
            "length_range": tool_config.get("length_range", []),
            "training_data": tool_config.get("training_data", {}),
        }, sort_keys=True)
        repo_dir = tool_config.get("_repo_dir", "")
        commit = ""
        if repo_dir and os.path.isdir(os.path.join(repo_dir, ".git")):
            try:
                result = subprocess.run(
                    ["git", "-C", repo_dir, "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    commit = result.stdout.strip()
            except Exception:
                pass
        return hashlib.sha256((data + commit).encode()).hexdigest()[:16]

    def needs_audit(self, tool_id, current_hash):
        """Return True if tool needs re-auditing."""
        tool_state = self.state.get("tools", {}).get(tool_id, {})
        if tool_state.get("config_hash", "") != current_hash:
            return True
        completed = tool_state.get("completed_steps", [])
        required = ["extract", "cdhit", "negatives", "audit"]
        return not all(s in completed for s in required)

    def mark_step_complete(self, tool_id, hash_val, step):
        if tool_id not in self.state["tools"]:
            self.state["tools"][tool_id] = {
                "config_hash": hash_val, "completed_steps": [],
                "last_audit": None}
        t = self.state["tools"][tool_id]
        t["config_hash"] = hash_val
        if step not in t["completed_steps"]:
            t["completed_steps"].append(step)

    def mark_complete(self, tool_id, hash_val):
        self.state["tools"][tool_id] = {
            "config_hash": hash_val,
            "completed_steps": ["extract", "cdhit", "negatives", "predict", "audit"],
            "last_audit": datetime.now(timezone.utc).isoformat(),
        }

    def get_completed_steps(self, tool_id):
        return self.state.get("tools", {}).get(tool_id, {}).get(
            "completed_steps", [])

    def mark_category_pool(self, category, n_sequences, pool_hash=None):
        self.state["category_pools"][category] = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "n_sequences": n_sequences, "hash": pool_hash or ""}

    def has_category_pool(self, category):
        return category in self.state.get("category_pools", {})

    def reset_tool(self, tool_id):
        if tool_id in self.state.get("tools", {}):
            del self.state["tools"][tool_id]
