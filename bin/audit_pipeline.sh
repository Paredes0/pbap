#!/usr/bin/env bash
set -euo pipefail

#=============================================================================
# audit_pipeline.sh - Master orchestrator for bioactivity tool leakage audit
#
# Usage:
#   ./audit_pipeline.sh                     # Audit all tools
#   ./audit_pipeline.sh --tool toxinpred3   # Audit one tool
#   ./audit_pipeline.sh --force             # Force re-audit all
#   ./audit_pipeline.sh --skip-pred         # Skip running predictions
#   ./audit_pipeline.sh --dry-run           # Show what would be done
#=============================================================================

# Convert Git Bash /z/... path back to Z:/... for Python on Windows
to_win_path() {
    local p="$1"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        if [[ "$p" =~ ^/([a-zA-Z])/ ]]; then
            p="${BASH_REMATCH[1]^}:${p:2}"
        fi
    fi
    echo "$p"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR_WIN="$(to_win_path "${SCRIPT_DIR}")"
ROOT_DIR_WIN="${SCRIPT_DIR_WIN}/.."
PIPELINE_CONFIG="${ROOT_DIR_WIN}/config/pipeline_config.yaml"
CATEGORY_CONFIG="${ROOT_DIR_WIN}/config/categories_config.yaml"
BASE_DIR="${ROOT_DIR_WIN}/Dataset_Bioactividad"
AUDIT_STATE="${BASE_DIR}/.audit_state.json"
LOG_DIR="${BASE_DIR}/logs"
PYTHON="${PYTHON:-python3}"

# Parse arguments
TOOLS_FILTER=""
FORCE_REAUDIT=false
SKIP_PREDICTIONS=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --tool)      TOOLS_FILTER="$2"; shift 2;;
        --force)     FORCE_REAUDIT=true; shift;;
        --skip-pred) SKIP_PREDICTIONS=true; shift;;
        --dry-run)   DRY_RUN=true; shift;;
        -h|--help)
            echo "Usage: $0 [--tool TOOL_ID] [--force] [--skip-pred] [--dry-run]"
            exit 0;;
        *)           echo "Unknown option: $1"; exit 1;;
    esac
done

mkdir -p "${LOG_DIR}" "${BASE_DIR}/Category_Pools" "${BASE_DIR}/Tool_Repos" \
         "${BASE_DIR}/Tool_Audits" "${BASE_DIR}/Global_Audit"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_LOG="${LOG_DIR}/audit_${TIMESTAMP}.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${MASTER_LOG}"; }

#=============================================================================
# Step 0: Validate prerequisites
#=============================================================================
log "=== AUDIT PIPELINE START ==="
log "Script dir: ${SCRIPT_DIR_WIN}"
log "Config:     ${PIPELINE_CONFIG}"

# Add root dir to PYTHONPATH so audit_lib and scripts are importable
export PYTHONPATH="${ROOT_DIR_WIN}:${PYTHONPATH:-}"

# Check Python and required packages
${PYTHON} -c "import yaml, pandas, requests, numpy" 2>/dev/null || {
    log "[ERROR] Missing Python packages. Install: pip install pyyaml pandas requests numpy"
    exit 1
}

# Get tool list
if [[ -n "${TOOLS_FILTER}" ]]; then
    IFS=',' read -ra TOOLS <<< "${TOOLS_FILTER}"
