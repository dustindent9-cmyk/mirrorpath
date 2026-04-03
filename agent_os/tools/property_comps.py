"""
Property comps engine — pulls sold + active comps, scores by similarity.

Sources:
  - MLS Bridge (sold + active)
  - Zillow public (Zestimate comparison)

Usage:
    from tools.property_comps import run_comps, CompsRequest

    result = run_comps(CompsRequest(
        address="123 Main St",
        city="Austin",
        state="TX",
        postal_code="78701",
        bedrooms=3,
        bathrooms=2.0,
        living_area=1800,
        list_price=450000,
        radius_miles=1.0,
    ))
    for comp in result.sold_comps:
        print(comp.address, comp.close_price, comp.similarity_score)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from .reso_models import Comp, Property
from . import mls_bridge_client as bridge
from . import zillow_public_client as zillow_pub
from . import zillow_zestimate_client as zestimate


# ── Request / result models ──────────────────────────────────────────────────

@dataclass
class CompsRequest:
    # Subject property
    address:       str
    city:          str
    state:         str
    postal_code:   str
    bedrooms:      int
    bathrooms:     float
    living_area:   float          # sq ft
    list_price:    float | None = None
    year_built:    int | None = None
    latitude:      float | None = None
    longitude:     float | None = None
    zpid:          str | None = None

    # Search parameters
    radius_miles:  float = 1.0
    sold_months:   int   = 6       # look back N months for sold comps
    min_comps:     int   = 3
    max_comps:     int   = 10
    bed_tolerance: int   = 1       # ±N bedrooms
    bath_tolerance: float = 1.0    # ±N bathrooms
    sqft_tolerance: float = 0.25   # ±25%


@dataclass
class CompsResult:
    subject_address:  str
    subject_zestimate: float | None = None
    sold_comps:        list[Comp] = field(default_factory=list)
    active_comps:      list[Comp] = field(default_factory=list)
    suggested_price:   float | None = None
    price_per_sqft:    float | None = None
    comp_count:        int = 0
    median_close_price: float | None = None
    median_price_psf:   float | None = None
    notes:             list[str] = field(default_factory=list)


# ── Distance calculation ─────────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance in miles between two lat/lon points."""
    R = 3958.8  # Earth radius, miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Similarity scoring ───────────────────────────────────────────────────────

def _similarity_score(subject: CompsRequest, comp: Property) -> float:
    """
    Score a comp against the subject on 0.0–1.0.

    Dimensions (weighted):
      beds match       25%
      baths match      20%
      sqft proximity   25%
      distance         20%
      year_built prox  10%
    """
    score = 0.0

    # Beds
    if comp.bedrooms is not None:
        bed_diff = abs(comp.bedrooms - subject.bedrooms)
        score += 0.25 * max(0, 1 - bed_diff / 2)

    # Baths
    if comp.bathrooms_total is not None:
        bath_diff = abs(comp.bathrooms_total - subject.bathrooms)
        score += 0.20 * max(0, 1 - bath_diff / 2)

    # Sqft
    if comp.living_area and subject.living_area:
        sqft_ratio = min(comp.living_area, subject.living_area) / max(
            comp.living_area, subject.living_area
        )
        score += 0.25 * sqft_ratio

    # Distance
    if comp.distance_miles is not None:
        dist_score = max(0, 1 - comp.distance_miles / max(subject.radius_miles, 0.1))
        score += 0.20 * dist_score
    else:
        score += 0.10  # partial credit if distance unknown

    # Year built
    if comp.year_built and subject.year_built:
        yr_diff = abs(comp.year_built - subject.year_built)
        score += 0.10 * max(0, 1 - yr_diff / 20)

    return round(min(score, 1.0), 3)


# ── Filtering helpers ─────────────────────────────────────────────────────────

def _within_tolerance(subject: CompsRequest, prop: Property) -> bool:
    if prop.bedrooms is not None:
        if abs(prop.bedrooms - subject.bedrooms) > subject.bed_tolerance:
            return False
    if prop.bathrooms_total is not None:
        if abs(prop.bathrooms_total - subject.bathrooms) > subject.bath_tolerance:
            return False
    if prop.living_area and subject.living_area:
        ratio = prop.living_area / subject.living_area
        if not (1 - subject.sqft_tolerance <= ratio <= 1 + subject.sqft_tolerance):
            return False
    return True


def _attach_distance(subject: CompsRequest, props: list[Property]) -> None:
    """Add distance_miles to any prop that has lat/lon and subject has lat/lon."""
    if not (subject.latitude and subject.longitude):
        return
    for p in props:
        if p.latitude and p.longitude:
            p.distance_miles = round(
                _haversine(subject.latitude, subject.longitude, p.latitude, p.longitude), 3
            )


# ── Comp-to-lightweight mapper ────────────────────────────────────────────────

