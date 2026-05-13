"""
audit_lib.cdhit_utils - CD-HIT and CD-HIT-2D utilities.
Handles intra-set redundancy reduction and inter-set leakage analysis.
Supports SSH dispatch for cross-platform execution (Windows -> Linux).
"""

import os
import shutil
import subprocess
import tempfile
import logging
import platform

log = logging.getLogger(__name__)


def get_word_size(identity):
    """Return appropriate word size for cd-hit identity threshold."""
    if identity >= 0.7:
        return 5
    elif identity >= 0.6:
        return 4
    elif identity >= 0.5:
        return 3
    else:
        return 2


def find_cdhit_binary(name="cd-hit"):
    """Find cd-hit or cd-hit-2d binary in PATH or common locations."""
    path = shutil.which(name)
    if path:
        return path
    for p in [f"/usr/bin/{name}", f"/usr/local/bin/{name}",
              os.path.expanduser(f"~/bin/{name}"),
              os.path.expanduser(f"~/miniconda3/bin/{name}")]:
        if os.path.isfile(p):
            return p
    return None


def _is_windows():
    return platform.system() == "Windows"


def _convert_path_for_linux(windows_path, sshfs_mount=None, linux_base=None):
    """Convert Windows SSHFS path to Linux path.

    Uses sshfs_mount and linux_base from config to do the mapping.
    E.g. Z:/sshfs/mount/foo -> /home/user/work/pipeline/foo
    """
    path = windows_path.replace("\\", "/")
    if sshfs_mount and linux_base:
        sshfs_mount = sshfs_mount.replace("\\", "/").rstrip("/")
        linux_base = linux_base.rstrip("/")
        if path.startswith(sshfs_mount):
            return linux_base + path[len(sshfs_mount):]
    # Fallback: strip drive letter
    if len(path) >= 2 and path[1] == ":":
        path = path[2:]
    return path


def _ssh_dispatch(cmd_list, ssh_host="localhost", ssh_user=None):
    """Dispatch a command to a remote Linux machine via SSH."""
    cmd_str = " ".join(cmd_list)
    ssh_cmd = ["ssh"]
    if ssh_user:
        ssh_cmd.extend(["-l", ssh_user])
    ssh_cmd.extend([ssh_host, cmd_str])
    log.info(f"  SSH dispatch to {ssh_host}")
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=600)


def write_fasta(df, fasta_path, id_col="ID", seq_col="Sequence"):
    """Write DataFrame to FASTA format."""
    with open(fasta_path, "w") as f:
        for _, row in df.iterrows():
            f.write(f">{row[id_col]}\n{row[seq_col]}\n")
    log.info(f"  FASTA written: {fasta_path} ({len(df)} sequences)")


def parse_fasta_ids(fasta_path):
    """Parse sequence IDs from a FASTA file."""
    ids = set()
    with open(fasta_path, "r") as f:
        for line in f:
            if line.startswith(">"):
                ids.add(line.strip().lstrip(">").split()[0])
    return ids


