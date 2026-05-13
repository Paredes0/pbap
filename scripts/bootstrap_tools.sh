#!/usr/bin/env bash
# scripts/bootstrap_tools.sh
#
# Clone the 10 active prediction tools into Dataset_Bioactividad/Tool_Repos/
# and apply any patch we ship under patches/.
#
# Designed to be idempotent: re-running it on an already-populated tree
# only re-applies patches that have not been applied yet (best-effort).
#
# Usage:
#   bash scripts/bootstrap_tools.sh                # clone all 10
#   bash scripts/bootstrap_tools.sh toxinpred3 apex   # clone a subset
#
# Requires: git, python3, PyYAML.
# Run from the repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$REPO_ROOT/config/pipeline_config.yaml"
DEST="$REPO_ROOT/Dataset_Bioactividad/Tool_Repos"
PATCHES="$REPO_ROOT/patches"

if [[ ! -f "$CONFIG" ]]; then
    echo "ERROR: $CONFIG not found. Run this script from the repo root." >&2
    exit 1
fi

# Default tool list = the 10 active ones documented in docs/deployment.md §3.
DEFAULT_TOOLS=(toxinpred3 antibp3 hemopi2 hemodl deepb3p deepbp apex perseucpp acp_dpe bertaip)
if [[ $# -gt 0 ]]; then
    TOOLS=("$@")
else
    TOOLS=("${DEFAULT_TOOLS[@]}")
fi

mkdir -p "$DEST"

declare -a OK
declare -a SKIP
declare -a FAIL

for tool in "${TOOLS[@]}"; do
    url="$(python3 - "$CONFIG" "$tool" <<'PY'
import sys, yaml
with open(sys.argv[1]) as f:
    cfg = yaml.safe_load(f)
t = cfg.get("tools", {}).get(sys.argv[2])
if not t:
    print("__NOT_IN_CONFIG__")
else:
    print(t.get("github_url", "__NO_URL__"))
PY
)"

    if [[ "$url" == "__NOT_IN_CONFIG__" ]]; then
        echo "[$tool] SKIP — not in pipeline_config.yaml"
        SKIP+=("$tool (unknown)")
        continue
    fi
    if [[ "$url" == "__NO_URL__" ]]; then
        echo "[$tool] SKIP — no github_url in config"
        SKIP+=("$tool (no url)")
        continue
    fi

    target="$DEST/$tool"
    if [[ -d "$target/.git" ]]; then
        echo "[$tool] already cloned — skipping git clone"
    else
        echo "[$tool] cloning $url → $target"
        if ! git clone --depth 1 "$url" "$target"; then
            echo "[$tool] FAIL — git clone exited non-zero"
            FAIL+=("$tool")
            continue
        fi
    fi

    patch_file="$PATCHES/$tool.patch"
    if [[ -f "$patch_file" ]]; then
        # `git apply --check` returns 0 if the patch applies cleanly; we use
        # that to detect "already applied" too: if --check fails with
        # "already applied" we treat it as success.
        if git -C "$target" apply --check "$patch_file" 2>/dev/null; then
            echo "[$tool] applying patch $tool.patch"
            git -C "$target" apply "$patch_file"
        elif git -C "$target" apply --check --reverse "$patch_file" 2>/dev/null; then
            echo "[$tool] patch already applied — skipping"
        else
            echo "[$tool] FAIL — patch $tool.patch does not apply cleanly"
            FAIL+=("$tool")
            continue
        fi
    fi

    OK+=("$tool")
done

echo
echo "=== bootstrap_tools.sh summary ==="
echo "OK   (${#OK[@]}): ${OK[*]:-none}"
echo "SKIP (${#SKIP[@]}): ${SKIP[*]:-none}"
echo "FAIL (${#FAIL[@]}): ${FAIL[*]:-none}"

if [[ ${#FAIL[@]} -gt 0 ]]; then
    exit 1
fi
