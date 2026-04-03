"""
Zillow Zestimate client — valuation endpoints.

Sources (in order of preference):
  1. Bridge Zillow API  — full Zestimate history + confidence range
  2. Zillow legacy ZWSID — GetZestimate.htm (XML, limited data)

Env vars:
    BRIDGE_API_KEY
    ZILLOW_ZWSID      (optional fallback)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

_API_KEY = os.getenv("BRIDGE_API_KEY", "")
_ZWSID   = os.getenv("ZILLOW_ZWSID", "")
_BASE    = "https://api.bridgedataoutput.com/api/v2"
_DATASET = "zestimates_bridge"


# ── Value objects ─────────────────────────────────────────────────────────────

@dataclass
class Zestimate:
    zpid:             str
    amount:           float | None
    low:              float | None     # 30-day confidence range low
    high:             float | None     # 30-day confidence range high
    last_updated:     date | None
    value_change_30d: float | None     # $ change in last 30 days
    percentile:       float | None     # 0–100, neighborhood percentile


@dataclass
class RentZestimate:
    zpid:         str
    amount:       float | None
    low:          float | None
    high:         float | None
    last_updated: date | None


@dataclass
class ZestimateHistory:
    zpid:   str
    points: list[dict]  # [{date, value, rent_value}]


# ── Low-level ────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _get(path: str, params: dict | None = None) -> dict:
    url = f"{_BASE}/{_DATASET}/{path}"
    r = requests.get(url, params={"access_token": _API_KEY, **(params or {})}, timeout=30)
    r.raise_for_status()
    return r.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _zwsid_zestimate(zpid: str) -> dict:
    """Legacy Zillow XML Zestimate — returns a minimal dict."""
    import xml.etree.ElementTree as ET
    r = requests.get(
        "https://www.zillow.com/webservice/GetZestimate.htm",
        params={"zws-id": _ZWSID, "zpid": zpid},
        timeout=30,
    )
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return {el.tag: el.text for el in root.iter() if el.text and el.text.strip()}


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except ValueError:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_zestimate(zpid: str) -> Zestimate | None:
    """Current Zestimate with confidence range."""
    try:
        data = _get("zestimates", {"$filter": f"zpid eq '{zpid}'", "$top": 1})
        records = data.get("bundle", data.get("value", []))
        if records:
            r = records[0]
            return Zestimate(
                zpid=zpid,
                amount=r.get("Zestimate") or r.get("zestimate"),
                low=r.get("ZestimateLow") or r.get("valuationRangeLow"),
                high=r.get("ZestimateHigh") or r.get("valuationRangeHigh"),
                last_updated=_parse_date(r.get("ZestimateLastUpdated")),
                value_change_30d=r.get("ZestimateValueChange30Day"),
                percentile=r.get("ZestimatePercentile"),
            )
    except Exception:
        pass

    # Fallback to legacy ZWSID
    if _ZWSID:
        try:
            raw = _zwsid_zestimate(zpid)
            return Zestimate(
                zpid=zpid,
                amount=float(raw["amount"]) if raw.get("amount") else None,
                low=float(raw["low"]) if raw.get("low") else None,
                high=float(raw["high"]) if raw.get("high") else None,
                last_updated=_parse_date(raw.get("last-updated")),
                value_change_30d=float(raw["valueChange"]) if raw.get("valueChange") else None,
                percentile=float(raw["percentile"]) if raw.get("percentile") else None,
            )
        except Exception:
            pass
    return None


def get_rent_zestimate(zpid: str) -> RentZestimate | None:
    """Current Rent Zestimate with confidence range."""
    try:
        data = _get("rentzestimates", {"$filter": f"zpid eq '{zpid}'", "$top": 1})
        records = data.get("bundle", data.get("value", []))
        if records:
            r = records[0]
            return RentZestimate(
                zpid=zpid,
                amount=r.get("RentZestimate"),
                low=r.get("RentZestimateLow"),
                high=r.get("RentZestimateHigh"),
                last_updated=_parse_date(r.get("RentZestimateLastUpdated")),
            )
    except Exception:
        pass
    return None


def get_zestimate_history(zpid: str, months: int = 24) -> ZestimateHistory:
    """
    Monthly Zestimate history for the last N months.
    Points: [{date, value, rent_value}]
    """
    data = _get("zestimatehistory", {
        "$filter": f"zpid eq '{zpid}'",
        "$top": months,
        "$orderby": "Date desc",
    })
    records = data.get("bundle", data.get("value", []))
    points = []
    for r in records:
        points.append({
            "date":        r.get("Date"),
            "value":       r.get("Zestimate"),
            "rent_value":  r.get("RentZestimate"),
        })
    return ZestimateHistory(zpid=zpid, points=points)


def get_zestimates_by_zip(
    postal_code: str,
    limit: int = 100,
) -> list[dict]:
    """
    All current Zestimates within a ZIP code.
    Returns raw list of {zpid, zestimate, rentZestimate} dicts.
    """
    data = _get("zestimates", {
        "$filter": f"PostalCode eq '{postal_code}'",
        "$top": limit,
        "$select": "zpid,Zestimate,RentZestimate,PostalCode",
    })
    return data.get("bundle", data.get("value", []))


def get_neighborhood_stats(postal_code: str) -> dict:
    """
    Aggregate Zestimate stats for a ZIP: median, avg, min, max.
    Computed locally from get_zestimates_by_zip().
    """
    records = get_zestimates_by_zip(postal_code, limit=200)
    values = [
        r["Zestimate"] for r in records
        if r.get("Zestimate") and float(r["Zestimate"]) > 0
    ]
    if not values:
        return {"postal_code": postal_code, "count": 0}
    values_sorted = sorted(values)
    n = len(values_sorted)
    return {
        "postal_code": postal_code,
        "count":       n,
        "median":      values_sorted[n // 2],
        "mean":        round(sum(values) / n, 0),
        "min":         values_sorted[0],
        "max":         values_sorted[-1],
        "p25":         values_sorted[n // 4],
        "p75":         values_sorted[(3 * n) // 4],
    }
