"""
audit_lib/downloader.py
=======================
Handles automatic and semi-automatic model weight downloads for tools
whose weights are NOT stored in the GitHub repo.

Supported platforms:
  - zenodo   : Automatic via Zenodo REST API (no auth needed for public records)
  - huggingface: Automatic via huggingface_hub
  - onedrive : Semi-auto — prints instructions + verifies file presence
  - webserver: Semi-auto — prints instructions + verifies file presence
  - baidu    : Manual only — prints instructions
  - in_repo  : No action needed
"""

import hashlib
import logging
import os
import time
import zipfile

import requests

log = logging.getLogger(__name__)

# ============================================================================
# PUBLIC ENTRY POINT
# ============================================================================


def ensure_weights(tool_id: str, tool_cfg: dict, repo_dir: str) -> bool:
    """
    Ensure model weights are present for a tool.
    Returns True if weights are ready, False if manual action required.

    Args:
        tool_id  : Tool identifier (e.g. "macppred2")
        tool_cfg : Full tool config dict from pipeline_config.yaml
        repo_dir : Absolute path to the cloned repo for this tool
    """
    wd_cfg = tool_cfg.get("weights_download", {})
    if not wd_cfg:
        log.debug(f"[{tool_id}] No weights_download config — assuming weights present")
        return True

    platform = wd_cfg.get("platform", "in_repo")

    if platform == "in_repo":
        log.debug(f"[{tool_id}] Weights are in-repo, no download needed")
        return True

    elif platform == "zenodo":
        return _download_zenodo(tool_id, wd_cfg, repo_dir)

    elif platform == "huggingface":
        return _download_huggingface(tool_id, wd_cfg, repo_dir)

    elif platform in ("onedrive", "webserver"):
        return _check_manual_download(tool_id, wd_cfg, repo_dir, platform)

    elif platform == "baidu":
        return _check_manual_download(tool_id, wd_cfg, repo_dir, platform)

    else:
        log.warning(f"[{tool_id}] Unknown weights platform: '{platform}'")
        return False


# ============================================================================
# ZENODO AUTO-DOWNLOAD
# ============================================================================


def _download_zenodo(tool_id: str, wd_cfg: dict, repo_dir: str) -> bool:
    """
    Download all files from a Zenodo record to target_path inside repo_dir.
    Uses Zenodo REST API: https://zenodo.org/api/records/{record_id}
    """
    zenodo_doi = wd_cfg.get("zenodo_doi", "")
    zenodo_url = wd_cfg.get("zenodo_url", "")
    target_rel = wd_cfg.get("target_path", "models/")
    target_dir = os.path.join(repo_dir, target_rel)

    # Extract record ID from DOI or URL
    record_id = None
    if zenodo_doi:
        # e.g. "10.5281/zenodo.11350064" → "11350064"
        parts = zenodo_doi.rstrip("/").split(".")
        if parts:
            record_id = parts[-1]
    elif zenodo_url:
        # e.g. "https://zenodo.org/record/11350064" → "11350064"
        record_id = zenodo_url.rstrip("/").split("/")[-1]

    if not record_id:
        log.error(f"[{tool_id}] Cannot extract Zenodo record ID from config")
        return False

    log.info(f"[{tool_id}] Fetching Zenodo record {record_id}...")
    api_url = f"https://zenodo.org/api/records/{record_id}"

    try:
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error(f"[{tool_id}] Zenodo API request failed: {e}")
        return False

    record = resp.json()
    files = record.get("files", [])
    if not files:
        log.error(f"[{tool_id}] No files found in Zenodo record {record_id}")
        return False

    os.makedirs(target_dir, exist_ok=True)
    log.info(f"[{tool_id}] Downloading {len(files)} files from Zenodo → {target_dir}")

    all_ok = True
    for file_info in files:
        filename = file_info["key"]
        download_url = file_info["links"]["self"]
        dest_path = os.path.join(target_dir, filename)

        if os.path.exists(dest_path):
            log.info(f"  [SKIP] {filename} already exists")
            continue

        log.info(f"  Downloading {filename}...")
        ok = _download_file(download_url, dest_path)
        if not ok:
            log.error(f"  [FAIL] {filename}")
            all_ok = False
            continue

        # Verify checksum if provided
        expected_md5 = file_info.get("checksum", "").replace("md5:", "")
        if expected_md5:
            actual_md5 = _md5(dest_path)
            if actual_md5 != expected_md5:
                log.error(f"  [CHECKSUM FAIL] {filename}: expected {expected_md5}, got {actual_md5}")
                os.remove(dest_path)
                all_ok = False
                continue
            log.info(f"  [OK] {filename} (md5 verified)")
        else:
            log.info(f"  [OK] {filename}")

        # Auto-unzip if zip
        if filename.endswith(".zip"):
            log.info(f"  Unzipping {filename}...")
            _unzip(dest_path, target_dir)

    return all_ok


