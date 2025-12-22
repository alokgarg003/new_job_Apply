# jobspy/pipeline.py
from __future__ import annotations
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
import pandas as pd
from jobspy.model import JobPost, JobResponse, Site, ScraperInput, Location
from jobspy.util import (
    create_session, create_logger, markdown_converter, extract_emails_from_text, norm_text,
)
from jobspy.exception import JobScrapingException
from jobspy.evaluator import ProfileMatchEvaluator
import settings

log = create_logger("Pipeline")

def discover_jobs(
    keywords: List[str],
    location: str | None = None,
    results_wanted: int = 100,
    sites: List[str] | None = None,
) -> List[Dict[str, any]]:
    if sites is None:
        sites = settings.SITES
    search_term = " OR ".join([f'"{k}"' for k in keywords])
    log.info(f"Discovery: keywords={keywords}, sites={sites}")
    from jobspy import scrape_jobs
    df = scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
    )
    rows = []
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            rows.append({
                "job_url": row.get("job_url"),
                "site": row.get("site"),
                "title": row.get("title"),
                "company": row.get("company"),
                "location": row.get("location"),
                "date_posted": row.get("date_posted"),
                "short_description": row.get("description"),
                "is_remote": row.get("is_remote"),
                "work_from_home_type": row.get("work_from_home_type"),
            })
    return rows

def validate_discovery_row(job_meta: Dict[str, any]) -> tuple[bool, str | None]:
    if not job_meta: return False, "empty row"
    if not job_meta.get("job_url"): return False, "missing job_url"
    if not job_meta.get("site"): return False, "missing site"
    return True, None

def normalize_output_df(df: pd.DataFrame) -> pd.DataFrame:
    import ast
    df = df.copy()
    if "location" in df.columns:
        def _normalize_location(val):
            try:
                if isinstance(val, Location): return val.display_location()
                if isinstance(val, dict): return Location(**val).display_location()
                if isinstance(val, str) and val.strip().startswith("{"):
                    d = ast.literal_eval(val)
                    if isinstance(d, dict): return Location(**d).display_location()
            except Exception: pass
            return val
        df["location"] = df["location"].apply(_normalize_location)
    for col in ("key_skills", "missing_skills", "match_reasons", "skills"):
        if col in df.columns:
            df[col] = df[col].apply(lambda v: ", ".join([str(x) for x in v]) if isinstance(v, (list, tuple)) else v)
    return df

def enrich_job(job_meta: Dict[str, any], timeout_seconds: int = 15) -> JobPost | None:
    url = job_meta.get("job_url")
    site = job_meta.get("site")
    title = job_meta.get("title")
    company = job_meta.get("company")
    evaluator = ProfileMatchEvaluator()
    session = create_session(is_tls=False, has_retry=False, clear_cookies=True)
    try:
        description = job_meta.get("short_description")
        if not description and url:
            try:
                res = session.get(url, timeout=5)
                html = getattr(res, "text", "")
                description = html
            except Exception as e:
                log.error(f"Fetch error {url}: {e}")
                description = None
        text = markdown_converter(description) if description else ""
        eval_res = evaluator.evaluate(text)
        loc_val = job_meta.get("location")
        loc_field = {"city": loc_val} if isinstance(loc_val, str) else loc_val
        meta_is_remote = job_meta.get("is_remote")
        meta_wfh = job_meta.get("work_from_home_type")
        txt_lower = text.lower() if text else ""
        inferred_is_remote = None
        if meta_is_remote is not None: inferred_is_remote = bool(meta_is_remote)
        else:
            inferred_is_remote = bool(any(k in txt_lower for k in ["remote", "work from home", "wfh"]))
        inferred_wfh = None
        if isinstance(meta_wfh, str) and meta_wfh.strip(): inferred_wfh = meta_wfh.strip()
        else:
            if "hybrid" in txt_lower: inferred_wfh = "Hybrid"
            elif any(k in txt_lower for k in ["remote", "work from home", "wfh"]): inferred_wfh = "Remote"
        job_post = JobPost(
            title=title,
            company_name=company,
            job_url=url,
            location=loc_field,
            description=text,
            key_skills=eval_res.get("key_skills"),
            experience_range=eval_res.get("experience_range"),
            match_score=eval_res.get("match_score"),
            match_reasons=eval_res.get("match_reasons"),
            missing_skills=eval_res.get("missing_skills"),
            resume_alignment_level=eval_res.get("resume_alignment_level"),
            why_this_job_fits=eval_res.get("why_this_job_fits"),
            site=site,
            is_remote=inferred_is_remote,
            work_from_home_type=inferred_wfh,
        )
        if job_post.resume_alignment_level and job_post.resume_alignment_level != "Ignore":
            log.info(f"Accepted: {job_post.resume_alignment_level} - {title} @ {company} (score={job_post.match_score})")
        else:
            log.info(f"Rejected: {job_post.resume_alignment_level or 'Ignore'} - {title} @ {company} (score={job_post.match_score})")
        return job_post
    except Exception as e:
        log.error(f"Enrichment error {url}: {e}")
        return None