def _to_comp(prop: Property, score: float) -> Comp:
    addr_str = prop.address.one_line if prop.address else str(prop.listing_key or "")
    return Comp(
        listing_key=prop.listing_key,
        address=addr_str,
        status=prop.standard_status.value if prop.standard_status else None,
        close_price=prop.close_price,
        list_price=prop.list_price,
        price_per_sqft=prop.price_per_sqft,
        living_area=prop.living_area,
        bedrooms=prop.bedrooms,
        bathrooms_total=prop.bathrooms_total,
        year_built=prop.year_built,
        close_date=prop.close_date,
        days_on_market=prop.days_on_market,
        distance_miles=getattr(prop, "distance_miles", None),
        similarity_score=score,
        data_source=prop.data_source,
    )


# ── Statistics ────────────────────────────────────────────────────────────────

def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _suggested_price(comps: list[Comp], living_area: float) -> tuple[float | None, float | None]:
    """
    Weighted average price/sqft from top comps → suggested list price.
    Returns (suggested_price, price_per_sqft).
    """
    if not comps:
        return None, None
    psf_values = [
        (c.price_per_sqft, c.similarity_score or 0)
        for c in comps
        if c.price_per_sqft and c.price_per_sqft > 0
    ]
    if not psf_values:
        return None, None
    total_weight = sum(w for _, w in psf_values)
    if total_weight == 0:
        return None, None
    weighted_psf = sum(psf * w for psf, w in psf_values) / total_weight
    return round(weighted_psf * living_area, 0), round(weighted_psf, 2)


# ── Main entry point ─────────────────────────────────────────────────────────

def run_comps(req: CompsRequest) -> CompsResult:
    """
    Pull sold and active comps for a subject property.

    Steps:
      1. Fetch sold comps from MLS (last N months, same ZIP/city)
      2. Fetch active comps from MLS
      3. Optionally enrich with Zillow Zestimate on subject
      4. Filter by tolerance (beds/baths/sqft)
      5. Attach distance (if lat/lon available)
      6. Score by similarity
      7. Sort, cap at max_comps, compute price statistics
    """
    result = CompsResult(subject_address=f"{req.address}, {req.city}, {req.state} {req.postal_code}")
    notes: list[str] = []

    # ── Zestimate on subject (optional enrichment) ─────────────────────────
    if req.zpid:
        try:
            z = zestimate.get_zestimate(req.zpid)
            if z:
                result.subject_zestimate = z.amount
        except Exception:
            notes.append("Zestimate unavailable — Zillow API not configured")

    # ── Sold comps ──────────────────────────────────────────────────────────
    sold_raw: list[Property] = []
    try:
        sold_raw = bridge.get_sold_listings(
            city=req.city,
            postal_code=req.postal_code,
            min_beds=max(0, req.bedrooms - req.bed_tolerance),
            limit=50,
        )
        _attach_distance(req, sold_raw)
    except Exception as exc:
        notes.append(f"MLS sold lookup failed: {exc}")

    sold_filtered = [p for p in sold_raw if _within_tolerance(req, p)]
    # Radius filter
    if req.latitude and req.longitude:
        sold_filtered = [
            p for p in sold_filtered
            if getattr(p, "distance_miles", 0) is None
            or getattr(p, "distance_miles", 0) <= req.radius_miles
        ]
    sold_scored = sorted(
        [(_similarity_score(req, p), p) for p in sold_filtered],
        reverse=True,
    )
    result.sold_comps = [
        _to_comp(p, s) for s, p in sold_scored[:req.max_comps]
    ]

    # ── Active comps ────────────────────────────────────────────────────────
    active_raw: list[Property] = []
    try:
        active_raw = bridge.get_active_listings(
            city=req.city,
            postal_code=req.postal_code,
            min_beds=max(0, req.bedrooms - req.bed_tolerance),
            limit=30,
        )
        _attach_distance(req, active_raw)
    except Exception as exc:
        notes.append(f"MLS active lookup failed: {exc}")

    active_filtered = [p for p in active_raw if _within_tolerance(req, p)]
    active_scored = sorted(
        [(_similarity_score(req, p), p) for p in active_filtered],
        reverse=True,
    )
    result.active_comps = [
        _to_comp(p, s) for s, p in active_scored[:req.max_comps]
    ]

    # ── Statistics ──────────────────────────────────────────────────────────
    close_prices = [c.close_price for c in result.sold_comps if c.close_price]
    psf_values   = [c.price_per_sqft for c in result.sold_comps if c.price_per_sqft]

    result.comp_count          = len(result.sold_comps)
    result.median_close_price  = _median(close_prices)
    result.median_price_psf    = _median(psf_values)
    result.suggested_price, result.price_per_sqft = _suggested_price(
        result.sold_comps, req.living_area
    )

    if result.comp_count < req.min_comps:
        notes.append(
            f"Only {result.comp_count} sold comps found (wanted {req.min_comps}) — "
            "consider expanding ZIP, radius, or tolerance."
        )

    result.notes = notes
    return result
