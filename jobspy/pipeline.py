from __future__ import annotations

import logging
import time
from typing import List, Dict, Any
from datetime import datetime

import pandas as pd
from jobspy import scrape_jobs
from jobspy.evaluator import ProfileMatchEvaluator
from jobspy.model import JobPost, JobResponse, Site, Location
from jobspy.util import create_session, create_logger, markdown_converter

log = create_logger("Pipeline")


def discover_jobs(
    keywords: List[str],
    location: str | None = None,
    results_wanted: int = 100,
    sites: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Phase 1: discover job listing URLs from Indeed and LinkedIn (by default).

    Returns list of dicts containing job_url, site, title, company, location, date_posted
    """
    if sites is None:
        # include supported discovery sites by default so pipeline returns broader coverage
        # Note: Bayt is excluded from defaults due to persistent 403 responses; enable it explicitly if you can
        sites = ["indeed", "linkedin", "google", "naukri", "ziprecruiter"]
    search_term = " OR ".join([f'"{k}"' for k in keywords])
    log.info(f"Starting discovery for keywords={keywords} sites={sites}")

    df = scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
    )

    rows = []
    if df is None or df.empty:
        log.info("No discovery results returned")
        return rows

    for _, row in df.iterrows():
        rows.append(
            {
                "job_url": row.get("job_url"),
                "site": row.get("site"),
                "title": row.get("title"),
                "company": row.get("company"),
                "location": row.get("location"),
                "date_posted": row.get("date_posted"),
                # include any short description if scraper provided
                "short_description": row.get("description"),
                # include remote/hybrid indicators when present
                "is_remote": row.get("is_remote"),
                "work_from_home_type": row.get("work_from_home_type"),
            }
        )
    return rows


def validate_discovery_row(job_meta: Dict[str, Any]) -> tuple[bool, str | None]:
    """Validate discovery meta row contains required fields.

    Returns (True, None) if valid, otherwise (False, reason).
    """
    if not job_meta:
        return False, "empty row"
    if not job_meta.get("job_url"):
        return False, "missing job_url"
    if not job_meta.get("site"):
        return False, "missing site"
    return True, None


def make_debug_filename(base: str) -> str:
    """Return a timestamped debug filename for a given base output file.

    Example: 'alok_personalized.csv' -> 'alok_personalized_debug_20251220_182233.csv'
    """
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return base.replace('.csv', f'_debug_{ts}.csv')


def normalize_output_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize location dicts and list columns for CSV-friendly output.

    - Convert location dicts or serialized dicts into human-readable "City, State, Country" strings
    - Convert list-like fields (real lists or serialized list strings) into comma-separated strings
    """
    import ast

    df = df.copy()

    # Normalize 'location' column
    if "location" in df.columns:
        def _normalize_location(val):
            try:
                if isinstance(val, Location):
                    return val.display_location()
                if isinstance(val, dict):
                    return Location(**val).display_location()
                if isinstance(val, str) and val.strip().startswith("{"):
                    try:
                        d = ast.literal_eval(val)
                        if isinstance(d, dict):
                            return Location(**d).display_location()
                    except Exception:
                        return val
                return val
            except Exception:
                return str(val)

        df["location"] = df["location"].apply(_normalize_location)

    # Normalize list-like fields (both real lists and serialized list strings)
    def _normalize_list_cell(v):
        if isinstance(v, float) and pd.isna(v):
            return None
        if isinstance(v, (list, tuple)):
            return ", ".join([str(x) for x in v])
        if isinstance(v, str) and v.strip().startswith("["):
            try:
                parsed = ast.literal_eval(v)
                if isinstance(parsed, (list, tuple)):
                    return ", ".join([str(x) for x in parsed])
            except Exception:
                return v
        return v

    for list_col in ("key_skills", "missing_skills", "match_reasons", "skills"):
        if list_col in df.columns:
            df[list_col] = df[list_col].apply(_normalize_list_cell)

    return df


def enrich_job(job_meta: Dict[str, Any], timeout_seconds: int = 15) -> JobPost | None:
    """Phase 2: fetch full job page and parse/enrich details and evaluate match.

    Returns a JobPost with enrichment fields populated.
    """
    url = job_meta.get("job_url")
    site = job_meta.get("site")
    title = job_meta.get("title")
    company = job_meta.get("company")

    evaluator = ProfileMatchEvaluator()

    # Use a resilient requests session for enrichment fetches (timeouts and retries)
    session = create_session(is_tls=False, has_retry=False, clear_cookies=True)
    try:
        # Some scrapers already included description; prefer that
        description = job_meta.get("short_description")
        if not description and url:
            log.info(f"Fetching job details for {url}")
            try:
                res = session.get(url, timeout=5)
                html = getattr(res, "text", None)
                if html is None:
                    content = getattr(res, "content", b"")
                    try:
                        html = content.decode("utf-8", errors="ignore")
                    except Exception:
                        html = str(content)
                description = html
            except Exception as e:
                log.error(f"Error fetching {url}: {e}")
                description = None
        # Basic parse: convert to plain text / markdown for evaluation
        text = markdown_converter(description) if description else ""

        eval_res = evaluator.evaluate(text)

        # Build JobPost (keep original minimal fields for compatibility)
        # Normalize location into a dict so pydantic can coerce it to Location
        loc_val = job_meta.get("location")
        if isinstance(loc_val, str):
            loc_field = {"city": loc_val}
        else:
            loc_field = loc_val

        # Determine remote/hybrid signals (use discovery hints first, fall back to text heuristics)
        meta_is_remote = job_meta.get("is_remote")
        meta_wfh = job_meta.get("work_from_home_type")
        txt_lower = text.lower() if text else ""
        inferred_is_remote = None
        inferred_wfh = None
        if meta_is_remote is not None:
            inferred_is_remote = bool(meta_is_remote)
        else:
            if any(k in txt_lower for k in ("remote", "work from home", "wfh")):
                inferred_is_remote = True
            elif any(k in txt_lower for k in ("onsite", "on-site", "work from office")):
                inferred_is_remote = False

        # coerce meta_wfh to a string if it's a valid string value; guard against pandas' NaN (float)
        if isinstance(meta_wfh, str) and meta_wfh.strip():
            inferred_wfh = meta_wfh.strip()
        else:
            if "hybrid" in txt_lower:
                inferred_wfh = "Hybrid"
            elif any(k in txt_lower for k in ("remote", "work from home", "wfh")):
                inferred_wfh = "Remote"

        job_post = JobPost(
            id=None,
            title=title,
            company_name=company,
            job_url=url,
            job_url_direct=None,
            location=loc_field,
            description=text,
            key_skills=eval_res.get("key_skills"),
            experience_range=eval_res.get("experience_range"),
            match_score=eval_res.get("match_score"),
            match_reasons=eval_res.get("match_reasons"),
            missing_skills=eval_res.get("missing_skills"),
            resume_alignment_level=eval_res.get("resume_alignment_level"),
            why_this_job_fits="; ".join(eval_res.get("match_reasons", [])) if eval_res.get("match_reasons") else None,
            site=site,
            is_remote=inferred_is_remote,
            work_from_home_type=inferred_wfh,
        )

        # Log decision
        if job_post.resume_alignment_level and job_post.resume_alignment_level != "Ignore":
            log.info(f"Accepted — {job_post.resume_alignment_level}: {title} @ {company} ({job_post.match_score})")
        else:
            log.info(f"Rejected — {job_post.resume_alignment_level or 'Ignore'}: {title} @ {company} ({job_post.match_score})")

        # Log remote/hybrid inference for visibility
        if inferred_is_remote is not None:
            src = "meta" if meta_is_remote is not None else "inferred"
            log.info(f"Remote status ({src}) for {title}: {inferred_is_remote}")
        if inferred_wfh is not None:
            src = "meta" if meta_wfh is not None else "inferred"
            log.info(f"Work-from-home type ({src}) for {title}: {inferred_wfh}")

        return job_post
    except Exception as e:
        log.error(f"Failed to enrich job {url}: {e}")
        return None


def run_personalized_pipeline(
    keywords: List[str],
    location: str | None,
    results_wanted: int,
    output_file: str = "personalized_jobs.csv",
) -> pd.DataFrame:
    discovery = discover_jobs(keywords=keywords, location=location, results_wanted=results_wanted)
    enriched_posts = []
    for meta in discovery:
        valid, reason = validate_discovery_row(meta)
        if not valid:
            log.warning(f"Skipping discovery row due to validation failure: {reason} -- {meta}")
            continue
        post = enrich_job(meta)
        if post:
            enriched_posts.append(post)
        # be polite
        time.sleep(0.5)

    if not enriched_posts:
        log.info("No enriched posts produced")
        return pd.DataFrame()

    # Convert to DataFrame
    rows = [p.dict() for p in enriched_posts]
    df = pd.DataFrame(rows)

    # Use helper to normalize
    df = normalize_output_df(df)

    # Write a debug dump with full columns for inspection — include timestamp to avoid overwrites
    def _make_debug_filename(base: str) -> str:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        return base.replace('.csv', f'_debug_{ts}.csv')

    debug_out = make_debug_filename(output_file)

    # Ensure a predictable set of debug columns (add missing ones as None for schema consistency)
    debug_cols = [
        "id",
        "title",
        "company_name",
        "location",
        "site",
        "job_url",
        "job_url_direct",
        "description",
        "company_url",
        "job_type",
        "compensation",
        "date_posted",
        "emails",
        "is_remote",
        "listing_type",
        "job_level",
        "company_industry",
        "company_addresses",
        "company_num_employees",
        "company_revenue",
        "company_description",
        "company_logo",
        "banner_photo_url",
        "job_function",
        "skills",
        "experience_range",
        "company_rating",
        "company_reviews_count",
        "vacancy_count",
        "work_from_home_type",
        "key_skills",
        "match_score",
        "match_reasons",
        "missing_skills",
        "resume_alignment_level",
        "why_this_job_fits",
    ]

    for c in debug_cols:
        if c not in df.columns:
            df[c] = None

    # Reorder to put debug columns first, keep any extra columns after
    extra_cols = [c for c in df.columns if c not in debug_cols]
    df = df[debug_cols + extra_cols]

    try:
        df.to_csv(debug_out, index=False)
        log.info(f"Wrote debug dump to {debug_out}")
    except Exception as e:
        log.error(f"Failed to write debug dump {debug_out}: {e}")

    # Ensure output columns per spec
    cols = [
        "title",
        "company_name",
        "location",
        "site",
        "job_url",
        "experience_range",
        "key_skills",
        "match_score",
        "why_this_job_fits",
        "missing_skills",
        "resume_alignment_level",
        # remote/hybrid indicators
        "is_remote",
        "work_from_home_type",
    ]
    # Add site column if not present
    if "site" not in df.columns:
        df["site"] = None

    # Reorder and write
    df_out = df[[c for c in cols if c in df.columns]]
    try:
        df_out.to_csv(output_file, index=False)
        log.info(f"Wrote personalized output to {output_file}")
    except Exception as e:
        # fallback filename
        alt = output_file.replace('.csv', '_final.csv')
        try:
            df_out.to_csv(alt, index=False)
            log.warning(f"Failed to write {output_file}; wrote to {alt} instead: {e}")
        except Exception as e2:
            log.error(f"Failed to write output to both {output_file} and {alt}: {e2}")
    return df_out
