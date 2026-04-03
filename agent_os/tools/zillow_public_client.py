"""
Zillow public data client — parcel lookup, assessment, and transaction history.

Uses the Zillow Bridge API (via Bridge Interactive), which is the supported
production path for Zillow data in RESO format.

Env vars required:
    BRIDGE_API_KEY       (same key as mls_bridge_client — Bridge hosts Zillow data)
    ZILLOW_ZWSID         (legacy Zillow Web Services ID, for fallback endpoints)

Bridge Zillow dataset endpoint:
    https://api.bridgedataoutput.com/api/v2/zestimates_bridge/...

RESO fields: https://bridgedataoutput.com/docs/explorer/
"""
from __future__ import annotations

import os
from datetime import date

import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from .reso_models import Property, PropertyAddress, Assessment, Transaction

load_dotenv()

_API_KEY  = os.getenv("BRIDGE_API_KEY", "")
_ZWSID    = os.getenv("ZILLOW_ZWSID", "")
_BASE     = "https://api.bridgedataoutput.com/api/v2"
_DATASET  = "zestimates_bridge"


# ── Low-level ────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _get(path: str, params: dict | None = None) -> dict:
    url = f"{_BASE}/{_DATASET}/{path}"
    r = requests.get(url, params={"access_token": _API_KEY, **(params or {})}, timeout=30)
    r.raise_for_status()
    return r.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _zwsid_get(endpoint: str, params: dict) -> dict:
    """Fallback: Zillow legacy XML API (returns XML, parsed minimally)."""
    import xml.etree.ElementTree as ET
    base = "https://www.zillow.com/webservice"
    r = requests.get(f"{base}/{endpoint}", params={"zws-id": _ZWSID, **params}, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    # Flatten into dict for easy consumption
    return {el.tag: el.text for el in root.iter() if el.text and el.text.strip()}


# ── Parcel lookup ────────────────────────────────────────────────────────────

def get_property_by_zpid(zpid: str) -> Property | None:
    """Fetch full property record by Zillow Property ID."""
    data = _get("properties", {"$filter": f"zpid eq '{zpid}'"})
    records = data.get("bundle", data.get("value", []))
    if not records:
        return None
    return _normalize_property(records[0])


def get_property_by_address(
    address: str,
    city_state_zip: str,
) -> Property | None:
    """
    Address lookup — resolves to a ZPID then fetches full record.
    address:        "123 Main St"
    city_state_zip: "Austin, TX 78701"
    """
    try:
        raw = _zwsid_get("GetSearchResults.htm", {
            "address": address,
            "citystatezip": city_state_zip,
        })
        zpid = raw.get("zpid")
        if zpid:
            return get_property_by_zpid(zpid)
    except Exception:
        pass

    # Bridge fallback: OData filter on address fields
    parts = address.strip().split(" ", 1)
    street_number = parts[0] if len(parts) > 1 else ""
    street_name   = parts[1] if len(parts) > 1 else address
    city = city_state_zip.split(",")[0].strip() if "," in city_state_zip else city_state_zip
    data = _get("properties", {
        "$filter": (
            f"StreetNumber eq '{street_number}' and "
            f"StreetName eq '{street_name}' and "
            f"City eq '{city}'"
        ),
        "$top": 1,
    })
    records = data.get("bundle", data.get("value", []))
    return _normalize_property(records[0]) if records else None


# ── Tax / assessment ─────────────────────────────────────────────────────────

def get_assessment(zpid: str) -> Assessment | None:
    """Return the most recent tax assessment record for a ZPID."""
    data = _get("assessments", {"$filter": f"zpid eq '{zpid}'", "$top": 1})
    records = data.get("bundle", data.get("value", []))
    if not records:
        return None
    r = records[0]
    return Assessment(
        zpid=zpid,
        parcel_number=r.get("ParcelNumber"),
        tax_year=r.get("TaxYear"),
        assessed_value=r.get("AssessedValue"),
        land_value=r.get("LandValue"),
        improvement_value=r.get("ImprovementValue"),
        tax_amount=r.get("TaxAmount"),
        exemptions=[e for e in r.get("Exemptions", "").split(",") if e],
    )


def get_assessment_history(zpid: str, years: int = 5) -> list[Assessment]:
    """Return up to N years of tax assessment records."""
    data = _get("assessments", {
        "$filter": f"zpid eq '{zpid}'",
        "$top": years,
        "$orderby": "TaxYear desc",
    })
    records = data.get("bundle", data.get("value", []))
    results = []
    for r in records:
        results.append(Assessment(
            zpid=zpid,
            parcel_number=r.get("ParcelNumber"),
            tax_year=r.get("TaxYear"),
            assessed_value=r.get("AssessedValue"),
            land_value=r.get("LandValue"),
            improvement_value=r.get("ImprovementValue"),
            tax_amount=r.get("TaxAmount"),
        ))
    return results


# ── Transaction history ───────────────────────────────────────────────────────

def get_transaction_history(zpid: str, limit: int = 10) -> list[Transaction]:
    """Return recorded sale transactions for a property."""
    data = _get("transactions", {
        "$filter": f"zpid eq '{zpid}'",
        "$top": limit,
        "$orderby": "SaleDate desc",
    })
    records = data.get("bundle", data.get("value", []))
    results = []
    for r in records:
        sale_date = r.get("SaleDate")
        if isinstance(sale_date, str) and sale_date:
            try:
                sale_date = date.fromisoformat(sale_date[:10])
            except ValueError:
                sale_date = None
        results.append(Transaction(
            zpid=zpid,
            parcel_number=r.get("ParcelNumber"),
            buyer_name=r.get("BuyerName"),
            seller_name=r.get("SellerName"),
            sale_price=r.get("SalePrice"),
            sale_date=sale_date,
            deed_type=r.get("DeedType"),
            recording_date=r.get("RecordingDate"),
            document_number=r.get("DocumentNumber"),
        ))
    return results


# ── Normalizer ───────────────────────────────────────────────────────────────

def _normalize_property(raw: dict) -> Property:
    addr = PropertyAddress(
        StreetNumber=raw.get("StreetNumber"),
        StreetName=raw.get("StreetName"),
        StreetSuffix=raw.get("StreetSuffix"),
        UnitNumber=raw.get("UnitNumber"),
        City=raw.get("City"),
        StateOrProvince=raw.get("StateOrProvince"),
        PostalCode=raw.get("PostalCode"),
        CountyOrParish=raw.get("CountyOrParish"),
    )
    return Property(
        zpid=raw.get("zpid") or raw.get("Zpid"),
        ParcelNumber=raw.get("ParcelNumber"),
        address=addr,
        Latitude=raw.get("Latitude"),
        Longitude=raw.get("Longitude"),
        LivingArea=raw.get("LivingArea"),
        LotSizeSquareFeet=raw.get("LotSizeSquareFeet"),
        LotSizeAcres=raw.get("LotSizeAcres"),
        BedroomsTotal=raw.get("BedroomsTotal"),
        BathroomsTotalInteger=raw.get("BathroomsTotalInteger"),
        YearBuilt=raw.get("YearBuilt"),
        TaxAnnualAmount=raw.get("TaxAnnualAmount"),
        TaxYear=raw.get("TaxYear"),
        assessed_value=raw.get("AssessedValue"),
        zestimate=raw.get("Zestimate") or raw.get("zestimate"),
        rent_zestimate=raw.get("RentZestimate") or raw.get("rentZestimate"),
        raw=raw,
        data_source="zillow_public",
    )
