"""CUPED sensitivity optimization for ARPU in A/B tests.

Usage:
  python cuped_arpu_opt.py --input data.csv --user-col user_id --group-col group \
    --outcome-col arpu --pre-cols arpu_pre_7d arpu_pre_14d

Input requirements:
  - group column values: control / treatment (or 0 / 1)
  - outcome column: post-period ARPU per user
  - pre columns: pre-experiment covariates aligned per user
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class CupedResult:
    raw_effect: float
    raw_se: float
    raw_t: float
    cuped_effect: float
    cuped_se: float
    cuped_t: float
    variance_reduction: float
    sensitivity_gain: float
    best_theta: np.ndarray
    used_covariates: List[str]


def _normalize_group(series: pd.Series) -> np.ndarray:
    values = series.astype(str).str.lower().str.strip()
    mapping = {
        "control": 0,
        "ctrl": 0,
        "0": 0,
        "treatment": 1,
        "test": 1,
        "1": 1,
    }
    if values.isin(mapping.keys()).all():
        return values.map(mapping).to_numpy(dtype=int)

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any():
        raise ValueError("group column must be binary: control/treatment or 0/1")
    uniq = sorted(numeric.unique())
    if len(uniq) != 2:
        raise ValueError(f"group column must have exactly 2 groups, got {uniq}")
    return (numeric == max(uniq)).astype(int).to_numpy()


def _ols_diff_in_means(y: np.ndarray, g: np.ndarray) -> Tuple[float, float, float]:
    y0, y1 = y[g == 0], y[g == 1]
    n0, n1 = len(y0), len(y1)
    diff = y1.mean() - y0.mean()
    se = np.sqrt(y0.var(ddof=1) / n0 + y1.var(ddof=1) / n1)
    t = diff / se if se > 0 else np.nan
    return float(diff), float(se), float(t)


def fit_cuped(
    data: pd.DataFrame,
    group_col: str,
    outcome_col: str,
    pre_cols: Iterable[str],
) -> CupedResult:
    pre_cols = list(pre_cols)
    required = [group_col, outcome_col, *pre_cols]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")

    df = data[required].dropna().copy()
    g = _normalize_group(df[group_col])
    y = pd.to_numeric(df[outcome_col], errors="coerce").to_numpy()

    x_df = df[pre_cols].apply(pd.to_numeric, errors="coerce")
    if x_df.isna().any().any():
        raise ValueError("pre-period covariates contain non-numeric values")

    x = x_df.to_numpy()
    x_centered = x - x.mean(axis=0, keepdims=True)

    y_centered = y - y.mean()
    theta = np.linalg.pinv(x_centered.T @ x_centered) @ (x_centered.T @ y_centered)

    y_cuped = y - x_centered @ theta

    raw_effect, raw_se, raw_t = _ols_diff_in_means(y, g)
    cuped_effect, cuped_se, cuped_t = _ols_diff_in_means(y_cuped, g)

    raw_var = np.var(y, ddof=1)
    cuped_var = np.var(y_cuped, ddof=1)
    variance_reduction = max(0.0, 1.0 - cuped_var / raw_var) if raw_var > 0 else 0.0
    sensitivity_gain = raw_se / cuped_se if cuped_se > 0 else np.nan

    return CupedResult(
        raw_effect=raw_effect,
        raw_se=raw_se,
        raw_t=raw_t,
        cuped_effect=cuped_effect,
        cuped_se=cuped_se,
        cuped_t=cuped_t,
        variance_reduction=float(variance_reduction),
        sensitivity_gain=float(sensitivity_gain),
        best_theta=theta,
        used_covariates=pre_cols,
    )


def format_report(result: CupedResult) -> str:
    theta_pairs = ", ".join(
        f"{name}: {coef:.4f}" for name, coef in zip(result.used_covariates, result.best_theta)
    )
    lines = [
        "=== A/B ARPU CUPED 敏感度优化报告 ===",
        f"Raw effect (treat-control): {result.raw_effect:.6f}",
        f"Raw SE: {result.raw_se:.6f}",
        f"Raw t-stat: {result.raw_t:.4f}",
        "---",
        f"CUPED effect: {result.cuped_effect:.6f}",
        f"CUPED SE: {result.cuped_se:.6f}",
        f"CUPED t-stat: {result.cuped_t:.4f}",
        "---",
        f"Variance reduction: {result.variance_reduction:.2%}",
        f"Sensitivity gain (SE ratio): {result.sensitivity_gain:.2f}x",
        f"Theta: {theta_pairs}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize A/B ARPU sensitivity with CUPED")
    parser.add_argument("--input", required=True, help="CSV input path")
    parser.add_argument("--user-col", default="user_id", help="User id column (for sanity check only)")
    parser.add_argument("--group-col", required=True, help="Experiment group column")
    parser.add_argument("--outcome-col", required=True, help="Post-period ARPU column")
    parser.add_argument(
        "--pre-cols",
        nargs="+",
        required=True,
        help="One or more pre-experiment covariates",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    if args.user_col not in data.columns:
        raise ValueError(f"user column '{args.user_col}' not found in input")
    if data[args.user_col].duplicated().any():
        raise ValueError("user column contains duplicates; input should be user-level")

    result = fit_cuped(
        data=data,
        group_col=args.group_col,
        outcome_col=args.outcome_col,
        pre_cols=args.pre_cols,
    )
    print(format_report(result))


if __name__ == "__main__":
    main()
