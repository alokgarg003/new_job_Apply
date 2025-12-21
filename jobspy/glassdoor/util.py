# jobspy/glassdoor/util.py
"""Utility helpers for the Glassdoor scraper – parsing salaries, locations and cursor logic."""

from __future__ import annotations

import json
import re
from typing import List, Optional, Tuple

import requests

# Custom Pydantic models that the package already defines.
from jobspy.model import Compensation, CompensationInterval, Location, JobType

# --------------------------------------------------------------------------- #
# 1️⃣  Salary parsing
# --------------------------------------------------------------------------- #

def parse_compensation(data: dict) -> Optional[Compensation]:
    """
    Convert Glassdoor’s raw salary JSON into a ``Compensation`` pydantic model.

    Parameters
    ----------
    data : dict
        Raw header dictionary that contains ``payPeriod`` and
        ``payPeriodAdjustedPay`` entries.

    Returns
    -------
    Optional[Compensation]
        ``None`` if the necessary keys are missing.
    """
    pay_period = data.get("payPeriod")
    adjusted_pay = data.get("payPeriodAdjustedPay")
    currency = data.get("payCurrency", "USD")

    if not pay_period or not adjusted_pay:
        return None

    # Map the API string to our enum
    if pay_period == "ANNUAL":
        interval = CompensationInterval.YEARLY
    else:
        interval = CompensationInterval.get_interval(pay_period)

    min_amount = int(adjusted_pay.get("p10", 0) // 1)
    max_amount = int(adjusted_pay.get("p90", 0) // 1)

    return Compensation(
        interval=interval,
        min_amount=min_amount,
        max_amount=max_amount,
        currency=currency,
    )

# --------------------------------------------------------------------------- #
# 2️⃣  Job‑type helper
# --------------------------------------------------------------------------- #

def get_job_type_enum(job_type_str: str) -> Optional[List[JobType]]:
    """
    Resolve a user provided string into the list of matching :class:`JobType` enums.

    Parameters
    ----------
    job_type_str : str
        Eg. ``"remote"``, ``"full_time"``, etc.

    Returns
    -------
    Optional[List[JobType]]
        ``None`` if nothing matches; otherwise a list containing the single
        matching enum.
    """
    for job_type in JobType:
        if job_type_str in job_type.value:
            return [job_type]
    return None

# --------------------------------------------------------------------------- #
# 3️⃣  Location parse
# --------------------------------------------------------------------------- #

def parse_location(location_name: str) -> Optional[Location]:
    """
    Convert a string such as ``"Berlin, Germany"`` into a ``Location`` model.
    
    The function keeps the logic simple – if the location contains a comma it
    splits on the first comma; otherwise it treats the whole string as a city.
    """
    if not location_name or location_name.lower() == "remote":
        return None

    city, _, state = location_name.partition(", ")
    return Location(city=city, state=state)

# --------------------------------------------------------------------------- #
# 4️⃣  Pagination cursor extraction
# --------------------------------------------------------------------------- #

def get_cursor_for_page(
    pagination_cursors: List[dict], page_num: int
) -> Optional[str]:
    """
    The Glassdoor GraphQL API returns a list of ``cursor`` objects.
    Find the cursor that belongs to ``page_num`` – it is then passed
    back as ``pageCursor`` for the next request.
    """
    for cursor_data in pagination_cursors:
        if cursor_data["pageNumber"] == page_num:
            return cursor_data["cursor"]
    return None