# jobspy/output_manager.py
from __future__ import annotations
import pandas as pd
from pathlib import Path
from typing import List, Optional


def append_to_master(
    output_csv: str | Path,
    master_csv: str | Path,
    dedupe_on: Optional[List[str]] = None,
    keep_strategy: str = "latest",  # "latest" or "best_score"
    date_column: str = "date_posted",
    score_column: str = "match_score",
) -> dict:
    """Append rows from output_csv to master_csv with deduplication.

    - dedupe_on: list of columns to consider same record (default ['job_url'] if available)
    - keep_strategy: if "latest", keep row with latest `date_column`; if "best_score" keep highest `score_column`.

    Returns dict with summary: {"added":n, "skipped":m, "master_rows":k}
    """
    output_csv = Path(output_csv)
    master_csv = Path(master_csv)

    if not output_csv.exists():
        raise FileNotFoundError(f"Output CSV not found: {output_csv}")

    out_df = pd.read_csv(output_csv)
    if out_df.empty:
        return {"added": 0, "skipped": 0, "master_rows": len(pd.read_csv(master_csv)) if master_csv.exists() else 0}

    # Default dedupe
    if not dedupe_on:
        # prefer job_url then id
        candidate = []
        if "job_url" in out_df.columns: candidate.append("job_url")
        if "id" in out_df.columns: candidate.append("id")
        if not candidate:
            # fallback: title+company+site
            candidate = ["title", "company", "site"]
        dedupe_on = candidate

    # Load master
    if master_csv.exists():
        master_df = pd.read_csv(master_csv)
    else:
        master_df = pd.DataFrame()

    # Normalize date column if present
    for df in (out_df, master_df):
        if date_column in df.columns:
            try:
                df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
            except Exception:
                df[date_column] = pd.NaT

    # Concatenate and dedupe based on strategy
    combined = pd.concat([master_df, out_df], ignore_index=True, sort=False)

    # Ensure dedupe_on contains only existing columns
    dedupe_on_filtered = [c for c in dedupe_on if c in combined.columns]
    if not dedupe_on_filtered:
        # fallback: try job_url/id/title/company/site
        for cand in ["job_url", "id", "title", "company", "site"]:
            if cand in combined.columns and cand not in dedupe_on_filtered:
                dedupe_on_filtered.append(cand)
    if not dedupe_on_filtered:
        # if nothing suitable, just append without deduplication
        before = len(master_df)
        final = combined.reset_index(drop=True)
        final.to_csv(master_csv, index=False)
        return {"added": max(0, len(final) - before), "skipped": 0, "master_rows": len(final)}

    # Sort based on strategy (only using filtered dedupe_on)
    if keep_strategy == "latest" and date_column in combined.columns:
        combined.sort_values(by=[*dedupe_on_filtered, date_column], ascending=[True] * len(dedupe_on_filtered) + [False], inplace=True)
    elif keep_strategy == "best_score" and score_column in combined.columns:
        combined.sort_values(by=[*dedupe_on_filtered, score_column], ascending=[True] * len(dedupe_on_filtered) + [False], inplace=True)
    else:
        # deterministic stable sort
        combined.sort_index(inplace=True)

    before = len(master_df)

    # Drop duplicates keeping first (which we ensured is the preferred record)
    deduped = combined.drop_duplicates(subset=dedupe_on_filtered, keep="first").reset_index(drop=True)
    final = deduped
    # Calculate stats
    added = max(0, len(deduped) - before)
    skipped = len(out_df) - added

    # Ensure output directory
    master_csv.parent.mkdir(parents=True, exist_ok=True)
    deduped.to_csv(master_csv, index=False)

    return {"added": added, "skipped": skipped, "master_rows": len(deduped)}