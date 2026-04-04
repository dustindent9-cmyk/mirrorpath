"""
Zillow reporting client — traffic, leads, and listing performance.

Used by listing agents to track:
  - Listing page views / favorites / shares
  - Lead volume and source breakdown
  - Inquiry contact info
  - Premier Agent performance

Env vars:
    ZILLOW_CLIENT_ID        (OAuth2 client ID for Zillow Tech Connect)
    ZILLOW_CLIENT_SECRET    (OAuth2 client secret)
    ZILLOW_REFRESH_TOKEN    (long-lived refresh token from OAuth handshake)

Zillow Tech Connect API:
    https://www.zillow.com/tech-connect/docs/
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

_CLIENT_ID     = os.getenv("ZILLOW_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("ZILLOW_CLIENT_SECRET", "")
_REFRESH_TOKEN = os.getenv("ZILLOW_REFRESH_TOKEN", "")
_BASE          = "https://api.zillow.com/webservice"
_TC_BASE       = "https://techconnect.zillow.com/api"

_access_token: str = ""


# ── OAuth token management ───────────────────────────────────────────────────

def _refresh_access_token() -> str:
    global _access_token
    r = requests.post(
        "https://api.zillow.com/oauth/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": _REFRESH_TOKEN,
            "client_id":     _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
        },
        timeout=30,
    )
    r.raise_for_status()
    _access_token = r.json()["access_token"]
    return _access_token


def _auth_headers() -> dict:
    global _access_token
    if not _access_token:
        _refresh_access_token()
    return {"Authorization": f"Bearer {_access_token}"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _get(path: str, params: dict | None = None) -> dict:
    r = requests.get(
        f"{_TC_BASE}/{path}",
        headers=_auth_headers(),
        params=params or {},
        timeout=30,
    )
    if r.status_code == 401:
        _refresh_access_token()
        r = requests.get(
            f"{_TC_BASE}/{path}",
            headers=_auth_headers(),
            params=params or {},
            timeout=30,
        )
    r.raise_for_status()
    return r.json()


# ── Value objects ─────────────────────────────────────────────────────────────

@dataclass
class ListingTraffic:
    zpid:          str
    listing_id:    str | None
    period_start:  date | None
    period_end:    date | None
    page_views:    int = 0
    unique_views:  int = 0
    saves:         int = 0
    shares:        int = 0
    contact_clicks: int = 0
    mobile_views:  int = 0


@dataclass
class Lead:
    lead_id:        str
    zpid:           str | None
    listing_id:     str | None
    first_name:     str | None
    last_name:      str | None
    email:          str | None
    phone:          str | None
    message:        str | None
    lead_type:      str | None       # "buyer", "seller", "renter"
    source:         str | None       # "zillow", "trulia", "hotpads"
    created_at:     str | None
    assigned_agent: str | None


@dataclass
class AgentPerformance:
    agent_id:         str
    period_start:     date | None
    period_end:       date | None
    total_leads:      int = 0
    converted_leads:  int = 0
    total_views:      int = 0
    avg_response_sec: float | None = None
    rating:           float | None = None
    review_count:     int = 0


# ── Traffic reporting ─────────────────────────────────────────────────────────

def get_listing_traffic(
    zpid: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ListingTraffic:
    """
    Page views, saves, and contact clicks for a listing.
    Defaults to the last 30 days.
    """
    end   = end_date   or date.today()
    start = start_date or (end - timedelta(days=30))
    data  = _get("listing/stats", {
        "zpid":       zpid,
        "startDate":  start.isoformat(),
        "endDate":    end.isoformat(),
    })
    return ListingTraffic(
        zpid=zpid,
        listing_id=data.get("listingId"),
        period_start=start,
        period_end=end,
        page_views=data.get("pageViews", 0),
        unique_views=data.get("uniqueViews", 0),
        saves=data.get("saves", 0),
        shares=data.get("shares", 0),
        contact_clicks=data.get("contactClicks", 0),
        mobile_views=data.get("mobileViews", 0),
    )


def get_traffic_by_agent(
    agent_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ListingTraffic]:
    """Traffic across all of an agent's active listings."""
    end   = end_date   or date.today()
    start = start_date or (end - timedelta(days=30))
    data  = _get("agent/listings/stats", {
        "agentId":   agent_id,
        "startDate": start.isoformat(),
        "endDate":   end.isoformat(),
    })
    results = []
    for item in data.get("listings", []):
        results.append(ListingTraffic(
            zpid=item.get("zpid", ""),
            listing_id=item.get("listingId"),
            period_start=start,
            period_end=end,
            page_views=item.get("pageViews", 0),
            unique_views=item.get("uniqueViews", 0),
            saves=item.get("saves", 0),
            shares=item.get("shares", 0),
            contact_clicks=item.get("contactClicks", 0),
        ))
    return results


# ── Lead reporting ────────────────────────────────────────────────────────────

def get_leads(
    agent_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
) -> list[Lead]:
    """Leads assigned to an agent in a date range."""
    end   = end_date   or date.today()
    start = start_date or (end - timedelta(days=30))
    data  = _get("agent/leads", {
        "agentId":   agent_id,
        "startDate": start.isoformat(),
        "endDate":   end.isoformat(),
        "limit":     limit,
    })
    results = []
    for item in data.get("leads", []):
        results.append(Lead(
            lead_id=item.get("leadId", ""),
            zpid=item.get("zpid"),
            listing_id=item.get("listingId"),
            first_name=item.get("firstName"),
            last_name=item.get("lastName"),
            email=item.get("email"),
            phone=item.get("phone"),
            message=item.get("message"),
            lead_type=item.get("leadType"),
            source=item.get("source"),
            created_at=item.get("createdAt"),
            assigned_agent=item.get("assignedAgent"),
        ))
    return results


def get_leads_by_listing(zpid: str, limit: int = 25) -> list[Lead]:
    """All leads generated by a specific listing."""
    data = _get("listing/leads", {"zpid": zpid, "limit": limit})
    results = []
    for item in data.get("leads", []):
        results.append(Lead(
            lead_id=item.get("leadId", ""),
            zpid=zpid,
            listing_id=item.get("listingId"),
            first_name=item.get("firstName"),
            last_name=item.get("lastName"),
            email=item.get("email"),
            phone=item.get("phone"),
            message=item.get("message"),
            lead_type=item.get("leadType"),
            source=item.get("source"),
            created_at=item.get("createdAt"),
            assigned_agent=item.get("assignedAgent"),
        ))
    return results


# ── Agent performance ─────────────────────────────────────────────────────────

def get_agent_performance(
    agent_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AgentPerformance:
    """Aggregate lead, traffic, and rating data for an agent."""
    end   = end_date   or date.today()
    start = start_date or (end - timedelta(days=30))
    data  = _get("agent/performance", {
        "agentId":   agent_id,
        "startDate": start.isoformat(),
        "endDate":   end.isoformat(),
    })
    return AgentPerformance(
        agent_id=agent_id,
        period_start=start,
        period_end=end,
        total_leads=data.get("totalLeads", 0),
        converted_leads=data.get("convertedLeads", 0),
        total_views=data.get("totalViews", 0),
        avg_response_sec=data.get("avgResponseTimeSec"),
        rating=data.get("rating"),
        review_count=data.get("reviewCount", 0),
    )