def run_cdhit_intraset(df, identity=0.90, output_dir=None,
                       id_col="ID", seq_col="Sequence", ssh_host=None):
    """Run CD-HIT to reduce intra-set redundancy. Returns filtered DataFrame."""
    cdhit_bin = find_cdhit_binary("cd-hit")
    use_ssh = False
    if not cdhit_bin and _is_windows() and ssh_host:
        use_ssh = True
        cdhit_bin = "cd-hit"
    elif not cdhit_bin:
        log.warning("CD-HIT not found. Skipping intra-set redundancy reduction.")
        return df
    if df.empty:
        return df

    word_size = get_word_size(identity)
    tmpdir = tempfile.mkdtemp(prefix="cdhit_intra_")
    try:
        fin = os.path.join(tmpdir, "input.fasta")
        fout = os.path.join(tmpdir, "output.fasta")
        write_fasta(df, fin, id_col, seq_col)

        i_p = _convert_path_for_linux(fin) if use_ssh else fin
        o_p = _convert_path_for_linux(fout) if use_ssh else fout
        cmd = [cdhit_bin, "-i", i_p, "-o", o_p,
               "-c", str(identity), "-n", str(word_size),
               "-l", "4", "-M", "0", "-T", "0"]

        log.info(f"  CD-HIT: identity={identity}, word_size={word_size}")
        if use_ssh:
            result = _ssh_dispatch(cmd, ssh_host=ssh_host)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            log.error(f"  CD-HIT failed: {result.stderr}")
            return df

        surviving_ids = parse_fasta_ids(fout)
        before = len(df)
        df_filtered = df[df[id_col].isin(surviving_ids)].copy()
        after = len(df_filtered)
        log.info(f"  CD-HIT {identity*100:.0f}%: {before} -> {after} ({before - after} removed)")

        if output_dir:
            clstr = fout + ".clstr"
            if os.path.exists(clstr):
                shutil.copy2(clstr, os.path.join(output_dir,
                             f"cdhit_intraset_{identity*100:.0f}.clstr"))
        return df_filtered
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def run_cdhit2d(training_fasta, test_fasta, output_path, identity=0.80,
                ssh_host=None, ssh_user=None, cdhit_binary=None,
                sshfs_mount=None, linux_base=None):
    """Run CD-HIT-2D: -i = training (reference), -i2 = test (query).
    Returns dict with survivors/removed sets and paths.
    """
    cdhit2d_bin = cdhit_binary or find_cdhit_binary("cd-hit-2d")
    use_ssh = False
    if not cdhit2d_bin and _is_windows() and ssh_host:
        use_ssh = True
        cdhit2d_bin = "cd-hit-2d"
    elif _is_windows() and ssh_host and cdhit2d_bin:
        use_ssh = True
    elif not cdhit2d_bin:
        log.error("CD-HIT-2D not found.")
        return {"survivors": set(), "removed": set(), "returncode": -1}

    word_size = get_word_size(identity)
    if use_ssh:
        i_p = _convert_path_for_linux(training_fasta, sshfs_mount, linux_base)
        i2_p = _convert_path_for_linux(test_fasta, sshfs_mount, linux_base)
        o_p = _convert_path_for_linux(output_path, sshfs_mount, linux_base)
    else:
        i_p, i2_p, o_p = training_fasta, test_fasta, output_path

    cmd = [cdhit2d_bin, "-i", i_p, "-i2", i2_p, "-o", o_p,
           "-c", str(identity), "-n", str(word_size),
           "-l", "4", "-M", "0", "-T", "0"]

    log.info(f"  CD-HIT-2D: identity={identity}, word_size={word_size}")
    if use_ssh:
        result = _ssh_dispatch(cmd, ssh_host=ssh_host, ssh_user=ssh_user)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        log.error(f"  CD-HIT-2D failed: {result.stderr}")
        return {"survivors": set(), "removed": set(), "returncode": result.returncode}

    survivors = parse_fasta_ids(output_path)
    all_test = parse_fasta_ids(test_fasta)
    removed = all_test - survivors
    log.info(f"  CD-HIT-2D {identity*100:.0f}%: {len(all_test)} -> {len(survivors)} survivors")

    return {
        "survivors": survivors, "removed": removed,
        "returncode": result.returncode,
        "output_path": output_path, "clstr_path": output_path + ".clstr",
    }


def classify_leakage_grades(test_ids, results_by_threshold):
    """Gold: survives 80/60/40 | Silver: 80+60 | Bronze: 80 only | Red: fails 80"""
    s80 = results_by_threshold.get(0.80, set())
    s60 = results_by_threshold.get(0.60, set())
    s40 = results_by_threshold.get(0.40, set())
    grades = {}
    for pid in test_ids:
        if pid in s80 and pid in s60 and pid in s40:
            grades[pid] = "Gold"
        elif pid in s80 and pid in s60:
            grades[pid] = "Silver"
        elif pid in s80:
            grades[pid] = "Bronze"
        else:
            grades[pid] = "Red"
    return grades
