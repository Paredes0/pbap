"""
audit_lib.length_sampling - Length distribution sampling with diversity.
Encourages length diversity without forcing uniform distribution.
"""

import logging
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def compute_length_distribution(df, length_col="Length", bins=None):
    """Compute natural length distribution from data."""
    if bins is None:
        from audit_lib.sequence_utils import DEFAULT_LENGTH_BINS
        bins = DEFAULT_LENGTH_BINS
    total = len(df)
    distribution = {}
    for i, (lo, hi) in enumerate(bins):
        count = ((df[length_col] >= lo) & (df[length_col] <= hi)).sum()
        distribution[i] = {"lo": lo, "hi": hi, "count": count,
                           "weight": count / total if total > 0 else 0}
    return distribution


def sample_with_diversity(df, target_size, length_col="Length", bins=None,
                          min_bin_pct=0.03, seed=42):
    """Sample encouraging length diversity without forcing uniformity.

    Uses natural distribution as base weights with a soft floor to ensure
    underrepresented length ranges get minimum representation.
    """
    if bins is None:
        from audit_lib.sequence_utils import DEFAULT_LENGTH_BINS
        bins = DEFAULT_LENGTH_BINS
    rng = np.random.RandomState(seed)

    if len(df) <= target_size:
        log.info(f"  Dataset ({len(df)}) <= target ({target_size}), using all.")
        return df

    dist = compute_length_distribution(df, length_col, bins)
    min_per_bin = max(1, int(target_size * min_bin_pct))
    bin_targets = {}

    for i, info in dist.items():
        if info["count"] == 0:
            bin_targets[i] = 0
            continue
        natural_target = int(target_size * info["weight"])
        bin_targets[i] = max(min_per_bin, natural_target)

    # Normalize to not exceed target
    total_targeted = sum(bin_targets.values())
    if total_targeted > target_size:
        scale = target_size / total_targeted
        bin_targets = {k: max(1, int(v * scale)) if v > 0 else 0
                       for k, v in bin_targets.items()}

    # Phase 1: Sample per bin
    selected_indices = set()
    df_tmp = df.copy()
    df_tmp["_bin"] = df_tmp[length_col].apply(
        lambda x: next((i for i, (lo, hi) in enumerate(bins)
                        if lo <= x <= hi), -1))

    for bin_idx, target in bin_targets.items():
        bin_df = df_tmp[df_tmp["_bin"] == bin_idx]
        available = bin_df.index.difference(selected_indices)
        if len(available) == 0:
            continue
        n = min(target, len(available))
        chosen = rng.choice(list(available), size=n, replace=False)
        selected_indices.update(chosen)

    log.info(f"  Phase 1 (binned): {len(selected_indices)} selected")

    # Phase 2: Fill remaining randomly
    remaining = target_size - len(selected_indices)
    if remaining > 0:
        available = df.index.difference(selected_indices)
        n = min(remaining, len(available))
        if n > 0:
            chosen = rng.choice(list(available), size=n, replace=False)
            selected_indices.update(chosen)

    log.info(f"  Phase 2 (fill): {len(selected_indices)} selected")
    return df.loc[list(selected_indices)].copy()


def match_length_distribution(source_df, target_df, target_size,
                              length_col="Length", bins=None, seed=42):
    """Sample from source_df matching target_df length distribution.
    Used for generating negatives that match the positive distribution.
    """
    if bins is None:
        from audit_lib.sequence_utils import DEFAULT_LENGTH_BINS
        bins = DEFAULT_LENGTH_BINS
    rng = np.random.RandomState(seed)
    target_dist = compute_length_distribution(target_df, length_col, bins)

    selected_indices = set()
    src = source_df.copy()
    src["_bin"] = src[length_col].apply(
        lambda x: next((i for i, (lo, hi) in enumerate(bins)
                        if lo <= x <= hi), -1))

    for bin_idx, info in target_dist.items():
        bt = int(target_size * info["weight"]) if info["weight"] > 0 else 0
        if bt == 0:
            continue
        bin_df = src[src["_bin"] == bin_idx]
        available = bin_df.index.difference(selected_indices)
        n = min(bt, len(available))
        if n > 0:
            chosen = rng.choice(list(available), size=n, replace=False)
            selected_indices.update(chosen)

    # Fill remaining
    remaining = target_size - len(selected_indices)
    if remaining > 0:
        available = source_df.index.difference(selected_indices)
        n = min(remaining, len(available))
        if n > 0:
            chosen = rng.choice(list(available), size=n, replace=False)
            selected_indices.update(chosen)

    return source_df.loc[list(selected_indices)].copy()
