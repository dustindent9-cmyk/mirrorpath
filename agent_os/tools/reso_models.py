"""
RESO-normalized property model — shared across all data sources.

Field names follow RESO Data Dictionary 2.0 where possible so that
Bridge MLS data, Zillow data, and comps can be compared in one schema.

https://www.reso.org/data-dictionary/
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class StandardStatus(str, Enum):
    ACTIVE             = "Active"
    ACTIVE_UNDER_CONTRACT = "Active Under Contract"
    PENDING            = "Pending"
    CLOSED             = "Closed"
    EXPIRED            = "Expired"
    WITHDRAWN          = "Withdrawn"
    CANCELLED          = "Cancelled"
    HOLD               = "Hold"
    COMING_SOON        = "Coming Soon"
    DELETE             = "Delete"


class PropertyType(str, Enum):
    RESIDENTIAL        = "Residential"
    RESIDENTIAL_INCOME = "ResidentialIncome"
    RESIDENTIAL_LEASE  = "ResidentialLease"
    LAND               = "Land"
    COMMERCIAL_SALE    = "CommercialSale"
    COMMERCIAL_LEASE   = "CommercialLease"
    BUSINESS_OPPOR     = "BusinessOpportunity"
    FARM               = "Farm"


class PropertySubType(str, Enum):
    SINGLE_FAMILY      = "Single Family Residence"
    CONDO              = "Condominium"
    TOWNHOUSE          = "Townhouse"
    MULTI_FAMILY_2_4   = "2 to 4 Units"
    MANUFACTURED       = "Manufactured Home"
    MOBILE_HOME        = "Mobile Home"
    DUPLEX             = "Duplex"
    TRIPLEX            = "Triplex"
    QUADRUPLEX         = "Quadruplex"
    APARTMENT          = "Apartment"
    OTHER              = "Other"


# ── Address sub-model ────────────────────────────────────────────────────────

class PropertyAddress(BaseModel):
    street_number:      str | None = Field(None, alias="StreetNumber")
    street_name:        str | None = Field(None, alias="StreetName")
    street_suffix:      str | None = Field(None, alias="StreetSuffix")
    street_dir_prefix:  str | None = Field(None, alias="StreetDirPrefix")
    street_dir_suffix:  str | None = Field(None, alias="StreetDirSuffix")
    unit_number:        str | None = Field(None, alias="UnitNumber")
    city:               str | None = Field(None, alias="City")
    state:              str | None = Field(None, alias="StateOrProvince")
    postal_code:        str | None = Field(None, alias="PostalCode")
    county:             str | None = Field(None, alias="CountyOrParish")

    model_config = {"populate_by_name": True}

    @property
    def full_street(self) -> str:
        parts = [
            self.street_number,
            self.street_dir_prefix,
            self.street_name,
            self.street_suffix,
            self.street_dir_suffix,
        ]
        street = " ".join(p for p in parts if p)
        if self.unit_number:
            street += f" #{self.unit_number}"
        return street

    @property
    def one_line(self) -> str:
        return f"{self.full_street}, {self.city}, {self.state} {self.postal_code}"


# ── Media ────────────────────────────────────────────────────────────────────

class Media(BaseModel):
    media_key:     str | None = Field(None, alias="MediaKey")
    media_url:     str | None = Field(None, alias="MediaURL")
    order:         int | None = Field(None, alias="Order")
    media_type:    str | None = Field(None, alias="MediaType")
    description:   str | None = Field(None, alias="MediaModificationTimestamp")

    model_config = {"populate_by_name": True}


# ── Core listing model ───────────────────────────────────────────────────────

class Property(BaseModel):
    # Identifiers
    listing_key:        str | None = Field(None, alias="ListingKey")
    listing_id:         str | None = Field(None, alias="ListingId")
    parcel_number:      str | None = Field(None, alias="ParcelNumber")
    zpid:               str | None = Field(None, description="Zillow Property ID")

    # Status
    standard_status:    StandardStatus | None = Field(None, alias="StandardStatus")
    mls_status:         str | None = Field(None, alias="MlsStatus")

    # Property type
    property_type:      PropertyType | None = Field(None, alias="PropertyType")
    property_sub_type:  PropertySubType | None = Field(None, alias="PropertySubType")

    # Address
    address:            PropertyAddress | None = None
    latitude:           float | None = Field(None, alias="Latitude")
    longitude:          float | None = Field(None, alias="Longitude")

    # Price
    list_price:         float | None = Field(None, alias="ListPrice")
    original_list_price: float | None = Field(None, alias="OriginalListPrice")
    close_price:        float | None = Field(None, alias="ClosePrice")
    price_per_sqft:     float | None = None  # computed

    # Dates
    listing_contract_date: date | None = Field(None, alias="ListingContractDate")
    close_date:         date | None = Field(None, alias="CloseDate")
    days_on_market:     int | None = Field(None, alias="DaysOnMarket")
    cumulative_dom:     int | None = Field(None, alias="CumulativeDaysOnMarket")

    # Size
    living_area:        float | None = Field(None, alias="LivingArea")
    living_area_units:  str | None = Field(None, alias="LivingAreaUnits")
    lot_size_sqft:      float | None = Field(None, alias="LotSizeSquareFeet")
    lot_size_acres:     float | None = Field(None, alias="LotSizeAcres")
    above_grade_sqft:   float | None = Field(None, alias="AboveGradeFinishedArea")

    # Rooms
    bedrooms:           int | None = Field(None, alias="BedroomsTotal")
    bathrooms_total:    float | None = Field(None, alias="BathroomsTotalInteger")
    bathrooms_full:     int | None = Field(None, alias="BathroomsFull")
    bathrooms_half:     int | None = Field(None, alias="BathroomsHalf")
    stories:            float | None = Field(None, alias="StoriesTotal")
    garage_spaces:      float | None = Field(None, alias="GarageSpaces")

    # Construction
    year_built:         int | None = Field(None, alias="YearBuilt")
    new_construction:   bool | None = Field(None, alias="NewConstructionYN")
    architecture_style: str | None = Field(None, alias="ArchitecturalStyle")

    # Location
    subdivision:        str | None = Field(None, alias="SubdivisionName")
    mls_area_major:     str | None = Field(None, alias="MLSAreaMajor")
    school_district:    str | None = Field(None, alias="ElementarySchoolDistrict")
    zoning:             str | None = Field(None, alias="Zoning")

    # Agent / office
    list_agent_key:     str | None = Field(None, alias="ListAgentKey")
    list_agent_name:    str | None = Field(None, alias="ListAgentFullName")
    list_office_key:    str | None = Field(None, alias="ListOfficeKey")
    list_office_name:   str | None = Field(None, alias="ListOfficeName")

    # HOA
    association_fee:    float | None = Field(None, alias="AssociationFee")
    association_fee_freq: str | None = Field(None, alias="AssociationFeeFrequency")

    # Tax / assessment
    tax_annual_amount:  float | None = Field(None, alias="TaxAnnualAmount")
    tax_year:           int | None = Field(None, alias="TaxYear")
    assessed_value:     float | None = None

    # Valuation
    zestimate:          float | None = None
    rent_zestimate:     float | None = None

    # Media
    photos_count:       int | None = Field(None, alias="PhotosCount")
    media:              list[Media] = Field(default_factory=list)

    # Raw data passthrough
    raw:                dict[str, Any] = Field(default_factory=dict, exclude=True)

    # Source tracking
    data_source:        str | None = None  # "bridge", "zillow", "public"

    model_config = {"populate_by_name": True}

    def model_post_init(self, __context: Any) -> None:
        if self.close_price and self.living_area and self.living_area > 0:
            self.price_per_sqft = round(self.close_price / self.living_area, 2)
        elif self.list_price and self.living_area and self.living_area > 0:
            self.price_per_sqft = round(self.list_price / self.living_area, 2)


# ── Transaction history ──────────────────────────────────────────────────────

class Transaction(BaseModel):
    zpid:           str | None = None
    parcel_number:  str | None = None
    buyer_name:     str | None = None
    seller_name:    str | None = None
    sale_price:     float | None = None
    sale_date:      date | None = None
    deed_type:      str | None = None
    recording_date: date | None = None
    document_number: str | None = None


# ── Tax / assessment record ──────────────────────────────────────────────────

class Assessment(BaseModel):
    zpid:                str | None = None
    parcel_number:       str | None = None
    tax_year:            int | None = None
    assessed_value:      float | None = None
    land_value:          float | None = None
    improvement_value:   float | None = None
    tax_amount:          float | None = None
    exemptions:          list[str] = Field(default_factory=list)


# ── Comp record (lightweight, for ranking) ───────────────────────────────────

class Comp(BaseModel):
    listing_key:        str | None = None
    address:            str | None = None
    status:             str | None = None
    close_price:        float | None = None
    list_price:         float | None = None
    price_per_sqft:     float | None = None
    living_area:        float | None = None
    bedrooms:           int | None = None
    bathrooms_total:    float | None = None
    year_built:         int | None = None
    close_date:         date | None = None
    days_on_market:     int | None = None
    distance_miles:     float | None = None
    similarity_score:   float | None = None  # 0.0–1.0, set by property_comps.py
    data_source:        str | None = None
