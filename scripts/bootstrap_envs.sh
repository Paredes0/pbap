#!/usr/bin/env bash
# scripts/bootstrap_envs.sh
#
# Create the 6 micromamba environments needed to run the 10 active tools,
# using the conda environment YAML exports we ship under envs/.
#
# Each YAML pins exact package versions (no `file://` paths, fully
# portable). Disk footprint: ~30–40 GB after all 6 envs are created.
#
# Usage:
#   bash scripts/bootstrap_envs.sh                # create all 6
#   bash scripts/bootstrap_envs.sh ml torch       # create a subset
#
# Requires: micromamba on PATH. If it lives under ~/bin/micromamba and
# is not on PATH, run with `MICROMAMBA_BIN=~/bin/micromamba bash ...`.
# Run from the repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVS_DIR="$REPO_ROOT/envs"
MICROMAMBA_BIN="${MICROMAMBA_BIN:-$(command -v micromamba || echo micromamba)}"

DEFAULT_ENVS=(ml torch qsar torch_legacy deepb3p_legacy pipeline_bertaip)
if [[ $# -gt 0 ]]; then
    ENVS=("$@")
else
    ENVS=("${DEFAULT_ENVS[@]}")
fi

if ! "$MICROMAMBA_BIN" --version >/dev/null 2>&1; then
    cat >&2 <<EOF
ERROR: micromamba not found.

Tried: $MICROMAMBA_BIN

Install it from https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html
and re-run, or pass an explicit path:

    MICROMAMBA_BIN=/path/to/micromamba bash scripts/bootstrap_envs.sh
EOF
    exit 1
fi

declare -a OK
declare -a SKIP
declare -a FAIL

for env in "${ENVS[@]}"; do
    yaml="$ENVS_DIR/$env.yaml"
    if [[ ! -f "$yaml" ]]; then
        echo "[$env] SKIP — $yaml not found"
        SKIP+=("$env (missing yaml)")
        continue
    fi

    if "$MICROMAMBA_BIN" env list | awk '{print $1}' | grep -qx "$env"; then
        echo "[$env] already exists — skipping (delete with \`micromamba env remove -n $env\` to reinstall)"
        SKIP+=("$env (exists)")
        continue
    fi

    echo "[$env] creating from $yaml"
    if "$MICROMAMBA_BIN" create -y -n "$env" -f "$yaml"; then
        OK+=("$env")
    else
        echo "[$env] FAIL — micromamba create returned non-zero"
        FAIL+=("$env")
    fi
done

echo
echo "=== bootstrap_envs.sh summary ==="
echo "OK   (${#OK[@]}): ${OK[*]:-none}"
echo "SKIP (${#SKIP[@]}): ${SKIP[*]:-none}"
echo "FAIL (${#FAIL[@]}): ${FAIL[*]:-none}"

if [[ ${#FAIL[@]} -gt 0 ]]; then
    cat >&2 <<EOF

One or more environments failed. Common causes:
- Insufficient disk (each env is 3–8 GB; 6 envs ≈ 30–40 GB).
- A package version is no longer available on conda-forge / bioconda.
  In that case, open the failing envs/<env>.yaml and either bump or
  unpin the offending entry.
- Network hiccups while resolving dependencies. Re-running the
  script picks up where it left off (existing envs are skipped).
EOF
    exit 1
fi