# ============================================================================
# HUGGINGFACE AUTO-DOWNLOAD
# ============================================================================


def _download_huggingface(tool_id: str, wd_cfg: dict, repo_dir: str) -> bool:
    """Download model from HuggingFace Hub."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        log.error(f"[{tool_id}] huggingface_hub not installed. Run: pip install huggingface_hub")
        return False

    hf_repo = wd_cfg.get("hf_repo_id", "")
    target_rel = wd_cfg.get("target_path", "models/")
    target_dir = os.path.join(repo_dir, target_rel)

    if not hf_repo:
        log.error(f"[{tool_id}] No hf_repo_id in weights_download config")
        return False

    log.info(f"[{tool_id}] Downloading from HuggingFace: {hf_repo} → {target_dir}")
    try:
        snapshot_download(repo_id=hf_repo, local_dir=target_dir)
        log.info(f"[{tool_id}] HuggingFace download complete")
        return True
    except Exception as e:
        log.error(f"[{tool_id}] HuggingFace download failed: {e}")
        return False


# ============================================================================
# MANUAL DOWNLOAD CHECKER (onedrive / webserver / baidu)
# ============================================================================


def _check_manual_download(tool_id: str, wd_cfg: dict, repo_dir: str, platform: str) -> bool:
    """
    Check if manually-downloaded weights are present.
    If not, print detailed instructions and return False.
    """
    target_rel = wd_cfg.get("target_path", "models/")
    target_dir = os.path.join(repo_dir, target_rel)
    instructions = wd_cfg.get("instructions", "")
    url = wd_cfg.get(
        "onedrive_url",
        wd_cfg.get("webserver_url", wd_cfg.get("baidu_url", ""))
    )

    # Check if target directory has any files
    if os.path.isdir(target_dir):
        files = [f for f in os.listdir(target_dir) if not f.startswith(".")]
        if files:
            log.info(f"[{tool_id}] Weights present in {target_dir} ({len(files)} files)")
            return True

    # Not present — print instructions
    log.warning(f"\n{'='*60}")
    log.warning(f"[{tool_id}] MANUAL WEIGHT DOWNLOAD REQUIRED ({platform.upper()})")
    log.warning(f"{'='*60}")
    if url:
        log.warning(f"  URL: {url}")
    if instructions:
        for line in instructions.split("\n"):
            log.warning(f"  {line}")
    else:
        log.warning(f"  Target directory: {target_dir}")
        log.warning(f"  Download weights manually and place them in: {target_dir}")
    log.warning(f"{'='*60}\n")

    return False


# ============================================================================
# UTILITIES
# ============================================================================


def _download_file(url: str, dest_path: str, chunk_size: int = 8192,
                   max_retries: int = 3) -> bool:
    """Download a file from URL to dest_path with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                downloaded = 0
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
            return True
        except Exception as e:
            log.warning(f"  Download attempt {attempt}/{max_retries} failed: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            if attempt < max_retries:
                time.sleep(5 * attempt)
    return False


def _md5(path: str) -> str:
    """Compute MD5 checksum of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _unzip(zip_path: str, dest_dir: str) -> None:
    """Unzip archive to dest_dir."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
