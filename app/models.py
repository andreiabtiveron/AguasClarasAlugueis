from typing import Literal

from pydantic import BaseModel, Field


InfraCategory = Literal["hospital", "school", "pharmacy", "market", "park"]


class Coordinates(BaseModel):
    lat: float
    lon: float


class Property(BaseModel):
    id: str
    title: str
    price: float
    area_m2: float | None = None
    bedrooms: int | None = None
    address: str | None = None
    url: str | None = None
    source: str
    coords: Coordinates


class InfrastructurePoint(BaseModel):
    id: str
    name: str
    category: InfraCategory
    coords: Coordinates
    source: str = "OpenStreetMap"


class AccessibilityScore(BaseModel):
    hospital: float = 0
    school: float = 0
    pharmacy: float = 0
    market: float = 0
    park: float = 0


class QualityProperty(Property):
    accessibility: AccessibilityScore
    iar: float = Field(ge=0, le=1)
    qv: float = Field(ge=0, le=1)
    nearest: dict[str, float]


class DashboardTopProperty(BaseModel):
    id: str
    title: str
    price: float
    qv: float
    iar: float
    price_score: float
    composite_score: float
    area_m2: float | None = None
    bedrooms: int | None = None
    source: str


class DashboardResponse(BaseModel):
    property_count: int
    average_qv: float
    top_value_properties: list[DashboardTopProperty]
    query_source: str
    query_description: str


class QualityResponse(BaseModel):
    provider: str
    property_source: str
    infrastructure_source: str
    graph_source: str
    center: Coordinates
    properties: list[QualityProperty]
    infrastructure: list[InfrastructurePoint]
    dashboard: DashboardResponse
    notes: list[str]


class GraphStatus(BaseModel):
    enabled: bool
    connected: bool
    uri: str
    database: str
    message: str


class GraphSummary(BaseModel):
    enabled: bool
    connected: bool
    properties: int = 0
    amenities: int = 0
    relationships: int = 0
    avg_qv: float | None = None
    top_properties: list[dict] = []
    message: str