def run_personalized_pipeline(
    keywords: List[str],
    location: str | None,
    results_wanted: int,
    output_file: str | None = None,
) -> pd.DataFrame:
    discovery = discover_jobs(keywords=keywords, location=location, results_wanted=results_wanted)
    enriched_posts = []
    for meta in discovery:
        valid, reason = validate_discovery_row(meta)
        if not valid:
            log.warning(f"Skipping row: {reason} -- {meta}")
            continue
        post = enrich_job(meta)
        if post: enriched_posts.append(post)
        time.sleep(0.5)
    if not enriched_posts: return pd.DataFrame()
    rows = [p.dict() for p in enriched_posts]
    df = pd.DataFrame(rows)
    df = normalize_output_df(df)
    debug_out = output_file.replace(".csv", f"_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv") if output_file else None
    debug_cols = [
        "id", "title", "company_name", "location", "site", "job_url", "description",
        "key_skills", "match_score", "match_reasons", "missing_skills", "resume_alignment_level",
        "why_this_job_fits", "is_remote", "work_from_home_type",
    ]
    for c in debug_cols:
        if c not in df.columns: df[c] = None
    extra_cols = [c for c in df.columns if c not in debug_cols]
    df = df[debug_cols + extra_cols]
    if debug_out:
        try:
            df.to_csv(debug_out, index=False)
            log.info(f"Wrote debug to {debug_out}")
        except Exception as e:
            log.error(f"Write debug failed: {e}")
    cols = [
        "title", "company_name", "location", "site", "job_url", "experience_range",
        "key_skills", "match_score", "why_this_job_fits", "missing_skills", "resume_alignment_level",
        "is_remote", "work_from_home_type",
    ]
    df_out = df[[c for c in cols if c in df.columns]]
    out_path = output_file or (settings.FINAL_CSV_TEMPLATE.name.format(timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")))
    try:
        df_out.to_csv(out_path, index=False)
        log.info(f"Wrote output to {out_path}")
    except Exception as e:
        alt = out_path.replace(".csv", "_final.csv")
        try:
            df_out.to_csv(alt, index=False)
            log.warning(f"Failed to write {out_path}; wrote to {alt}: {e}")
            out_path = alt
        except Exception as e2:
            log.error(f"Failed to write to both {out_path} and {alt}: {e2}")
            return df_out

    # Append to aggregate master CSV if enabled
    try:
        from jobspy.output_manager import append_to_master
        import settings as project_settings
        if getattr(project_settings, "ENABLE_AGGREGATE_OUTPUT", False):
            master = project_settings.AGGREGATE_CSV
            res = append_to_master(out_path, master, dedupe_on=getattr(project_settings, "AGGREGATE_DEDUPE_ON", None), keep_strategy=getattr(project_settings, "AGGREGATE_KEEP_STRATEGY", "latest"))
            log.info(f"Aggregate update: added={res['added']} skipped={res['skipped']} master_rows={res['master_rows']}")
    except Exception as e:
        log.error(f"Failed to append to aggregate master CSV: {e}")

    return df_out