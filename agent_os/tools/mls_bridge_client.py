"""
Bridge Interactive MLS client — RESO Web API (OData).

Docs:  https://bridgedataoutput.com/docs/explorer/
Base:  https://api.bridgedataoutput.com/api/v2/{dataset}/listings

Auth:  ?access_token=<BRIDGE_API_KEY>
       Dataset (server): your MLS dataset key, e.g. "actris" (Austin), "bright", etc.

Env vars required:
    BRIDGE_API_KEY
    BRIDGE_DATASET     (e.g. "actris")
"""
from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from .reso_models import (
    Property, PropertyAddress, Media, StandardStatus, PropertyType, PropertySubType
)

load_dotenv()

_API_KEY  = os.getenv("BRIDGE_API_KEY", "")
_DATASET  = os.getenv("BRIDGE_DATASET", "")
_BASE_URL = "https://api.bridgedataoutput.com/api/v2"


# ── Low-level HTTP ───────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _get(endpoint: str, params: dict | None = None) -> dict:
    url = f"{_BASE_URL}/{_DATASET}/{endpoint}"
    p = {"access_token": _API_KEY, **(params or {})}
    r = requests.get(url, params=p, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Normalizer ───────────────────────────────────────────────────────────────

def _normalize(raw: dict) -> Property:
    """Map a Bridge/RESO JSON record → Property model."""
    addr = PropertyAddress(
        StreetNumber=raw.get("StreetNumber"),
        StreetName=raw.get("StreetName"),
        StreetSuffix=raw.get("StreetSuffix"),
        StreetDirPrefix=raw.get("StreetDirPrefix"),
        StreetDirSuffix=raw.get("StreetDirSuffix"),
        UnitNumber=raw.get("UnitNumber"),
        City=raw.get("City"),
        StateOrProvince=raw.get("StateOrProvince"),
        PostalCode=raw.get("PostalCode"),
        CountyOrParish=raw.get("CountyOrParish"),
    )

    media = [
        Media(MediaURL=m.get("MediaURL"), Order=m.get("Order"), MediaKey=m.get("MediaKey"))
        for m in raw.get("Media", [])
    ]

    try:
        status = StandardStatus(raw.get("StandardStatus", ""))
    except ValueError:
        status = None

    try:
        prop_type = PropertyType(raw.get("PropertyType", ""))
    except ValueError:
        prop_type = None

    try:
        prop_sub = PropertySubType(raw.get("PropertySubType", ""))
    except ValueError:
        prop_sub = None

    return Property(
        ListingKey=raw.get("ListingKey"),
        ListingId=raw.get("ListingId"),
        StandardStatus=status,
        PropertyType=prop_type,
        PropertySubType=prop_sub,
        address=addr,
        Latitude=raw.get("Latitude"),
        Longitude=raw.get("Longitude"),
        ListPrice=raw.get("ListPrice"),
        OriginalListPrice=raw.get("OriginalListPrice"),
        ClosePrice=raw.get("ClosePrice"),
        ListingContractDate=raw.get("ListingContractDate"),
        CloseDate=raw.get("CloseDate"),
        DaysOnMarket=raw.get("DaysOnMarket"),
        CumulativeDaysOnMarket=raw.get("CumulativeDaysOnMarket"),
        LivingArea=raw.get("LivingArea"),
        LivingAreaUnits=raw.get("LivingAreaUnits"),
        LotSizeSquareFeet=raw.get("LotSizeSquareFeet"),
        LotSizeAcres=raw.get("LotSizeAcres"),
        BedroomsTotal=raw.get("BedroomsTotal"),
        BathroomsTotalInteger=raw.get("BathroomsTotalInteger"),
        BathroomsFull=raw.get("BathroomsFull"),
        BathroomsHalf=raw.get("BathroomsHalf"),
        GarageSpaces=raw.get("GarageSpaces"),
        YearBuilt=raw.get("YearBuilt"),
        SubdivisionName=raw.get("SubdivisionName"),
        MLSAreaMajor=raw.get("MLSAreaMajor"),
        ListAgentKey=raw.get("ListAgentKey"),
        ListAgentFullName=raw.get("ListAgentFullName"),
        ListOfficeKey=raw.get("ListOfficeKey"),
        ListOfficeName=raw.get("ListOfficeName"),
        AssociationFee=raw.get("AssociationFee"),
        AssociationFeeFrequency=raw.get("AssociationFeeFrequency"),
        TaxAnnualAmount=raw.get("TaxAnnualAmount"),
        TaxYear=raw.get("TaxYear"),
        PhotosCount=raw.get("PhotosCount"),
        media=media,
        raw=raw,
        data_source="bridge",
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_active_listings(
    city: str | None = None,
    postal_code: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_beds: int | None = None,
    min_sqft: float | None = None,
    property_type: str = "Residential",
    limit: int = 50,
    offset: int = 0,
) -> list[Property]:
    """Fetch active MLS listings with optional filters."""
    filters: list[str] = [
        f"StandardStatus eq 'Active'",
        f"PropertyType eq '{property_type}'",
    ]
    if city:
        filters.append(f"City eq '{city}'")
    if postal_code:
        filters.append(f"PostalCode eq '{postal_code}'")
    if min_price:
        filters.append(f"ListPrice ge {min_price}")
    if max_price:
        filters.append(f"ListPrice le {max_price}")
    if min_beds:
        filters.append(f"BedroomsTotal ge {min_beds}")
    if min_sqft:
        filters.append(f"LivingArea ge {min_sqft}")

    params = {
        "$filter":  " and ".join(filters),
        "$top":     limit,
        "$skip":    offset,
        "$orderby": "ListingContractDate desc",
        "$expand":  "Media",
    }
    data = _get("listings", params)
    return [_normalize(r) for r in data.get("value", [])]


def get_sold_listings(
    city: str | None = None,
    postal_code: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_beds: int | None = None,
    max_dom: int | None = None,
    limit: int = 50,
) -> list[Property]:
    """Fetch closed/sold listings for comp analysis."""
    filters = [
        "StandardStatus eq 'Closed'",
        "PropertyType eq 'Residential'",
    ]
    if city:
        filters.append(f"City eq '{city}'")
    if postal_code:
        filters.append(f"PostalCode eq '{postal_code}'")
    if min_price:
        filters.append(f"ClosePrice ge {min_price}")
    if max_price:
        filters.append(f"ClosePrice le {max_price}")
    if min_beds:
        filters.append(f"BedroomsTotal ge {min_beds}")
    if max_dom:
        filters.append(f"DaysOnMarket le {max_dom}")

    params = {
        "$filter":  " and ".join(filters),
        "$top":     limit,
        "$orderby": "CloseDate desc",
        "$expand":  "Media",
    }
    data = _get("listings", params)
    return [_normalize(r) for r in data.get("value", [])]


def get_listing(listing_key: str) -> Property | None:
    """Fetch a single listing by its RESO ListingKey."""
    data = _get(f"listings/{listing_key}", {"$expand": "Media"})
    if not data:
        return None
    # Single record or wrapped in value
    record = data if "ListingKey" in data else data.get("value", [{}])[0]
    return _normalize(record) if record else None


def search_by_address(
    street_number: str,
    street_name: str,
    city: str,
    state: str,
) -> list[Property]:
    """Search MLS for a specific address."""
    filters = [
        f"StreetNumber eq '{street_number}'",
        f"StreetName eq '{street_name}'",
        f"City eq '{city}'",
        f"StateOrProvince eq '{state}'",
    ]
    params = {
        "$filter":  " and ".join(filters),
        "$top":     5,
        "$expand":  "Media",
    }
    data = _get("listings", params)
    return [_normalize(r) for r in data.get("value", [])]


def get_price_reduced(
    city: str,
    days: int = 7,
    limit: int = 25,
) -> list[Property]:
    """Listings with a price reduction in the last N days."""
    params = {
        "$filter":  f"StandardStatus eq 'Active' and City eq '{city}'",
        "$top":     limit,
        "$orderby": "ListingContractDate desc",
        "$select":  (
            "ListingKey,ListingId,ListPrice,OriginalListPrice,"
            "StreetNumber,StreetName,City,PostalCode,"
            "BedroomsTotal,BathroomsTotalInteger,LivingArea"
        ),
    }
    data = _get("listings", params)
    records = data.get("value", [])
    # Filter locally to those with a price reduction
    return [
        _normalize(r) for r in records
        if r.get("OriginalListPrice") and r.get("ListPrice")
        and r["ListPrice"] < r["OriginalListPrice"]
    ]


def get_agent_listings(agent_key: str, status: str = "Active") -> list[Property]:
    """All active listings for a specific agent."""
    params = {
        "$filter":  f"ListAgentKey eq '{agent_key}' and StandardStatus eq '{status}'",
        "$top":     100,
        "$expand":  "Media",
    }
    data = _get("listings", params)
    return [_normalize(r) for r in data.get("value", [])]