else
    mapfile -t TOOLS < <(${PYTHON} -c "
import yaml
with open('${PIPELINE_CONFIG}') as f:
    cfg = yaml.safe_load(f)
for t in cfg['tools']:
    print(t)
" | tr -d '\r')
fi

log "Tools to audit: ${#TOOLS[@]}"
log "Force re-audit: ${FORCE_REAUDIT}"
log "Skip predictions: ${SKIP_PREDICTIONS}"

if [[ "${DRY_RUN}" == "true" ]]; then
    log "[DRY RUN] Would audit: ${TOOLS[*]}"
    exit 0
fi

#=============================================================================
# Step 1: Category Pool Downloads (one per unique category)
#=============================================================================
log ""
log "--- Phase 1: Category Pool Downloads ---"

mapfile -t CATEGORIES < <(${PYTHON} -c "
import yaml
with open('${PIPELINE_CONFIG}') as f:
    cfg = yaml.safe_load(f)
tools_filter = '${TOOLS_FILTER}'.split(',') if '${TOOLS_FILTER}' else list(cfg['tools'].keys())
seen = set()
for t in tools_filter:
    t = t.strip()
    if t in cfg['tools']:
        cat = cfg['tools'][t]['category']
        if cat not in seen:
            print(cat)
            seen.add(cat)
" | tr -d '\r')

for CATEGORY in "${CATEGORIES[@]}"; do
    POOL_CSV="${BASE_DIR}/Category_Pools/${CATEGORY}_pool.csv"
    POOL_FASTA="${BASE_DIR}/Category_Pools/${CATEGORY}_pool.fasta"

    if [[ -f "${POOL_CSV}" ]] && [[ "${FORCE_REAUDIT}" == "false" ]]; then
        POOL_SIZE=$(wc -l < "${POOL_CSV}")
        log "  [SKIP] Pool exists: ${CATEGORY} (${POOL_SIZE} lines)"
    else
        log "  [RUN]  Mining positives: ${CATEGORY}"
        ${PYTHON} "${ROOT_DIR_WIN}/scripts/mine_positives_per_bioactivity.py" \
            --category "${CATEGORY}" \
            --config "${CATEGORY_CONFIG}" \
            --output-dir "${BASE_DIR}/Category_Pools" \
            2>&1 | tee -a "${MASTER_LOG}" || {
            log "  [ERROR] Failed mining positives for ${CATEGORY}"
            continue
        }
        log "  [DONE] Pool created: ${CATEGORY}"
    fi
done

#=============================================================================
# Step 2: Per-Tool Audit Loop
#=============================================================================
log ""
log "--- Phase 2: Per-Tool Audits ---"

declare -a STANDBY_TOOLS=()
declare -a SUCCESS_TOOLS=()
declare -a ERROR_TOOLS=()

for TOOL_ID in "${TOOLS[@]}"; do
    TOOL_ID=$(echo "${TOOL_ID}" | tr -d ' ')
    log ""
    log "====== Tool: ${TOOL_ID} ======"

    TOOL_DIR="${BASE_DIR}/Tool_Audits/${TOOL_ID}"
    mkdir -p "${TOOL_DIR}/training_data" "${TOOL_DIR}/test_positives" \
             "${TOOL_DIR}/test_negatives" "${TOOL_DIR}/leakage_report" \
             "${TOOL_DIR}/predictions"
    TOOL_LOG="${TOOL_DIR}/audit_${TIMESTAMP}.log"

    # --- Change detection ---
    if [[ "${FORCE_REAUDIT}" == "false" ]]; then
        NEEDS=$(${PYTHON} -c "
from audit_lib.state_manager import AuditStateManager
from audit_lib.config import load_pipeline_config
cfg = load_pipeline_config('${PIPELINE_CONFIG}')
sm = AuditStateManager('${AUDIT_STATE}')
h = sm.compute_tool_hash('${TOOL_ID}', cfg['tools']['${TOOL_ID}'])
print('yes' if sm.needs_audit('${TOOL_ID}', h) else 'no')
" 2>/dev/null | tr -d '\r' || echo "yes")

        if [[ "${NEEDS}" == "no" ]]; then
            log "  [SKIP] No changes detected"
            SUCCESS_TOOLS+=("${TOOL_ID}")
            continue
        fi
    fi

    # Get category for this tool
    CATEGORY=$(${PYTHON} -c "
from audit_lib.config import load_pipeline_config
cfg = load_pipeline_config('${PIPELINE_CONFIG}')
print(cfg['tools']['${TOOL_ID}']['category'])
" | tr -d '\r')

    # --- Step 2a: Extract training data ---
    # Check if training FASTA already exists (manually provided)
    TRAINING_FASTA=$(find "${TOOL_DIR}/training_data" -name "*.fasta" -type f 2>/dev/null | head -1)
    if [[ -n "${TRAINING_FASTA}" ]] && [[ ! -f "${TOOL_DIR}/training_data/STANDBY_REPORT.json" ]]; then
        log "  [2a] Training FASTA already exists: ${TRAINING_FASTA}"
    else
        log "  [2a] Extracting training data..."
        ${PYTHON} "${ROOT_DIR_WIN}/scripts/extract_training_data.py" \
            --tool "${TOOL_ID}" \
            --config "${PIPELINE_CONFIG}" \
            --output-dir "${TOOL_DIR}/training_data" \
            2>&1 | tee -a "${TOOL_LOG}" || true

        # Check for STANDBY
        if [[ -f "${TOOL_DIR}/training_data/STANDBY_REPORT.json" ]]; then
            log "  [STANDBY] Training data not found for ${TOOL_ID}"
            log "  [STANDBY] Check: ${TOOL_DIR}/training_data/STANDBY_REPORT.json"
            STANDBY_TOOLS+=("${TOOL_ID}")
            continue
        fi

        # Re-check training FASTA after extraction
        TRAINING_FASTA=$(find "${TOOL_DIR}/training_data" -name "*.fasta" -type f 2>/dev/null | head -1)
    fi

    if [[ -z "${TRAINING_FASTA}" ]]; then
        log "  [ERROR] No training FASTA found for ${TOOL_ID}"
        ERROR_TOOLS+=("${TOOL_ID}")
        continue
    fi

    # --- Step 2b: CD-HIT-2D leakage analysis ---
    POOL_FASTA="${BASE_DIR}/Category_Pools/${CATEGORY}_pool.fasta"
    if [[ ! -f "${POOL_FASTA}" ]]; then
        log "  [ERROR] Category pool FASTA not found: ${POOL_FASTA}"
        ERROR_TOOLS+=("${TOOL_ID}")
        continue
    fi

    log "  [2b] Running CD-HIT-2D leakage analysis..."
    ${PYTHON} "${ROOT_DIR_WIN}/scripts/cdhit_leakage_analysis.py" \
        --tool "${TOOL_ID}" \
        --config "${PIPELINE_CONFIG}" \
        --test-fasta "${POOL_FASTA}" \
        --training-fasta "${TRAINING_FASTA}" \
        --output-dir "${TOOL_DIR}/leakage_report" \
        2>&1 | tee -a "${TOOL_LOG}" || {
        log "  [ERROR] CD-HIT-2D failed for ${TOOL_ID}"
        ERROR_TOOLS+=("${TOOL_ID}")
        continue
    }

    # --- Step 2c: Generate tool-specific negatives ---
    POOL_CSV="${BASE_DIR}/Category_Pools/${CATEGORY}_pool.csv"
    log "  [2c] Generating negatives..."
    ${PYTHON} "${ROOT_DIR_WIN}/scripts/generate_category_negatives.py" \
        --tool "${TOOL_ID}" \
        --config "${PIPELINE_CONFIG}" \
        --categories-config "${CATEGORY_CONFIG}" \
        --positives-csv "${POOL_CSV}" \
        --output-dir "${TOOL_DIR}/test_negatives" \
        2>&1 | tee -a "${TOOL_LOG}" || {
        log "  [ERROR] Negative generation failed for ${TOOL_ID}"
        ERROR_TOOLS+=("${TOOL_ID}")
        continue
    }

    # --- Step 2d: Run prediction tool (optional) ---
    if [[ "${SKIP_PREDICTIONS}" == "false" ]]; then
        log "  [2d] Running prediction tool..."
        ${PYTHON} "${ROOT_DIR_WIN}/scripts/run_tool_prediction.py" \
            --tool "${TOOL_ID}" \
            --config "${PIPELINE_CONFIG}" \
            --output-dir "${TOOL_DIR}/predictions" \
            2>&1 | tee -a "${TOOL_LOG}" || {
            log "  [WARN] Prediction failed for ${TOOL_ID} (non-fatal)"
        }
    fi

    # --- Step 2e: Taxonomic bias analysis (Gold-only, requires predictions) ---
    if [[ "${SKIP_PREDICTIONS}" == "false" ]]; then
        PRED_FILE="${TOOL_DIR}/predictions/predictions_${TOOL_ID}.csv"
        if [[ -f "${PRED_FILE}" ]]; then
            log "  [2e] Running taxonomic bias analysis (Gold-only)..."
            ${PYTHON} "${ROOT_DIR_WIN}/scripts/taxonomic_bias_analysis.py" \
                --tool "${TOOL_ID}" \
                --config "${PIPELINE_CONFIG}" \
                --output-dir "${TOOL_DIR}/predictions" \
                --grades Gold \
                2>&1 | tee -a "${TOOL_LOG}" || {
                log "  [WARN] Taxonomic bias analysis failed for ${TOOL_ID} (non-fatal)"
            }
        else
            log "  [2e] Skipping taxonomic bias (no predictions file)"
        fi
    fi

    # --- Step 2f: Per-tool audit ---
    log "  [2f] Running audit..."
    ${PYTHON} "${ROOT_DIR_WIN}/scripts/auditoria_validation.py" \
        --tool "${TOOL_ID}" \
        --config "${PIPELINE_CONFIG}" \
        --output-dir "${TOOL_DIR}" \
        2>&1 | tee -a "${TOOL_LOG}" || true

    # --- Update state ---
    ${PYTHON} -c "
from audit_lib.state_manager import AuditStateManager
from audit_lib.config import load_pipeline_config
cfg = load_pipeline_config('${PIPELINE_CONFIG}')
sm = AuditStateManager('${AUDIT_STATE}')
h = sm.compute_tool_hash('${TOOL_ID}', cfg['tools']['${TOOL_ID}'])
sm.mark_complete('${TOOL_ID}', h)
sm.save()
" 2>/dev/null || true

    SUCCESS_TOOLS+=("${TOOL_ID}")
    log "  [DONE] ${TOOL_ID} audit complete"
done

#=============================================================================
# Step 3: Global Report
#=============================================================================
log ""
log "--- Phase 3: Global Report ---"
${PYTHON} "${ROOT_DIR_WIN}/scripts/final_audit_report.py" \
    --config "${PIPELINE_CONFIG}" \
    --output-dir "${BASE_DIR}/Global_Audit" \
    2>&1 | tee -a "${MASTER_LOG}" || {
    log "[WARN] Global report generation failed"
}

#=============================================================================
# Summary
#=============================================================================
log ""
log "=========================================="
log "  AUDIT PIPELINE COMPLETE"
log "=========================================="
log "  Success: ${#SUCCESS_TOOLS[@]} tools (${SUCCESS_TOOLS[*]:-none})"
log "  Standby: ${#STANDBY_TOOLS[@]} tools (${STANDBY_TOOLS[*]:-none})"
log "  Errors:  ${#ERROR_TOOLS[@]} tools (${ERROR_TOOLS[*]:-none})"
log ""
log "  Logs:    ${MASTER_LOG}"
log "  Results: ${BASE_DIR}/Tool_Audits/"
log "  Report:  ${BASE_DIR}/Global_Audit/"
log "=========================================="

# Exit with error if any tools failed
[[ ${#ERROR_TOOLS[@]} -eq 0 ]] || exit 1
